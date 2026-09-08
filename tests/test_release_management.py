"""Tests for Release Management, Staging, Promotion, and Rollback."""

import os
import pytest
from ml_platform.registry.models import register_model_version, transition_model_status
from ml_platform.release.promotion import promote_to_production
from ml_platform.release.rollback import rollback_production_model
from ml_platform.release.staging import stage_candidate_model


def test_promotion_requires_approved_status():
    model = register_model_version(architecture="pipeline_v3", status="TRAINED")
    v_id = model["version_id"]

    # Not approved yet -> promotion fails
    with pytest.raises(ValueError, match="must be in APPROVED or STAGED"):
        promote_to_production(v_id, promoted_by="super_admin")


def test_staging_and_promotion_flow():
    # Setup approved model
    model = register_model_version(architecture="resnet50", status="TRAINED")
    v_id = model["version_id"]
    transition_model_status(v_id, "EVALUATED")
    transition_model_status(v_id, "CANDIDATE")
    transition_model_status(v_id, "APPROVED")

    # Stage
    stage_res = stage_candidate_model(v_id, staged_by="tester")
    assert stage_res["status"] == "STAGED"

    # Promote
    prom_res = promote_to_production(v_id, promoted_by="super_admin")
    assert prom_res["status"] == "ACTIVE"
    assert prom_res["model_version_id"] == v_id


def test_emergency_rollback():
    # Model 1 in production
    m1 = register_model_version(architecture="resnet50", status="TRAINED")
    v1 = m1["version_id"]
    transition_model_status(v1, "EVALUATED")
    transition_model_status(v1, "CANDIDATE")
    transition_model_status(v1, "APPROVED")
    promote_to_production(v1, promoted_by="admin")

    # Model 2 in production
    m2 = register_model_version(architecture="pipeline_v3", status="TRAINED")
    v2 = m2["version_id"]
    transition_model_status(v2, "EVALUATED")
    transition_model_status(v2, "CANDIDATE")
    transition_model_status(v2, "APPROVED")
    promote_to_production(v2, promoted_by="admin")

    # Rollback to Model 1
    rb = rollback_production_model(target_version_id=v1, authorized_by="sec_officer", incident_reason="Test rollback")
    assert rb["status"] == "ROLLED_BACK"
    assert rb["restored_version_id"] == v1
    assert rb["demoted_version_id"] == v2
