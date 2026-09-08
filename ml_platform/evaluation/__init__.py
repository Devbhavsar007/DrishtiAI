"""Evaluation subpackage — metrics, safety gates, and regression testing."""

from ml_platform.evaluation.evaluator import (
    EvaluationResult,
    evaluate_predictions,
    compute_binary_metrics,
    compute_confusion_matrix,
    compute_per_class_metrics,
    compute_qwk,
    compute_ece,
)
from ml_platform.evaluation.regression import compare_models
from ml_platform.evaluation.safety_gates import evaluate_safety_gates

__all__ = [
    "EvaluationResult",
    "evaluate_predictions",
    "compute_binary_metrics",
    "compute_confusion_matrix",
    "compute_per_class_metrics",
    "compute_qwk",
    "compute_ece",
    "compare_models",
    "evaluate_safety_gates",
]
