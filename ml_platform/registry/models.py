"""Model registry for the DrishtiAI Intelligence Control Plane.

Governs immutable model versions and tracks lifecycle state transitions:
  EXPERIMENTAL → TRAINED → EVALUATED → CANDIDATE → APPROVED → STAGED → PRODUCTION → ARCHIVED
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from database import get_db

log = logging.getLogger(__name__)

VALID_STATUSES = {
    "EXPERIMENTAL",
    "TRAINED",
    "EVALUATED",
    "CANDIDATE",
    "APPROVED",
    "STAGED",
    "PRODUCTION",
    "ARCHIVED",
}

VALID_TRANSITIONS = {
    "EXPERIMENTAL": {"TRAINED", "ARCHIVED"},
    "TRAINED": {"EVALUATED", "ARCHIVED"},
    "EVALUATED": {"CANDIDATE", "ARCHIVED"},
    "CANDIDATE": {"APPROVED", "ARCHIVED"},
    "APPROVED": {"STAGED", "PRODUCTION", "ARCHIVED"},
    "STAGED": {"PRODUCTION", "ARCHIVED"},
    "PRODUCTION": {"ARCHIVED"},
    "ARCHIVED": set(),
}


def register_model_version(
    architecture: str,
    training_run_id: str | None = None,
    dataset_id: str | None = None,
    model_path: str = "",
    calibration_path: str = "",
    hyperparameters: dict[str, Any] | None = None,
    git_sha: str = "",
    created_by: str = "system",
    status: str = "TRAINED",
) -> dict[str, Any]:
    """Register a new immutable model version in the registry."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid initial model status: {status}")

    version_id = f"mv-{uuid.uuid4().hex[:12]}"
    version_tag = f"v-{uuid.uuid4().hex[:6]}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    # Use None instead of empty string for optional foreign keys to respect FK constraints
    run_fk = training_run_id if training_run_id else None
    ds_fk = dataset_id if dataset_id else None

    with get_db() as conn:
        conn.execute(
            """INSERT INTO model_versions
               (version_id, version_tag, training_run_id, dataset_id, architecture,
                weights_path, calibration_path, evaluation_summary_json,
                created_by, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                version_id,
                version_tag,
                run_fk,
                ds_fk,
                architecture,
                model_path,
                calibration_path,
                json.dumps(hyperparameters or {}),
                created_by,
                status,
            ),
        )
        conn.commit()

    log.info("Registered model version %s (id=%s, status=%s)", version_tag, version_id, status)

    return {
        "version_id": version_id,
        "version_tag": version_tag,
        "architecture": architecture,
        "training_run_id": training_run_id,
        "dataset_id": dataset_id,
        "status": status,
        "created_by": created_by,
    }


def transition_model_status(
    version_id: str,
    target_status: str,
    actor_id: str = "system",
    reason: str = "",
) -> dict[str, Any]:
    """Transition a model version to a new lifecycle state with state validation."""
    target_status = target_status.upper()
    if target_status not in VALID_STATUSES:
        raise ValueError(f"Invalid target status: {target_status}")

    with get_db() as conn:
        row = conn.execute(
            "SELECT status FROM model_versions WHERE version_id = ?",
            (version_id,),
        ).fetchone()

        if not row:
            raise KeyError(f"Model version not found: {version_id}")

        current_status = row["status"]
        allowed = VALID_TRANSITIONS.get(current_status, set())

        # Allow admin bypass to ARCHIVED from any active status
        if target_status not in allowed and target_status != "ARCHIVED":
            raise ValueError(
                f"Illegal transition: {current_status} → {target_status}. Allowed: {sorted(list(allowed))}"
            )

        # If promoting to PRODUCTION, demote existing production models to ARCHIVED
        if target_status == "PRODUCTION":
            conn.execute(
                "UPDATE model_versions SET status = 'ARCHIVED' WHERE status = 'PRODUCTION'"
            )

        conn.execute(
            "UPDATE model_versions SET status = ? WHERE version_id = ?",
            (target_status, version_id),
        )
        conn.commit()

    log.info("Model %s transitioned %s → %s by %s", version_id, current_status, target_status, actor_id)
    return {
        "version_id": version_id,
        "previous_status": current_status,
        "new_status": target_status,
        "actor_id": actor_id,
        "reason": reason,
    }


def get_model_version(version_id: str) -> dict[str, Any] | None:
    """Fetch model version record by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM model_versions WHERE version_id = ?",
            (version_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["model_path"] = d.get("weights_path", "")
        return d


def get_production_model() -> dict[str, Any] | None:
    """Fetch the currently active PRODUCTION model version."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM model_versions WHERE status = 'PRODUCTION' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["model_path"] = d.get("weights_path", "")
        return d


def list_model_versions(status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """List model versions with optional status filtering."""
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM model_versions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status.upper(), limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM model_versions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["model_path"] = d.get("weights_path", "")
            result.append(d)
        return result

