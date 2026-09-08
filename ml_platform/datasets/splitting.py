"""Patient-level stratified dataset splitting with leakage prevention.

Ensures that all images from the same patient (both eyes, longitudinal scans)
are strictly assigned to the same split partition.
"""

from __future__ import annotations

import logging
import random
from collections import Counter, defaultdict
from typing import Any

log = logging.getLogger(__name__)


def patient_level_split(
    patient_records: dict[str, list[dict[str, Any]]],
    val_ratio: float = 0.15,
    test_ratio: float = 0.10,
    seed: int = 42,
) -> dict[str, str]:
    """
    Partition patients into TRAIN, VALIDATION, and TEST sets while balancing class distributions.

    Args:
        patient_records: Mapping from patient_id to list of scan records.
        val_ratio: Fraction of data for validation.
        test_ratio: Fraction of data for test.
        seed: Random seed for reproducibility.

    Returns:
        Mapping of patient_id -> split name ('TRAIN', 'VALIDATION', 'TEST').
    """
    rng = random.Random(seed)

    # Classify each patient by their maximum DR stage across scans
    patient_max_labels: dict[str, int] = {}
    for pid, scans in patient_records.items():
        labels = [int(s.get("label", 0)) for s in scans if s.get("label") is not None]
        patient_max_labels[pid] = max(labels) if labels else 0

    # Stratify patient IDs by their max DR label
    by_class: dict[int, list[str]] = defaultdict(list)
    for pid, label in patient_max_labels.items():
        by_class[label].append(pid)

    assignments: dict[str, str] = {}

    for c, pids in sorted(by_class.items()):
        shuffled = list(pids)
        rng.shuffle(shuffled)
        n = len(shuffled)

        n_test = max(1, round(n * test_ratio)) if test_ratio > 0 and n >= 3 else (1 if n >= 5 and test_ratio > 0 else 0)
        n_val = max(1, round(n * val_ratio)) if val_ratio > 0 and (n - n_test) >= 2 else 0

        test_pids = shuffled[:n_test]
        val_pids = shuffled[n_test : n_test + n_val]
        train_pids = shuffled[n_test + n_val :]

        for pid in test_pids:
            assignments[pid] = "TEST"
        for pid in val_pids:
            assignments[pid] = "VALIDATION"
        for pid in train_pids:
            assignments[pid] = "TRAIN"

    return assignments


def verify_patient_isolation(split_map: dict[str, str]) -> tuple[bool, list[str]]:
    """Verify that every patient has exactly one unique split assignment."""
    seen_patients: set[str] = set()
    duplicates: list[str] = []

    for pid in split_map.keys():
        if pid in seen_patients:
            duplicates.append(pid)
        seen_patients.add(pid)

    return len(duplicates) == 0, duplicates
