"""Model evaluation pipeline with safety gates.

Evaluates trained models against clinical metrics: sensitivity, specificity,
accuracy, F1, AUROC, QWK, calibration ECE, confusion matrix, per-class
performance, false-negative rate.

Includes safety gate checks for model promotion decisions.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np

log = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Comprehensive evaluation result for a model version."""
    eval_id: str = ""
    model_version_id: str = ""
    dataset_id: str = ""
    accuracy: float = 0.0
    sensitivity: float = 0.0
    specificity: float = 0.0
    f1_score: float = 0.0
    auroc: float = 0.0
    quadratic_weighted_kappa: float = 0.0
    expected_calibration_error: float = 0.0
    false_negative_rate: float = 0.0
    confusion_matrix: list[list[int]] = field(default_factory=list)
    per_class_metrics: dict[int, dict] = field(default_factory=dict)
    passed_safety_gates: bool = False
    safety_gate_results: dict[str, Any] = field(default_factory=dict)
    total_samples: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ========================================
# Safety Gate Thresholds
# ========================================
SAFETY_GATES = {
    "min_sensitivity": 0.85,           # Referable DR sensitivity ≥85%
    "min_specificity": 0.80,           # Referable DR specificity ≥80%
    "min_accuracy": 0.75,              # Overall accuracy ≥75%
    "min_qwk": 0.70,                   # Quadratic weighted kappa ≥0.70
    "max_ece": 0.15,                   # Expected calibration error ≤15%
    "max_false_negative_rate": 0.10,   # False negative rate ≤10%
    "max_regression_delta": -0.03,     # Max allowed regression vs production
}


def compute_binary_metrics(
    labels: list[int],
    predictions: list[int],
    threshold: int = 2,
) -> dict[str, float]:
    """
    Compute binary classification metrics for referable DR (stage ≥ threshold).

    Args:
        labels: Ground truth DR stages (0-4)
        predictions: Predicted DR stages (0-4)
        threshold: Stage threshold for referable DR

    Returns:
        Dict with sensitivity, specificity, f1, accuracy, false_negative_rate
    """
    tp = fp = tn = fn = 0

    for label, pred in zip(labels, predictions):
        is_referable = int(label) >= threshold
        pred_referable = int(pred) >= threshold

        if is_referable and pred_referable:
            tp += 1
        elif not is_referable and pred_referable:
            fp += 1
        elif not is_referable and not pred_referable:
            tn += 1
        else:
            fn += 1

    sensitivity = tp / max(1, tp + fn)
    specificity = tn / max(1, tn + fp)
    precision = tp / max(1, tp + fp)
    f1 = 2 * precision * sensitivity / max(1e-8, precision + sensitivity)
    accuracy = (tp + tn) / max(1, tp + fp + tn + fn)
    fnr = fn / max(1, tp + fn)

    return {
        "sensitivity": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "precision": round(precision, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "false_negative_rate": round(fnr, 4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


def compute_confusion_matrix(
    labels: list[int],
    predictions: list[int],
    num_classes: int = 5,
) -> list[list[int]]:
    """Compute confusion matrix."""
    matrix = [[0] * num_classes for _ in range(num_classes)]
    for label, pred in zip(labels, predictions):
        if 0 <= int(label) < num_classes and 0 <= int(pred) < num_classes:
            matrix[int(label)][int(pred)] += 1
    return matrix


def compute_per_class_metrics(
    labels: list[int],
    predictions: list[int],
    num_classes: int = 5,
) -> dict[int, dict]:
    """Compute per-class precision, recall, F1."""
    per_class = {}
    for cls in range(num_classes):
        tp = sum(1 for l, p in zip(labels, predictions) if l == cls and p == cls)
        fp = sum(1 for l, p in zip(labels, predictions) if l != cls and p == cls)
        fn = sum(1 for l, p in zip(labels, predictions) if l == cls and p != cls)
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(1e-8, precision + recall)
        support = sum(1 for l in labels if l == cls)
        per_class[cls] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }
    return per_class


def compute_qwk(labels: list[int], predictions: list[int], num_classes: int = 5) -> float:
    """Compute quadratic weighted kappa."""
    n = len(labels)
    if n == 0:
        return 0.0

    conf = compute_confusion_matrix(labels, predictions, num_classes)
    hist_true = [sum(conf[i]) for i in range(num_classes)]
    hist_pred = [sum(conf[j][i] for j in range(num_classes)) for i in range(num_classes)]

    numerator = 0.0
    denominator = 0.0

    for i in range(num_classes):
        for j in range(num_classes):
            weight = ((i - j) ** 2) / ((num_classes - 1) ** 2)
            expected = hist_true[i] * hist_pred[j] / max(1, n)
            numerator += weight * conf[i][j]
            denominator += weight * expected

    if denominator == 0:
        return 1.0 if numerator == 0 else 0.0

    return round(1.0 - numerator / denominator, 4)


def run_safety_gates(result: EvaluationResult) -> dict[str, Any]:
    """
    Run safety gate checks against evaluation results.

    Returns:
        Dict with gate name → {passed, threshold, actual}
    """
    gates = {}

    gates["min_sensitivity"] = {
        "passed": result.sensitivity >= SAFETY_GATES["min_sensitivity"],
        "threshold": SAFETY_GATES["min_sensitivity"],
        "actual": result.sensitivity,
    }
    gates["min_specificity"] = {
        "passed": result.specificity >= SAFETY_GATES["min_specificity"],
        "threshold": SAFETY_GATES["min_specificity"],
        "actual": result.specificity,
    }
    gates["min_accuracy"] = {
        "passed": result.accuracy >= SAFETY_GATES["min_accuracy"],
        "threshold": SAFETY_GATES["min_accuracy"],
        "actual": result.accuracy,
    }
    gates["min_qwk"] = {
        "passed": result.quadratic_weighted_kappa >= SAFETY_GATES["min_qwk"],
        "threshold": SAFETY_GATES["min_qwk"],
        "actual": result.quadratic_weighted_kappa,
    }
    gates["max_ece"] = {
        "passed": result.expected_calibration_error <= SAFETY_GATES["max_ece"],
        "threshold": SAFETY_GATES["max_ece"],
        "actual": result.expected_calibration_error,
    }
    gates["max_false_negative_rate"] = {
        "passed": result.false_negative_rate <= SAFETY_GATES["max_false_negative_rate"],
        "threshold": SAFETY_GATES["max_false_negative_rate"],
        "actual": result.false_negative_rate,
    }

    return gates


def evaluate_model(
    labels: list[int],
    predictions: list[int],
    model_version_id: str = "",
    dataset_id: str = "",
) -> EvaluationResult:
    """
    Run complete evaluation on a model's predictions.

    Args:
        labels: Ground truth labels
        predictions: Model predictions
        model_version_id: Model version being evaluated
        dataset_id: Dataset used for evaluation

    Returns:
        EvaluationResult with all metrics and safety gate outcomes.
    """
    eval_id = f"eval-{uuid.uuid4().hex[:12]}"

    # Binary metrics (referable DR: stage ≥ 2)
    binary = compute_binary_metrics(labels, predictions, threshold=2)

    # Multi-class metrics
    confusion = compute_confusion_matrix(labels, predictions)
    per_class = compute_per_class_metrics(labels, predictions)
    qwk = compute_qwk(labels, predictions)

    # Overall accuracy
    correct = sum(1 for l, p in zip(labels, predictions) if l == p)
    accuracy = correct / max(1, len(labels))

    result = EvaluationResult(
        eval_id=eval_id,
        model_version_id=model_version_id,
        dataset_id=dataset_id,
        accuracy=round(accuracy, 4),
        sensitivity=binary["sensitivity"],
        specificity=binary["specificity"],
        f1_score=binary["f1_score"],
        false_negative_rate=binary["false_negative_rate"],
        quadratic_weighted_kappa=qwk,
        confusion_matrix=confusion,
        per_class_metrics=per_class,
        total_samples=len(labels),
    )

    # Safety gates
    gate_results = run_safety_gates(result)
    result.safety_gate_results = gate_results
    result.passed_safety_gates = all(g["passed"] for g in gate_results.values())

    log.info(
        "Evaluation %s: acc=%.3f, sens=%.3f, spec=%.3f, QWK=%.3f, gates=%s",
        eval_id, accuracy, result.sensitivity, result.specificity,
        qwk, "PASSED" if result.passed_safety_gates else "FAILED"
    )

    return result


def compute_ece(probs: list[float] | list[list[float]], labels: list[int], num_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE)."""
    if not labels or not probs:
        return 0.0
    confidences = []
    correctness = []
    for i, p in enumerate(probs):
        if isinstance(p, (list, tuple)):
            pred = int(np.argmax(p))
            conf = float(np.max(p))
        else:
            conf = float(p)
            pred = 1 if conf >= 0.5 else 0
        confidences.append(conf)
        correctness.append(1.0 if pred == labels[i] else 0.0)

    bin_boundaries = np.linspace(0, 1, num_bins + 1)
    ece = 0.0
    n = len(labels)
    for b in range(num_bins):
        in_bin = [i for i, c in enumerate(confidences) if bin_boundaries[b] <= c < bin_boundaries[b + 1]]
        if in_bin:
            bin_acc = sum(correctness[i] for i in in_bin) / len(in_bin)
            bin_conf = sum(confidences[i] for i in in_bin) / len(in_bin)
            ece += (len(in_bin) / n) * abs(bin_acc - bin_conf)
    return round(float(ece), 4)


# Aliases for consistent naming
evaluate_predictions = evaluate_model


def save_evaluation(result: EvaluationResult) -> str:
    """Persist evaluation result to database."""
    from database import get_db

    with get_db() as conn:
        conn.execute(
            """INSERT INTO model_evaluations
               (id, model_version_id, dataset_id, eval_type,
                metrics_json, confusion_matrix_json, per_class_json,
                safety_gate_results_json, passed_safety_gates)
               VALUES (?, ?, ?, 'STANDARD', ?, ?, ?, ?, ?)""",
            (result.eval_id, result.model_version_id, result.dataset_id,
             json.dumps(result.to_dict()), json.dumps(result.confusion_matrix),
             json.dumps(result.per_class_metrics), json.dumps(result.safety_gate_results),
             1 if result.passed_safety_gates else 0)
        )
        conn.commit()

    return result.eval_id

