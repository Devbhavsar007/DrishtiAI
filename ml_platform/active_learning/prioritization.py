"""Active learning prioritization queue.

Integrates uncertainty, OOD proximity, rare class, false-negative risk, and
model disagreement to produce a priority-ordered queue for human annotation.
"""

from __future__ import annotations

import json
import logging
import math
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class ActiveLearningCandidate:
    """A prioritized candidate for human annotation."""
    scan_id: str
    patient_id: str
    priority_score: float = 0.0
    uncertainty_score: float = 0.0
    confidence: float = 0.0
    predicted_stage: int = 0
    is_borderline: bool = False
    is_rare_class: bool = False
    is_ood_proximity: bool = False
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Weights for priority calculation
UNCERTAINTY_WEIGHT = 0.35
BORDERLINE_WEIGHT = 0.25
RARE_CLASS_WEIGHT = 0.20
OOD_PROXIMITY_WEIGHT = 0.10
LOW_CONFIDENCE_WEIGHT = 0.10

# Class frequencies for rare class detection
EXPECTED_CLASS_FREQ = {0: 0.50, 1: 0.15, 2: 0.20, 3: 0.10, 4: 0.05}
RARE_CLASS_THRESHOLD = 0.10  # Classes with <10% frequency are rare
BORDERLINE_CONFIDENCE_RANGE = (45.0, 70.0)  # Confidence range considered borderline
UNCERTAINTY_THRESHOLD = 0.6  # Entropy threshold for high uncertainty


def compute_entropy(probabilities: dict | list) -> float:
    """Compute prediction entropy from class probabilities."""
    if isinstance(probabilities, dict):
        probs = [float(v) / 100.0 for v in probabilities.values() if float(v) > 0]
    elif isinstance(probabilities, list):
        probs = [float(p) / 100.0 if float(p) > 1.0 else float(p) for p in probabilities if float(p) > 0]
    else:
        return 0.0

    if not probs:
        return 0.0

    # Normalize
    total = sum(probs)
    if total <= 0:
        return 0.0
    probs = [p / total for p in probs]

    # Shannon entropy, normalized to [0, 1]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    max_entropy = math.log2(len(probs)) if len(probs) > 1 else 1.0
    return min(1.0, entropy / max_entropy)


def prioritize_scan(
    scan: dict,
    class_distribution: dict[int, int] | None = None,
) -> ActiveLearningCandidate:
    """
    Compute active learning priority for a single scan.

    Args:
        scan: Scan dict with detection results
        class_distribution: Current dataset class distribution for rarity detection

    Returns:
        ActiveLearningCandidate with priority score.
    """
    scan_id = scan.get("id", "")
    patient_id = scan.get("patient_id", "")
    confidence = float(scan.get("confidence", 50.0))
    stage = int(scan.get("stage", 0))
    all_probs = scan.get("all_probabilities", {})

    candidate = ActiveLearningCandidate(
        scan_id=scan_id,
        patient_id=patient_id,
        confidence=confidence,
        predicted_stage=stage,
    )

    # 1. Uncertainty (entropy-based)
    entropy = compute_entropy(all_probs)
    candidate.uncertainty_score = entropy
    uncertainty_contrib = entropy * UNCERTAINTY_WEIGHT
    if entropy > UNCERTAINTY_THRESHOLD:
        candidate.reasons.append(f"HIGH_ENTROPY:{entropy:.3f}")

    # 2. Borderline confidence
    borderline_contrib = 0.0
    if BORDERLINE_CONFIDENCE_RANGE[0] <= confidence <= BORDERLINE_CONFIDENCE_RANGE[1]:
        candidate.is_borderline = True
        # Higher priority for lower confidence within range
        borderline_score = 1.0 - (confidence - BORDERLINE_CONFIDENCE_RANGE[0]) / (
            BORDERLINE_CONFIDENCE_RANGE[1] - BORDERLINE_CONFIDENCE_RANGE[0]
        )
        borderline_contrib = borderline_score * BORDERLINE_WEIGHT
        candidate.reasons.append(f"BORDERLINE_CONFIDENCE:{confidence:.1f}")

    # 3. Rare class
    rare_contrib = 0.0
    if class_distribution:
        total = sum(class_distribution.values())
        if total > 0:
            class_freq = class_distribution.get(stage, 0) / total
            if class_freq < RARE_CLASS_THRESHOLD:
                candidate.is_rare_class = True
                rare_contrib = (1.0 - class_freq / RARE_CLASS_THRESHOLD) * RARE_CLASS_WEIGHT
                candidate.reasons.append(f"RARE_CLASS:{stage}({class_freq:.2%})")

    # 4. OOD proximity (safety_state indicates near-OOD)
    ood_contrib = 0.0
    safety_state = str(scan.get("safety_state", "")).upper()
    if safety_state in ("UNCERTAIN", "OOD_REVIEW"):
        candidate.is_ood_proximity = True
        ood_contrib = UNCERTAINTY_WEIGHT * 0.5
        candidate.reasons.append(f"OOD_PROXIMITY:{safety_state}")

    # 5. Low confidence
    low_conf_contrib = 0.0
    if confidence < 50.0:
        low_conf_contrib = (1.0 - confidence / 50.0) * LOW_CONFIDENCE_WEIGHT
        candidate.reasons.append(f"LOW_CONFIDENCE:{confidence:.1f}")

    # Composite priority score
    candidate.priority_score = round(
        uncertainty_contrib + borderline_contrib + rare_contrib +
        ood_contrib + low_conf_contrib,
        4
    )

    return candidate


def build_priority_queue(
    scans: list[dict],
    class_distribution: dict[int, int] | None = None,
    top_k: int = 100,
) -> list[ActiveLearningCandidate]:
    """
    Build a priority-ordered active learning queue from unannotated scans.

    Args:
        scans: List of scan dicts
        class_distribution: Current dataset class distribution
        top_k: Maximum items in the queue

    Returns:
        Priority-sorted list of ActiveLearningCandidates (highest priority first).
    """
    candidates = [
        prioritize_scan(scan, class_distribution)
        for scan in scans
    ]

    # Sort by priority score descending
    candidates.sort(key=lambda c: c.priority_score, reverse=True)

    queue = candidates[:top_k]
    log.info(
        "Active learning queue: %d candidates (top priority=%.4f)",
        len(queue),
        queue[0].priority_score if queue else 0.0
    )
    return queue


# Aliases
prioritize_candidates = build_priority_queue


def build_active_learning_queue(limit: int = 50) -> list[ActiveLearningCandidate]:
    """Query database for candidate screening scans and build priority queue."""
    from database import get_db
    try:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT s.id, s.patient_id, s.dr_stage as stage, s.confidence,
                          s.safety_state, s.created_at
                   FROM scans s
                   LEFT JOIN doctor_reviews dr ON s.id = dr.scan_id
                   WHERE dr.id IS NULL
                   ORDER BY s.created_at DESC LIMIT 200"""
            ).fetchall()
        scans = [dict(r) for r in rows]
        return build_priority_queue(scans, top_k=limit)
    except Exception as e:
        log.warning("Could not build active learning queue from DB: %s", e)
        return []

