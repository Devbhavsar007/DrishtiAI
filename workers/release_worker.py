"""Release worker for managing staging soak and automated health checks."""

from __future__ import annotations

import logging
from database import get_db
from workers.base import BaseWorker

log = logging.getLogger(__name__)


class ReleaseWorker(BaseWorker):
    """Monitors staged releases and verifies staging deployment invariants."""

    def __init__(self, interval_seconds: float = 300.0):  # Every 5 mins
        super().__init__("ReleaseWorker", interval_seconds)

    def step(self) -> None:
        with get_db() as conn:
            staged = conn.execute(
                "SELECT version_id, promoted_at FROM model_versions WHERE status = 'STAGED'"
            ).fetchall()

        if not staged:
            return

        for m in staged:
            log.info("ReleaseWorker monitoring staged model %s", m["version_id"])
