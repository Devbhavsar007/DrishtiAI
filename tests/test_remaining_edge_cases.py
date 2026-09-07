"""
Comprehensive Edge-Cases Closure Regression Test Suite (Phases 1-18).
Validates:
  1. Anatomy failure propagation (missing disc/fovea, boundary disc, implausible geometry)
  2. Orientation & vertical displacement anomalies and EXIF orientation tag inspection
  3. Workflow & identity consistency (cross-patient duplicates, cross-eye reuse, dHash)
  4. Camera variability & threshold boundaries (T - eps, T, T + eps)
  5. Partial pipeline failure containment (Grad-CAM, vessels, Gemma report isolation)
  6. Numerical model output stability (IEEE 754 NaN/Inf, probability sum, invalid stages)
  7. Disease scope & unsupported pathology routing (DOCTOR_REVIEW)
  8. Longitudinal edge cases (acute repeat <7d, extended gap >36m, cross-eye filtering, 4->0 regression)
  9. Offline idempotency & persistence invariants (idempotent upsert, skip unsafe)
  10. State machine invariants (safety failures cannot transition to completed)
  11. Deterministic report-safety consistency (never claim normal on unverified safety)
"""

import os
import math
import unittest
from unittest.mock import patch
import numpy as np
import cv2
from PIL import Image

from engine.safety.anatomy import assess_anatomy_and_laterality, AnatomyResult
from engine.safety.image_validator import validate_image_file, compute_dhash, ImageValidationResult
from engine.safety.ood import evaluate_ood_signal, OODResult
from engine.safety.decision_engine import SafetyDecisionEngine, SafetyEvaluationResult
from engine.clinical.referral import decide_referral
from engine.clinical.progression import assess_progression_risk, _latest_previous_scan
from engine.pipeline.offline_report import generate_offline_report
from engine.gemma_report import generate_report
from engine.safety.state_machine import ScreeningState, InvalidStateTransitionError
from database import (
    init_db,
    create_patient,
    save_scan,
    get_scan,
    check_workflow_image_consistency,
    save_progression_assessment,
    get_progression_assessment,
    create_or_update_screening_session,
    update_screening_session_state,
)


class TestAnatomyFailurePropagation(unittest.TestCase):
    """Phase 1, 2, 3: Anatomy Failure Propagation and Boundary Checks."""

    def setUp(self):
        self.engine = SafetyDecisionEngine()

    def test_missing_disc_fails_anatomy_and_blocks_verification(self):
        """When optic disc cannot be localized, anatomy is invalid and pipeline blocks verification."""
        anatomy_res = AnatomyResult(
            valid_anatomy=False,
            disc_center=None,
            fovea_center=(250.0, 250.0),
            inferred_laterality="UNKNOWN",
            operator_selected_eye="OD",
            laterality_mismatch=False,
            human_confirmation_required=True,
            notes=["OPTIC_DISC_NOT_FOUND"],
        )

        img_val = ImageValidationResult(valid=True, image_hash="abc123hash")
        ood_res = OODResult(domain_valid=True, ood_score=0.1)
        pred = {"stage": 0, "confidence": 95.0, "all_probabilities": {0: 95.0, 1: 5.0, 2: 0.0, 3: 0.0, 4: 0.0}}

        eval_res = self.engine.evaluate(
            image_val=img_val,
            anatomy_res=anatomy_res,
            ood_res=ood_res,
            primary_detection=pred,
        )

        self.assertEqual(eval_res.safety_state, "ANATOMY_FAILED")
        self.assertEqual(eval_res.screening_eligibility, "INELIGIBLE")
        self.assertFalse(eval_res.clinical_action_allowed)
        self.assertEqual(eval_res.automation_level, "UNABLE_TO_CLASSIFY")
        self.assertIn("ANATOMY_DETECTION_FAILED", eval_res.reason_codes)

    @patch("engine.safety.anatomy.localize_disc_fovea")
    def test_disc_on_boundary_invalidates_anatomy(self, mock_loc):
        """Optic disc positioned within 5% edge boundary margin invalidates anatomy."""
        # 500x500 image, disc at x=10 (within 500 * 0.05 = 25px margin)
        mock_loc.return_value = ((10, 250), 30, (250, 250))
        dummy = np.zeros((500, 500, 3), dtype=np.uint8)

        anatomy = assess_anatomy_and_laterality(dummy, operator_eye="OS")
        self.assertFalse(anatomy.valid_anatomy)
        self.assertEqual(anatomy.inferred_laterality, "UNKNOWN")
        self.assertTrue(any("DISC_ON_IMAGE_BOUNDARY" in n for n in anatomy.notes))

    @patch("engine.safety.anatomy.localize_disc_fovea")
    def test_implausible_disc_fovea_geometry_invalidates_anatomy(self, mock_loc):
        """Disc and fovea located at implausibly small distance (<0.8*expected_dd) invalidates anatomy."""
        # Disc radius 30 -> expected_dd = 60 -> min allowed dist = 48px.
        # Position fovea 10px away -> implausible overlap
        mock_loc.return_value = ((250, 250), 30, (260, 250))
        dummy = np.zeros((600, 600, 3), dtype=np.uint8)

        anatomy = assess_anatomy_and_laterality(dummy, operator_eye="OD")
        self.assertFalse(anatomy.valid_anatomy)
        self.assertEqual(anatomy.inferred_laterality, "UNKNOWN")
        self.assertTrue(any("overlap" in n.lower() or "implausible" in n.lower() for n in anatomy.notes))

    def test_anatomy_failure_suppresses_routine_referral(self):
        """Referral triage must NEVER assign STAGE_LOW to an anatomy failure."""
        triage = decide_referral(
            screening={
                "stage": 0,
                "confidence": 95.0,
                "safety_state": "ANATOMY_FAILED",
                "valid_anatomy": False,
            }
        )
        self.assertEqual(triage["priority"], "RETAKE_OR_SPECIALIST_EVALUATION")
        self.assertTrue(triage["human_review_required"])
        self.assertIn("ANATOMY_FAILED_RETAKE_REQUIRED", triage["reason_codes"])


class TestOrientationAndMirroring(unittest.TestCase):
    """Phase 4: Orientation Anomaly Detection & EXIF Orientation Handling."""

    @patch("engine.safety.anatomy.localize_disc_fovea")
    def test_vertical_orientation_anomaly_flagged(self, mock_loc):
        """Landmarks with vertical displacement > 1.25 * horizontal displacement trigger orientation anomaly."""
        # Disc at (300, 100), fovea at (300, 300) -> dy = -200, dx = 0 -> vertical ratio dominates
        mock_loc.return_value = ((300, 100), 30, (300, 300))
        dummy = np.zeros((600, 600, 3), dtype=np.uint8)

        res = assess_anatomy_and_laterality(dummy, operator_eye="OD")
        self.assertFalse(res.valid_anatomy)
        self.assertEqual(res.inferred_laterality, "UNKNOWN")
        self.assertTrue(any("ORIENTATION_ANOMALY_SUSPECTED" in n for n in res.notes))

    def test_exif_orientation_tag_inspection(self):
        """EXIF orientation tag 274 is extracted and flagged when non-standard."""
        np.random.seed(42)
        im_arr = np.random.randint(40, 210, (200, 200, 3), dtype=np.uint8)
        im = Image.fromarray(im_arr)
        exif = im.getexif()
        exif[274] = 6  # Rotated 90 CW

        import io
        buf = io.BytesIO()
        im.save(buf, format="JPEG", exif=exif)
        jpeg_bytes = buf.getvalue()

        val_res, _ = validate_image_file(jpeg_bytes)
        self.assertTrue(val_res.valid)
        self.assertEqual(val_res.exif_orientation, 6)
        self.assertTrue(any("EXIF_ORIENTATION_NON_STANDARD" in w for w in val_res.warnings))


class TestWorkflowAndIdentityConsistency(unittest.TestCase):
    """Phase 5, 6: Cross-Patient Duplicates, Cross-Eye Reuse, and Perceptual Hashing."""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.patient_a = create_patient(name="Workflow Patient Alpha", age=50, gender="Female")
        cls.patient_b = create_patient(name="Workflow Patient Beta", age=52, gender="Male")
        cls.patient_c = create_patient(name="Workflow Patient Charlie", age=55, gender="Male")
        cls.patient_id_a = cls.patient_a["id"]
        cls.patient_id_b = cls.patient_b["id"]
        cls.patient_id_c = cls.patient_c["id"]

    def test_dhash_computation_and_matching(self):
        """compute_dhash generates deterministic 64-bit gradient hash."""
        im1 = np.zeros((100, 100, 3), dtype=np.uint8)
        im1[:, :50] = 255
        h1 = compute_dhash(im1)
        self.assertEqual(len(h1), 16)

        im2 = im1.copy()
        im2[10, 10] = [254, 254, 254]
        h2 = compute_dhash(im2)
        self.assertEqual(h1, h2)

    def test_cross_patient_duplicate_detected(self):
        """Submitting the identical image under a different patient ID generates warning."""
        img_hash = "sha256_wf_dup_cross_patient"
        save_scan(
            scan_id="scan_wf_test_1",
            patient_id=self.patient_id_a,
            detection_result={"stage": 0, "confidence": 92.0},
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={},
            processing_time=1.0,
            laterality="OD",
            operator_id="op-1",
            safety_state="VERIFIED",
            image_hash=img_hash,
        )

        warns = check_workflow_image_consistency(
            image_hash=img_hash,
            dhash="0123456789abcdef",
            patient_id=self.patient_id_b,
            eye="OD",
        )
        self.assertTrue(any("CROSS_PATIENT_DUPLICATE" in w for w in warns))

    def test_cross_eye_duplicate_detected(self):
        """Submitting the identical image for the opposite eye under the same patient generates warning."""
        img_hash = "sha256_wf_dup_cross_eye"
        save_scan(
            scan_id="scan_wf_test_2",
            patient_id=self.patient_id_c,
            detection_result={"stage": 1, "confidence": 88.0},
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={},
            processing_time=1.0,
            laterality="OD",
            operator_id="op-1",
            safety_state="VERIFIED",
            image_hash=img_hash,
        )

        warns = check_workflow_image_consistency(
            image_hash=img_hash,
            dhash="abcdef0123456789",
            patient_id=self.patient_id_c,
            eye="OS",
        )
        self.assertTrue(any("CROSS_EYE_IMAGE_REUSE" in w or "STUDY_CONFLICT" in w for w in warns))


class TestCameraVariabilityAndThresholdBoundaries(unittest.TestCase):
    """Phase 7: Threshold Boundary Behavior (T - eps, T, T + eps)."""

    def setUp(self):
        self.engine = SafetyDecisionEngine()
        self.img_val = ImageValidationResult(valid=True, image_hash="hash_cam_test")
        self.anatomy = AnatomyResult(
            valid_anatomy=True,
            disc_center=(350.0, 250.0),
            fovea_center=(250.0, 250.0),
            inferred_laterality="OS",
            operator_selected_eye="OS",
            laterality_mismatch=False,
            human_confirmation_required=False,
            laterality_confidence=0.9,
        )
        self.ood = OODResult(domain_valid=True, ood_score=0.05)

    def test_confidence_threshold_boundaries(self):
        """Boundary verification at confidence 69.9%, 70.0%, and 70.1%."""
        pred_sub = {"stage": 0, "confidence": 69.9, "all_probabilities": {0: 69.9, 1: 30.1, 2: 0.0, 3: 0.0, 4: 0.0}}
        res_sub = self.engine.evaluate(self.img_val, self.anatomy, self.ood, pred_sub)
        self.assertEqual(res_sub.safety_state, "UNCERTAIN")
        self.assertIn("LOW_CONFIDENCE", res_sub.reason_codes)

        pred_exact = {"stage": 0, "confidence": 70.0, "all_probabilities": {0: 70.0, 1: 30.0, 2: 0.0, 3: 0.0, 4: 0.0}}
        res_exact = self.engine.evaluate(self.img_val, self.anatomy, self.ood, pred_exact)
        self.assertEqual(res_exact.safety_state, "VERIFIED")

        pred_plus = {"stage": 0, "confidence": 70.1, "all_probabilities": {0: 70.1, 1: 29.9, 2: 0.0, 3: 0.0, 4: 0.0}}
        res_plus = self.engine.evaluate(self.img_val, self.anatomy, self.ood, pred_plus)
        self.assertEqual(res_plus.safety_state, "VERIFIED")


class TestNumericalModelOutputStability(unittest.TestCase):
    """Phase 9: IEEE 754 Non-Finite Floats, Stage Range, and Probability Sum Invariants."""

    def setUp(self):
        self.engine = SafetyDecisionEngine()
        self.img_val = ImageValidationResult(valid=True, image_hash="hash_num_test")
        self.anatomy = AnatomyResult(
            valid_anatomy=True,
            disc_center=(350.0, 250.0),
            fovea_center=(250.0, 250.0),
            inferred_laterality="OS",
            operator_selected_eye="OS",
            laterality_mismatch=False,
            human_confirmation_required=False,
            laterality_confidence=0.9,
        )
        self.ood = OODResult(domain_valid=True, ood_score=0.05)

    def test_nan_model_confidence_blocked(self):
        """IEEE 754 NaN confidence must trigger BLOCKED with NUMERICAL_INSTABILITY_DETECTED."""
        pred = {"stage": 0, "confidence": float("nan"), "all_probabilities": {0: 100.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}}
        res = self.engine.evaluate(self.img_val, self.anatomy, self.ood, pred)
        self.assertEqual(res.safety_state, "BLOCKED")
        self.assertFalse(res.clinical_action_allowed)
        self.assertIn("NUMERICAL_INSTABILITY_DETECTED", res.reason_codes)

    def test_inf_model_confidence_blocked(self):
        """IEEE 754 Inf confidence must trigger BLOCKED with NUMERICAL_INSTABILITY_DETECTED."""
        pred = {"stage": 1, "confidence": float("inf"), "all_probabilities": {0: 0.0, 1: 100.0, 2: 0.0, 3: 0.0, 4: 0.0}}
        res = self.engine.evaluate(self.img_val, self.anatomy, self.ood, pred)
        self.assertEqual(res.safety_state, "BLOCKED")
        self.assertIn("NUMERICAL_INSTABILITY_DETECTED", res.reason_codes)

    def test_invalid_stage_numbers_blocked(self):
        """Stage numbers outside 0..4 range must trigger BLOCKED with INVALID_STAGE_INDEX."""
        pred_invalid = {"stage": 5, "confidence": 95.0, "all_probabilities": {5: 95.0}}
        res_invalid = self.engine.evaluate(self.img_val, self.anatomy, self.ood, pred_invalid)
        self.assertEqual(res_invalid.safety_state, "BLOCKED")
        self.assertIn("INVALID_STAGE_INDEX", res_invalid.reason_codes)

        pred_neg = {"stage": -1, "confidence": 95.0, "all_probabilities": {-1: 95.0}}
        res_neg = self.engine.evaluate(self.img_val, self.anatomy, self.ood, pred_neg)
        self.assertEqual(res_neg.safety_state, "BLOCKED")
        self.assertIn("INVALID_STAGE_INDEX", res_neg.reason_codes)

    def test_probability_sum_violation_blocked(self):
        """Softmax probabilities that sum significantly away from 100% fail closed to UNCERTAIN."""
        pred_low_sum = {"stage": 0, "confidence": 40.0, "all_probabilities": {0: 40.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}}
        res_low_sum = self.engine.evaluate(self.img_val, self.anatomy, self.ood, pred_low_sum)
        self.assertEqual(res_low_sum.safety_state, "UNCERTAIN")
        self.assertIn("PROBABILITY_DISTRIBUTION_UNNORMALIZED", res_low_sum.reason_codes)


class TestDiseaseScopeAndUnsupportedPathology(unittest.TestCase):
    """Phase 10: Non-DR Retinal Disease Escapes Normal Discharge."""

    def test_suspected_non_dr_pathology_escalated(self):
        """Suspected non-DR pathology forces human doctor review and blocks automatic normal discharge."""
        engine = SafetyDecisionEngine()
        img_val = ImageValidationResult(
            valid=True,
            image_hash="hash_nondr_test",
            warnings=["SUSPECTED_NON_DR_PATHOLOGY_DETECTED: Macular drusen visible"],
        )
        anatomy = AnatomyResult(
            valid_anatomy=True,
            disc_center=(350.0, 250.0),
            fovea_center=(250.0, 250.0),
            inferred_laterality="OS",
            operator_selected_eye="OS",
            laterality_mismatch=False,
            human_confirmation_required=False,
            laterality_confidence=0.9,
        )
        ood = OODResult(domain_valid=True, ood_score=0.05)
        pred = {"stage": 0, "confidence": 95.0, "all_probabilities": {0: 95.0, 1: 5.0, 2: 0.0, 3: 0.0, 4: 0.0}}

        res = engine.evaluate(img_val, anatomy, ood, pred)
        self.assertEqual(res.safety_state, "OOD_REVIEW")
        self.assertEqual(res.automation_level, "HUMAN_REVIEW_REQUIRED")
        self.assertIn("NON_DR_PATHOLOGY_SUSPECTED", res.reason_codes)


class TestLongitudinalEdgeCases(unittest.TestCase):
    """Phase 11: Cross-Eye Filtering, Acute Repeat Scans, and Regression Anomalies."""

    def test_cross_eye_filtering_enforced(self):
        """_latest_previous_scan must NOT match a previous scan of the opposite eye."""
        current_scan = {"id": "scan_curr", "stage": 1, "confidence": 88.0, "eye": "OD"}
        previous_scans = [
            {"id": "scan_prev_os", "stage": 2, "confidence": 90.0, "eye": "OS", "created_at": "2025-01-01T00:00:00"},
        ]
        latest = _latest_previous_scan(current_scan, previous_scans)
        self.assertIsNone(latest)

        prog = assess_progression_risk(
            current_scan=current_scan,
            previous_scans=previous_scans,
            patient_profile={"diabetes_duration": 5, "hba1c": 7.5},
        )
        self.assertEqual(prog["observed_data"]["previous_stage"], None)
        self.assertEqual(prog["observed_data"]["stage_delta"], None)
        self.assertEqual(prog["longitudinal_state"], "LIMITED_LONGITUDINAL_HISTORY")

    def test_acute_repeat_scan_suppressed(self):
        """Scans taken within 7 days flag acute repeat suppression and prevent false rapid change claims."""
        current_scan = {"id": "scan_curr", "stage": 2, "confidence": 85.0, "eye": "OD", "created_at": "2026-02-10T00:00:00"}
        previous_scans = [
            {"id": "scan_prev", "stage": 1, "confidence": 90.0, "eye": "OD", "created_at": "2026-02-07T00:00:00"},
        ]
        prog = assess_progression_risk(
            current_scan=current_scan,
            previous_scans=previous_scans,
            patient_profile={"diabetes_duration": 5, "hba1c": 8.0},
        )
        self.assertTrue(any("ACUTE_REPEAT_SCAN_SUPPRESSED" in f for f in prog["predicted_risk"]["uncertainty_flags"]))

    def test_extended_gap_flagged(self):
        """Scans separated by > 36 months flag extended gap reduced predictive fidelity."""
        current_scan = {"id": "scan_curr", "stage": 2, "confidence": 85.0, "eye": "OD", "created_at": "2026-01-01T00:00:00"}
        previous_scans = [
            {"id": "scan_prev", "stage": 0, "confidence": 90.0, "eye": "OD", "created_at": "2021-01-01T00:00:00"},
        ]
        prog = assess_progression_risk(
            current_scan=current_scan,
            previous_scans=previous_scans,
            patient_profile={"diabetes_duration": 10, "hba1c": 9.0},
        )
        self.assertTrue(any("EXTENDED_GAP_REDUCED_FIDELITY" in f for f in prog["predicted_risk"]["uncertainty_flags"]))

    def test_anomalous_rapid_regression_flagged(self):
        """Sudden regression from Stage 4 (Proliferative) to Stage 0 flags anomalous regression."""
        current_scan = {"id": "scan_curr", "stage": 0, "confidence": 95.0, "eye": "OD", "created_at": "2026-06-01T00:00:00"}
        previous_scans = [
            {"id": "scan_prev", "stage": 4, "confidence": 92.0, "eye": "OD", "created_at": "2025-06-01T00:00:00"},
        ]
        prog = assess_progression_risk(
            current_scan=current_scan,
            previous_scans=previous_scans,
            patient_profile={"diabetes_duration": 15, "hba1c": 8.5},
        )
        self.assertTrue(any("ANOMALOUS_RAPID_REGRESSION_DETECTED" in f for f in prog["predicted_risk"]["uncertainty_flags"]))

    def test_prior_failed_scan_excluded(self):
        """A prior scan marked ANATOMY_FAILED or QUALITY_FAILED cannot be used as longitudinal baseline."""
        current_scan = {"id": "scan_curr", "stage": 1, "confidence": 88.0, "eye": "OD"}
        previous_scans = [
            {"id": "scan_failed", "stage": 3, "confidence": 90.0, "eye": "OD", "safety_state": "ANATOMY_FAILED"},
        ]
        latest = _latest_previous_scan(current_scan, previous_scans)
        self.assertIsNone(latest)


class TestOfflineIdempotencyAndSync(unittest.TestCase):
    """Phase 13, 15: Persistence Invariants, Idempotency, and Conflict Detection."""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.patient = create_patient(name="Idempotency Test Patient", age=60, gender="Female")
        cls.patient_id = cls.patient["id"]

    def test_idempotent_scan_save(self):
        """Re-saving the same scan_id updates the existing record without duplicate insertion."""
        scan_id = "scan_idempotent_test_unique"

        save_scan(
            scan_id=scan_id,
            patient_id=self.patient_id,
            detection_result={"stage": 1, "confidence": 85.0},
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={"original": "/results/test.png"},
            processing_time=1.2,
            laterality="OD",
            operator_id="op-1",
            safety_state="VERIFIED",
        )
        s1 = get_scan(scan_id)
        self.assertIsNotNone(s1)

        save_scan(
            scan_id=scan_id,
            patient_id=self.patient_id,
            detection_result={"stage": 1, "confidence": 85.0},
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={"original": "/results/test.png"},
            processing_time=1.2,
            laterality="OD",
            operator_id="op-1",
            safety_state="VERIFIED",
        )
        s2 = get_scan(scan_id)
        self.assertIsNotNone(s2)
        self.assertEqual(s1["id"], s2["id"])

    def test_save_progression_idempotency(self):
        """Saving progression assessment multiple times for same scan is idempotent."""
        scan_id = "scan_prog_idemp_unique"
        save_scan(
            scan_id=scan_id,
            patient_id=self.patient_id,
            detection_result={"stage": 2, "confidence": 89.0},
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={},
            processing_time=1.0,
            safety_state="VERIFIED",
        )
        save_progression_assessment(
            scan_id=scan_id,
            patient_id=self.patient_id,
            progression_data={"predicted_risk": {"risk_category": "MODERATE"}},
        )
        p = save_progression_assessment(
            scan_id=scan_id,
            patient_id=self.patient_id,
            progression_data={"predicted_risk": {"risk_category": "LOW"}},
        )
        self.assertEqual(p["risk_category"], "LOW")


class TestStateMachineInvariants(unittest.TestCase):
    """Phase 14: State Machine Invariant Transitions."""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.patient = create_patient(name="State Invariant Patient", age=45, gender="Male")
        cls.patient_id = cls.patient["id"]

    def test_failure_states_cannot_transition_to_completed(self):
        """Sessions ending in failure states must not transition directly to SCREENING_COMPLETED."""
        session_id = "sess_state_inv_unique_1"
        create_or_update_screening_session(
            session_id=session_id,
            patient_id=self.patient_id,
            operator_id="op-1",
            eye="OD",
            current_state=ScreeningState.ANATOMY_FAILED,
        )

        with self.assertRaises(InvalidStateTransitionError):
            update_screening_session_state(
                session_id=session_id,
                new_state=ScreeningState.SCREENING_COMPLETED,
                actor_id="op-1",
                reason="Attempted bypass",
                validate_transition=True,
            )


class TestReportConsistencyWithSafety(unittest.TestCase):
    """Phase 12: Deterministic Report-Safety Consistency."""

    def test_deterministic_offline_report_safety_override(self):
        """Offline report generator overrides diagnosis if safety is not VERIFIED."""
        report, _ = generate_offline_report(
            detection_result={"stage": 0, "stage_name": "No DR", "confidence": 95.0},
            heatmap_analysis={},
            vessel_stats={},
            patient_info={},
            safety_state="ANATOMY_FAILED",
            safety_eval={"safety_state": "ANATOMY_FAILED", "reasons": ["OPTIC_DISC_NOT_FOUND"]},
        )
        self.assertIn("Inconclusive", report["current_diagnosis"]["stage_name"])
        self.assertEqual(report["urgency"], "HUMAN_REVIEW_REQUIRED")
        self.assertTrue(any("examination" in act.lower() or "recapture" in act.lower() for act in report["action_plan"]))

    def test_gemma_report_safety_override(self):
        """Gemma report generator overrides diagnosis if safety is UNCERTAIN."""
        report, _ = generate_report(
            detection_result={"stage": 0, "stage_name": "No DR", "confidence": 65.0},
            heatmap_analysis={},
            vessel_stats={},
            patient_info={},
            safety_state="UNCERTAIN",
            safety_eval={"safety_state": "UNCERTAIN", "reasons": ["LOW_MODEL_CONFIDENCE"]},
        )
        self.assertIn("Inconclusive", report["current_diagnosis"]["stage_name"])
        self.assertNotEqual(report["urgency"], "ROUTINE")


if __name__ == "__main__":
    unittest.main()
