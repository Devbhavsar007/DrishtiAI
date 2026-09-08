"""Tests for Input, Output, and Clinical Drift Detection."""

import pytest
import numpy as np
from ml_platform.drift.input_drift import calculate_psi, detect_input_feature_drift
from ml_platform.drift.output_drift import detect_output_stage_drift
from ml_platform.drift.clinical_drift import evaluate_clinical_discordance


def test_psi_identical_distributions():
    dist = [float(x) for x in range(100)]
    psi = calculate_psi(dist, dist)
    assert psi == 0.0


def test_psi_shifted_distributions():
    baseline = np.random.normal(0.0, 1.0, 500).tolist()
    shifted = np.random.normal(2.5, 1.0, 500).tolist()

    psi = calculate_psi(baseline, shifted)
    assert psi > 0.25

    drift = detect_input_feature_drift("sharpness", baseline, shifted)
    assert drift["severity"] in ("WARNING", "CRITICAL")
    assert drift["psi"] > 0.10


def test_output_stage_drift():
    baseline_stages = [0]*50 + [1]*20 + [2]*15 + [3]*10 + [4]*5
    current_stages = [0]*10 + [1]*10 + [2]*30 + [3]*30 + [4]*20  # Massive shift toward high stages

    drift = detect_output_stage_drift(baseline_stages, current_stages)
    assert drift["severity"] in ("WARNING", "CRITICAL")
    assert drift["referral_rate_delta"] > 0.20


def test_clinical_discordance_drift():
    res = evaluate_clinical_discordance(days=30, persist_event=False)
    assert "status" in res
    assert "severity" in res
