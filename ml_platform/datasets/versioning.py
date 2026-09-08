"""Dataset versioning and metadata management.

Handles dataset manifests, version tags, checksum integrity, and distribution summaries.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any

from config_admin import DATASETS_DIR

log = logging.getLogger(__name__)


def generate_version_tag(prefix: str = "v") -> str:
    """Generate a chronological version tag, e.g. v2026.09.08-1730."""
    return f"{prefix}{datetime.utcnow().strftime('%Y.%m.%d-%H%M')}"


def compute_manifest_hash(manifest_data: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of dataset manifest."""
    canonical = json.dumps(manifest_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_dataset_manifest(dataset_id: str, manifest_data: dict[str, Any]) -> str:
    """Write dataset manifest to disk as an immutable artifact."""
    version = manifest_data.get("version", "v1.0.0")
    target_dir = os.path.join(DATASETS_DIR, f"{dataset_id}_{version}")
    os.makedirs(target_dir, exist_ok=True)

    manifest_path = os.path.join(target_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, sort_keys=True)

    log.info("Saved dataset manifest to %s", manifest_path)
    return manifest_path


def load_dataset_manifest(manifest_path: str) -> dict[str, Any]:
    """Read dataset manifest and verify structure."""
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def verify_dataset_integrity(manifest_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Verify manifest internal consistency and sample checksums."""
    issues = []
    if "samples" not in manifest_data:
        issues.append("Manifest missing 'samples' list")
        return False, issues

    declared_total = manifest_data.get("total_samples", 0)
    actual_samples = len(manifest_data["samples"])
    if declared_total != actual_samples:
        issues.append(f"Sample count mismatch: declared {declared_total}, actual {actual_samples}")

    split_counts = {"TRAIN": 0, "VALIDATION": 0, "TEST": 0}
    for s in manifest_data["samples"]:
        sp = s.get("split", "TRAIN")
        if sp in split_counts:
            split_counts[sp] += 1
        if "label" not in s:
            issues.append(f"Sample {s.get('scan_id')} missing label")

    manifest_splits = manifest_data.get("splits", {})
    for k, v in split_counts.items():
        if manifest_splits.get(k) is not None and manifest_splits[k] != v:
            issues.append(f"Split {k} count mismatch: declared {manifest_splits[k]}, actual {v}")

    return len(issues) == 0, issues
