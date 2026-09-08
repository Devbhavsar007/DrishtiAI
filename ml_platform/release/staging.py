"""Staging and shadow validation pipeline for pre-release verification.

Allows a model to be deployed to a non-clinical staging environment to run
canary or smoke checks before final production promotion.
"""

from __future__ import annotations

import logging
from typing import Any

from database import get_db
from ml_platform.registry.models import transition_model_status, get_model_version

log = logging.getLogger(__name__)


def stage_candidate_model(
    model_version_id: str,
    staged_by: str,
    notes: str = "Staging deployment for canary smoke testing",
) -> dict[str, Any]:
    """
    Transition an approved model to STAGED status.
    """
    model = get_model_version(model_version_id)
    if not model:
        raise KeyError(f"Model version {model_version_id} not found")

    if model["status"] != "APPROVED":
        raise ValueError(f"Model must be in APPROVED status to stage, currently {model['status']}")

    transition_model_status(
        model_version_id,
        "STAGED",
        actor_id=staged_by,
        reason=notes,
    )

    log.info("Model %s staged by %s", model_version_id, staged_by)
    return {
        "model_version_id": model_version_id,
        "status": "STAGED",
        "staged_by": staged_by,
        "notes": notes,
    }
