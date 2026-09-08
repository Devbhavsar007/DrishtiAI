"""End-to-end test verifying the complete DrishtiAI lifecycle:
Screening -> Sync -> Doctor Review -> Candidate Eligibility -> Dataset Construction ->
Training Orchestration -> Safety Gates Evaluation -> Model Registration -> Staging ->
Production -> Rollback
"""

import uuid
import pytest
from database import (
    get_db,
    create_patient,
    delete_patient,
    save_scan,
    get_scan,
    save_doctor_review,
    get_doctor_review,
    record_sync_event,
    reconcile_sync_batch,
)
from ml_platform.data.eligibility import check_eligibility
from ml_platform.datasets.builder import build_dataset
from ml_platform.training.orchestrator import (
    TrainingJobConfig,
    submit_training_job,
    get_training_job_status,
)
from ml_platform.evaluation.safety_gates import evaluate_safety_gates
from ml_platform.registry.models import register_model_version, transition_model_status
from ml_platform.release.staging import stage_candidate_model
from ml_platform.release.promotion import promote_to_production
from ml_platform.release.rollback import rollback_production_model


def test_full_drishti_ai_lifecycle():
    # 1. CLINICAL SCREENING & PERSISTENCE
    patient = create_patient(
        name="E2E Lifecycle Test Patient",
        age=58,
        gender="Female",
        diabetes_duration=10,
        sugar_level=170.0,
        hba1c=8.4,
        notes="Full lifecycle test subject",
    )
    patient_id = patient["id"]
    scan_id = f"e2e-scan-{uuid.uuid4().hex[:8]}"

    try:
        save_scan(
            scan_id=scan_id,
            patient_id=patient_id,
            detection_result={"stage": 2, "stage_name": "Moderate NPDR", "confidence": 88.0, "severity": "moderate", "color": "#EA580C"},
            heatmap_analysis={},
            vessel_stats={},
            report={"findings": ["Microaneurysms detected"]},
            image_paths={"original": "sample.png"},
            processing_time=0.45,
            safety_state="VERIFIED",
            screening_state="FINALIZED"
        )
        saved_scan = get_scan(scan_id)
        assert saved_scan is not None
        assert saved_scan["stage"] == 2

        # 2. OFFLINE SYNC RECORDING & RECONCILIATION
        sync_evt_id = record_sync_event(
            device_id="CLINIC-EDGE-01",
            entity_type="scan",
            entity_id=scan_id,
            action="UPSERT",
            payload={"stage": 2, "patient_id": patient_id},
            version=1
        )
        assert sync_evt_id.startswith("sync-")

        reconcile_res = reconcile_sync_batch([{
            "id": sync_evt_id,
            "device_id": "CLINIC-EDGE-01",
            "entity_type": "scan",
            "entity_id": scan_id,
            "action": "UPSERT",
            "payload": {"stage": 2, "patient_id": patient_id},
            "version": 1
        }])
        assert reconcile_res["synced_count"] >= 1

        # 3. DOCTOR REVIEW (Ground Truth Confirmation)
        saved_review = save_doctor_review(
            scan_id=scan_id,
            patient_id=patient_id,
            doctor_id="DR-E2E-CHIEF",
            doctor_name="Dr. Radhika Sharma",
            decision="APPROVED",
            original_stage=2,
            adjusted_stage=2,
            approved_priority="ROUTINE",
            clinical_notes="Confirmed moderate NPDR with classic microaneurysms.",
            recommended_intervention="Follow-up in 3 months",
        )
        assert saved_review["decision"] == "APPROVED"

        # Verify doctor review retrieval
        retrieved_review = get_doctor_review(scan_id)
        assert retrieved_review is not None
        assert retrieved_review["doctor_id"] == "DR-E2E-CHIEF"

        # 4. CANDIDATE DATA ELIGIBILITY
        eligibility = check_eligibility(saved_scan, doctor_review=retrieved_review)
        assert eligibility.eligible is True
        assert eligibility.label_provenance == "DOCTOR_CONFIRMED"

        # 5. DATASET CONSTRUCTION
        dataset_name = f"DATASET-E2E-{uuid.uuid4().hex[:6]}"
        ds_result = build_dataset(
            name=dataset_name,
            version=f"v1-{uuid.uuid4().hex[:4]}",
            val_ratio=0.2,
            test_ratio=0.1
        )
        assert ds_result["dataset_id"] is not None
        dataset_id = ds_result["dataset_id"]

        # 6. TRAINING ORCHESTRATION
        job_cfg = TrainingJobConfig(dataset_id=dataset_id, max_iterations=1, epochs_head=1)
        res = submit_training_job(job_cfg, triggered_by="e2e_test")
        assert res["status"] in ("QUEUED", "RUNNING", "COMPLETED", "FAILED")
        run_id = res["run_id"]

        status = get_training_job_status(run_id)
        assert status is not None
        assert status["id"] == run_id

        # 7. CLINICAL SAFETY GATES EVALUATION
        high_perf_metrics = {
            "sensitivity": 0.94,
            "specificity": 0.91,
            "accuracy": 0.93,
            "quadratic_weighted_kappa": 0.88,
            "expected_calibration_error": 0.04,
            "false_negative_rate": 0.06
        }
        gate_result = evaluate_safety_gates(high_perf_metrics)
        assert gate_result["all_passed"] is True
        assert len(gate_result["failed_gates"]) == 0

        # 8. MODEL REGISTRATION IN REGISTRY & LIFECYCLE TRANSITIONS
        model = register_model_version(
            architecture="efficientnet_b4_dr",
            training_run_id=run_id,
            dataset_id=dataset_id,
            model_path="models/grading/e2e_candidate.onnx",
            status="TRAINED"
        )
        v_id = model["version_id"]
        assert v_id is not None

        # Transition through governance states: TRAINED -> EVALUATED -> CANDIDATE -> APPROVED
        transition_model_status(v_id, "EVALUATED")
        transition_model_status(v_id, "CANDIDATE")
        transition_model_status(v_id, "APPROVED")

        # 9. STAGING CANDIDATE MODEL
        stage_res = stage_candidate_model(v_id, staged_by="tester@drishtiai.org")
        assert stage_res["status"] == "STAGED"

        # 10. PRODUCTION PROMOTION
        prom_res = promote_to_production(v_id, promoted_by="super_admin@drishtiai.org")
        assert prom_res["status"] == "ACTIVE"
        assert prom_res["model_version_id"] == v_id

        # 11. EMERGENCY ROLLBACK CAPABILITY DRILL
        # Register a fallback baseline model
        baseline_model = register_model_version(architecture="resnet50_baseline", status="TRAINED")
        base_id = baseline_model["version_id"]
        transition_model_status(base_id, "EVALUATED")
        transition_model_status(base_id, "CANDIDATE")
        transition_model_status(base_id, "APPROVED")

        # Rollback active model to the baseline
        rb = rollback_production_model(
            target_version_id=base_id,
            authorized_by="sec_admin@drishtiai.org",
            incident_reason="Verification drill rollback"
        )
        assert rb["status"] == "ROLLED_BACK"
        assert rb["restored_version_id"] == base_id
        assert rb["demoted_version_id"] == v_id

    finally:
        # Cleanup
        with get_db() as conn:
            conn.execute("DELETE FROM training_samples WHERE patient_id = ?", (patient_id,))
            conn.execute("DELETE FROM sync_events WHERE entity_id IN (?, ?)", (patient_id, scan_id))
            conn.execute("DELETE FROM doctor_reviews WHERE patient_id = ?", (patient_id,))
            conn.commit()
        delete_patient(patient_id)
