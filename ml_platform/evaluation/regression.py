"""Regression comparison pipeline for model evaluation.

Evaluates a candidate model side-by-side with the current production model
on the identical locked test set to detect regressions in clinical safety metrics.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# Maximum tolerable degradation vs production baseline
DEFAULT_MAX_SENSITIVITY_DROP = 0.02
DEFAULT_MAX_SPECIFICITY_DROP = 0.03
DEFAULT_MAX_QWK_DROP = 0.04


def compare_models(
    candidate_metrics: dict[str, Any],
    production_metrics: dict[str, Any],
    max_sensitivity_drop: float = DEFAULT_MAX_SENSITIVITY_DROP,
    max_specificity_drop: float = DEFAULT_MAX_SPECIFICITY_DROP,
    max_qwk_drop: float = DEFAULT_MAX_QWK_DROP,
) -> dict[str, Any]:
    """
    Compare candidate model metrics directly against production model metrics.

    Returns:
        Dict with comparison deltas, violation flags, and promotion recommendation.
    """
    cand_sens = float(candidate_metrics.get("sensitivity", 0.0))
    prod_sens = float(production_metrics.get("sensitivity", 0.0))
    delta_sens = round(cand_sens - prod_sens, 4)

    cand_spec = float(candidate_metrics.get("specificity", 0.0))
    prod_spec = float(production_metrics.get("specificity", 0.0))
    delta_spec = round(cand_spec - prod_spec, 4)

    cand_qwk = float(candidate_metrics.get("quadratic_weighted_kappa", 0.0))
    prod_qwk = float(production_metrics.get("quadratic_weighted_kappa", 0.0))
    delta_qwk = round(cand_qwk - prod_qwk, 4)

    cand_fnr = float(candidate_metrics.get("false_negative_rate", 0.0))
    prod_fnr = float(production_metrics.get("false_negative_rate", 0.0))
    delta_fnr = round(cand_fnr - prod_fnr, 4)  # Lower is better

    violations: list[str] = []

    if delta_sens < -max_sensitivity_drop:
        violations.append(
            f"Sensitivity degraded by {-delta_sens:.3f} (max allowed drop: {max_sensitivity_drop:.3f})"
        )

    if delta_spec < -max_specificity_drop:
        violations.append(
            f"Specificity degraded by {-delta_spec:.3f} (max allowed drop: {max_specificity_drop:.3f})"
        )

    if delta_qwk < -max_qwk_drop:
        violations.append(
            f"QWK degraded by {-delta_qwk:.3f} (max allowed drop: {max_qwk_drop:.3f})"
        )

    if delta_fnr > 0.02:
        violations.append(
            f"False Negative Rate increased by {delta_fnr:.3f}"
        )

    passed = len(violations) == 0

    return {
        "passed_regression_test": passed,
        "recommendation": "APPROVE_FOR_STAGING" if passed else "REJECT_DUE_TO_REGRESSION",
        "deltas": {
            "sensitivity": delta_sens,
            "specificity": delta_spec,
            "quadratic_weighted_kappa": delta_qwk,
            "false_negative_rate": delta_fnr,
        },
        "thresholds": {
            "max_sensitivity_drop": max_sensitivity_drop,
            "max_specificity_drop": max_specificity_drop,
            "max_qwk_drop": max_qwk_drop,
        },
        "violations": violations,
    }
