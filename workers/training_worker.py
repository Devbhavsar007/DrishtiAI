"""Training worker for processing queued training runs."""

from __future__ import annotations

import json
import logging
from database import get_db
from workers.base import BaseWorker
from ml_platform.training.orchestrator import _execute_training, TrainingJobConfig

log = logging.getLogger(__name__)


class TrainingWorker(BaseWorker):
    """Polls database for training_runs in QUEUED state and triggers execution."""

    def __init__(self, interval_seconds: float = 15.0):
        super().__init__("TrainingWorker", interval_seconds)

    def step(self) -> None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, dataset_id, config_json FROM training_runs WHERE status = 'QUEUED' ORDER BY created_at ASC LIMIT 1"
            ).fetchone()

        if not row:
            return

        run_id = row["id"]
        log.info("TrainingWorker picking up queued run %s", run_id)
        try:
            cfg_dict = json.loads(row["config_json"]) if row["config_json"] else {}
            cfg = TrainingJobConfig(dataset_id=row["dataset_id"], **cfg_dict)
            _execute_training(run_id, cfg)
        except Exception as e:
            log.error("Failed to execute training run %s: %s", run_id, e)
