"""Configuration settings for the DrishtiAI Intelligence Control Plane.

Governs dataset building, training orchestration, evaluation safety gates,
model registry, drift monitoring, and admin access control.
"""

from __future__ import annotations

import os
from config import BASE_DIR, MODELS_DIR

# ---------------------------------------------------------------------------
# Directories & Storage
# ---------------------------------------------------------------------------
ML_PLATFORM_DIR = os.path.join(BASE_DIR, "ml_platform")
DATASETS_DIR = os.path.join(BASE_DIR, "data", "datasets")
REGISTRY_DIR = os.path.join(MODELS_DIR, "registry")
PRODUCTION_MODELS_DIR = os.path.join(MODELS_DIR, "production")
EVAL_REPORTS_DIR = os.path.join(BASE_DIR, "reports", "evaluations")
DRIFT_REPORTS_DIR = os.path.join(BASE_DIR, "reports", "drift")

for _d in [DATASETS_DIR, REGISTRY_DIR, PRODUCTION_MODELS_DIR, EVAL_REPORTS_DIR, DRIFT_REPORTS_DIR]:
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------------------
# Authentication & Security
# ---------------------------------------------------------------------------
INTELLIGENCE_ADMIN_SECRET = os.getenv("INTELLIGENCE_ADMIN_SECRET", "drishti-intelligence-admin-secret-2026")
ADMIN_JWT_EXPIRY_SECONDS = int(os.getenv("ADMIN_JWT_EXPIRY_SECONDS", "43200"))  # 12 hours

# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------
ENABLE_AUTO_DATASET_BUILD = os.getenv("ENABLE_AUTO_DATASET_BUILD", "false").lower() in ("true", "1", "yes")
ENABLE_ACTIVE_LEARNING_SAMPLING = os.getenv("ENABLE_ACTIVE_LEARNING_SAMPLING", "true").lower() in ("true", "1", "yes")
ENABLE_DRIFT_MONITORING = os.getenv("ENABLE_DRIFT_MONITORING", "true").lower() in ("true", "1", "yes")
ENABLE_AUTO_PROMOTION = os.getenv("ENABLE_AUTO_PROMOTION", "false").lower() in ("true", "1", "yes")  # Safety: requires human approval by default

# ---------------------------------------------------------------------------
# Safety Gates Thresholds
# ---------------------------------------------------------------------------
SAFETY_GATES = {
    "min_sensitivity": float(os.getenv("GATE_MIN_SENSITIVITY", "0.85")),
    "min_specificity": float(os.getenv("GATE_MIN_SPECIFICITY", "0.80")),
    "min_accuracy": float(os.getenv("GATE_MIN_ACCURACY", "0.75")),
    "min_qwk": float(os.getenv("GATE_MIN_QWK", "0.70")),
    "max_ece": float(os.getenv("GATE_MAX_ECE", "0.15")),
    "max_false_negative_rate": float(os.getenv("GATE_MAX_FNR", "0.10")),
    "max_regression_delta": float(os.getenv("GATE_MAX_REGRESSION_DELTA", "-0.03")),
}

# ---------------------------------------------------------------------------
# Drift Detection Thresholds
# ---------------------------------------------------------------------------
DRIFT_CONFIG = {
    "psi_warning": float(os.getenv("DRIFT_PSI_WARNING", "0.10")),
    "psi_critical": float(os.getenv("DRIFT_PSI_CRITICAL", "0.25")),
    "ks_pvalue_threshold": float(os.getenv("DRIFT_KS_PVALUE", "0.05")),
    "clinical_discordance_warning": float(os.getenv("DRIFT_DISCORDANCE_WARNING", "0.20")),
    "clinical_discordance_critical": float(os.getenv("DRIFT_DISCORDANCE_CRITICAL", "0.35")),
    "window_days": int(os.getenv("DRIFT_WINDOW_DAYS", "30")),
    "min_samples_for_drift": int(os.getenv("DRIFT_MIN_SAMPLES", "20")),
}

# ---------------------------------------------------------------------------
# Active Learning Sampling Config
# ---------------------------------------------------------------------------
AL_CONFIG = {
    "batch_size": int(os.getenv("AL_BATCH_SIZE", "50")),
    "entropy_weight": 0.35,
    "ood_weight": 0.25,
    "discordance_weight": 0.25,
    "rare_class_weight": 0.15,
}

# ---------------------------------------------------------------------------
# MLflow / Experiment Tracking
# ---------------------------------------------------------------------------
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", os.path.join(BASE_DIR, "mlruns"))
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "DrishtiAI-DR-Grading")
