"""Model artifact management and integrity verification.

Secures model checkpoints with SHA-256 hashes, manages registry storage,
and verifies integrity before any model promotion or inference loading.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from typing import Any

from config_admin import REGISTRY_DIR, PRODUCTION_MODELS_DIR

log = logging.getLogger(__name__)


def compute_file_sha256(filepath: str, block_size: int = 65536) -> str:
    """Compute SHA-256 checksum of a file on disk."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Artifact not found: {filepath}")

    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def stage_model_artifacts(
    version_id: str,
    weights_path: str,
    calibration_path: str | None = None,
) -> dict[str, str]:
    """
    Store model weights and calibration file into versioned registry storage.
    Returns mapping of artifact paths and sha256 checksums.
    """
    dest_dir = os.path.join(REGISTRY_DIR, version_id)
    os.makedirs(dest_dir, exist_ok=True)

    weights_sha256 = ""
    staged_weights_path = ""
    if os.path.isfile(weights_path):
        weights_sha256 = compute_file_sha256(weights_path)
        ext = os.path.splitext(weights_path)[1]
        staged_weights_path = os.path.join(dest_dir, f"model{ext}")
        shutil.copy2(weights_path, staged_weights_path)

    staged_calib_path = ""
    if calibration_path and os.path.isfile(calibration_path):
        staged_calib_path = os.path.join(dest_dir, "calibration.json")
        shutil.copy2(calibration_path, staged_calib_path)

    return {
        "staged_weights_path": staged_weights_path,
        "staged_calibration_path": staged_calib_path,
        "weights_sha256": weights_sha256,
    }


def verify_artifact_integrity(filepath: str, expected_sha256: str) -> bool:
    """Verify that file on disk matches expected SHA-256 digest."""
    try:
        actual_hash = compute_file_sha256(filepath)
        return actual_hash.lower() == expected_sha256.lower()
    except Exception as e:
        log.error("Failed to verify artifact integrity for %s: %s", filepath, e)
        return False
