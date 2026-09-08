"""Input drift detection for clinical fundus images.

Monitors shifts in image quality, brightness, sharpness, and camera source
distributions using Population Stability Index (PSI) and Kolmogorov-Smirnov tests.
"""

from __future__ import annotations

import logging
import math
import numpy as np
from typing import Sequence, Any
from config_admin import DRIFT_CONFIG

log = logging.getLogger(__name__)


def calculate_psi(baseline: Sequence[float], current: Sequence[float], num_bins: int = 10) -> float:
    """
    Compute Population Stability Index (PSI) between baseline and current distributions.
      PSI < 0.10: No significant shift
      0.10 <= PSI < 0.25: Moderate shift / Warning
      PSI >= 0.25: Significant shift / Critical
    """
    b = np.asarray(baseline, dtype=float)
    c = np.asarray(current, dtype=float)

    if len(b) < 5 or len(c) < 5:
        return 0.0

    min_val = min(float(np.min(b)), float(np.min(c)))
    max_val = max(float(np.max(b)), float(np.max(c)))
    if math.isclose(min_val, max_val):
        return 0.0

    bins = np.linspace(min_val, max_val, num_bins + 1)
    b_counts, _ = np.histogram(b, bins=bins)
    c_counts, _ = np.histogram(c, bins=bins)

    b_pct = (b_counts + 1e-4) / (len(b) + 1e-4 * num_bins)
    c_pct = (c_counts + 1e-4) / (len(c) + 1e-4 * num_bins)

    psi_val = np.sum((c_pct - b_pct) * np.log(c_pct / b_pct))
    return float(max(0.0, psi_val))


def detect_input_feature_drift(
    feature_name: str,
    baseline_values: Sequence[float],
    current_values: Sequence[float],
) -> dict[str, Any]:
    """
    Evaluate drift for a single continuous input feature (e.g. quality_score).
    """
    psi = calculate_psi(baseline_values, current_values)
    mean_baseline = float(np.mean(baseline_values)) if len(baseline_values) > 0 else 0.0
    mean_current = float(np.mean(current_values)) if len(current_values) > 0 else 0.0

    psi_warn = DRIFT_CONFIG["psi_warning"]
    psi_crit = DRIFT_CONFIG["psi_critical"]

    severity = "NONE"
    if psi >= psi_crit:
        severity = "CRITICAL"
    elif psi >= psi_warn:
        severity = "WARNING"

    return {
        "feature": feature_name,
        "psi": round(psi, 4),
        "severity": severity,
        "mean_baseline": round(mean_baseline, 4),
        "mean_current": round(mean_current, 4),
        "baseline_count": len(baseline_values),
        "current_count": len(current_values),
    }
