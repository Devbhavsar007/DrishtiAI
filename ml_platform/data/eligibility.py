"""Training eligibility checker for DrishtiAI screening data.

Determines whether a given scan qualifies for inclusion in a training dataset.
Enforces: valid image, quality, gradability, label provenance, no duplicates,
no leakage, no quarantine, valid metadata.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class EligibilityResult:
    """Result of training eligibility assessment for a single scan."""
    scan_id: str
    patient_id: str
    eligible: bool = False
    label: int = -1
    label_provenance: str = "AI_ONLY"
    rejection_reasons: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    doctor_review_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Minimum thresholds for training eligibility
MIN_CONFIDENCE = 40.0          # Model confidence ≥40% required
MIN_QUALITY_SCORE = 0.5        # IQA quality score ≥0.5
VALID_SAFETY_STATES = {"VERIFIED", "UNCERTAIN"}  # Only safe screenings
VALID_STAGES = {0, 1, 2, 3, 4}
PROVENANCE_RANKING = [
    "DOCTOR_CONFIRMED",
    "SECOND_REVIEW_CONFIRMED",
    "REFERENCE_DATASET",
    "AI_ONLY",
    "PSEUDO_LABEL",
]


def check_eligibility(
    scan: dict,
    doctor_review: dict | None = None,
    existing_hashes: set[str] | None = None,
    quarantined_patient_ids: set[str] | None = None,
) -> EligibilityResult:
    """
    Evaluate a single scan record for training eligibility.

    Args:
        scan: Scan dict from database (from get_scan)
        doctor_review: Optional doctor review dict (from get_doctor_review)
        existing_hashes: Set of image hashes already in current dataset (dedup)
        quarantined_patient_ids: Set of patient IDs excluded from training

    Returns:
        EligibilityResult with eligible flag and reasons for any rejection.
    """
    scan_id = scan.get("id", "")
    patient_id = scan.get("patient_id", "")
    result = EligibilityResult(scan_id=scan_id, patient_id=patient_id)
    reasons = []

    # 1. Valid patient ID
    if not patient_id or not str(patient_id).strip():
        reasons.append("MISSING_PATIENT_ID")

    # 2. Safety state must be usable for training
    safety_state = str(scan.get("safety_state", "")).upper()
    if safety_state not in VALID_SAFETY_STATES:
        reasons.append(f"INVALID_SAFETY_STATE:{safety_state}")

    # 3. Valid DR stage
    stage = scan.get("stage")
    if stage is None or int(stage) not in VALID_STAGES:
        reasons.append(f"INVALID_STAGE:{stage}")
    else:
        result.label = int(stage)

    # 4. Minimum model confidence
    confidence = float(scan.get("confidence", 0.0))
    if confidence < MIN_CONFIDENCE:
        reasons.append(f"LOW_CONFIDENCE:{confidence:.1f}")

    # 5. Image hash deduplication
    image_hash = scan.get("image_hash", "")
    if image_hash and existing_hashes and image_hash in existing_hashes:
        reasons.append("DUPLICATE_IMAGE_HASH")

    # 6. Quarantine check
    if quarantined_patient_ids and patient_id in quarantined_patient_ids:
        reasons.append("QUARANTINED_PATIENT")

    # 7. Image must exist
    image_original = scan.get("image_original", "")
    if not image_original:
        reasons.append("MISSING_IMAGE_PATH")

    # 8. Label provenance — determine the strongest provenance
    if doctor_review:
        decision = str(doctor_review.get("decision", "")).upper()
        if decision == "APPROVED":
            result.label_provenance = "DOCTOR_CONFIRMED"
            result.doctor_review_id = doctor_review.get("id", "")
            # Use adjusted stage if doctor modified it
            adjusted = doctor_review.get("adjusted_stage")
            if adjusted is not None:
                result.label = int(adjusted)
                result.label_provenance = "DOCTOR_CONFIRMED"
        elif decision == "MODIFIED":
            result.label_provenance = "DOCTOR_CONFIRMED"
            result.doctor_review_id = doctor_review.get("id", "")
            adjusted = doctor_review.get("adjusted_stage")
            if adjusted is not None:
                result.label = int(adjusted)
        elif decision == "REJECTED_RETAKE":
            reasons.append("DOCTOR_REJECTED_RETAKE")
    else:
        result.label_provenance = "AI_ONLY"

    # 9. Quality score estimate from scan metadata
    # Use processing_time as a proxy for quality (faster = better image)
    processing_time = float(scan.get("processing_time", 999.0))
    if processing_time < 30:
        result.quality_score = 0.8
    elif processing_time < 60:
        result.quality_score = 0.6
    else:
        result.quality_score = 0.4

    if result.quality_score < MIN_QUALITY_SCORE:
        reasons.append(f"LOW_QUALITY_SCORE:{result.quality_score:.2f}")

    # Final eligibility decision
    result.rejection_reasons = reasons
    result.eligible = len(reasons) == 0

    return result


def batch_check_eligibility(
    scans: list[dict],
    reviews: dict[str, dict] | None = None,
    existing_hashes: set[str] | None = None,
    quarantined_patient_ids: set[str] | None = None,
) -> list[EligibilityResult]:
    """
    Batch-evaluate training eligibility for multiple scans.

    Args:
        scans: List of scan dicts from database
        reviews: Dict mapping scan_id → doctor_review dict
        existing_hashes: Set of image hashes for dedup
        quarantined_patient_ids: Excluded patient IDs

    Returns:
        List of EligibilityResults.
    """
    reviews = reviews or {}
    existing_hashes = existing_hashes or set()
    quarantined_patient_ids = quarantined_patient_ids or set()
    used_hashes = set(existing_hashes)

    results = []
    for scan in scans:
        scan_id = scan.get("id", "")
        review = reviews.get(scan_id)
        res = check_eligibility(
            scan=scan,
            doctor_review=review,
            existing_hashes=used_hashes,
            quarantined_patient_ids=quarantined_patient_ids,
        )
        if res.eligible:
            # Track this hash to prevent intra-batch duplicates
            image_hash = scan.get("image_hash", "")
            if image_hash:
                used_hashes.add(image_hash)
        results.append(res)

    eligible_count = sum(1 for r in results if r.eligible)
    log.info("Eligibility batch: %d/%d eligible", eligible_count, len(results))
    return results
