"""Label provenance tracking for training data.

Links scan labels to their source of truth:
  - DOCTOR_CONFIRMED: label verified by ophthalmologist review
  - SECOND_REVIEW_CONFIRMED: label verified by ≥2 independent reviewers
  - REFERENCE_DATASET: label from a reference dataset (e.g., APTOS, EyePACS)
  - AI_ONLY: label from model prediction only (no human review)
  - PSEUDO_LABEL: label from semi-supervised or ensemble methods
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any

log = logging.getLogger(__name__)


class ProvenanceLevel(str, Enum):
    """Label provenance levels, ranked from strongest to weakest."""
    SECOND_REVIEW_CONFIRMED = "SECOND_REVIEW_CONFIRMED"
    DOCTOR_CONFIRMED = "DOCTOR_CONFIRMED"
    REFERENCE_DATASET = "REFERENCE_DATASET"
    AI_ONLY = "AI_ONLY"
    PSEUDO_LABEL = "PSEUDO_LABEL"


# Provenance strength ranking (lower = stronger)
PROVENANCE_STRENGTH = {
    ProvenanceLevel.SECOND_REVIEW_CONFIRMED: 1,
    ProvenanceLevel.DOCTOR_CONFIRMED: 2,
    ProvenanceLevel.REFERENCE_DATASET: 3,
    ProvenanceLevel.AI_ONLY: 4,
    ProvenanceLevel.PSEUDO_LABEL: 5,
}


@dataclass
class ProvenanceRecord:
    """Provenance metadata for a single training label."""
    scan_id: str
    patient_id: str
    label: int
    provenance: ProvenanceLevel
    doctor_review_id: str = ""
    second_reviewer_id: str = ""
    reference_dataset: str = ""
    confidence: float = 0.0
    notes: str = ""

    @property
    def strength(self) -> int:
        return PROVENANCE_STRENGTH.get(self.provenance, 99)

    @property
    def is_human_verified(self) -> bool:
        return self.provenance in (
            ProvenanceLevel.DOCTOR_CONFIRMED,
            ProvenanceLevel.SECOND_REVIEW_CONFIRMED,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["provenance"] = self.provenance.value
        d["strength"] = self.strength
        d["is_human_verified"] = self.is_human_verified
        return d


def determine_provenance(
    scan: dict,
    doctor_review: dict | None = None,
    reference_source: str = "",
) -> ProvenanceRecord:
    """
    Determine the label provenance for a scan.

    Args:
        scan: Scan record from database
        doctor_review: Optional doctor review record
        reference_source: Name of reference dataset if applicable

    Returns:
        ProvenanceRecord with the strongest applicable provenance level.
    """
    scan_id = scan.get("id", "")
    patient_id = scan.get("patient_id", "")
    label = int(scan.get("stage", 0))
    confidence = float(scan.get("confidence", 0.0))

    # Check doctor review
    if doctor_review:
        decision = str(doctor_review.get("decision", "")).upper()
        if decision in ("APPROVED", "MODIFIED"):
            # Use adjusted stage if doctor modified
            adjusted = doctor_review.get("adjusted_stage")
            if adjusted is not None:
                label = int(adjusted)

            return ProvenanceRecord(
                scan_id=scan_id,
                patient_id=patient_id,
                label=label,
                provenance=ProvenanceLevel.DOCTOR_CONFIRMED,
                doctor_review_id=doctor_review.get("id", ""),
                confidence=confidence,
            )

    # Check reference dataset
    if reference_source:
        return ProvenanceRecord(
            scan_id=scan_id,
            patient_id=patient_id,
            label=label,
            provenance=ProvenanceLevel.REFERENCE_DATASET,
            reference_dataset=reference_source,
            confidence=confidence,
        )

    # Default: AI-only
    return ProvenanceRecord(
        scan_id=scan_id,
        patient_id=patient_id,
        label=label,
        provenance=ProvenanceLevel.AI_ONLY,
        confidence=confidence,
    )


def filter_by_minimum_provenance(
    records: list[ProvenanceRecord],
    minimum_provenance: ProvenanceLevel = ProvenanceLevel.AI_ONLY,
) -> list[ProvenanceRecord]:
    """
    Filter provenance records to only include those meeting minimum provenance.

    Args:
        records: List of ProvenanceRecords
        minimum_provenance: Minimum acceptable provenance level

    Returns:
        Filtered list of records that meet the threshold.
    """
    min_strength = PROVENANCE_STRENGTH.get(minimum_provenance, 99)
    filtered = [r for r in records if r.strength <= min_strength]
    log.info(
        "Provenance filter: %d/%d pass minimum=%s",
        len(filtered), len(records), minimum_provenance.value
    )
    return filtered
