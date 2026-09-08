# DrishtiAI Security: Authentication Architecture

## Overview
DrishtiAI enforces strict cryptographic authentication across two isolated domains:
1. **Clinical Authentication Domain**: Serves healthcare workers, technicians, ophthalmologists, and patients.
2. **Intelligence Control Plane Domain**: Serves MLOps engineers, data stewards, clinical reviewers, and administrators.

## Token Specifications
* **Format**: `dr1.<base64_payload>.<base64_hmac_sha256>`
* **Signing Algorithm**: HMAC-SHA256 with key rotation support (`FLASK_SECRET`).
* **Expiration**: Default 24 hours (86,400 seconds) for standard sessions; shorter for high-privilege operations.
* **Tamper Resistance**: Payload modifications immediately invalidate cryptographic signature checks.

## Authentication Endpoints
* `POST /api/auth/token`: Exchanges credentials for a clinical session token.
* `POST /api/admin/auth/login`: Exchanges administrative credentials and role identity for an Intelligence Control Plane access token.

## Invariant Enforcement
* Clinical tokens cannot be used to invoke administrative or model deployment endpoints.
* Intelligence tokens must declare an approved administrative role (`SUPER_ADMIN`, `ML_ENGINEER`, `DATA_STEWARD`, `CLINICAL_REVIEWER`, `SECURITY_ADMIN`, `AUDITOR`).
