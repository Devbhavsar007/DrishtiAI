"""Explicit Safety Gates evaluator for model promotion eligibility.

Enforces absolute clinical minimum thresholds for patient safety:
  - Referable DR sensitivity >= 85%
  - Referable DR specificity >= 80%
  - Quadratic Weighted Kappa >= 0.70
  - Expected Calibration Error <= 15%
  - False Negative Rate <= 10%
"""

from __future__ import annotations

from typing import Any
from config_admin import SAFETY_GATES


def evaluate_safety_gates(metrics: dict[str, Any], custom_thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    """
    Run clinical safety gate checks against evaluation metrics.

    Returns:
        Dict detailing passed status, per-gate breakdown, and blocker messages.
    """
    thresholds = dict(SAFETY_GATES)
    if custom_thresholds:
        thresholds.update(custom_thresholds)

    gate_results: dict[str, dict[str, Any]] = {}
    failed_gates: list[str] = []

    # 1. Sensitivity
    sens = float(metrics.get("sensitivity", 0.0))
    min_sens = thresholds["min_sensitivity"]
    pass_sens = sens >= min_sens
    gate_results["sensitivity"] = {"passed": pass_sens, "threshold": min_sens, "actual": sens}
    if not pass_sens:
        failed_gates.append(f"Sensitivity {sens:.3f} < required {min_sens:.3f}")

    # 2. Specificity
    spec = float(metrics.get("specificity", 0.0))
    min_spec = thresholds["min_specificity"]
    pass_spec = spec >= min_spec
    gate_results["specificity"] = {"passed": pass_spec, "threshold": min_spec, "actual": spec}
    if not pass_spec:
        failed_gates.append(f"Specificity {spec:.3f} < required {min_spec:.3f}")

    # 3. Accuracy
    acc = float(metrics.get("accuracy", 0.0))
    min_acc = thresholds["min_accuracy"]
    pass_acc = acc >= min_acc
    gate_results["accuracy"] = {"passed": pass_acc, "threshold": min_acc, "actual": acc}
    if not pass_acc:
        failed_gates.append(f"Accuracy {acc:.3f} < required {min_acc:.3f}")

    # 4. QWK
    qwk = float(metrics.get("quadratic_weighted_kappa", 0.0))
    min_qwk = thresholds["min_qwk"]
    pass_qwk = qwk >= min_qwk
    gate_results["quadratic_weighted_kappa"] = {"passed": pass_qwk, "threshold": min_qwk, "actual": qwk}
    if not pass_qwk:
        failed_gates.append(f"QWK {qwk:.3f} < required {min_qwk:.3f}")

    # 5. ECE
    ece = float(metrics.get("expected_calibration_error", 0.0))
    max_ece = thresholds["max_ece"]
    pass_ece = ece <= max_ece
    gate_results["expected_calibration_error"] = {"passed": pass_ece, "threshold": max_ece, "actual": ece}
    if not pass_ece:
        failed_gates.append(f"ECE {ece:.3f} > allowed {max_ece:.3f}")

    # 6. False Negative Rate
    fnr = float(metrics.get("false_negative_rate", 0.0))
    max_fnr = thresholds["max_false_negative_rate"]
    pass_fnr = fnr <= max_fnr
    gate_results["false_negative_rate"] = {"passed": pass_fnr, "threshold": max_fnr, "actual": fnr}
    if not pass_fnr:
        failed_gates.append(f"FNR {fnr:.3f} > allowed {max_fnr:.3f}")

    all_passed = len(failed_gates) == 0

    return {
        "all_passed": all_passed,
        "gates": gate_results,
        "failed_gates": failed_gates,
        "promotion_eligible": all_passed,
    }
