"""Training subpackage — orchestrator, configs, job management."""

from ml_platform.training.orchestrator import (
    TrainingJobConfig,
    submit_training_job,
    get_training_job_status,
    cancel_training_job,
    list_training_jobs,
)
from ml_platform.training.configs import PRESET_CONFIGS, get_preset_config

__all__ = [
    "TrainingJobConfig",
    "submit_training_job",
    "get_training_job_status",
    "cancel_training_job",
    "list_training_jobs",
    "PRESET_CONFIGS",
    "get_preset_config",
]
