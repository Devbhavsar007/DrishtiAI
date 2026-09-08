"""Patient-level data leakage prevention.

Ensures strict patient-level separation between TRAIN, VALIDATION, and
LOCKED_TEST splits. No images from the same patient may appear in multiple
splits.
"""

from __future__ import annotations

import hashlib
import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class SplitAssignment:
    """Split assignment for a patient."""
    patient_id: str
    split: str  # TRAIN, VALIDATION, LOCKED_TEST
    num_samples: int = 0


@dataclass
class LeakageCheckResult:
    """Result of leakage detection check."""
    has_leakage: bool = False
    leaked_patients: list[str] = field(default_factory=list)
    leaked_splits: dict[str, list[str]] = field(default_factory=dict)
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def patient_stratified_split(
    patient_samples: dict[str, list[dict]],
    val_ratio: float = 0.15,
    test_ratio: float = 0.10,
    seed: int = 42,
    locked_test_patients: set[str] | None = None,
) -> dict[str, list[SplitAssignment]]:
    """
    Perform patient-level stratified splitting.

    Each patient's ALL samples go entirely into one split.
    Stratification is by majority DR stage per patient.

    Args:
        patient_samples: Dict mapping patient_id → list of sample dicts
                        (each sample must have 'label' key)
        val_ratio: Fraction of patients for validation
        test_ratio: Fraction of patients for locked test
        seed: Random seed for reproducibility
        locked_test_patients: Patients that MUST be in LOCKED_TEST

    Returns:
        Dict with 'TRAIN', 'VALIDATION', 'LOCKED_TEST' → list of SplitAssignment
    """
    rng = random.Random(seed)
    locked_test_patients = locked_test_patients or set()

    # Group patients by their majority class for stratification
    class_patients: dict[int, list[str]] = defaultdict(list)
    for patient_id, samples in patient_samples.items():
        if not samples:
            continue
        labels = [s.get("label", 0) for s in samples]
        majority_class = max(set(labels), key=labels.count)
        class_patients[majority_class].append(patient_id)

    assignments: dict[str, list[SplitAssignment]] = {
        "TRAIN": [],
        "VALIDATION": [],
        "LOCKED_TEST": [],
    }

    for class_label in sorted(class_patients.keys()):
        patients = class_patients[class_label]
        rng.shuffle(patients)

        # Separate locked test patients
        locked = [p for p in patients if p in locked_test_patients]
        unlocked = [p for p in patients if p not in locked_test_patients]

        # Calculate split sizes from unlocked patients
        n_total = len(unlocked)
        n_test = max(1, int(n_total * test_ratio)) if n_total > 3 else 0
        n_val = max(1, int(n_total * val_ratio)) if n_total > 2 else 0
        n_train = n_total - n_test - n_val

        # Assign splits
        for p in locked:
            assignments["LOCKED_TEST"].append(SplitAssignment(
                patient_id=p,
                split="LOCKED_TEST",
                num_samples=len(patient_samples.get(p, []))
            ))

        for p in unlocked[:n_train]:
            assignments["TRAIN"].append(SplitAssignment(
                patient_id=p,
                split="TRAIN",
                num_samples=len(patient_samples.get(p, []))
            ))

        for p in unlocked[n_train:n_train + n_val]:
            assignments["VALIDATION"].append(SplitAssignment(
                patient_id=p,
                split="VALIDATION",
                num_samples=len(patient_samples.get(p, []))
            ))

        for p in unlocked[n_train + n_val:]:
            assignments["LOCKED_TEST"].append(SplitAssignment(
                patient_id=p,
                split="LOCKED_TEST",
                num_samples=len(patient_samples.get(p, []))
            ))

    total = sum(len(v) for v in assignments.values())
    log.info(
        "Patient-level split: TRAIN=%d, VALIDATION=%d, LOCKED_TEST=%d (total=%d patients)",
        len(assignments["TRAIN"]),
        len(assignments["VALIDATION"]),
        len(assignments["LOCKED_TEST"]),
        total,
    )
    return assignments


def check_leakage(
    split_assignments: dict[str, list[SplitAssignment]],
) -> LeakageCheckResult:
    """
    Verify that no patient appears in multiple splits (data leakage check).

    Args:
        split_assignments: Dict from patient_stratified_split()

    Returns:
        LeakageCheckResult indicating whether leakage was detected.
    """
    patient_splits: dict[str, list[str]] = defaultdict(list)

    for split_name, assignments in split_assignments.items():
        for assignment in assignments:
            patient_splits[assignment.patient_id].append(split_name)

    leaked_patients = []
    leaked_splits: dict[str, list[str]] = {}

    for patient_id, splits in patient_splits.items():
        if len(splits) > 1:
            leaked_patients.append(patient_id)
            leaked_splits[patient_id] = splits

    has_leakage = len(leaked_patients) > 0
    result = LeakageCheckResult(
        has_leakage=has_leakage,
        leaked_patients=leaked_patients,
        leaked_splits=leaked_splits,
        details=f"Leakage detected in {len(leaked_patients)} patients" if has_leakage else "No leakage detected"
    )

    if has_leakage:
        log.error("DATA LEAKAGE DETECTED: %d patients appear in multiple splits", len(leaked_patients))
    else:
        log.info("Leakage check passed: all patients in exactly one split")

    return result


def deterministic_patient_hash(patient_id: str, salt: str = "drishtiai-split-v1") -> str:
    """Generate a deterministic hash for patient assignment (reproducible across runs)."""
    combined = f"{salt}:{patient_id}"
    return hashlib.sha256(combined.encode()).hexdigest()
