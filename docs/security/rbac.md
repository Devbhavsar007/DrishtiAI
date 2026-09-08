# Role-Based Access Control (RBAC) & Governance Security

## 1. Domain Separation
DrishtiAI isolates permissions into two logical domains:

### Clinical Roles
- `PATIENT`: Access personal screening records and educational reports.
- `HEALTH_WORKER`: Upload scans, run IQA, manage eye camp batch queues.
- `DOCTOR`: Override AI stages, write clinical notes, assign referrals.
- `ADMIN`: Manage clinic settings and user accounts.

### Intelligence Control Plane Roles
- `SUPER_ADMIN`: Root control plane administrator.
- `ML_ENGINEER`: Submits retraining runs, configures hyperparameters, views loss telemetry.
- `DATA_STEWARD`: Manages dataset compilation, inspects data leakage, monitors quality.
- `CLINICAL_REVIEWER`: Licensed clinician providing mandatory sign-off for model candidates.
- `SECURITY_ADMIN`: Key rotation, edge signature verification, emergency rollbacks.
- `AUDITOR`: Read-only access to immutable audit trails and compliance logs.

## 2. Separation of Duties Enforced in Code
In `ml_platform/governance/approvals.py`, an ML Engineer who trained a model (`created_by`) is strictly prohibited from signing off on that same model as the clinical reviewer. Only independent clinicians or super administrators can grant approval.

## 3. Token & Edge Signatures
- Cloud/Admin API: HMAC-SHA256 bearer tokens with 12-hour expiration.
- Edge Sync: Nonce and timestamped HMAC signature (`X-Drishti-Edge-Signature`) ensuring authentic screening data transmission.
