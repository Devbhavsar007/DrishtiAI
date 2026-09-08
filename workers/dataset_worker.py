"""Dataset worker for scheduled dataset compilation."""

from __future__ import annotations

import logging
from workers.base import BaseWorker
from config_admin import ENABLE_AUTO_DATASET_BUILD
from ml_platform.datasets.builder import build_dataset

log = logging.getLogger(__name__)


class DatasetWorker(BaseWorker):
    """Periodically snapshots verified clinical scans into monthly training datasets."""

    def __init__(self, interval_seconds: float = 3600.0):
        super().__init__("DatasetWorker", interval_seconds)

    def step(self) -> None:
        if not ENABLE_AUTO_DATASET_BUILD:
            return

        log.info("DatasetWorker running periodic dataset build check...")
        try:
            res = build_dataset(name="drishti-periodic", triggered_by="DatasetWorker")
            log.info("DatasetWorker build result: %s", res.get("status"))
        except Exception as e:
            log.warning("DatasetWorker periodic build error: %s", e)
