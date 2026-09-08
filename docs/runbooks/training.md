# Runbook: Training & Model Retraining

## Objective
Safely compile synchronized clinical data and execute a curriculum retraining run for diabetic retinopathy grading.

## Prerequisites
- Active role: `ML_ENGINEER` or `SUPER_ADMIN`
- At least 100 verified screening samples with doctor ground-truth reviews

## Procedure
1. **Compile Dataset**:
   - Navigate to **Dataset Registry** in the Intelligence Control Plane.
   - Click **Compile New Dataset**.
   - Specify `val_ratio=0.15`, `test_ratio=0.10`.
   - Verify that patient-level isolation completes with zero data leakage. Note the generated `dataset_id`.

2. **Launch Training**:
   - Navigate to **Training Jobs**.
   - Click **Launch Training Job**.
   - Select the target dataset and choose the preset `standard_retina`.
   - Monitor real-time progress via logs or `GET /api/admin/training/<run_id>`.

3. **Verify Evaluation**:
   - Check that the job reached `COMPLETED`.
   - Ensure all 6 clinical safety gates passed.
   - The model is automatically registered into the Model Registry in `EVALUATED` status.
