"""Versioned dataset builder for the DrishtiAI Intelligence Control Plane.

Builds immutable, versioned training datasets from synchronized clinical data.
Pipeline: ingest → eligibility → quality → provenance → split → manifest → finalize.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections import Counter
from datetime import datetime
from typing import Any

log = logging.getLogger(__name__)


def build_dataset(
    name: str = "drishti-retina",
    version: str | None = None,
    min_date: str | None = None,
    max_date: str | None = None,
    min_provenance: str = "AI_ONLY",
    val_ratio: float = 0.15,
    test_ratio: float = 0.10,
    seed: int = 42,
    triggered_by: str = "system",
) -> dict[str, Any]:
    """
    Build a versioned training dataset from clinical data.

    Pipeline steps:
      1. Ingest candidate scans from database
      2. Retrieve doctor reviews for label provenance
      3. Check eligibility for each candidate
      4. Apply patient-level stratified splitting
      5. Verify no data leakage
      6. Create dataset manifest
      7. Persist to database

    Args:
        name: Dataset family name
        version: Version tag (auto-generated if None)
        min_date: Minimum scan date filter
        max_date: Maximum scan date filter
        min_provenance: Minimum label provenance level
        val_ratio: Validation split ratio
        test_ratio: Test split ratio
        seed: Random seed
        triggered_by: User/system that triggered the build

    Returns:
        Dataset summary dict
    """
    from database import get_db
    from ml_platform.data.ingestion import (
        get_training_candidates, get_doctor_reviews_for_scans,
        get_existing_image_hashes, get_quarantined_patients,
    )
    from ml_platform.data.eligibility import batch_check_eligibility
    from ml_platform.data.leakage import patient_stratified_split, check_leakage

    # Auto-generate version
    if not version:
        version = datetime.utcnow().strftime("v%Y.%m.%d-%H%M")

    dataset_id = f"ds-{uuid.uuid4().hex[:12]}"
    log.info("Building dataset %s/%s (id=%s)", name, version, dataset_id)

    # Step 1: Ingest candidates
    candidates = get_training_candidates(
        min_date=min_date, max_date=max_date, limit=50000
    )
    if not candidates:
        log.warning("No candidates found for dataset build")
        return {"dataset_id": dataset_id, "status": "EMPTY", "total_samples": 0}

    # Step 2: Get reviews
    scan_ids = [c["id"] for c in candidates]
    reviews = get_doctor_reviews_for_scans(scan_ids)

    # Step 3: Eligibility check
    existing_hashes = get_existing_image_hashes()
    quarantined = get_quarantined_patients()
    eligibility_results = batch_check_eligibility(
        candidates, reviews, existing_hashes, quarantined
    )

    # Filter to eligible only
    eligible_pairs = [
        (candidates[i], eligibility_results[i])
        for i in range(len(candidates))
        if eligibility_results[i].eligible
    ]

    if not eligible_pairs:
        log.warning("No eligible candidates after filtering")
        return {"dataset_id": dataset_id, "status": "NO_ELIGIBLE", "total_samples": 0}

    # Step 4: Patient-level splitting
    from collections import defaultdict
    patient_samples: dict[str, list[dict]] = defaultdict(list)
    for scan, elig in eligible_pairs:
        patient_samples[scan["patient_id"]].append({
            "scan_id": scan["id"],
            "label": elig.label,
            "provenance": elig.label_provenance,
            "quality_score": elig.quality_score,
            "image_hash": scan.get("image_hash", ""),
            "doctor_review_id": elig.doctor_review_id,
        })

    split_assignments = patient_stratified_split(
        patient_samples, val_ratio=val_ratio, test_ratio=test_ratio, seed=seed
    )

    # Step 5: Leakage check
    leakage_result = check_leakage(split_assignments)
    if leakage_result.has_leakage:
        log.error("ABORTING dataset build: data leakage detected")
        return {
            "dataset_id": dataset_id,
            "status": "LEAKAGE_DETECTED",
            "leaked_patients": leakage_result.leaked_patients,
        }

    # Step 6: Build sample records and manifest
    patient_split_map: dict[str, str] = {}
    for split_name, assignments in split_assignments.items():
        for assignment in assignments:
            patient_split_map[assignment.patient_id] = split_name

    sample_records = []
    class_dist = Counter()
    split_dist = Counter()

    for scan, elig in eligible_pairs:
        patient_id = scan["patient_id"]
        split = patient_split_map.get(patient_id, "TRAIN")

        sample_id = f"samp-{uuid.uuid4().hex[:12]}"
        sample_records.append({
            "id": sample_id,
            "dataset_id": dataset_id,
            "scan_id": scan["id"],
            "patient_id": patient_id,
            "split": split,
            "label": elig.label,
            "label_provenance": elig.label_provenance,
            "doctor_review_id": elig.doctor_review_id,
            "eligibility_status": "ELIGIBLE",
            "quality_score": elig.quality_score,
            "image_hash": scan.get("image_hash", ""),
        })

        class_dist[elig.label] += 1
        split_dist[split] += 1

    # Step 7: Persist
    manifest = {
        "name": name,
        "version": version,
        "total_samples": len(sample_records),
        "total_patients": len(patient_samples),
        "class_distribution": dict(class_dist),
        "split_distribution": dict(split_dist),
        "seed": seed,
        "min_date": min_date,
        "max_date": max_date,
        "min_provenance": min_provenance,
    }
    manifest_json = json.dumps(manifest, sort_keys=True)
    manifest_checksum = hashlib.sha256(manifest_json.encode()).hexdigest()[:16]

    exclusion_summary = {
        "total_candidates": len(candidates),
        "total_eligible": len(eligible_pairs),
        "total_excluded": len(candidates) - len(eligible_pairs),
    }

    with get_db() as conn:
        # Insert dataset record
        conn.execute(
            """INSERT INTO training_datasets
               (id, name, version, status, total_samples, total_patients,
                class_distribution, split_strategy, manifest_json, manifest_checksum,
                exclusion_summary, created_by)
               VALUES (?, ?, ?, 'BUILDING', ?, ?, ?, 'patient_stratified', ?, ?, ?, ?)""",
            (dataset_id, name, version, len(sample_records), len(patient_samples),
             json.dumps(dict(class_dist)), manifest_json, manifest_checksum,
             json.dumps(exclusion_summary), triggered_by)
        )

        # Insert sample records
        for s in sample_records:
            conn.execute(
                """INSERT INTO training_samples
                   (id, dataset_id, scan_id, patient_id, split, label,
                    label_provenance, doctor_review_id, eligibility_status,
                    quality_score, image_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (s["id"], s["dataset_id"], s["scan_id"], s["patient_id"],
                 s["split"], s["label"], s["label_provenance"],
                 s["doctor_review_id"], s["eligibility_status"],
                 s["quality_score"], s["image_hash"])
            )

        # Finalize
        conn.execute(
            "UPDATE training_datasets SET status = 'FINALIZED', finalized_at = datetime('now') WHERE id = ?",
            (dataset_id,)
        )
        conn.commit()

    log.info(
        "Dataset %s/%s finalized: %d samples, %d patients, checksum=%s",
        name, version, len(sample_records), len(patient_samples), manifest_checksum
    )

    return {
        "dataset_id": dataset_id,
        "name": name,
        "version": version,
        "status": "FINALIZED",
        "total_samples": len(sample_records),
        "total_patients": len(patient_samples),
        "class_distribution": dict(class_dist),
        "split_distribution": dict(split_dist),
        "manifest_checksum": manifest_checksum,
    }


def get_dataset(dataset_id: str) -> dict | None:
    """Retrieve a dataset record by ID."""
    from database import get_db

    with get_db() as conn:
        row = conn.execute("SELECT * FROM training_datasets WHERE id = ?", (dataset_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for field_name in ['class_distribution', 'manifest_json', 'exclusion_summary',
                       'site_distribution', 'device_distribution']:
        try:
            d[field_name] = json.loads(d[field_name]) if d.get(field_name) else {}
        except (json.JSONDecodeError, TypeError):
            d[field_name] = {}
    return d


def list_datasets(limit: int = 50) -> list[dict]:
    """List all datasets, newest first."""
    from database import get_db

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM training_datasets ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    datasets = []
    for row in rows:
        d = dict(row)
        for field_name in ['class_distribution', 'manifest_json', 'exclusion_summary']:
            try:
                d[field_name] = json.loads(d[field_name]) if d.get(field_name) else {}
            except (json.JSONDecodeError, TypeError):
                d[field_name] = {}
        datasets.append(d)
    return datasets


def get_dataset_samples(dataset_id: str, split: str | None = None) -> list[dict]:
    """Retrieve all samples in a dataset, optionally filtered by split."""
    from database import get_db

    with get_db() as conn:
        if split:
            rows = conn.execute(
                "SELECT * FROM training_samples WHERE dataset_id = ? AND split = ? ORDER BY created_at ASC",
                (dataset_id, split)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM training_samples WHERE dataset_id = ? ORDER BY split, created_at ASC",
                (dataset_id,)
            ).fetchall()
    return [dict(r) for r in rows]
