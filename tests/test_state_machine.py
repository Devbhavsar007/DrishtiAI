"""
Unit Tests for Gate 4: Screening State Machine with First-Class Failure States.
Validates:
  1. Complete Golden Path lifecycle transitions
  2. Failure states: QUALITY_FAILED, ANATOMY_FAILED, SCREENING_UNCERTAIN, OOD_REVIEW
  3. Recovery, operator override, and sync failure transitions
  4. Illegal transition prevention (InvalidStateTransitionError)
  5. Audit history tracking across transitions
"""

import unittest
from engine.safety.state_machine import (
    ScreeningState,
    ScreeningStateMachine,
    InvalidStateTransitionError,
)


class TestScreeningStateMachine(unittest.TestCase):
    def setUp(self):
        self.sm = ScreeningStateMachine(
            session_id="session-test-01",
            patient_id="P-0001",
            operator_id="operator-ashok",
        )

    def test_01_golden_path_lifecycle(self):
        """Verify seamless state progression through standard golden path."""
        self.assertEqual(self.sm.current_state, ScreeningState.CREATED)

        self.sm.transition_to(ScreeningState.CAPTURED, "operator-ashok", "OPERATOR")
        self.sm.transition_to(ScreeningState.VALIDATING_IMAGE, "sys-validator", "SYSTEM")
        self.sm.transition_to(ScreeningState.QUALITY_PASSED, "sys-iqa", "SYSTEM")
        self.sm.transition_to(ScreeningState.ANATOMY_VALIDATED, "sys-anatomy", "SYSTEM")
        self.sm.transition_to(ScreeningState.SCREENING_RUNNING, "sys-inference", "SYSTEM")
        self.sm.transition_to(ScreeningState.SCREENING_COMPLETED, "sys-detector", "SYSTEM")
        self.sm.transition_to(ScreeningState.RISK_ASSESSED, "sys-triage", "SYSTEM")
        self.sm.transition_to(ScreeningState.DOCTOR_REVIEW, "operator-ashok", "OPERATOR")
        self.sm.transition_to(ScreeningState.FINALIZED, "dr-sharma", "DOCTOR", "Approved with routine 12m follow-up")
        self.sm.transition_to(ScreeningState.SYNC_PENDING, "sys-sync", "SYSTEM")
        self.sm.transition_to(ScreeningState.SYNCED, "sys-sync", "SYSTEM")

        self.assertEqual(self.sm.current_state, ScreeningState.SYNCED)
        self.assertEqual(len(self.sm.history), 12)  # Initial + 11 transitions

    def test_02_quality_failure_and_recapture(self):
        """Verify image quality failure correctly routes to RECAPTURE_REQUESTED."""
        self.sm.transition_to(ScreeningState.CAPTURED, "operator-ashok")
        self.sm.transition_to(ScreeningState.VALIDATING_IMAGE, "sys-validator")
        self.sm.transition_to(ScreeningState.QUALITY_FAILED, "sys-iqa", "SYSTEM", "Severe cataract blur")

        self.assertEqual(self.sm.current_state, ScreeningState.QUALITY_FAILED)
        self.sm.transition_to(ScreeningState.RECAPTURE_REQUESTED, "sys-iqa")
        self.sm.transition_to(ScreeningState.CAPTURED, "operator-ashok", "OPERATOR", "New image taken with increased flash")

        self.assertEqual(self.sm.current_state, ScreeningState.CAPTURED)

    def test_03_anatomy_failure_and_operator_override(self):
        """Verify anatomy conflict requires operator override before proceeding."""
        self.sm.transition_to(ScreeningState.CAPTURED, "operator-ashok")
        self.sm.transition_to(ScreeningState.VALIDATING_IMAGE, "sys-validator")
        self.sm.transition_to(ScreeningState.QUALITY_PASSED, "sys-iqa")
        self.sm.transition_to(ScreeningState.ANATOMY_FAILED, "sys-anatomy", "SYSTEM", "Laterality mismatch suspected")

        self.assertEqual(self.sm.current_state, ScreeningState.ANATOMY_FAILED)
        self.sm.transition_to(ScreeningState.OPERATOR_OVERRIDE_PENDING, "sys-anatomy")
        
        # Operator confirms eye selection
        self.sm.transition_to(
            ScreeningState.ANATOMY_VALIDATED,
            "operator-ashok",
            "OPERATOR",
            "Confirmed OD despite mirrored fundus camera setting"
        )
        self.assertEqual(self.sm.current_state, ScreeningState.ANATOMY_VALIDATED)

    def test_04_screening_uncertain_and_ood_review(self):
        """Verify low confidence or OOD transitions to screening uncertain and OOD review."""
        self.sm.transition_to(ScreeningState.CAPTURED, "operator-ashok")
        self.sm.transition_to(ScreeningState.VALIDATING_IMAGE, "sys-validator")
        self.sm.transition_to(ScreeningState.QUALITY_PASSED, "sys-iqa")
        self.sm.transition_to(ScreeningState.ANATOMY_VALIDATED, "sys-anatomy")
        self.sm.transition_to(ScreeningState.SCREENING_RUNNING, "sys-inference")
        self.sm.transition_to(ScreeningState.SCREENING_UNCERTAIN, "safety-engine", "SYSTEM", "Model disagreement")
        self.sm.transition_to(ScreeningState.OOD_REVIEW, "safety-engine", "SYSTEM", "High distribution shift")
        self.sm.transition_to(ScreeningState.DOCTOR_REVIEW, "operator-ashok", "OPERATOR")

        self.assertEqual(self.sm.current_state, ScreeningState.DOCTOR_REVIEW)

    def test_05_sync_failure_and_conflict_handling(self):
        """Verify network sync drop routes to SYNC_FAILED and conflict state."""
        self.sm.transition_to(ScreeningState.CAPTURED, "operator-ashok")
        self.sm.transition_to(ScreeningState.VALIDATING_IMAGE, "sys-validator")
        self.sm.transition_to(ScreeningState.QUALITY_PASSED, "sys-iqa")
        self.sm.transition_to(ScreeningState.ANATOMY_VALIDATED, "sys-anatomy")
        self.sm.transition_to(ScreeningState.SCREENING_RUNNING, "sys-inference")
        self.sm.transition_to(ScreeningState.SCREENING_COMPLETED, "sys-detector")
        self.sm.transition_to(ScreeningState.FINALIZED, "dr-sharma", "DOCTOR")
        self.sm.transition_to(ScreeningState.SYNC_PENDING, "sys-sync")
        self.sm.transition_to(ScreeningState.SYNC_FAILED, "sys-sync", "SYSTEM", "HTTP 503 Gateway Timeout")

        self.assertEqual(self.sm.current_state, ScreeningState.SYNC_FAILED)
        self.sm.transition_to(ScreeningState.CONFLICT_REQUIRES_REVIEW, "sys-sync", "SYSTEM", "Version divergence")
        self.assertEqual(self.sm.current_state, ScreeningState.CONFLICT_REQUIRES_REVIEW)

    def test_06_illegal_transition_rejection(self):
        """State machine must raise InvalidStateTransitionError on illegal skips."""
        with self.assertRaises(InvalidStateTransitionError):
            # Cannot jump directly from CREATED to FINALIZED without screening
            self.sm.transition_to(ScreeningState.FINALIZED, "hacker", "ATTACKER")


if __name__ == "__main__":
    unittest.main()
