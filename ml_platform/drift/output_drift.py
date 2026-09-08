"""Output prediction and referral drift detection.

Monitors DR stage distribution, referable rates, and confidence score shifts.
"""

from __future__ import annotations

import logging
import numpy as np
from collections import Counter
from typing import Sequence, Any

from config_admin import DRIFT_CONFIG

log = logging.getLogger(__name__)


def detect_output_stage_drift(
    baseline_stages: Sequence[int],
    current_stages: Sequence[int],
    num_classes: int = 5,
) -> dict[str, Any]:
    """
    Compute distribution shift for predicted DR stages (0 to 4).
    """
    b_len = len(baseline_stages)
    c_len = len(current_stages)

    if b_len < 10 or c_len < 10:
        return {"severity": "NONE", "message": "Insufficient samples for output drift calculation"}

    b_counts = Counter(baseline_stages)
    c_counts = Counter(current_stages)

    # Class probabilities with smoothing
    b_probs = np.array([(b_counts[i] + 1e-4) / (b_len + 1e-4 * num_classes) for i in range(num_classes)])
    c_probs = np.array([(c_counts[i] + 1e-4) / (c_len + 1e-4 * num_classes) for i in range(num_classes)])

    # Discrete PSI across 5 categories
    psi = float(np.sum((c_probs - b_probs) * np.log(c_probs / b_probs)))

    # Referable DR rates (stage >= 2)
    b_referable = sum(1 for s in baseline_stages if s >= 2) / b_len
    c_referable = sum(1 for s in current_stages if s >= 2) / c_len
    referral_delta = round(c_referable - b_referable, 4)

    severity = "NONE"
    if psi >= DRIFT_CONFIG["psi_critical"] or abs(referral_delta) > 0.15:
        severity = "CRITICAL"
    elif psi >= DRIFT_CONFIG["psi_warning"] or abs(referral_delta) > 0.08:
        severity = "WARNING"

    return {
        "metric": "dr_stage_distribution",
        "psi": round(psi, 4),
        "severity": severity,
        "baseline_referral_rate": round(b_referable, 4),
        "current_referral_rate": round(c_referable, 4),
        "referral_rate_delta": referral_delta,
        "baseline_counts": dict(b_counts),
        "current_counts": dict(c_counts),
    }
