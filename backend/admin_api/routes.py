"""Admin API Route Handlers for the DrishtiAI Intelligence Control Plane."""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from flask import request, jsonify, g

from backend.admin_api import admin_bp
from database import get_db
from engine.security.auth import (
    require_admin_role,
    AdminRole,
    Role,
    verify_role_credentials,
    create_admin_token,
    get_current_actor,
)
from ml_platform.datasets.builder import build_dataset
from ml_platform.training.orchestrator import (
    TrainingJobConfig,
    submit_training_job,
    get_training_job_status,
    list_training_jobs,
)
from ml_platform.registry.models import (
    register_model_version,
    get_model_version,
    get_production_model,
    list_model_versions,
    transition_model_status,
)
from ml_platform.evaluation.evaluator import evaluate_predictions, EvaluationResult
from ml_platform.drift.clinical_drift import evaluate_clinical_discordance
from ml_platform.release.promotion import promote_to_production
from ml_platform.release.rollback import rollback_production_model
from ml_platform.governance.approvals import submit_model_approval, list_model_approvals
from ml_platform.governance.audit import log_governance_action, query_governance_audit_trail
from ml_platform.active_learning.prioritization import build_active_learning_queue

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Authentication
# ---------------------------------------------------------------------------
@admin_bp.route("/auth/login", methods=["POST"])
def admin_login():
    """Authenticate an administrator into the Intelligence Control Plane."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "").strip() or "admin_user"
    role = data.get("role", "").strip().upper()
    secret = data.get("secret", "").strip()

    valid_admin_roles = {r.value for r in AdminRole} | {Role.ADMIN.value}
    if role not in valid_admin_roles:
        return jsonify({
            "success": False,
            "error": f"Invalid admin role. Must be one of: {sorted(list(valid_admin_roles))}"
        }), 400

    if not verify_role_credentials(role=role, secret=secret, user_id=user_id):
        return jsonify({
            "success": False,
            "error": "Invalid credentials for requested administrative role."
        }), 401

    token = create_admin_token(user_id=user_id, admin_role=role)
    log_governance_action(
        actor_id=user_id,
        actor_role=role,
        action="LOGIN",
        resource_type="ADMIN_SESSION",
        resource_id=user_id,
    )

    return jsonify({
        "success": True,
        "token": token,
        "user_id": user_id,
        "role": role,
    }), 200


# ---------------------------------------------------------------------------
# 2. Executive Dashboard Overview
# ---------------------------------------------------------------------------
@admin_bp.route("/dashboard", methods=["GET"])
@require_admin_role(*[r.value for r in AdminRole])
def get_dashboard_summary():
    """Get high-level MLOps status across models, data, runs, and drift."""
    prod_model = get_production_model()

    with get_db() as conn:
        total_scans = conn.execute("SELECT COUNT(*) as cnt FROM scans").fetchone()["cnt"]
        reviewed_scans = conn.execute("SELECT COUNT(*) as cnt FROM doctor_reviews").fetchone()["cnt"]
        recent_runs = conn.execute(
            "SELECT id, dataset_id, status, started_at, duration_seconds FROM training_runs ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        total_datasets = conn.execute("SELECT COUNT(*) as cnt FROM training_datasets").fetchone()["cnt"]
        latest_drift = conn.execute(
            "SELECT * FROM drift_events ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

    # Get active learning queue size
    try:
        al_candidates = build_active_learning_queue(limit=50)
        al_queue_len = len(al_candidates)
    except Exception:
        al_queue_len = 0

    return jsonify({
        "success": True,
        "production_model": prod_model,
        "metrics": {
            "total_screenings": total_scans,
            "reviewed_screenings": reviewed_scans,
            "total_datasets": total_datasets,
            "active_learning_queue_depth": al_queue_len,
        },
        "latest_drift": dict(latest_drift) if latest_drift else None,
        "recent_training_runs": [dict(r) for r in recent_runs],
    }), 200


# ---------------------------------------------------------------------------
# 3. Data Health & Ingestion Overview
# ---------------------------------------------------------------------------
@admin_bp.route("/data/overview", methods=["GET"])
@require_admin_role(AdminRole.DATA_STEWARD, AdminRole.ML_ENGINEER, AdminRole.SUPER_ADMIN)
def get_data_overview():
    """Retrieve data pipeline metrics, ungradable rates, and class distributions."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as cnt FROM scans").fetchone()["cnt"]
        stage_counts = conn.execute(
            "SELECT dr_stage, COUNT(*) as cnt FROM scans GROUP BY dr_stage"
        ).fetchall()
        quality_counts = conn.execute(
            "SELECT quality_grade, COUNT(*) as cnt FROM scans GROUP BY quality_grade"
        ).fetchall()

    return jsonify({
        "success": True,
        "total_scans": total,
        "stage_distribution": {str(r["dr_stage"]): r["cnt"] for r in stage_counts if r["dr_stage"] is not None},
        "quality_distribution": {str(r["quality_grade"]): r["cnt"] for r in quality_counts if r["quality_grade"]},
    }), 200


# ---------------------------------------------------------------------------
# 4. Active Learning Queue
# ---------------------------------------------------------------------------
@admin_bp.route("/active-learning", methods=["GET"])
@require_admin_role(AdminRole.DATA_STEWARD, AdminRole.ML_ENGINEER, AdminRole.CLINICAL_REVIEWER, AdminRole.SUPER_ADMIN)
def get_active_learning_candidates():
    """Return prioritized scans needing clinical review or second opinion."""
    limit = int(request.args.get("limit", 50))
    candidates = build_active_learning_queue(limit=limit)
    return jsonify({
        "success": True,
        "count": len(candidates),
        "candidates": [c.to_dict() for c in candidates],
    }), 200


# ---------------------------------------------------------------------------
# 5. Datasets
# ---------------------------------------------------------------------------
@admin_bp.route("/datasets", methods=["GET"])
@require_admin_role(AdminRole.DATA_STEWARD, AdminRole.ML_ENGINEER, AdminRole.SUPER_ADMIN, AdminRole.AUDITOR)
def list_datasets():
    """List all registered versioned training datasets."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM training_datasets ORDER BY created_at DESC"
        ).fetchall()
        return jsonify({
            "success": True,
            "datasets": [dict(r) for r in rows],
        }), 200


@admin_bp.route("/datasets/build", methods=["POST"])
@require_admin_role(AdminRole.DATA_STEWARD, AdminRole.ML_ENGINEER, AdminRole.SUPER_ADMIN)
def trigger_dataset_build():
    """Trigger creation of a new immutable, versioned training dataset."""
    actor = g.get("current_user", {})
    actor_id = actor.get("actor_id", "admin")

    body = request.get_json(silent=True) or {}
    name = body.get("name", "drishti-retina")
    version = body.get("version")

    result = build_dataset(
        name=name,
        version=version,
        val_ratio=float(body.get("val_ratio", 0.15)),
        test_ratio=float(body.get("test_ratio", 0.10)),
        triggered_by=actor_id,
    )

    log_governance_action(
        actor_id=actor_id,
        actor_role=actor.get("actor_role", "ADMIN"),
        action="BUILD_DATASET",
        resource_type="DATASET",
        resource_id=result.get("dataset_id", "unknown"),
        details=result,
    )

    return jsonify({"success": True, "dataset": result}), 201


# ---------------------------------------------------------------------------
# 6. Training Orchestration
# ---------------------------------------------------------------------------
@admin_bp.route("/training", methods=["GET"])
@require_admin_role(AdminRole.ML_ENGINEER, AdminRole.SUPER_ADMIN, AdminRole.AUDITOR)
def get_training_runs():
    """List all past and active training jobs."""
    runs = list_training_jobs(limit=100)
    return jsonify({"success": True, "runs": runs}), 200


@admin_bp.route("/training/submit", methods=["POST"])
@require_admin_role(AdminRole.ML_ENGINEER, AdminRole.SUPER_ADMIN)
def submit_training():
    """Submit a new background training run."""
    actor = g.get("current_user", {})
    actor_id = actor.get("actor_id", "ml_engineer")

    body = request.get_json(silent=True) or {}
    dataset_id = body.get("dataset_id")
    if not dataset_id:
        return jsonify({"success": False, "error": "dataset_id is required"}), 400

    cfg = TrainingJobConfig(
        dataset_id=dataset_id,
        data_dir=body.get("data_dir", "data/aptos"),
        out_dir=body.get("out_dir", "models/dr_pipeline"),
        max_iterations=int(body.get("max_iterations", 4)),
        epochs_head=int(body.get("epochs_head", 2)),
        epochs_partial=int(body.get("epochs_partial", 3)),
        epochs_full=int(body.get("epochs_full", 4)),
        batch_size=int(body.get("batch_size", 8)),
        img_size=int(body.get("img_size", 300)),
        target_sensitivity=float(body.get("target_sensitivity", 0.90)),
        target_specificity=float(body.get("target_specificity", 0.85)),
    )

    job_info = submit_training_job(cfg, triggered_by=actor_id)

    log_governance_action(
        actor_id=actor_id,
        actor_role=actor.get("actor_role", "ML_ENGINEER"),
        action="SUBMIT_TRAINING_JOB",
        resource_type="TRAINING_RUN",
        resource_id=job_info["run_id"],
        details=job_info,
    )

    return jsonify({"success": True, "job": job_info}), 202


@admin_bp.route("/training/<run_id>", methods=["GET"])
@require_admin_role(AdminRole.ML_ENGINEER, AdminRole.SUPER_ADMIN, AdminRole.AUDITOR)
def get_training_run_detail(run_id: str):
    """Get status and metrics for a specific training run."""
    run = get_training_job_status(run_id)
    if not run:
        return jsonify({"success": False, "error": f"Run {run_id} not found"}), 404
    return jsonify({"success": True, "run": run}), 200


# ---------------------------------------------------------------------------
# 7. Model Registry
# ---------------------------------------------------------------------------
@admin_bp.route("/models", methods=["GET"])
@require_admin_role(*[r.value for r in AdminRole])
def list_models():
    """List registered models with optional status filter."""
    status = request.args.get("status")
    models = list_model_versions(status=status)
    return jsonify({"success": True, "models": models}), 200


@admin_bp.route("/models/<version_id>", methods=["GET"])
@require_admin_role(*[r.value for r in AdminRole])
def get_model_detail(version_id: str):
    """Retrieve full metadata for a registered model version."""
    model = get_model_version(version_id)
    if not model:
        return jsonify({"success": False, "error": f"Model {version_id} not found"}), 404
    return jsonify({"success": True, "model": model}), 200


# ---------------------------------------------------------------------------
# 8. Drift Monitoring
# ---------------------------------------------------------------------------
@admin_bp.route("/drift", methods=["GET"])
@require_admin_role(AdminRole.ML_ENGINEER, AdminRole.DATA_STEWARD, AdminRole.SUPER_ADMIN, AdminRole.AUDITOR)
def get_drift_status():
    """Fetch current drift assessment and historical drift events."""
    with get_db() as conn:
        events = conn.execute(
            "SELECT * FROM drift_events ORDER BY created_at DESC LIMIT 50"
        ).fetchall()

    clinical_drift = evaluate_clinical_discordance(days=30, persist_event=False)

    return jsonify({
        "success": True,
        "clinical_drift": clinical_drift,
        "history": [dict(e) for e in events],
    }), 200


@admin_bp.route("/drift/check", methods=["POST"])
@require_admin_role(AdminRole.ML_ENGINEER, AdminRole.SUPER_ADMIN)
def run_drift_check():
    """Trigger an immediate clinical and distribution drift evaluation."""
    res = evaluate_clinical_discordance(days=30, persist_event=True)
    return jsonify({"success": True, "result": res}), 200


# ---------------------------------------------------------------------------
# 9. Release Management (Promotion & Rollback)
# ---------------------------------------------------------------------------
@admin_bp.route("/releases", methods=["GET"])
@require_admin_role(*[r.value for r in AdminRole])
def list_deployments():
    """List deployment and promotion history."""
    with get_db() as conn:
        deps = conn.execute("SELECT * FROM deployments ORDER BY deployed_at DESC LIMIT 50").fetchall()
        return jsonify({"success": True, "deployments": [dict(d) for d in deps]}), 200


@admin_bp.route("/releases/promote", methods=["POST"])
@require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.ML_ENGINEER)
def promote_model():
    """Promote an approved model version to production."""
    actor = g.get("current_user", {})
    actor_id = actor.get("actor_id", "admin")

    body = request.get_json(silent=True) or {}
    version_id = body.get("model_version_id")
    if not version_id:
        return jsonify({"success": False, "error": "model_version_id is required"}), 400

    try:
        res = promote_to_production(
            model_version_id=version_id,
            promoted_by=actor_id,
            reason=body.get("reason", "Admin promotion via Control Plane"),
        )
        log_governance_action(
            actor_id=actor_id,
            actor_role=actor.get("actor_role", "SUPER_ADMIN"),
            action="PROMOTE_MODEL",
            resource_type="MODEL_VERSION",
            resource_id=version_id,
            details=res,
        )
        return jsonify({"success": True, "promotion": res}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@admin_bp.route("/releases/rollback", methods=["POST"])
@require_admin_role(AdminRole.SUPER_ADMIN, AdminRole.SECURITY_ADMIN)
def rollback_model():
    """Execute an emergency or routine production rollback."""
    actor = g.get("current_user", {})
    actor_id = actor.get("actor_id", "security_admin")

    body = request.get_json(silent=True) or {}
    target_id = body.get("target_model_version_id")
    reason = body.get("reason", "Emergency rollback triggered via Intelligence Control Plane")

    try:
        res = rollback_production_model(
            target_version_id=target_id,
            authorized_by=actor_id,
            incident_reason=reason,
        )
        log_governance_action(
            actor_id=actor_id,
            actor_role=actor.get("actor_role", "SECURITY_ADMIN"),
            action="ROLLBACK_MODEL",
            resource_type="MODEL_VERSION",
            resource_id=target_id or "auto-detected",
            details=res,
        )
        return jsonify({"success": True, "rollback": res}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------------------------------------------------------------------------
# 10. Human Governance & Approvals
# ---------------------------------------------------------------------------
@admin_bp.route("/approvals", methods=["GET"])
@require_admin_role(*[r.value for r in AdminRole])
def get_approvals():
    """List historical approval records."""
    version_id = request.args.get("model_version_id")
    records = list_model_approvals(version_id)
    return jsonify({"success": True, "approvals": records}), 200


@admin_bp.route("/approvals/submit", methods=["POST"])
@require_admin_role(AdminRole.CLINICAL_REVIEWER, AdminRole.SUPER_ADMIN)
def submit_approval():
    """Submit clinical or administrative approval decision for model promotion."""
    actor = g.get("current_user", {})
    actor_id = actor.get("actor_id", "clinical_reviewer")
    actor_role = actor.get("actor_role", AdminRole.CLINICAL_REVIEWER.value)

    body = request.get_json(silent=True) or {}
    version_id = body.get("model_version_id")
    decision = body.get("decision", "APPROVED")
    comments = body.get("comments", "")

    if not version_id:
        return jsonify({"success": False, "error": "model_version_id is required"}), 400

    try:
        res = submit_model_approval(
            model_version_id=version_id,
            reviewer_id=actor_id,
            reviewer_role=actor_role,
            decision=decision,
            safety_checks_reviewed=bool(body.get("safety_checks_reviewed", True)),
            comments=comments,
        )
        log_governance_action(
            actor_id=actor_id,
            actor_role=actor_role,
            action=f"MODEL_{decision}",
            resource_type="MODEL_VERSION",
            resource_id=version_id,
            details=res,
        )
        return jsonify({"success": True, "approval": res}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------------------------------------------------------------------------
# 11. Audit Trail & System Health
# ---------------------------------------------------------------------------
@admin_bp.route("/audit", methods=["GET"])
@require_admin_role(AdminRole.AUDITOR, AdminRole.SECURITY_ADMIN, AdminRole.SUPER_ADMIN)
def get_audit_trail():
    """Query recent governance audit logs."""
    limit = int(request.args.get("limit", 100))
    trail = query_governance_audit_trail(limit=limit)
    return jsonify({"success": True, "audit_trail": trail}), 200


@admin_bp.route("/system", methods=["GET"])
@require_admin_role(*[r.value for r in AdminRole])
def get_system_health():
    """Get system health metrics, storage, and runtime information."""
    import platform

    return jsonify({
        "success": True,
        "plane": "INTELLIGENCE_CONTROL_PLANE",
        "timestamp": time.time(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "status": "OPERATIONAL",
    }), 200
