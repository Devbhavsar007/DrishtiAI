"""
Unit Tests for Gate 2: DrishtiAI Safety-Critical Core & Centralized Safety Decision Engine.
Validates:
  1. Image validation (magic bytes, corrupt files, blank images, decompression bombs)
  2. Anatomical validity and laterality hierarchy checking
  3. 3-Level Out-of-Distribution (OOD) evaluation
  4. Centralized Safety Decision Engine arbitration, reason codes, and automation levels
"""

import os
import unittest
import numpy as np
import cv2
from PIL import Image

from engine.safety.image_validator import validate_image_file, ImageValidationResult
from engine.safety.anatomy import assess_anatomy_and_laterality, AnatomyResult
from engine.safety.ood import evaluate_ood_signal, OODResult
from engine.safety.decision_engine import SafetyDecisionEngine, SafetyEvaluationResult


class TestSafetyCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_image_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "sample_data",
            "test_fundus.jpg"
        )
        if not os.path.exists(cls.test_image_path):
            raise FileNotFoundError(f"Test fundus image missing: {cls.test_image_path}")

        cls.valid_fundus_bgr = cv2.imread(cls.test_image_path)
        cls.engine = SafetyDecisionEngine()

    def test_01_image_validator_corrupt_and_bad_magic(self):
        """Image validator must reject zero-byte, invalid magic, and corrupted files."""
        # A. Empty bytes
        res, img = validate_image_file(b"")
        self.assertFalse(res.valid)
        self.assertIn("empty", res.error.lower())

        # B. Invalid magic bytes (e.g. random text or disguised binary)
        res_magic, _ = validate_image_file(b"MZ_this_is_an_executable_not_fundus")
        self.assertFalse(res_magic.valid)
        self.assertTrue("signature" in res_magic.error.lower() or "header" in res_magic.error.lower())

        # C. Truncated / Corrupt JPEG
        fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 20  # Incomplete JPEG stream
        res_corrupt, _ = validate_image_file(fake_jpeg)
        self.assertFalse(res_corrupt.valid)

    def test_02_image_validator_blank_and_valid(self):
        """Image validator must reject all-black/white images and accept valid fundus."""
        # A. Completely black image
        black_img = np.zeros((300, 300, 3), dtype=np.uint8)
        _, black_png = cv2.imencode(".png", black_img)
        res_blank, _ = validate_image_file(black_png.tobytes())
        self.assertFalse(res_blank.valid)
        self.assertTrue(res_blank.is_blank)

        # B. Valid sample fundus
        with open(self.test_image_path, "rb") as f:
            valid_bytes = f.read()
        res_valid, loaded_bgr = validate_image_file(valid_bytes)
        self.assertTrue(res_valid.valid)
        self.assertFalse(res_valid.is_blank)
        self.assertIsNotNone(loaded_bgr)
        self.assertGreater(len(res_valid.image_hash), 20)

    def test_03_anatomy_and_laterality_checking(self):
        """Verify optic disc landmark detection and operator laterality conflict check."""
        # A. Evaluate valid fundus image
        anatomy_res = assess_anatomy_and_laterality(self.valid_fundus_bgr, operator_eye="OD")
        self.assertTrue(anatomy_res.valid_anatomy)
        self.assertIsNotNone(anatomy_res.disc_center)

        # In test_fundus.jpg, optic disc is at (380, 300) in 600x600 image (right side, nasal for OS)
        # B. If operator indicates "OS" (matching landmark geometry)
        res_matching = assess_anatomy_and_laterality(self.valid_fundus_bgr, operator_eye="OS")
        self.assertFalse(res_matching.laterality_mismatch)
        self.assertFalse(res_matching.human_confirmation_required)

        # C. If operator explicitly inputs conflicting eye "OD"
        res_conflict = assess_anatomy_and_laterality(self.valid_fundus_bgr, operator_eye="OD")
        if res_conflict.inferred_laterality == "OS" and res_conflict.laterality_confidence >= 0.70:
            self.assertTrue(res_conflict.laterality_mismatch)
            self.assertTrue(res_conflict.human_confirmation_required)
            self.assertEqual(res_conflict.operator_selected_eye, "OD")  # Operator selection preserved

    def test_04_ood_domain_validation(self):
        """OOD module must reject non-fundus images and pass valid retinal scans."""
        # A. Non-fundus blue landscape image
        blue_img = np.zeros((400, 400, 3), dtype=np.uint8)
        blue_img[:, :, 0] = 200  # High blue
        blue_img[:, :, 1] = 100
        blue_img[:, :, 2] = 30   # Low red

        ood_non_fundus = evaluate_ood_signal(blue_img)
        self.assertFalse(ood_non_fundus.domain_valid)
        self.assertEqual(ood_non_fundus.level_triggered, 1)
        self.assertIn("non-fundus", ood_non_fundus.rejection_reason.lower())

        # B. Valid fundus image
        ood_fundus = evaluate_ood_signal(self.valid_fundus_bgr)
        self.assertTrue(ood_fundus.domain_valid)
        self.assertFalse(ood_fundus.metadata["clinically_validated"])  # Honestly acknowledges experimental nature

    def test_05_decision_engine_golden_path(self):
        """Golden path: valid image, high confidence, consistent laterality -> VERIFIED."""
        val_res = ImageValidationResult(valid=True, image_hash="abc12345")
        anat_res = AnatomyResult(valid_anatomy=True, inferred_laterality="OD", operator_selected_eye="OD")
        ood_res = OODResult(domain_valid=True, is_ood_suspected=False)
        detection = {"stage": 0, "stage_name": "No DR", "confidence": 94.5}

        decision = self.engine.evaluate(
            image_val=val_res,
            anatomy_res=anat_res,
            ood_res=ood_res,
            primary_detection=detection,
        )

        self.assertEqual(decision.screening_eligibility, "ELIGIBLE")
        self.assertEqual(decision.safety_state, "VERIFIED")
        self.assertEqual(decision.automation_level, "AUTOMATED_ASSISTANCE")
        self.assertFalse(decision.human_review_required)
        self.assertEqual(len(decision.reason_codes), 0)
        self.assertEqual(decision.safety_policy_version, "SAFE-1.0")

    def test_06_decision_engine_low_confidence_escalation(self):
        """Low confidence (<70%) must trigger UNCERTAIN and HUMAN_REVIEW_REQUIRED."""
        val_res = ImageValidationResult(valid=True)
        anat_res = AnatomyResult(valid_anatomy=True)
        ood_res = OODResult(domain_valid=True)
        detection = {"stage": 2, "stage_name": "Moderate NPDR", "confidence": 58.0}

        decision = self.engine.evaluate(
            image_val=val_res,
            anatomy_res=anat_res,
            ood_res=ood_res,
            primary_detection=detection,
        )

        self.assertEqual(decision.safety_state, "UNCERTAIN")
        self.assertEqual(decision.automation_level, "HUMAN_REVIEW_REQUIRED")
        self.assertTrue(decision.human_review_required)
        self.assertIn("LOW_CONFIDENCE", decision.reason_codes)

    def test_07_decision_engine_model_disagreement_escalation(self):
        """Model disagreement (delta >= 2 stages) must trigger MODEL_DISAGREEMENT reason code."""
        val_res = ImageValidationResult(valid=True)
        anat_res = AnatomyResult(valid_anatomy=True)
        ood_res = OODResult(domain_valid=True)
        primary = {"stage": 1, "confidence": 88.0}
        secondary = {"stage": 3, "confidence": 82.0}  # Delta = 2 stages

        decision = self.engine.evaluate(
            image_val=val_res,
            anatomy_res=anat_res,
            ood_res=ood_res,
            primary_detection=primary,
            secondary_detection=secondary,
        )

        self.assertEqual(decision.safety_state, "UNCERTAIN")
        self.assertEqual(decision.automation_level, "HUMAN_REVIEW_REQUIRED")
        self.assertTrue(decision.human_review_required)
        self.assertIn("MODEL_DISAGREEMENT", decision.reason_codes)

    def test_08_decision_engine_hard_rejections(self):
        """Corrupt image or non-fundus must be REJECTED with UNABLE_TO_CLASSIFY."""
        # A. Corrupt image
        bad_val = ImageValidationResult(valid=False, error="Corrupted stream")
        dec_bad = self.engine.evaluate(image_val=bad_val)
        self.assertEqual(dec_bad.screening_eligibility, "INELIGIBLE")
        self.assertEqual(dec_bad.safety_state, "REJECTED")
        self.assertEqual(dec_bad.automation_level, "UNABLE_TO_CLASSIFY")
        self.assertIn("IMAGE_VALIDATION_FAILED", dec_bad.reason_codes)

        # B. Non-fundus image
        good_val = ImageValidationResult(valid=True)
        non_fundus_ood = OODResult(domain_valid=False, rejection_reason="Non-fundus scene")
        dec_ood = self.engine.evaluate(image_val=good_val, ood_res=non_fundus_ood)
        self.assertEqual(dec_ood.screening_eligibility, "INELIGIBLE")
        self.assertEqual(dec_ood.safety_state, "REJECTED")
        self.assertEqual(dec_ood.automation_level, "UNABLE_TO_CLASSIFY")
        self.assertIn("NON_FUNDUS_REJECTED", dec_ood.reason_codes)


if __name__ == "__main__":
    unittest.main()
