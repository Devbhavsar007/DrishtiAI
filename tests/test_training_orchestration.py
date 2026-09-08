"""Tests for Training Orchestration and Job Lifecycle."""

import pytest
from ml_platform.training.configs import get_preset_config, PRESET_CONFIGS
from ml_platform.training.orchestrator import (
    TrainingJobConfig,
    submit_training_job,
    get_training_job_status,
    list_training_jobs,
    cancel_training_job,
)


def test_preset_configs():
    cfg = get_preset_config("quick_test", dataset_id="ds-test-123")
    assert cfg.dataset_id == "ds-test-123"
    assert cfg.max_iterations == 1
    assert cfg.epochs_head == 1

    cfg_std = get_preset_config("standard_retina", dataset_id="ds-test-456", batch_size=16)
    assert cfg_std.batch_size == 16
    assert cfg_std.dataset_id == "ds-test-456"


@pytest.fixture(autouse=True)
def setup_mock_datasets():
    from database import get_db
    with get_db() as conn:
        for ds_id in ["ds-mock-001", "ds-mock-002"]:
            conn.execute(
                "INSERT OR IGNORE INTO training_datasets (id, name, version) VALUES (?, ?, ?)",
                (ds_id, "mock-dataset", f"v1-{ds_id}"),
            )
        conn.commit()



def test_job_submission_and_status():
    cfg = TrainingJobConfig(dataset_id="ds-mock-001", max_iterations=1)
    res = submit_training_job(cfg, triggered_by="test_suite")

    assert res["status"] in ("QUEUED", "RUNNING", "COMPLETED", "FAILED")
    run_id = res["run_id"]

    status = get_training_job_status(run_id)
    assert status is not None
    assert status["id"] == run_id
    assert status["dataset_id"] == "ds-mock-001"


def test_job_cancellation():
    cfg = TrainingJobConfig(dataset_id="ds-mock-002", max_iterations=1)
    res = submit_training_job(cfg, triggered_by="test_suite")
    run_id = res["run_id"]

    cancelled = cancel_training_job(run_id)
    assert cancelled is True

    status = get_training_job_status(run_id)
    assert status["status"] == "CANCELLED"
