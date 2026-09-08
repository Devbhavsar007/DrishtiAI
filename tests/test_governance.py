"""Tests for Governance, Separation of Duties, and Audit Trail."""

import pytest
from ml_platform.registry.models import register_model_version, transition_model_status
from ml_platform.governance.approvals import submit_model_approval, list_model_approvals
from ml_platform.governance.audit import log_governance_action, query_governance_audit_trail


def test_separation_of_duties_enforcement():
    model = register_model_version(
        architecture="pipeline_v3",
        created_by="engineer_alice",
        status="TRAINED",
    )
    v_id = model["version_id"]
    transition_model_status(v_id, "EVALUATED", actor_id="engineer_alice")

    # Creator Alice tries to approve her own model as CLINICAL_REVIEWER -> must be rejected
    with pytest.raises(PermissionError, match="Separation of duties"):
        submit_model_approval(
            model_version_id=v_id,
            reviewer_id="engineer_alice",
            reviewer_role="CLINICAL_REVIEWER",
            decision="APPROVED",
        )

    # Independent doctor/reviewer Bob can approve
    appr = submit_model_approval(
        model_version_id=v_id,
        reviewer_id="dr_bob",
        reviewer_role="CLINICAL_REVIEWER",
        decision="APPROVED",
        comments="Clinically validated on held-out cohort",
    )
    assert appr["decision"] == "APPROVED"


def test_unauthorized_role_approval_rejected():
    model = register_model_version(architecture="resnet50", status="EVALUATED")
    v_id = model["version_id"]

    # Role HEALTH_WORKER or ML_ENGINEER cannot sign off on clinical models
    with pytest.raises(PermissionError):
        submit_model_approval(
            model_version_id=v_id,
            reviewer_id="worker_sam",
            reviewer_role="HEALTH_WORKER",
            decision="APPROVED",
        )


def test_governance_audit_trail():
    log_id = log_governance_action(
        actor_id="admin_1",
        actor_role="SUPER_ADMIN",
        action="TEST_ACTION",
        resource_type="TEST_RES",
        resource_id="res-123",
        details={"key": "value"},
    )
    assert log_id.startswith("aud-")

    trail = query_governance_audit_trail(limit=10)
    assert isinstance(trail, list)
