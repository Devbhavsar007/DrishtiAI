"""Drift detection background worker."""

from __future__ import annotations

import logging
from workers.base import BaseWorker
from config_admin import ENABLE_DRIFT_MONITORING
from ml_platform.drift.clinical_drift import evaluate_clinical_discordance

log = logging.getLogger(__name__)


class DriftWorker(BaseWorker):
    """Periodically evaluates clinical discordance and data drift."""

    def __init__(self, interval_seconds: float = 1800.0):  # Every 30 mins
        super().__init__("DriftWorker", interval_seconds)

    def step(self) -> None:
        if not ENABLE_DRIFT_MONITORING:
            return

        log.info("DriftWorker running clinical discordance assessment...")
        try:
            res = evaluate_clinical_discordance(days=30, persist_event=True)
            if res.get("severity") in ("WARNING", "CRITICAL"):
                log.warning("DriftWorker detected clinical drift: %s", res)
        except Exception as e:
            log.warning("DriftWorker error during discordance check: %s", e)
