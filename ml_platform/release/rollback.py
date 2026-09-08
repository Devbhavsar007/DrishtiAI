"""Emergency and automated rollback mechanisms for production models.

Enables instant restoration of previous stable models upon safety or drift incidents.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from typing import Any

from database import get_db
from config_admin import PRODUCTION_MODELS_DIR
from ml_platform.registry.models import transition_model_status, get_model_version

log = logging.getLogger(__name__)


def rollback_production_model(
    target_version_id: str | None = None,
    authorized_by: str = "security_admin",
    incident_reason: str = "Rollback triggered due to safety gate or drift threshold breach",
) -> dict[str, Any]:
    """
    Rollback active production model to a target version or previous deployed version.
    """
    with get_db() as conn:
        # Identify current production model
        curr_row = conn.execute(
            "SELECT version_id FROM model_versions WHERE status = 'PRODUCTION' LIMIT 1"
        ).fetchone()
        curr_prod_id = curr_row["version_id"] if curr_row else None

        # Find candidate target for rollback if not explicitly provided
        if not target_version_id:
            dep_row = conn.execute(
                """SELECT model_version_id FROM deployments
                   WHERE status = 'ACTIVE' AND model_version_id != ?
                   ORDER BY deployed_at DESC LIMIT 1""",
                (curr_prod_id or "",),
            ).fetchone()
            if not dep_row:
                # Fallback to any ARCHIVED or APPROVED model
                arch_row = conn.execute(
                    "SELECT version_id FROM model_versions WHERE status IN ('ARCHIVED', 'APPROVED') ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                if not arch_row:
                    raise RuntimeError("No suitable prior model found for rollback")
                target_version_id = arch_row["version_id"]
            else:
                target_version_id = dep_row["model_version_id"]

    target_model = get_model_version(target_version_id)
    if not target_model:
        raise KeyError(f"Target rollback model version {target_version_id} not found")

    # Demote current production model if present
    if curr_prod_id:
        with get_db() as conn:
            conn.execute(
                "UPDATE model_versions SET status = 'ARCHIVED' WHERE version_id = ?",
                (curr_prod_id,),
            )
            conn.commit()

    # Promote target version to PRODUCTION
    with get_db() as conn:
        conn.execute(
            "UPDATE model_versions SET status = 'PRODUCTION' WHERE version_id = ?",
            (target_version_id,),
        )
        conn.commit()

    # Copy target model weights back to production
    src_weights = target_model.get("model_path")
    if src_weights and os.path.isfile(src_weights):
        shutil.copy2(src_weights, os.path.join(PRODUCTION_MODELS_DIR, "best_model.pt"))

    src_calib = target_model.get("calibration_path")
    if src_calib and os.path.isfile(src_calib):
        shutil.copy2(src_calib, os.path.join(PRODUCTION_MODELS_DIR, "calibration.json"))

    # Record deployment event
    dep_id = f"dep-{uuid.uuid4().hex[:12]}"
    with get_db() as conn:
        conn.execute(
            """INSERT INTO deployments
               (id, model_version_id, environment, approval_id, deployed_by, status, previous_version_id, rollback_reason)
               VALUES (?, ?, 'production', NULL, ?, 'ROLLED_BACK', ?, ?)""",
            (
                dep_id,
                target_version_id,
                authorized_by,
                curr_prod_id if curr_prod_id else None,
                incident_reason,
            ),
        )
        conn.commit()



    log.warning(
        "ROLLBACK COMPLETE: Restored %s to PRODUCTION (replaced %s). Authorized by: %s",
        target_version_id, curr_prod_id, authorized_by
    )

    return {
        "status": "ROLLED_BACK",
        "restored_version_id": target_version_id,
        "demoted_version_id": curr_prod_id,
        "deployment_id": dep_id,
        "authorized_by": authorized_by,
        "reason": incident_reason,
    }
