"""
Authoritative End-to-End Safety Invariant Test Suite for DrishtiAI.

Strictly verifies the 10 core architectural safety invariants:
INVARIANT 1:  If safety_state != VERIFIED, clinical_action_allowed == False.
INVARIANT 2:  If human_review_required == True, automation cannot be marked fully autonomous.
INVARIANT 3:  Invalid/missing model output cannot create a valid clinical result.
INVARIANT 4:  Invalid anatomy cannot create a verified screening result.
INVARIANT 5:  Unsafe historical records cannot create valid automated progression evidence.
INVARIANT 6:  Auxiliary component failure cannot silently alter the authoritative screening decision.
INVARIANT 7:  Report generation cannot override deterministic safety state.
INVARIANT 8:  Offline replay cannot create duplicate clinical assessments.
INVARIANT 9:  Illegal state transitions must be rejected.
INVARIANT 10: Human override must remain semantically distinguishable from automated validation.
"""

import unittest
import json
import math
import uuid

from engine.safety.decision_engine import SafetyDecisionEngine, SafetyEvaluationResult
from engine.safety.anatomy import AnatomyResult
from engine.safety.image_validator import ImageValidationResult
from engine.safety.ood import OODResult
from engine.safety.state_machine import ScreeningState, InvalidStateTransitionError
from engine.clinical.progression import assess_progression_risk
from engine.gemma_report import generate_report
from engine.pipeline.offline_report import generate_offline_report
import database


class TestAuthoritativeSafetyInvariants(unittest.TestCase):
    def setUp(self):
        self.engine = SafetyDecisionEngine()
        self.val_ok = ImageValidationResult(valid=True, image_hash="inv-hash-01")
        # Plausible geometric coordinates for verified OD anatomy
        self.anat_ok = AnatomyResult(
            valid_anatomy=True,
            disc_center=(160.0, 256.0),
            disc_radius=35,
            fovea_center=(300.0, 256.0),
            operator_selected_eye="OD",
            inferred_laterality="OD",
            laterality_confidence=0.95,
            orientation_state="UPRIGHT_VERIFIED",
        )
        self.ood_ok = OODResult(domain_valid=True)
        self.pred_normal = {"stage": 0, "stage_name": "No DR", "confidence": 92.0}

    # =========================================================================
    # INVARIANT 1: If safety_state != VERIFIED -> clinical_action_allowed == False
    # =========================================================================
    def test_invariant_01_non_verified_states_never_allow_clinical_action(self):
        """Invariant 1: If safety_state != VERIFIED, clinical_action_allowed MUST be False."""
        unsafe_scenarios = [
            # Low confidence
            {"stage": 0, "confidence": 55.0},
            # Model disagreement
            {"stage": 0, "confidence": 95.0, "_sec": {"stage": 3, "confidence": 90.0}},
            # Referable DR (requires human clinician signoff)
            {"stage": 2, "confidence": 95.0},
            {"stage": 3, "confidence": 95.0},
            {"stage": 4, "confidence": 95.0},
        ]
        for scen in unsafe_scenarios:
            sec = scen.pop("_sec", None)
            res = self.engine.evaluate(
                image_val=self.val_ok,
                anatomy_res=self.anat_ok,
                ood_res=self.ood_ok,
                primary_detection=scen,
                secondary_detection=sec,
            )
            self.assertNotEqual(res.safety_state, "VERIFIED")
            self.assertFalse(
                res.clinical_action_allowed,
                f"Violation for scenario {scen}: clinical_action_allowed was True under {res.safety_state}"
            )

    # =========================================================================
    # INVARIANT 2: If human_review_required == True -> automation cannot be autonomous
    # =========================================================================
    def test_invariant_02_human_review_required_blocks_automated_assistance(self):
        """Invariant 2: human_review_required == True forbids AUTOMATED_ASSISTANCE."""
        pred = {"stage": 1, "confidence": 60.0} # Low conf
        res = self.engine.evaluate(
            image_val=self.val_ok,
            anatomy_res=self.anat_ok,
            primary_detection=pred,
        )
        self.assertTrue(res.human_review_required)
        self.assertNotEqual(res.automation_level, "AUTOMATED_ASSISTANCE")
        self.assertEqual(res.automation_level, "HUMAN_REVIEW_REQUIRED")
        self.assertFalse(res.clinical_action_allowed)

    # =========================================================================
    # INVARIANT 3: Invalid/missing model output cannot create valid clinical result
    # =========================================================================
    def test_invariant_03_invalid_model_output_cannot_create_valid_clinical_result(self):
        """Invariant 3: NaN, Inf, negative probs, unnormalized sum, invalid stage must fail safe."""
        malformed_preds = [
            {"stage": 0, "confidence": float("nan")},
            {"stage": 0, "confidence": float("inf")},
            {"stage": -1, "confidence": 90.0},
            {"stage": 5, "confidence": 90.0},
            {"stage": "STAGE_UNKNOWN", "confidence": 90.0},
            {"stage": 0, "confidence": 90.0, "all_probabilities": {0: -10.0, 1: 110.0}},
            {"stage": 0, "confidence": 90.0, "all_probabilities": {0: 10.0, 1: 10.0}}, # Sum = 20%
            {},
        ]
        for bad_pred in malformed_preds:
            res = self.engine.evaluate(
                image_val=self.val_ok,
                anatomy_res=self.anat_ok,
                primary_detection=bad_pred,
            )
            self.assertIn(res.safety_state, ("MODEL_FAILURE", "BLOCKED", "UNCERTAIN"))
            self.assertFalse(res.clinical_action_allowed)
            self.assertTrue(res.human_review_required)

    # =========================================================================
    # INVARIANT 4: Invalid anatomy cannot create a verified screening result
    # =========================================================================
    def test_invariant_04_invalid_anatomy_cannot_create_verified_screening_result(self):
        """Invariant 4: valid_anatomy=False, None, malformed, or inconsistent must fail to ANATOMY_FAILED."""
        bad_anatomies = [
            AnatomyResult(valid_anatomy=False, notes=["Optic disc could not be reliably located."]),
            {"valid_anatomy": False},
            {"valid_anatomy": None},
            {},
            {"exception": "Landmark detection timeout"},
            {"status": "UNAVAILABLE", "available": False},
            # Inconsistent: valid claimed True but coordinates impossible
            AnatomyResult(valid_anatomy=True, disc_center=(-5, 100), disc_radius=30),
            AnatomyResult(valid_anatomy=True, disc_center=(100, 100), fovea_center=(102, 101)), # overlap < 5px
        ]
        for bad_anat in bad_anatomies:
            res = self.engine.evaluate(
                image_val=self.val_ok,
                anatomy_res=bad_anat,
                primary_detection=self.pred_normal,
            )
            self.assertEqual(res.safety_state, "ANATOMY_FAILED")
            self.assertFalse(res.clinical_action_allowed)
            self.assertTrue(res.human_review_required)
            self.assertEqual(res.screening_eligibility, "INELIGIBLE")

    # =========================================================================
    # INVARIANT 5: Unsafe historical records cannot create progression evidence
    # =========================================================================
    def test_invariant_05_unsafe_historical_records_excluded_from_progression(self):
        """Invariant 5: Historical scans with ANATOMY_FAILED, QUALITY_FAILED, UNCERTAIN excluded."""
        current = {"id": "c-1", "stage": 1, "confidence": 90.0, "safety_state": "VERIFIED", "eye": "OD", "created_at": "2026-05-01T10:00:00Z"}
        
        # All prior scans are invalid/unsafe
        invalid_history = [
            {"id": "p-1", "stage": 3, "confidence": 90.0, "safety_state": "ANATOMY_FAILED", "eye": "OD", "created_at": "2025-05-01T10:00:00Z"},
            {"id": "p-2", "stage": 2, "confidence": 45.0, "safety_state": "QUALITY_FAILED", "eye": "OD", "created_at": "2024-05-01T10:00:00Z"},
            {"id": "p-3", "stage": 0, "confidence": 85.0, "safety_state": "SCREENING_UNCERTAIN", "eye": "OD", "created_at": "2023-05-01T10:00:00Z"},
        ]
        prog = assess_progression_risk(current_scan=current, previous_scans=invalid_history)
        
        # Must report limited history (baseline only), never computing a delta from an invalid scan
        self.assertEqual(prog["longitudinal_state"], "LIMITED_LONGITUDINAL_HISTORY")
        self.assertIsNone(prog["observed_data"]["previous_stage"])
        self.assertIsNone(prog["observed_data"]["stage_delta"])

        # Contradictory timestamps: current scan date precedes historical date
        inverted_history = [
            {"id": "p-ok", "stage": 0, "confidence": 90.0, "safety_state": "VERIFIED", "eye": "OD", "created_at": "2027-01-01T10:00:00Z"}
        ]
        prog_inv = assess_progression_risk(current_scan=current, previous_scans=inverted_history)
        self.assertEqual(prog_inv["longitudinal_state"], "LONGITUDINAL_UNAVAILABLE")

    # =========================================================================
    # INVARIANT 6: Auxiliary component failure cannot alter screening decision
    # =========================================================================
    def test_invariant_06_auxiliary_failure_does_not_alter_screening_decision(self):
        """Invariant 6: Grad-CAM / Segmentation / Report failure must never alter screening result."""
        # Test detection is referable Stage 3
        det = {"stage": 3, "stage_name": "Severe NPDR", "confidence": 88.0}
        res = self.engine.evaluate(
            image_val=self.val_ok,
            anatomy_res=self.anat_ok,
            primary_detection=det,
        )
        self.assertIn("REFERABLE_DR_DETECTED", res.reason_codes)

        # In offline report with failed auxiliary heatmap / vessel stats
        bad_heatmap = {"status": "EXPLANATION_UNAVAILABLE", "explanation_available": False}
        bad_vessels = {"status": "VESSELS_UNAVAILABLE", "vessel_available": False}
        rep, _ = generate_offline_report(det, bad_heatmap, bad_vessels, safety_state="VERIFIED")
        
        # Report preserves the true stage and urgency
        self.assertEqual(rep["current_diagnosis"]["stage"], 3)
        self.assertEqual(rep["urgency"], "URGENT")

    # =========================================================================
    # INVARIANT 7: Report generation cannot override deterministic safety state
    # =========================================================================
    def test_invariant_07_report_generation_cannot_override_safety_state(self):
        """Invariant 7: When safety_state != VERIFIED, report must be Inconclusive (stage: -1)."""
        det_clean = {"stage": 0, "stage_name": "No DR", "confidence": 95.0}
        
        for bad_state in ("MODEL_FAILURE", "ANATOMY_FAILED", "UNCERTAIN", "QUALITY_FAILED", "OOD_REVIEW"):
            rep, _ = generate_report(
                det_clean, None, None,
                safety_state=bad_state,
            )
            self.assertEqual(rep["current_diagnosis"]["stage"], -1)
            self.assertIn("inconclusive", rep["current_diagnosis"]["stage_name"].lower())
            self.assertEqual(rep["urgency"], "HUMAN_REVIEW_REQUIRED")
            self.assertIn("clinical evaluation", rep["current_diagnosis"]["plain_language"].lower())

    # =========================================================================
    # INVARIANT 8: Offline replay cannot create duplicate clinical assessments
    # =========================================================================
    def test_invariant_08_offline_replay_idempotency(self):
        """Invariant 8: Repeated saving of the same scan ID updates in-place, never duplicating."""
        p = database.create_patient(f"Idempotent Subject {uuid.uuid4().hex[:6]}", age=45)
        pid = p["id"]
        scan_id = f"idemp-scan-{uuid.uuid4().hex[:8]}"

        det = {"stage": 1, "stage_name": "Mild NPDR", "confidence": 85.0}
        # First save
        database.save_scan(
            scan_id=scan_id,
            patient_id=pid,
            detection_result=det,
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={},
            processing_time=1.2,
        )
        # Replay save (exact same scan_id)
        database.save_scan(
            scan_id=scan_id,
            patient_id=pid,
            detection_result=det,
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={},
            processing_time=1.5,
        )
        # Check patient timeline: must contain exactly 1 event for this scan_id
        timeline = database.get_patient_timeline(pid)
        matching = [e for e in timeline.get("events", []) if e.get("scan_id") == scan_id]
        self.assertEqual(len(matching), 1)

    # =========================================================================
    # INVARIANT 9: Illegal state transitions must be rejected
    # =========================================================================
    def test_invariant_09_illegal_state_transitions_rejected(self):
        """Invariant 9: State machine strictly forbids invalid skips (e.g. ANATOMY_FAILED -> FINALIZED)."""
        sess_id = f"sess-inv9-{uuid.uuid4().hex[:6]}"
        database.create_or_update_screening_session(
            session_id=sess_id,
            patient_id="P-0001",
            operator_id="operator-1",
            eye="OD",
            current_state=ScreeningState.ANATOMY_FAILED,
        )
        # Non-doctor operator cannot transition ANATOMY_FAILED directly to FINALIZED or SCREENING_COMPLETED
        with self.assertRaises(InvalidStateTransitionError):
            database.update_screening_session_state(
                session_id=sess_id,
                new_state=ScreeningState.FINALIZED,
                actor_id="operator-1",
                actor_role="HEALTH_WORKER",
                validate_transition=True,
            )

    # =========================================================================
    # INVARIANT 10: Human override must remain distinguishable from automated validation
    # =========================================================================
    def test_invariant_10_human_override_semantically_distinguishable(self):
        """Invariant 10: Human confirmation sets automation_level to HUMAN_CONFIRMED with audit trail."""
        sess_id = f"sess-inv10-{uuid.uuid4().hex[:6]}"
        database.create_or_update_screening_session(
            session_id=sess_id,
            patient_id="P-0001",
            operator_id="operator-1",
            eye="OD",
            current_state=ScreeningState.OPERATOR_OVERRIDE_PENDING,
        )
        # Operator confirms override
        database.update_screening_session_state(
            session_id=sess_id,
            new_state=ScreeningState.ANATOMY_VALIDATED,
            actor_id="operator-nurse-1",
            actor_role="HEALTH_WORKER",
            reason="Operator confirmed landmark alignment override manually.",
            validate_transition=True,
        )
        sess = database.get_screening_session(sess_id)
        self.assertEqual(sess["current_state"], ScreeningState.ANATOMY_VALIDATED)
        self.assertEqual(sess["automation_level"], "HUMAN_CONFIRMED")
        self.assertNotEqual(sess["automation_level"], "AUTOMATED_ASSISTANCE")


if __name__ == "__main__":
    unittest.main()
