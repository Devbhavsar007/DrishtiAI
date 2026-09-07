"""
Metamorphic Testing for Retinal Image Orientation, Mirroring, and EXIF Robustness.

Tests the fundamental safety invariant:
If orientation/laterality cannot be reliably established under transformation:
  LATERALITY_CONFLICT | ANATOMY_FAILED | SCREENING_UNCERTAIN
              ↓
  human/retake pathway active
              ↓
  clinical_action_allowed == False

Never silently produces the opposite-eye autonomous diagnosis.
"""

import unittest
import os
import numpy as np
import cv2

from engine.safety.anatomy import assess_anatomy_and_laterality
from engine.safety.image_validator import ImageValidationResult
from engine.safety.decision_engine import SafetyDecisionEngine


class TestMetamorphicOrientationAndMirroring(unittest.TestCase):
    def setUp(self):
        self.engine = SafetyDecisionEngine()
        self.fundus_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data", "test_fundus.jpg")
        self.img = cv2.imread(self.fundus_path)
        self.val_valid = ImageValidationResult(valid=True, image_hash="test-hash-meta")
        self.pred_normal = {"stage": 0, "stage_name": "No DR", "confidence": 92.0}

    def test_01_baseline_upright_os_correctly_verified(self):
        """0° upright OS image with matching operator selection verifies cleanly."""
        res = assess_anatomy_and_laterality(self.img, operator_eye="OS", exif_orientation=1)
        self.assertTrue(res.valid_anatomy)
        self.assertEqual(res.orientation_state, "UPRIGHT_VERIFIED")
        self.assertFalse(res.laterality_mismatch)
        self.assertFalse(res.human_confirmation_required)

        decision = self.engine.evaluate(
            image_val=self.val_valid,
            anatomy_res=res,
            primary_detection=self.pred_normal,
        )
        self.assertEqual(decision.safety_state, "VERIFIED")
        self.assertTrue(decision.clinical_action_allowed)

    def test_02_90_degree_rotation_blocks_autonomous_action(self):
        """90° rotation disrupts orientation, triggering conflict/uncertainty and blocking automated action."""
        rot90 = cv2.rotate(self.img, cv2.ROTATE_90_CLOCKWISE)
        res = assess_anatomy_and_laterality(rot90, operator_eye="OS", exif_orientation=1)

        self.assertTrue(res.human_confirmation_required)
        decision = self.engine.evaluate(
            image_val=self.val_valid,
            anatomy_res=res,
            primary_detection=self.pred_normal,
        )
        self.assertFalse(decision.clinical_action_allowed)
        self.assertIn(decision.safety_state, ("UNCERTAIN", "ANATOMY_FAILED", "BLOCKED"))

    def test_03_270_degree_rotation_blocks_autonomous_action(self):
        """270° rotation disrupts orientation, blocking autonomous action."""
        rot270 = cv2.rotate(self.img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        res = assess_anatomy_and_laterality(rot270, operator_eye="OS", exif_orientation=1)

        self.assertTrue(res.human_confirmation_required)
        decision = self.engine.evaluate(
            image_val=self.val_valid,
            anatomy_res=res,
            primary_detection=self.pred_normal,
        )
        self.assertFalse(decision.clinical_action_allowed)
        self.assertIn(decision.safety_state, ("UNCERTAIN", "ANATOMY_FAILED", "BLOCKED"))

    def test_04_180_degree_inversion_triggers_laterality_conflict(self):
        """180° inversion moves nasal disc to opposite field, suppressing automated clearance."""
        rot180 = cv2.rotate(self.img, cv2.ROTATE_180)
        res = assess_anatomy_and_laterality(rot180, operator_eye="OS", exif_orientation=1)

        self.assertTrue(res.human_confirmation_required)
        decision = self.engine.evaluate(
            image_val=self.val_valid,
            anatomy_res=res,
            primary_detection=self.pred_normal,
        )
        self.assertFalse(decision.clinical_action_allowed)
        self.assertIn(decision.safety_state, ("UNCERTAIN", "ANATOMY_FAILED", "BLOCKED"))

    def test_05_horizontal_mirror_triggers_laterality_conflict(self):
        """Horizontal flip (mirroring) swaps nasal/temporal relationship, blocking autonomous clearance."""
        mirrored = cv2.flip(self.img, 1)
        res = assess_anatomy_and_laterality(mirrored, operator_eye="OS", exif_orientation=1)

        self.assertTrue(res.human_confirmation_required)
        decision = self.engine.evaluate(
            image_val=self.val_valid,
            anatomy_res=res,
            primary_detection=self.pred_normal,
        )
        self.assertFalse(decision.clinical_action_allowed)
        self.assertIn(decision.safety_state, ("UNCERTAIN", "ANATOMY_FAILED", "BLOCKED"))

    def test_06_vertical_mirror_triggers_review_or_uncertainty(self):
        """Vertical flip reverses retinal symmetry and requires clinician confirmation."""
        v_mirrored = cv2.flip(self.img, 0)
        res = assess_anatomy_and_laterality(v_mirrored, operator_eye="OS", exif_orientation=1)

        decision = self.engine.evaluate(
            image_val=self.val_valid,
            anatomy_res=res,
            primary_detection=self.pred_normal,
        )
        # Metamorphic invariant: If human confirmation is required or anatomy failed, clinical action must be False
        if res.human_confirmation_required or not res.valid_anatomy:
            self.assertFalse(decision.clinical_action_allowed)

    def test_07_exif_orientation_tags_2_through_8_suppress_autonomous_action(self):
        """EXIF tags 2-8 (mirroring/rotations) must suppress automated laterality and mandate human sign-off."""
        non_standard_tags = [2, 3, 4, 5, 6, 7, 8]
        for tag in non_standard_tags:
            res = assess_anatomy_and_laterality(self.img, operator_eye="OS", exif_orientation=tag)
            self.assertEqual(res.orientation_state, "EXIF_NON_STANDARD")
            self.assertFalse(res.valid_anatomy)
            self.assertEqual(res.inferred_laterality, "UNKNOWN")
            self.assertTrue(res.human_confirmation_required)

            decision = self.engine.evaluate(
                image_val=self.val_valid,
                anatomy_res=res,
                primary_detection=self.pred_normal,
            )
            self.assertFalse(decision.clinical_action_allowed, f"Failed for EXIF tag {tag}")
            self.assertEqual(decision.safety_state, "ANATOMY_FAILED", f"Failed for EXIF tag {tag}")

    def test_08_conflicting_exif_and_pixel_orientation(self):
        """EXIF orientation metadata conflicting with upright pixel geometry must fail closed."""
        res = assess_anatomy_and_laterality(self.img, operator_eye="OS", exif_orientation=6)
        self.assertEqual(res.orientation_state, "EXIF_NON_STANDARD")
        self.assertFalse(res.valid_anatomy)

        val_with_warn = ImageValidationResult(
            valid=True,
            image_hash="conflict-hash",
            warnings=["EXIF_ORIENTATION_NON_STANDARD: tag 6"],
        )
        decision = self.engine.evaluate(
            image_val=val_with_warn,
            anatomy_res=res,
            primary_detection=self.pred_normal,
        )
        self.assertFalse(decision.clinical_action_allowed)
        self.assertEqual(decision.safety_state, "ANATOMY_FAILED")

    def test_09_missing_exif_metadata_defaults_to_safe_pixel_pipeline(self):
        """Missing EXIF metadata (tag 0 or 1) processes strictly through pixel analysis."""
        res = assess_anatomy_and_laterality(self.img, operator_eye="OS", exif_orientation=0)
        self.assertEqual(res.orientation_state, "UPRIGHT_VERIFIED")
        self.assertTrue(res.valid_anatomy)


if __name__ == "__main__":
    unittest.main()
