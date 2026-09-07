# DrishtiAI — Route Authorization Matrix

This document provides a comprehensive, verified security catalog for all HTTP routes registered in the **DrishtiAI** (OptiGemma) clinical screening API.

---

## Authorization & Governance Standard

| Symbol / Tag | Definition |
| :--- | :--- |
| **`AUTH`** | Zero-trust cryptographic Bearer token (`dr1.<payload>.<sig>`) or HMAC-SHA256 signed edge device header required. |
| **`PUBLIC`** | Publicly accessible health check probe; strictly no PHI or mutating capabilities. |
| **`IDOR-GUARD`** | Tenant / object-level authorization enforced (`Role.PATIENT` callers can only view/mutate their own records; clinicians have practice-level access). |
| **`AUDITED`** | Mutation or sensitive read generates an immutable, request-correlated entry in `audit_log`. |
| **`LIMITED`** | Rate-limited via Flask-Limiter (in-memory or Redis-backed). |
| **`PHI`** | Returns Protected Health Information; carries `Cache-Control: no-store, no-cache, must-revalidate, private` headers. |

---

## Route Inventory

| # | HTTP Method | Path | Purpose | Authentication | Allowed Roles | Object Authorization | Rate Limit | Audit Event | Sensitive Data (PHI) | State Mutation | Mode / Lifecycle |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `GET` | `/` | Serves SPA static shell | None (Public) | All | N/A | None | No | No | No | Production |
| 2 | `GET` | `/static/<path:filename>` | Static assets (JS/CSS/Fonts) | None (Public) | All | Static path safe | None | No | No | No | Production |
| 3 | `GET` | `/api/health` | Liveness probe | Public | All | None | Exempt | No | No | No | Production |
| 4 | `GET` | `/api/health/ready` | Readiness probe (DB ping) | Public | All | None | Exempt | No | No | No | Production |
| 5 | `GET` | `/api/health/detailed` | Internal diagnostics & metrics | Protected | `ADMIN`, `DOCTOR` | Practice scope | 30/min | No | No | No | Production |
| 6 | `POST` | `/api/auth/login` | Issues tamper-proof JWT | Public with Secret Gate | All (Secret required for `ADMIN`, `DOCTOR`, `HEALTH_WORKER` in prod) | User/Role check | 20/min | No | No | No | Production |
| 7 | `GET` | `/api/auth/me` | Current actor identity | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN`, `PATIENT` | Self | None | No | No | No | Production |
| 8 | `GET` | `/results/<path:filename>` | Serves fundus scans & XAI maps | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN`, `PATIENT` | `IDOR-GUARD` (patient matches filename scan_id) | 60/min | No | Yes (PHI) | No | Production |
| 9 | `GET` | `/api/dashboard` | Clinical statistics & KPIs | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Clinic scope | None | No | Aggregated | No | Production |
| 10 | `GET` | `/api/patients` | Patient directory & search | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Clinic scope | None | No | Yes (PHI) | No | Production |
| 11 | `POST` | `/api/patients` | Registers new patient | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Clinic scope | None | `CREATE:patient` | Yes (PHI) | Yes (DB) | Production |
| 12 | `GET` | `/api/patients/<patient_id>` | Detailed patient profile & scans | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN`, `PATIENT` | `IDOR-GUARD` (`caller_id == patient_id`) | None | No | Yes (PHI) | No | Production |
| 13 | `PUT` | `/api/patients/<patient_id>` | Update patient biomarkers | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Clinic scope | None | `UPDATE:patient` | Yes (PHI) | Yes (DB) | Production |
| 14 | `DELETE` | `/api/patients/<patient_id>` | Delete patient & cascade scans | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Clinic scope | None | `DELETE:patient` | Yes (PHI) | Yes (DB) | Production |
| 15 | `GET` | `/api/scans/<scan_id>` | Detailed scan report & findings | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN`, `PATIENT` | `IDOR-GUARD` (`scan.patient_id == caller_id`) | None | No | Yes (PHI) | No | Production |
| 16 | `POST` | `/api/scans/<scan_id>/progression` | Longitudinal progression risk | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Clinic scope | None | `CREATE:progression` | Yes (PHI) | Yes (DB) | Production |
| 17 | `POST` | `/api/scans/<scan_id>/triage` | Referral recommendation policy | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Clinic scope | None | `CREATE:referral` | Yes (PHI) | Yes (DB) | Production |
| 18 | `GET` | `/api/patients/<patient_id>/timeline` | Longitudinal patient timeline | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN`, `PATIENT` | `IDOR-GUARD` (`caller_id == patient_id`) | None | No | Yes (PHI) | No | Production |
| 19 | `POST` | `/api/screenings/safety-check` | Standalone multi-model check | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Input validation | 30/min | No | Ephemeral | No | Production |
| 20 | `POST` | `/api/medical/query` | RAG evidence query | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Read-only | 20/min | No | No | No | Production |
| 21 | `POST` | `/api/scans/<scan_id>/doctor-review` | Clinician sign-off & override | `AUTH` | `DOCTOR`, `ADMIN` | Authenticated `doctor_id` bound to JWT | None | `CREATE:doctor_review` | Yes (PHI) | Yes (DB) | Production |
| 22 | `GET` | `/api/scans/<scan_id>/doctor-review` | Clinician sign-off details | `AUTH` | `DOCTOR`, `HEALTH_WORKER`, `ADMIN` | Clinic scope | None | No | Yes (PHI) | No | Production |
| 23 | `POST` | `/api/sessions/bind` | Bind screening session to patient | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Sourced from `g.current_user["actor_id"]` | 60/min | `BIND:session` | Yes (PHI) | Yes (DB) | Production |
| 24 | `GET` | `/api/sessions/<session_id>` | Session state & verification | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Clinic scope | None | No | Yes (PHI) | No | Production |
| 25 | `POST` | `/api/sessions/<session_id>/confirm` | Operator confirmation gate | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Sourced from `g.current_user["actor_id"]` | 60/min | `CONFIRM:session` | Yes (PHI) | Yes (DB) | Production |
| 26 | `POST` | `/api/ingest/validate` | Pre-ingest quality & binary gate | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Ephemeral bytes | 60/min | No | Ephemeral | No | Production |
| 27 | `POST` | `/analyze` | Legacy v1 full screening pipeline | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | `operator_id` bound to JWT | 10/min | `CREATE:scan` | Yes (PHI) | Yes (DB) | Legacy (Hardened) |
| 28 | `POST` | `/translate` | Gemma report translation | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN`, `PATIENT` | Ephemeral text | None | No | Ephemeral | No | Production |
| 29 | `POST` | `/api/analyze-v2` | v2 Calibrated ordinal pipeline | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | `operator_id` bound to JWT | 10/min | `CREATE:scan` | Yes (PHI) | Yes (DB) | Production |
| 30 | `POST` | `/api/analyze-v3` | v3 Edge/Cloud two-tiered pipeline | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | `operator_id` bound to JWT | 10/min | `CREATE:scan` | Yes (PHI) | Yes (DB) | Production |
| 31 | `POST` | `/api/sync` | Reconciles offline event batch | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Verified device / session | 30/min | `SYNC:batch` | Yes (PHI) | Yes (DB) | Production |
| 32 | `GET` | `/api/sync/status` | Outbox sync health & metrics | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Device scope | None | No | Aggregated | No | Production |
| 33 | `GET` | `/api/sync/pending` | Retrieves unsynced outbox queue | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Device scope | None | No | Yes (PHI) | No | Production |
| 34 | `GET` | `/api/analytics/metrics` | Clinical observability & metrics | `AUTH` | `HEALTH_WORKER`, `DOCTOR`, `ADMIN` | Clinic scope | 30/min | No | Aggregated | No | Production |
| 35 | `GET` | `/api/demo/scenarios` | Lists 10 sandbox test scenarios | Public | All | Sandboxed | None | No | No | No | Demo Only |
| 36 | `POST` | `/api/demo/run` | Executes synthetic simulation | Public (Sandboxed) | All | Isolated namespace (`DEMO-SIM-*`) | 30/min | `DEMO:scenario` | Synthetic | Yes (Isolated) | Demo Only |

---

## Cross-Cutting Invariants

1. **Identity Provenance**: All clinical actions (`operator_id`, `doctor_id`, `actor_id`) derive strictly from the verified cryptographic claims of `g.current_user["actor_id"]`. Client payloads cannot overwrite or spoof identity.
2. **Safety Before Commit**: Scans evaluated as `safety_state == "REJECTED"` are never persisted as finalized clinical records.
3. **Fail-Closed Artifact Access**: `/results/<path:filename>` strictly blocks path traversal (`..`, `%2f`, `\`) and ensures patient callers can only retrieve artifacts associated with their authenticated patient ID.
4. **PHI Protection**: All `/api/` and `/results/` responses return `Cache-Control: no-store, no-cache, must-revalidate, private` and `Pragma: no-cache`.
