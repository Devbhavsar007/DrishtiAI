"""
Screening Session State Machine for DrishtiAI.

Models the complete clinical screening lifecycle with FIRST-CLASS FAILURE STATES:
  Success States:
    CREATED -> CAPTURED -> VALIDATING_IMAGE -> ANATOMY_VALIDATED ->
    SCREENING_RUNNING -> SCREENING_COMPLETED -> RISK_ASSESSED ->
    DOCTOR_REVIEW -> FINALIZED -> SYNC_PENDING -> SYNCED

  Failure / Interruption / Review States:
    QUALITY_FAILED (triggers RECAPTURE_REQUESTED)
    ANATOMY_FAILED (triggers OPERATOR_OVERRIDE_PENDING)
    SCREENING_UNCERTAIN (triggers OOD_REVIEW or specialist triage)
    OOD_REVIEW
    SYNC_FAILED (triggers CONFLICT_REQUIRES_REVIEW)
    RECOVERY_REQUIRED
    CANCELLED
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any


class ScreeningState:
    CREATED = "CREATED"
    CAPTURED = "CAPTURED"
    VALIDATING_IMAGE = "VALIDATING_IMAGE"
    QUALITY_PASSED = "QUALITY_PASSED"
    QUALITY_FAILED = "QUALITY_FAILED"
    RECAPTURE_REQUESTED = "RECAPTURE_REQUESTED"
    ANATOMY_VALIDATED = "ANATOMY_VALIDATED"
    ANATOMY_FAILED = "ANATOMY_FAILED"
    OPERATOR_OVERRIDE_PENDING = "OPERATOR_OVERRIDE_PENDING"
    SCREENING_RUNNING = "SCREENING_RUNNING"
    SCREENING_COMPLETED = "SCREENING_COMPLETED"
    SCREENING_UNCERTAIN = "SCREENING_UNCERTAIN"
    OOD_REVIEW = "OOD_REVIEW"
    RISK_ASSESSED = "RISK_ASSESSED"
    DOCTOR_REVIEW = "DOCTOR_REVIEW"
    FINALIZED = "FINALIZED"
    SYNC_PENDING = "SYNC_PENDING"
    SYNCED = "SYNCED"
    SYNC_FAILED = "SYNC_FAILED"
    CONFLICT_REQUIRES_REVIEW = "CONFLICT_REQUIRES_REVIEW"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    CANCELLED = "CANCELLED"


# Deterministic transition table
ALLOWED_TRANSITIONS: Dict[str, set[str]] = {
    ScreeningState.CREATED: {
        ScreeningState.CAPTURED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.CAPTURED: {
        ScreeningState.VALIDATING_IMAGE,
        ScreeningState.QUALITY_FAILED,
        ScreeningState.RECOVERY_REQUIRED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.VALIDATING_IMAGE: {
        ScreeningState.QUALITY_PASSED,
        ScreeningState.QUALITY_FAILED,
        ScreeningState.ANATOMY_VALIDATED,
        ScreeningState.ANATOMY_FAILED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.QUALITY_PASSED: {
        ScreeningState.ANATOMY_VALIDATED,
        ScreeningState.ANATOMY_FAILED,
        ScreeningState.SCREENING_RUNNING,
        ScreeningState.CANCELLED,
    },
    ScreeningState.QUALITY_FAILED: {
        ScreeningState.RECAPTURE_REQUESTED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.RECAPTURE_REQUESTED: {
        ScreeningState.CAPTURED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.ANATOMY_VALIDATED: {
        ScreeningState.SCREENING_RUNNING,
        ScreeningState.CANCELLED,
    },
    ScreeningState.ANATOMY_FAILED: {
        ScreeningState.OPERATOR_OVERRIDE_PENDING,
        ScreeningState.RECAPTURE_REQUESTED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.OPERATOR_OVERRIDE_PENDING: {
        ScreeningState.ANATOMY_VALIDATED,  # Confirmed by operator
        ScreeningState.RECAPTURE_REQUESTED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.SCREENING_RUNNING: {
        ScreeningState.SCREENING_COMPLETED,
        ScreeningState.SCREENING_UNCERTAIN,
        ScreeningState.OOD_REVIEW,
        ScreeningState.RECOVERY_REQUIRED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.SCREENING_COMPLETED: {
        ScreeningState.RISK_ASSESSED,
        ScreeningState.DOCTOR_REVIEW,
        ScreeningState.FINALIZED,
    },
    ScreeningState.SCREENING_UNCERTAIN: {
        ScreeningState.DOCTOR_REVIEW,
        ScreeningState.OOD_REVIEW,
        ScreeningState.RISK_ASSESSED,
    },
    ScreeningState.OOD_REVIEW: {
        ScreeningState.DOCTOR_REVIEW,
        ScreeningState.RECAPTURE_REQUESTED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.RISK_ASSESSED: {
        ScreeningState.DOCTOR_REVIEW,
        ScreeningState.FINALIZED,
    },
    ScreeningState.DOCTOR_REVIEW: {
        ScreeningState.FINALIZED,
        ScreeningState.RECAPTURE_REQUESTED,
        ScreeningState.CANCELLED,
    },
    ScreeningState.FINALIZED: {
        ScreeningState.SYNC_PENDING,
        ScreeningState.SYNCED,
    },
    ScreeningState.SYNC_PENDING: {
        ScreeningState.SYNCED,
        ScreeningState.SYNC_FAILED,
    },
    ScreeningState.SYNC_FAILED: {
        ScreeningState.SYNC_PENDING,  # Retry
        ScreeningState.CONFLICT_REQUIRES_REVIEW,
    },
    ScreeningState.CONFLICT_REQUIRES_REVIEW: {
        ScreeningState.FINALIZED,     # Re-finalized after review
        ScreeningState.SYNC_PENDING,
    },
    ScreeningState.RECOVERY_REQUIRED: {
        ScreeningState.CAPTURED,
        ScreeningState.SCREENING_RUNNING,
        ScreeningState.CANCELLED,
    },
    ScreeningState.CANCELLED: set(),  # Terminal state
    ScreeningState.SYNCED: set(),     # Terminal state
}


class InvalidStateTransitionError(Exception):
    """Raised when an illegal transition is attempted."""
    pass


class ScreeningStateMachine:
    """
    State machine instance for a single screening session.
    Preserves audit history and rejects invalid lifecycle mutations.
    """

    def __init__(
        self,
        session_id: str,
        patient_id: str,
        operator_id: str,
        initial_state: str = ScreeningState.CREATED,
    ):
        self.session_id = session_id
        self.patient_id = patient_id
        self.operator_id = operator_id
        self.current_state = initial_state
        self.history: List[Dict[str, Any]] = [
            {
                "from_state": None,
                "to_state": initial_state,
                "actor_id": operator_id,
                "actor_role": "OPERATOR",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "Session initialized",
            }
        ]

    def can_transition_to(self, target_state: str) -> bool:
        """Check if transition is allowable under current state."""
        allowed = ALLOWED_TRANSITIONS.get(self.current_state, set())
        return target_state in allowed

    def transition_to(
        self,
        target_state: str,
        actor_id: str,
        actor_role: str = "OPERATOR",
        reason: Optional[str] = None,
    ) -> str:
        """
        Transition session to target state or raise InvalidStateTransitionError.
        """
        if not self.can_transition_to(target_state):
            raise InvalidStateTransitionError(
                f"Cannot transition screening session {self.session_id} from "
                f"'{self.current_state}' to '{target_state}'. "
                f"Permitted next states: {sorted(list(ALLOWED_TRANSITIONS.get(self.current_state, [])))}"
            )

        previous_state = self.current_state
        self.current_state = target_state

        event = {
            "from_state": previous_state,
            "to_state": target_state,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason or f"Transitioned from {previous_state} to {target_state}",
        }
        self.history.append(event)
        return self.current_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "patient_id": self.patient_id,
            "operator_id": self.operator_id,
            "current_state": self.current_state,
            "total_transitions": len(self.history),
            "history": self.history,
        }
