"""Dataset subpackage — building, versioning, splitting, validation."""

from ml_platform.datasets.builder import build_dataset
from ml_platform.datasets.versioning import (
    generate_version_tag,
    compute_manifest_hash,
    save_dataset_manifest,
    load_dataset_manifest,
    verify_dataset_integrity,
)
from ml_platform.datasets.splitting import patient_level_split, verify_patient_isolation
from ml_platform.datasets.validation import validate_dataset_health

__all__ = [
    "build_dataset",
    "generate_version_tag",
    "compute_manifest_hash",
    "save_dataset_manifest",
    "load_dataset_manifest",
    "verify_dataset_integrity",
    "patient_level_split",
    "verify_patient_isolation",
    "validate_dataset_health",
]
