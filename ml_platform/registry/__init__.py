"""Model registry subpackage — versioning, compatibility, and artifact security."""

from ml_platform.registry.models import (
    register_model_version,
    transition_model_status,
    get_model_version,
    get_production_model,
    list_model_versions,
    VALID_STATUSES,
)
from ml_platform.registry.compatibility import check_runtime_compatibility
from ml_platform.registry.artifacts import (
    compute_file_sha256,
    stage_model_artifacts,
    verify_artifact_integrity,
)

__all__ = [
    "register_model_version",
    "transition_model_status",
    "get_model_version",
    "get_production_model",
    "list_model_versions",
    "VALID_STATUSES",
    "check_runtime_compatibility",
    "compute_file_sha256",
    "stage_model_artifacts",
    "verify_artifact_integrity",
]
