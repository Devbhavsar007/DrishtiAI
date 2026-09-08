"""Data ingestion from synced clinical data.

Queries validated, doctor-reviewed scans from existing clinical tables
and prepares training candidates for the Intelligence Control Plane.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)


def get_training_candidates(
    min_date: str | None = None,
    max_date: str | None = None,
    safety_states: set[str] | None = None,
    min_confidence: float = 0.0,
    limit: int = 10000,
) -> list[dict]:
    """
    Query clinical scan data for training candidate selection.

    Pulls from existing scans table with optional filters.

    Args:
        min_date: ISO datetime string for minimum scan date
        max_date: ISO datetime string for maximum scan date
        safety_states: Set of acceptable safety states (default: VERIFIED, UNCERTAIN)
        min_confidence: Minimum model confidence threshold
        limit: Maximum records to return

    Returns:
        List of scan dicts suitable for eligibility evaluation.
    """
    from database import get_db

    safety_states = safety_states or {"VERIFIED", "UNCERTAIN"}

    query = """
        SELECT s.*, p.name as patient_name, p.age, p.gender
        FROM scans s
        JOIN patients p ON s.patient_id = p.id
        WHERE s.safety_state IN ({placeholders})
        AND s.confidence >= ?
    """.format(
        placeholders=",".join("?" for _ in safety_states)
    )
    params: list[Any] = list(safety_states) + [min_confidence]

    if min_date:
        query += " AND s.created_at >= ?"
        params.append(min_date)
    if max_date:
        query += " AND s.created_at <= ?"
        params.append(max_date)

    query += " ORDER BY s.created_at ASC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    candidates = []
    for row in rows:
        scan = dict(row)
        # Parse JSON fields
        for field_name in ['all_probabilities', 'heatmap_analysis', 'vessel_stats', 'report']:
            try:
                scan[field_name] = json.loads(scan[field_name]) if scan.get(field_name) else {}
            except (json.JSONDecodeError, TypeError):
                scan[field_name] = {}
        candidates.append(scan)

    log.info("Ingestion query returned %d candidates", len(candidates))
    return candidates


def get_doctor_reviews_for_scans(scan_ids: list[str]) -> dict[str, dict]:
    """
    Retrieve all doctor reviews for the given scan IDs.

    Returns:
        Dict mapping scan_id → doctor_review dict
    """
    if not scan_ids:
        return {}

    from database import get_db

    reviews = {}
    # Batch in chunks to avoid SQLite variable limits
    chunk_size = 500
    for i in range(0, len(scan_ids), chunk_size):
        chunk = scan_ids[i:i + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        query = f"""
            SELECT * FROM doctor_reviews
            WHERE scan_id IN ({placeholders})
            ORDER BY created_at DESC
        """
        with get_db() as conn:
            rows = conn.execute(query, chunk).fetchall()

        for row in rows:
            r = dict(row)
            sid = r.get("scan_id", "")
            if sid not in reviews:  # Keep only latest review per scan
                reviews[sid] = r

    log.info("Retrieved %d doctor reviews for %d scans", len(reviews), len(scan_ids))
    return reviews


def get_existing_image_hashes(dataset_id: str | None = None) -> set[str]:
    """
    Get all image hashes already used in training datasets.

    Args:
        dataset_id: If specified, get hashes from a specific dataset only

    Returns:
        Set of image hash strings
    """
    from database import get_db

    with get_db() as conn:
        if dataset_id:
            rows = conn.execute(
                "SELECT image_hash FROM training_samples WHERE dataset_id = ? AND image_hash != ''",
                (dataset_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT image_hash FROM training_samples WHERE image_hash != ''"
            ).fetchall()

    hashes = {row["image_hash"] for row in rows}
    log.info("Found %d existing image hashes", len(hashes))
    return hashes


def get_quarantined_patients() -> set[str]:
    """
    Get patient IDs that are excluded from training.

    Currently checks for patients with rejected doctor reviews or
    patients flagged for data quality issues.
    """
    from database import get_db

    quarantined: set[str] = set()

    with get_db() as conn:
        # Patients with rejected-retake reviews are quarantined
        rows = conn.execute(
            "SELECT DISTINCT patient_id FROM doctor_reviews WHERE decision = 'REJECTED_RETAKE'"
        ).fetchall()
        for row in rows:
            quarantined.add(row["patient_id"])

        # Patients with failed data quality events
        rows = conn.execute(
            "SELECT DISTINCT patient_id FROM data_quality_events WHERE passed = 0 AND patient_id != ''"
        ).fetchall()
        for row in rows:
            quarantined.add(row["patient_id"])

    log.info("Found %d quarantined patients", len(quarantined))
    return quarantined
