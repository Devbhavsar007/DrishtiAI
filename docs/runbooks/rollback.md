# Runbook: Emergency Production Model Rollback

## Objective
Restore the previous approved production vision model when an active model displays critical drift, clinical disagreement, or inference instability.

## Prerequisites
* Role: `SUPER_ADMIN` or `SECURITY_ADMIN`.
* A previously deployed model exists in `model_versions` with status `ARCHIVED` or known-good history.

## Procedure

### Option 1: Via Intelligence Admin UI
1. Navigate to **Releases & Promotion** in the Admin Control Plane (`/admin/releases`).
2. Select the rollback target model version.
3. Provide an incident justification (e.g., "Elevated false-negative rate detected by clinical review").
4. Click **Execute Rollback**.

### Option 2: Via REST API
```bash
curl -X POST http://localhost:5000/api/admin/releases/rollback \
  -H "Authorization: Bearer <SUPER_ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "target_model_version_id": "drishti-retina-v1.7.0",
    "reason": "Elevated discordance detected on edge site #4"
  }'
```

## Invariants Verified
* The target model must exist and have previously passed all safety gates.
* The previous active model is demoted to status `ROLLED_BACK`.
* An immutable audit record is committed to `audit_log` and `deployments`.
