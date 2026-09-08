"""Training configurations and preset profiles.

Provides standardized hyperparameters for different deployment environments
(local testing, development, production retraining).
"""

from __future__ import annotations

from typing import Any
from ml_platform.training.orchestrator import TrainingJobConfig


PRESET_CONFIGS: dict[str, dict[str, Any]] = {
    "quick_test": {
        "max_iterations": 1,
        "epochs_head": 1,
        "epochs_partial": 1,
        "epochs_full": 1,
        "batch_size": 4,
        "img_size": 224,
        "target_sensitivity": 0.80,
        "target_specificity": 0.75,
        "use_lesion_features": False,
    },
    "standard_retina": {
        "max_iterations": 4,
        "epochs_head": 3,
        "epochs_partial": 5,
        "epochs_full": 6,
        "batch_size": 8,
        "img_size": 300,
        "target_sensitivity": 0.90,
        "target_specificity": 0.85,
        "use_lesion_features": True,
    },
    "high_precision": {
        "max_iterations": 6,
        "epochs_head": 4,
        "epochs_partial": 6,
        "epochs_full": 8,
        "batch_size": 16,
        "img_size": 384,
        "target_sensitivity": 0.92,
        "target_specificity": 0.88,
        "use_lesion_features": True,
    },
}


def get_preset_config(preset_name: str, dataset_id: str, **overrides: Any) -> TrainingJobConfig:
    """Retrieve a TrainingJobConfig populated with preset defaults and applied overrides."""
    base = PRESET_CONFIGS.get(preset_name, PRESET_CONFIGS["standard_retina"]).copy()
    base["dataset_id"] = dataset_id
    base.update(overrides)
    return TrainingJobConfig(**base)
