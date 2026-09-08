# Runbook: Model Deployment & Promotion

## Objective
Promote a validated and approved candidate model to active clinical production.

## Prerequisites
- Active role: `CLINICAL_REVIEWER` (for approval) and `SUPER_ADMIN` (for promotion)
- Model must be in `CANDIDATE` or `APPROVED` status

## Procedure
1. **Clinical Review Sign-off**:
   - Navigate to **Clinical Approvals**.
   - Inspect held-out performance metrics (Sensitivity, Specificity, QWK, ECE).
   - Enter clinical notes and click **Approve for Staging / Production**.
   - Model status transitions to `APPROVED`.

2. **Stage Model (Optional Canary)**:
   - Run non-clinical synthetic test queries to verify ONNX runtime compatibility and latency bounds (< 250ms).

3. **Promote to Production**:
   - Navigate to **Model Registry**.
   - Locate the approved model and click **Promote to Prod**.
   - The system archives the previous production model, deploys weights to `models/production/best_model.pt`, and logs the deployment event.
