# DrishtiAI Intelligence Control Plane — Architecture

## 1. Overview
The **Intelligence Control Plane** is the governing MLOps lifecycle infrastructure for DrishtiAI. It controls data eligibility, immutable dataset versioning, curriculum training orchestration, clinical safety gates, model registry, drift surveillance, and separation-of-duties release management.

## 2. Architectural Separation
```
+-------------------------------------------------------------------------+
|                       DRISHTIAI PLATFORM                                |
+------------------------------------+------------------------------------+
|       CLINICAL PLATFORM            |     INTELLIGENCE CONTROL PLANE     |
| (Edge / Clinic / Patient Flow)     | (MLOps / Governance / Lifecyle)    |
+------------------------------------+------------------------------------+
| - Patient Directory & Timeline     | - Data Eligibility & Provenance    |
| - Fundus Camera IQA & Inference    | - Patient-Isolated Datasets        |
| - Grad-CAM & Vessel Segmentations  | - Active Learning Priority Queue   |
| - Referral & Triage Rules          | - Training Job Orchestration       |
| - Doctor Reviews & Overrides       | - Model Registry (Immutable)       |
| - Offline Sync Outbox              | - Safety Gate Evaluation           |
|                                    | - Feature & Discordance Drift      |
|                                    | - Separation-of-Duties Approvals   |
|                                    | - Staged Deployment & Rollback     |
+------------------------------------+------------------------------------+
```

## 3. Governance & Roles
The Intelligence Control Plane introduces dedicated RBAC roles separated from clinical users:
- `SUPER_ADMIN`: System-wide governance and administrative oversight.
- `ML_ENGINEER`: Submits retraining runs, inspects loss curves, tunes hyperparameters.
- `DATA_STEWARD`: Governs dataset compilation, validates manifests, inspects data leakage.
- `CLINICAL_REVIEWER`: Licensed ophthalmologist providing human clinical sign-off for model candidates.
- `SECURITY_ADMIN`: Governs access tokens, edge credentials, and emergency rollbacks.
- `AUDITOR`: Read-only access to immutable compliance logs.
