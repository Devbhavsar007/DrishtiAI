"""Tests for ML Platform Data Governance, Dataset Registry, and Active Learning."""

import pytest
from ml_platform.data.eligibility import check_eligibility, batch_check_eligibility, EligibilityResult
from ml_platform.data.leakage import patient_stratified_split, check_leakage, LeakageCheckResult
from ml_platform.datasets.splitting import patient_level_split, verify_patient_isolation
from ml_platform.datasets.validation import validate_dataset_health
from ml_platform.datasets.versioning import (
    generate_version_tag,
    compute_manifest_hash,
    verify_dataset_integrity,
)
from ml_platform.active_learning.uncertainty import (
    shannon_entropy,
    margin_sampling,
    least_confidence,
    ensemble_disagreement,
)
from ml_platform.active_learning.prioritization import (
    prioritize_scan,
    build_priority_queue,
    compute_entropy,
)


def test_shannon_entropy_bounds():
    # Uniform 5-class distribution should have entropy near 1.0
    uniform = [0.2, 0.2, 0.2, 0.2, 0.2]
    ent = shannon_entropy(uniform)
    assert 0.99 <= ent <= 1.0

    # Deterministic distribution should have entropy 0.0
    deterministic = [1.0, 0.0, 0.0, 0.0, 0.0]
    assert shannon_entropy(deterministic) == 0.0


def test_margin_sampling():
    # Very close predictions -> high uncertainty
    close = [0.41, 0.39, 0.1, 0.05, 0.05]
    score_close = margin_sampling(close)
    assert score_close > 0.95

    # Decisive prediction -> low uncertainty
    decisive = [0.95, 0.02, 0.01, 0.01, 0.01]
    score_decisive = margin_sampling(decisive)
    assert score_decisive < 0.1


def test_least_confidence():
    uniform = [0.2, 0.2, 0.2, 0.2, 0.2]
    assert least_confidence(uniform) == 1.0

    decisive = [1.0, 0.0, 0.0, 0.0, 0.0]
    assert least_confidence(decisive) == 0.0


def test_ensemble_disagreement():
    # 4 models agree
    assert ensemble_disagreement([1, 1, 1, 1]) == 0.0

    # Split 2 vs 2
    assert ensemble_disagreement([1, 1, 2, 2]) == 0.5


def test_patient_level_leakage_prevention():
    patient_records = {
        f"P-{i:04d}": [
            {"scan_id": f"s-{i}-1", "label": i % 5},
            {"scan_id": f"s-{i}-2", "label": i % 5},
        ]
        for i in range(20)
    }

    split_map = patient_level_split(patient_records, val_ratio=0.2, test_ratio=0.1, seed=42)

    # Every patient has exactly one split
    is_isolated, dupes = verify_patient_isolation(split_map)
    assert is_isolated
    assert len(dupes) == 0
    assert len(split_map) == 20

    # Check splits assigned
    assigned_splits = set(split_map.values())
    assert "TRAIN" in assigned_splits


def test_dataset_health_validation():
    samples = [
        {"scan_id": f"s{i}", "patient_id": f"p{i}", "label": i % 5, "split": "TRAIN", "provenance": "DOCTOR_CONFIRMED"}
        for i in range(10)
    ]
    health = validate_dataset_health(samples, min_total_samples=5, min_samples_per_class=1)
    assert health["valid"]
    assert health["total_samples"] == 10
    assert health["clinical_ground_truth_fraction"] == 1.0


def test_active_learning_prioritization():
    scan_uncertain = {
        "id": "scan-1",
        "patient_id": "P-1001",
        "confidence": 55.0,
        "stage": 1,
        "all_probabilities": [0.35, 0.40, 0.15, 0.05, 0.05],
    }
    candidate = prioritize_scan(scan_uncertain)
    assert candidate.priority_score > 0.2
    assert candidate.is_borderline
    assert len(candidate.reasons) > 0
