"""Training orchestrator for the Intelligence Control Plane.

Wraps the existing training/loop_trainer.py to manage async job lifecycle:
  QUEUED → RUNNING → COMPLETED | FAILED

Persists all training metadata to the training_runs table.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class TrainingJobConfig:
    """Configuration for a training job."""
    dataset_id: str
    data_dir: str = "data/aptos"
    out_dir: str = "models/dr_pipeline"
    max_iterations: int = 6
    epochs_head: int = 4
    epochs_partial: int = 6
    epochs_full: int = 8
    batch_size: int = 8
    img_size: int = 300
    target_sensitivity: float = 0.90
    target_specificity: float = 0.85
    use_lesion_features: bool = True
    parent_checkpoint: str = ""
    git_sha: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Active training jobs (thread-safe tracking)
_active_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def submit_training_job(
    config: TrainingJobConfig,
    triggered_by: str = "system",
) -> dict[str, Any]:
    """
    Submit a new training job for asynchronous execution.

    Creates a training_runs record in QUEUED status, then launches
    a background thread to execute the training.

    Args:
        config: Training job configuration
        triggered_by: Actor who triggered the job

    Returns:
        Dict with run_id, status, config summary
    """
    from database import get_db

    run_id = f"run-{uuid.uuid4().hex[:12]}"

    # Persist to database
    with get_db() as conn:
        conn.execute(
            """INSERT INTO training_runs
               (id, dataset_id, status, config_json, parent_checkpoint,
                git_sha, triggered_by)
               VALUES (?, ?, 'QUEUED', ?, ?, ?, ?)""",
            (run_id, config.dataset_id, json.dumps(config.to_dict()),
             config.parent_checkpoint, config.git_sha, triggered_by)
        )
        conn.commit()

    # Launch background thread
    thread = threading.Thread(
        target=_execute_training,
        args=(run_id, config),
        name=f"training-{run_id}",
        daemon=True,
    )

    with _jobs_lock:
        _active_jobs[run_id] = {
            "thread": thread,
            "status": "QUEUED",
            "started_at": None,
        }

    thread.start()
    log.info("Training job %s submitted (dataset=%s, triggered_by=%s)",
             run_id, config.dataset_id, triggered_by)

    return {
        "run_id": run_id,
        "status": "QUEUED",
        "dataset_id": config.dataset_id,
        "config": config.to_dict(),
    }


def _execute_training(run_id: str, config: TrainingJobConfig) -> None:
    """Background execution of training job."""
    from database import get_db

    start_time = time.time()

    with _jobs_lock:
        if run_id in _active_jobs and _active_jobs[run_id]["status"] == "CANCELLED":
            log.info("Training job %s was cancelled before execution started", run_id)
            return
        if run_id in _active_jobs:
            _active_jobs[run_id]["status"] = "RUNNING"
            _active_jobs[run_id]["started_at"] = datetime.utcnow().isoformat()

    # Update status to RUNNING only if not already cancelled
    with get_db() as conn:
        conn.execute(
            "UPDATE training_runs SET status = 'RUNNING', started_at = datetime('now') WHERE id = ? AND status != 'CANCELLED'",
            (run_id,)
        )
        conn.commit()
        row = conn.execute("SELECT status FROM training_runs WHERE id = ?", (run_id,)).fetchone()
        if row and row["status"] == "CANCELLED":
            return

    try:
        # Import and configure the existing loop trainer
        from training.loop_trainer import LoopConfig, LoopTrainer

        loop_config = LoopConfig(
            data_dir=config.data_dir,
            out_dir=config.out_dir,
            max_iterations=config.max_iterations,
            epochs_head=config.epochs_head,
            epochs_partial=config.epochs_partial,
            epochs_full=config.epochs_full,
            batch_size=config.batch_size,
            img_size=config.img_size,
            target_sensitivity=config.target_sensitivity,
            target_specificity=config.target_specificity,
            use_lesion_features=config.use_lesion_features,
        )

        trainer = LoopTrainer(loop_config)
        trainer.run()

        # Collect results
        duration = round(time.time() - start_time, 2)
        history = loop_config.history if hasattr(loop_config, 'history') else []
        final_metrics = history[-1] if history else {}

        # Determine best checkpoint path
        from pathlib import Path
        best_ckpt = str(Path(config.out_dir) / "best_model.pt")
        calib_path = str(Path(config.out_dir) / "calibration.json")

        with get_db() as conn:
            conn.execute(
                """UPDATE training_runs SET
                   status = 'COMPLETED',
                   completed_at = datetime('now'),
                   duration_seconds = ?,
                   final_metrics_json = ?,
                   best_checkpoint_path = ?,
                   calibration_path = ?,
                   history_json = ?
                   WHERE id = ?""",
                (duration, json.dumps(final_metrics), best_ckpt, calib_path,
                 json.dumps(history), run_id)
            )
            conn.commit()

        with _jobs_lock:
            if run_id in _active_jobs:
                _active_jobs[run_id]["status"] = "COMPLETED"

        log.info("Training job %s completed in %.1fs", run_id, duration)

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        error_msg = f"{type(e).__name__}: {str(e)}"
        tb = traceback.format_exc()

        with get_db() as conn:
            conn.execute(
                """UPDATE training_runs SET
                   status = 'FAILED',
                   completed_at = datetime('now'),
                   duration_seconds = ?,
                   error_message = ?
                   WHERE id = ?""",
                (duration, f"{error_msg}\n{tb}", run_id)
            )
            conn.commit()

        with _jobs_lock:
            if run_id in _active_jobs:
                _active_jobs[run_id]["status"] = "FAILED"

        log.error("Training job %s failed after %.1fs: %s", run_id, duration, error_msg)


def get_training_run(run_id: str) -> dict | None:
    """Retrieve a training run record."""
    from database import get_db

    with get_db() as conn:
        row = conn.execute("SELECT * FROM training_runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for field_name in ['config_json', 'final_metrics_json', 'history_json']:
        try:
            d[field_name] = json.loads(d[field_name]) if d.get(field_name) else {}
        except (json.JSONDecodeError, TypeError):
            d[field_name] = {}
    return d


def list_training_runs(limit: int = 50) -> list[dict]:
    """List training runs, newest first."""
    from database import get_db

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM training_runs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()

    runs = []
    for row in rows:
        d = dict(row)
        for field_name in ['config_json', 'final_metrics_json']:
            try:
                d[field_name] = json.loads(d[field_name]) if d.get(field_name) else {}
            except (json.JSONDecodeError, TypeError):
                d[field_name] = {}
        runs.append(d)
    return runs


def get_active_jobs() -> list[dict]:
    """Get currently active training jobs."""
    with _jobs_lock:
        return [
            {"run_id": rid, "status": info["status"], "started_at": info.get("started_at")}
            for rid, info in _active_jobs.items()
            if info["status"] in ("QUEUED", "RUNNING")
        ]


# Aliases for consistent API naming
get_training_job_status = get_training_run
list_training_jobs = list_training_runs


def cancel_training_job(run_id: str) -> bool:
    """Mark a queued or running job as cancelled."""
    from database import get_db
    with _jobs_lock:
        if run_id in _active_jobs:
            _active_jobs[run_id]["status"] = "CANCELLED"
    with get_db() as conn:
        conn.execute("UPDATE training_runs SET status = 'CANCELLED' WHERE id = ?", (run_id,))
        conn.commit()
    return True

