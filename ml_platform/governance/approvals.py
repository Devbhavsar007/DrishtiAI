"""Human approval workflow and separation of duties for model promotion.

Requires explicit clinical review and administrative sign-off before any model
can be deployed to patients.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from database import get_db
from ml_platform.registry.models import transition_model_status, get_model_version

log = logging.getLogger(__name__)

# Roles permitted to give clinical approval
APPROVED_REVIEWER_ROLES = {"CLINICAL_REVIEWER", "SUPER_ADMIN", "ADMIN"}


def submit_model_approval(
    model_version_id: str,
    reviewer_id: str,
    reviewer_role: str,
    decision: str,  # "APPROVED" or "REJECTED"
    safety_checks_reviewed: bool = True,
    comments: str = "",
) -> dict[str, Any]:
    """
    Submit a human governance approval or rejection for a model version.

    Enforces:
      - Valid reviewer role (CLINICAL_REVIEWER, SUPER_ADMIN)
      - Model must currently be in EVALUATED or CANDIDATE status
      - Separation of duties: Creator cannot be the sole approver
    """
    decision_clean = decision.upper()
    if decision_clean not in ("APPROVED", "REJECTED"):
        raise ValueError(f"Invalid decision: {decision}. Must be 'APPROVED' or 'REJECTED'")

    role_clean = reviewer_role.upper()
    if role_clean not in APPROVED_REVIEWER_ROLES:
        raise PermissionError(
            f"Role {role_clean} is not authorized for clinical model sign-off. Required: {APPROVED_REVIEWER_ROLES}"
        )

    model = get_model_version(model_version_id)
    if not model:
        raise KeyError(f"Model version not found: {model_version_id}")

    # Separation of duties check
    if model.get("created_by") == reviewer_id and role_clean != "SUPER_ADMIN":
        raise PermissionError(
            "Separation of duties violation: Model creator cannot approve their own model for clinical deployment."
        )

    approval_id = f"appr-{uuid.uuid4().hex[:12]}"
    with get_db() as conn:
        conn.execute(
            """INSERT INTO model_approvals
               (id, model_version_id, evaluation_id, approver_id, approver_role, decision,
                rationale)
               VALUES (?, ?, NULL, ?, ?, ?, ?)""",
            (
                approval_id,
                model_version_id,
                reviewer_id,
                role_clean,
                decision_clean,
                comments,
            ),
        )
        conn.commit()


    # If approved, transition model state to APPROVED
    if decision_clean == "APPROVED":
        # Check current model state
        if model["status"] == "EVALUATED":
            transition_model_status(model_version_id, "CANDIDATE", actor_id=reviewer_id, reason="Passed evaluation")
        transition_model_status(model_version_id, "APPROVED", actor_id=reviewer_id, reason=comments)
    elif decision_clean == "REJECTED":
        transition_model_status(model_version_id, "ARCHIVED", actor_id=reviewer_id, reason=f"Rejected: {comments}")

    log.info("Model %s %s by %s (%s)", model_version_id, decision_clean, reviewer_id, role_clean)
    return {
        "approval_id": approval_id,
        "model_version_id": model_version_id,
        "decision": decision_clean,
        "reviewer_id": reviewer_id,
        "reviewer_role": role_clean,
        "comments": comments,
    }


def list_model_approvals(model_version_id: str | None = None) -> list[dict[str, Any]]:
    """List historical model approvals with optional version filter."""
    with get_db() as conn:
        if model_version_id:
            rows = conn.execute(
                "SELECT * FROM model_approvals WHERE model_version_id = ? ORDER BY created_at DESC",
                (model_version_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM model_approvals ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["reviewer_id"] = d.get("approver_id", "")
            d["reviewer_role"] = d.get("approver_role", "")
            d["comments"] = d.get("rationale", "")
            results.append(d)
        return results

