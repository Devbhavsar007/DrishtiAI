"""Dataset validation and health checks.

Validates that a constructed dataset meets clinical machine learning criteria
prior to training orchestration.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

log = logging.getLogger(__name__)


def validate_dataset_health(
    samples: list[dict[str, Any]],
    min_total_samples: int = 5,
    min_samples_per_class: int = 1,
) -> dict[str, Any]:
    """
    Evaluate comprehensive health and readiness of a dataset candidate.

    Checks:
      - Total sample count
      - Class coverage across 5 DR stages (0-4)
      - Minimum samples per class
      - Split distribution (TRAIN / VALIDATION / TEST)
      - Provenance quality (fraction with doctor reviews)
    """
    total = len(samples)
    warnings: list[str] = []
    errors: list[str] = []

    if total < min_total_samples:
        errors.append(f"Insufficient samples: {total} < minimum {min_total_samples}")

    label_counts = Counter(s.get("label") for s in samples if s.get("label") is not None)
    split_counts = Counter(s.get("split", "UNKNOWN") for s in samples)
    provenance_counts = Counter(s.get("provenance", "UNKNOWN") for s in samples)

    # Class balance check
    for stage in range(5):
        cnt = label_counts.get(stage, 0)
        if cnt < min_samples_per_class:
            warnings.append(f"Stage {stage} has only {cnt} sample(s), below threshold {min_samples_per_class}")

    # Split coverage
    for required_split in ["TRAIN"]:
        if split_counts.get(required_split, 0) == 0:
            errors.append(f"Missing essential split partition: {required_split}")

    # Provenance score: proportion of DOCTOR_CONFIRMED or SECOND_REVIEW_CONFIRMED
    clinical_labels = sum(
        1 for s in samples
        if s.get("provenance") in ("DOCTOR_CONFIRMED", "SECOND_REVIEW_CONFIRMED", "REFERENCE_DATASET")
    )
    clinical_fraction = (clinical_labels / total) if total > 0 else 0.0

    return {
        "valid": len(errors) == 0,
        "total_samples": total,
        "class_distribution": dict(label_counts),
        "split_distribution": dict(split_counts),
        "provenance_distribution": dict(provenance_counts),
        "clinical_ground_truth_fraction": round(clinical_fraction, 3),
        "errors": errors,
        "warnings": warnings,
    }
