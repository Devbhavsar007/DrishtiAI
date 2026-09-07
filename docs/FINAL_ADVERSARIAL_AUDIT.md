# DRISHTIAI — FINAL ADVERSARIAL ARCHITECTURE AUDIT

**Date:** March 2026  
**Auditor Mode:** Principal AI Safety Engineer, Principal Software Architect, DevSecOps & Red-Team  
**Scope:** DrishtiAI Full-Stack Architecture, Production Hardening, Zero-Trust Verification  
**Repository State:** Evaluated against complete 104-test regression suite prior to remediation  

---

## 1. Executive Summary & Audit Methodology

DrishtiAI is an edge-cloud hybrid clinical AI decision-support platform for Diabetic Retinopathy (DR) screening. The system incorporates deep learning computer vision (EfficientNet-B3, HiResCAM/Grad-CAM), edge retinal structure segmentation, longitudinal progression modeling, deterministic safety arbitration, and grounded clinical guidelines retrieval (RAG).

The platform has undergone previous hardening passes. However, rigorous adversarial penetration testing and forensic code inspection reveal critical vulnerabilities, privilege escalation paths, identity spoofing vectors, and architectural inconsistencies where security mechanisms rely on client trust rather than server-side enforcement.

This document serves as the authoritative, uncompromised audit baseline.

---

## 2. Complete Route Security Matrix (All 35 Flask Routes)

| # | Route | Method | Purpose | Public? | Auth Mechanism | Allowed Roles | Object Auth (IDOR)? | Input Validation | Rate Limit | Audit Event | Sensitive Data (PHI)? | Demo Only? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `/api/health` | GET | Liveness probe | Yes | None | Any | N/A | None | Exempt | No | No | No |
| 2 | `/api/health/ready` | GET | DB readiness probe | Yes | None | Any | N/A | None | Exempt | No | No | No |
| 3 | `/api/health/detailed` | GET | Internal diagnostics | No | Bearer / Edge Sig | ADMIN, DOCTOR | N/A | None | 30/min | No | Yes (Counts/Env) | No |
| 4 | `/api/sessions/bind` | POST | 4-way session bind | **YES (VULN)** | **NONE (P0)** | **ANY (P0)** | **None (P0)** | Partial | Default (60/m) | CREATE | Yes (Patient ID) | No |
| 5 | `/api/sessions/<id>` | GET | Session state query | **YES (VULN)** | **NONE (P0)** | **ANY (P0)** | **None (P0)** | session_id | Default (60/m) | No | Yes (Session/Eye) | No |
| 6 | `/api/sessions/<id>/confirm` | POST | Operator sign-off | **YES (VULN)** | **NONE (P0)** | **ANY (P0)** | **None (P0)** | session_id, notes | Default (60/m) | STATE_TRANSITION | Yes (Clinical) | No |
| 7 | `/api/ingest/validate` | POST | Image pre-inference sanity | **YES (VULN)** | **NONE (P0)** | **ANY (P0)** | N/A | Magic, bytes | Default (60/m) | No | Image Payload | No |
| 8 | `/api/demo/scenarios` | GET | List 10 demo cases | Yes (if DEMO) | None | Any | N/A | None | Default (60/m) | No | No (Synthetic) | Yes |
| 9 | `/api/demo/run` | POST | Run demo scenario | Yes (if DEMO) | None | Any | Restricted to DEMO-SIM-* | scenario_id | Default (60/m) | No | No (Synthetic) | Yes |
| 10 | `/` | GET | Serve SPA HTML | Yes | None | Any | N/A | None | Default (60/m) | No | No | No |
| 11 | `/results/<path:filename>` | GET | Serve heatmaps/masks | No | Bearer / Edge Sig | HW, DOC, ADMIN, PATIENT | **NONE (P0 IDOR)** | Basename check | Default (60/m) | No | **YES (Fundus/Scans)** | No |
| 12 | `/api/dashboard` | GET | Global aggregate stats | No | Bearer / Edge Sig | HW, DOC, ADMIN | Aggregated | None | Default (60/m) | No | Aggregate PHI | No |
| 13 | `/api/patients` | GET | Patient directory list | No | Bearer / Edge Sig | HW, DOC, ADMIN | Role-wide | Search sanitize | Default (60/m) | No | **YES (All Patients)** | No |
| 14 | `/api/patients` | POST | Create patient | No | Bearer / Edge Sig | HW, DOC, ADMIN | Role-wide | Clinical bounds | Default (60/m) | CREATE | **YES (Patient PHI)** | No |
| 15 | `/api/patients/<id>` | GET | Patient detail + scans | No | Bearer / Edge Sig | HW, DOC, ADMIN | **NO PATIENT CHECK** | Regex ID format | Default (60/m) | No | **YES (Patient PHI)** | No |
| 16 | `/api/patients/<id>` | PUT | Update patient | No | Bearer / Edge Sig | HW, DOC, ADMIN | Role-wide | Allowlist cols | Default (60/m) | UPDATE | **YES (Patient PHI)** | No |
| 17 | `/api/patients/<id>` | DELETE | Delete patient | No | Bearer / Edge Sig | HW, DOC, ADMIN | Role-wide | Regex ID format | Default (60/m) | DELETE | **YES (Patient PHI)** | No |
| 18 | `/api/scans/<id>` | GET | Scan record detail | No | Bearer / Edge Sig | HW, DOC, ADMIN | **NO PATIENT CHECK** | String ID | Default (60/m) | No | **YES (Clinical Scan)** | No |
| 19 | `/api/scans/<id>/progression` | POST | Progression compute | No | Bearer / Edge Sig | HW, DOC, ADMIN | Scan existence | Bounds | Default (60/m) | SAVE | **YES (Progression)** | No |
| 20 | `/api/scans/<id>/triage` | POST | Referral triage compute | No | Bearer / Edge Sig | HW, DOC, ADMIN | Scan existence | DB sign-off | Default (60/m) | SAVE | **YES (Referral)** | No |
| 21 | `/api/patients/<id>/timeline` | GET | Longitudinal history | No | Bearer / Edge Sig | HW, DOC, ADMIN | **NO PATIENT CHECK** | Regex ID format | Default (60/m) | No | **YES (Timeline)** | No |
| 22 | `/api/screenings/safety-check` | POST | Isolated safety check | No | Bearer / Edge Sig | HW, DOC, ADMIN | N/A | Payload bounds | Default (60/m) | No | Screening signals | No |
| 23 | `/api/medical/query` | POST | Grounded RAG search | No | Bearer / Edge Sig | HW, DOC, ADMIN | N/A | Query string | Default (60/m) | No | Clinical query | No |
| 24 | `/api/scans/<id>/doctor-review` | POST | Clinician sign-off | No | Bearer / Edge Sig | DOCTOR | Scan existence | Review fields | Default (60/m) | SAVE | **YES (Doctor Review)**| No |
| 25 | `/api/scans/<id>/doctor-review` | GET | Query doctor sign-off | No | Bearer / Edge Sig | HW, DOC, ADMIN | Scan existence | None | Default (60/m) | No | **YES (Doctor Review)**| No |
| 26 | `/api/auth/login` | POST | Session token minting | **YES** | **NONE (P0)** | **SELF-ASSIGNED** | N/A | Role string | Default (60/m) | No | Auth Token | No |
| 27 | `/api/auth/me` | GET | Introspect active user | No | Bearer / Edge Sig | HW, DOC, ADMIN, PATIENT | Self | None | Default (60/m) | No | User Profile | No |
| 28 | `/api/sync` | POST | Offline batch reconciler | No | Bearer / Edge Sig | ADMIN, HW, DOC | Batch structure | Events list | Default (60/m) | SYNC_RECONCILE | **YES (Batch PHI)** | No |
| 29 | `/api/sync/status` | GET | Queue depth & health | No | Bearer / Edge Sig | ADMIN, DOC, HW | Global | None | Default (60/m) | No | Operational metrics | No |
| 30 | `/api/sync/pending` | GET | Outbox events query | No | Bearer / Edge Sig | ADMIN, DOCTOR | Device scope | Limit integer | Default (60/m) | No | **YES (Outbox PHI)** | No |
| 31 | `/api/analytics/metrics` | GET | Epi & system metrics | No | Bearer / Edge Sig | HW, DOC, ADMIN | Aggregated | None | Default (60/m) | No | Operational metrics | No |
| 32 | `/analyze` | POST | v1 Clinical Pipeline | No | Bearer / Edge Sig | HW, DOC, ADMIN | **NO PATIENT CHECK** | Image, bounds | 10/min | CREATE | **YES (Full Scan)** | No |
| 33 | `/translate` | POST | Report localization | No | Bearer / Edge Sig | HW, DOC, ADMIN, PATIENT | N/A | Report, language | Default (60/m) | No | Report text | No |
| 34 | `/api/analyze-v2` | POST | v2 Full Pipeline | No | Bearer / Edge Sig | HW, DOC, ADMIN | **NO PATIENT CHECK** | Image, bounds | 10/min | CREATE | **YES (Full Scan)** | No |
| 35 | `/api/analyze-v3` | POST | v3 Two-Tier Pipeline | No | Bearer / Edge Sig | HW, DOC, ADMIN | **NO PATIENT CHECK** | Image, bounds | 10/min | CREATE | **YES (Full Scan)** | No |

---

## 3. Top 20 Prioritized Findings

| Rank | Severity | Finding Name | Target Route / Component | Exploitation Vector | Remediation Required |
|---|---|---|---|---|---|
| 1 | **P0** | Self-Assigned Role Privilege Escalation | `/api/auth/login` | Attacker sends `{"role": "ADMIN"}` or `{"role": "DOCTOR"}` and receives signed admin JWT without authentication | Enforce credential verification or disable self-assignment of privileged roles |
| 2 | **P0** | Completely Unauthenticated Session APIs | `/api/sessions/*` (`bind`, `confirm`, `get`) | Anonymous attackers can inspect, bind, or confirm laterality overrides on screening sessions | Protect with `@require_role` and enforce authenticated actor |
| 3 | **P0** | Client-Supplied Actor Identity Spoofing | `/analyze`, `/api/analyze-v2`, `/api/analyze-v3`, `/api/sessions/<id>/confirm` | Callers supply `operator_id` in form/JSON; backend trusts and writes client string to database and audit log | Derive operator identity strictly from `get_current_actor()` / `g.current_user` |
| 4 | **P0** | Lack of Object-Level Authorization (IDOR) on Scans & Results | `/results/<path:filename>`, `/api/scans/<id>`, `/api/patients/<id>` | Any authenticated actor (including `Role.PATIENT`) can access, view, or download other patients' retinal images/scans | Implement resource-ownership check: Patient can only access own records; enforce lookup |
| 5 | **P0** | Unauthenticated Ingestion Validation DoS Vector | `/api/ingest/validate` | Anonymous clients upload large files or probe hashes without session or auth | Require valid session or `@require_role` |
| 6 | **P1** | Duplicate & Incomplete `audit_log` Schema Definition | `database.py:99-106, 153-162` | `CREATE TABLE IF NOT EXISTS audit_log` duplicated; missing `request_id`; relies on fragile `ALTER TABLE` | Unify schema, create explicit migration v3, add `request_id` column |
| 7 | **P1** | Camera / Microphone Policy Conflict in Security Headers | `app.py:109` | `Permissions-Policy: camera=(), microphone=()` blocks browser webcam/fundus cameras and voice navigation | Update policy to allow `camera=(self), microphone=(self)` for app origins |
| 8 | **P1** | State Machine Bypass in Direct Database Updates | `database.py:340-349` (`update_screening_session_state`) | Direct SQL UPDATE mutates session state without validating against `ScreeningStateMachine` transitions | Route all state updates through `ScreeningStateMachine.transition_to()` |
| 9 | **P1** | Missing Mandatory States in `ScreeningState` Enum | `engine/safety/state_machine.py` | Missing `LATERALITY_CONFLICT`, `SCREENING_PENDING`, `MODEL_FAILURE`, `REFERRAL_PENDING` | Add missing states and define explicit transition graph |
| 10 | **P1** | Nginx Proxy Configuration Hole for `/results/` | `nginx.conf:38-41` | Nginx proxies `/uploads/` (unused) but omits `/results/`, breaking all scan/heatmap rendering in production | Proxy `/results/` to `backend:5000/results/` |
| 11 | **P1** | Frontend Silent Authentication Failure & Mock Fallback | `src/context/MedicalDataContext.tsx:259` | Frontend sends unauthenticated `fetch` to `/analyze`, gets 401, and silently switches to fake data | Attach Bearer token from auth session to all API requests |
| 12 | **P1** | Missing Request Correlation (`request_id`) Across Audit Trail | `database.py:274-286`, `app.py` | `_audit()` does not capture or propagate HTTP `request_id`, severing forensic audit trails | Inject `g.request_id` into all audit logs and API responses |
| 13 | **P1** | Insecure Configuration Key Mismatches in Deployments | `docker-compose.yml`, `render.yaml`, `.env.example` | Uses `FLASK_SECRET` instead of `FLASK_SECRET_KEY`; ships `FLASK_DEBUG=true` in example | Normalize environment variable names and enforce secure production defaults |
| 14 | **P2** | Inconsistent Safety Reason Codes Between Contracts | `engine/clinical/safety.py:51-60` vs `engine/safety/decision_engine.py` | Reason codes mutated (`LOW_CONFIDENCE` -> `LOW_MODEL_CONFIDENCE`), creating contract drift | Standardize canonical reason codes across all layers |
| 15 | **P2** | Non-Atomic Patient ID Allocation Under Concurrency | `database.py:351-366` | Separate `SELECT MAX` and `INSERT` creates race conditions under concurrent health worker registrations | Enforce atomic table sequence or transactional row reservation |
| 16 | **P2** | Static Fallback Identities in Production DB Operations | `app.py:738`, `database.py:565` | `operator-1` and `DOC-ONLINE` inserted when actor is unpopulated, corrupting provenance | Reject transactions missing verified actor context |
| 17 | **P2** | Permissive CORS Regex on Vercel Domains | `app.py:81` | `^https:\/\/.*\.vercel\.app$` allows any attacker's Vercel deployment to initiate credentialed requests | Restrict to configured origins or strict project-specific domain |
| 18 | **P2** | In-Memory Rate Limiting Ineffective Across Multi-Worker Deployments | `app.py:96` | Memory limiter resets on worker restart and does not coordinate across Gunicorn workers | Document Redis backing requirement for clustered production deployments |
| 19 | **P3** | Inconsistent Field Naming in Referral Payload (`reasonCodes` vs `reason_codes`) | `engine/clinical/referral.py:61` | CamelCase in referral JSON vs snake_case in database and safety contracts | Provide dual compatibility or canonical snake_case serialization |
| 20 | **P3** | Missing Cache-Control Headers for PHI Protection | `app.py:100-112` | Patient scan data and details can be cached by intermediate client proxies | Add `Cache-Control: no-store, no-cache, must-revalidate` to all patient/scan endpoints |

---

## 4. Architectural Inconsistencies

1. **Dual Safety Decision Callers:**
   - `/analyze`, `/api/analyze-v2`, `/api/analyze-v3` call `SafetyDecisionEngine.evaluate()` directly.
   - `/api/screenings/safety-check` calls `engine/clinical/safety.py:evaluate_safety()`, which wraps `SafetyDecisionEngine` but alters reason code strings (`LOW_CONFIDENCE` -> `LOW_MODEL_CONFIDENCE`).
2. **Actor Provenance Storage vs Request Execution:**
   - `auth.py:require_role` places the verified actor into `g.current_user`.
   - However, endpoint implementations throughout `app.py` routinely ignore `g.current_user` and read `request.form.get("operator_id")` or `request.json.get("doctor_id")`.
3. **State Machine vs Database Decoupling:**
   - `ScreeningStateMachine` class maintains transition graphs and lifecycle events.
   - `database.py` maintains an isolated `update_screening_session_state()` function that issues raw SQL updates without checking the state machine.

---

## 5. Security Bypasses

1. **Privilege Self-Assignment Bypass:**
   - A client calls `POST /api/auth/login {"role": "ADMIN", "user_id": "attacker"}`.
   - The server signs an HMAC-SHA256 token encoding role `ADMIN`.
   - The client presents `Authorization: Bearer dr1...` and accesses `/api/health/detailed`, deletes patients via `DELETE /api/patients/<id>`, and queries `sync/pending`.
2. **Laterality Override Safety Bypass:**
   - When anatomy verification fails or detects a laterality mismatch, an operator confirmation is required.
   - Because `/api/sessions/<id>/confirm` has no authentication check, an unauthorized client can forge confirmation requests with arbitrary notes and override safety blocks.
3. **Direct File Retrieval IDOR Bypass:**
   - When a scan is analyzed, images are saved to `results/<analysis_id>_scan.png`.
   - A `PATIENT` role user can request `/results/<victim_analysis_id>_scan.png` and directly obtain another patient's raw fundus image.

---

## 6. Safety Bypasses

1. **Unverified Fallback Masking:**
   - If model weights fail to load, `predict()` falls back to heuristic grading. While `MODEL_FALLBACK_ACTIVE` is flagged in reason codes, if an endpoint does not gate database storage on `clinical_action_allowed`, synthetic scores can be misinterpreted as clinically validated.
2. **Laterality Conflict Override Integrity:**
   - If disc/fovea geometry indicates `OS` but operator entered `OD`, the conflict must not be resolved without verified operator identity logging. Bypassing identity verification allows unaccountable clinical errors.

---

## 7. Data-Integrity Risks

1. **Schema Duplication in `database.py`:**
   - Two competing `CREATE TABLE IF NOT EXISTS audit_log` statements create ambiguity during fresh deployments.
2. **Lack of Correlation Tracking:**
   - Audit logs lack `request_id`, preventing trace correlation between an incoming HTTP request, the safety decision, database mutation, and subsequent sync event.
3. **Silent Conflict Risk in Cloud Sync:**
   - Edge devices submitting offline records could conflict with cloud doctor reviews. DrishtiAI correctly implements `CONFLICT_REQUIRES_REVIEW`, but the state machine did not include this as a formal transition state in all paths.

---

## 8. AI/ML Risks

1. **OOD Generalization Limit:**
   - Level 2 OOD heuristic monitors color ratios and edge density. While effective for non-fundus and extreme blur, subtle domain shifts (e.g. different camera vendor sensors) must be handled with appropriate humility and not claimed as full OOD proof.
2. **Multi-Model Consensus Boundary Crossings:**
   - In border cases between Stage 1 (Mild NPDR, non-referable) and Stage 2 (Moderate NPDR, referable), a 1-stage difference crosses the clinical action boundary. The safety engine correctly catches `REFERABLE_BOUNDARY_DISAGREEMENT`, which must always enforce `HUMAN_REVIEW_REQUIRED`.

---

## 9. Clinical Claim Risks

1. **Diagnostic Claims vs Decision Support:**
   - DrishtiAI must NEVER describe its outputs as "autonomous diagnosis" or "standalone medical diagnosis".
   - The system must consistently use the three-tier taxonomy:
     - `SCREENING_ELIGIBLE`
     - `AI_RESULT_AVAILABLE`
     - `CLINICAL_ACTION_ALLOWED`
   - Clinical action is strictly forbidden when `safety_state != 'VERIFIED'` or `human_review_required == True`.

---

## 10. Demo Risks

1. **Production Contamination:**
   - Demo endpoints (`/api/demo/run`) must NEVER accept or operate on real patient IDs.
   - Isolation to `DEMO-SIM-*` must be enforced at both the API layer and the `demo_engine` layer.
   - `DEMO_MODE` flag must default to `False` in production environments.

---

## 11. Prioritized Remediation Action Plan

We proceed strictly by addressing **P0 and P1 findings first**, followed by running the full adversarial regression test suite before addressing P2/P3:

- **P0.1:** Fix `/api/auth/login` to prohibit self-assigned privileged roles (`ADMIN`, `DOCTOR`) without master credentials/secrets.
- **P0.2:** Protect `/api/sessions/*` (`bind`, `confirm`, `get`) with `@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)`.
- **P0.3:** Bind operator and doctor identities in `/analyze`, `/api/analyze-v2`, `/api/analyze-v3`, and `/api/sessions/<id>/confirm` strictly to the verified server-side session actor (`g.current_user`).
- **P0.4:** Implement Object-Level Authorization: verify patient ownership before serving `/results/<filename>`, `/api/patients/<id>`, `/api/scans/<id>`, and `/api/patients/<id>/timeline`.
- **P0.5:** Protect `/api/ingest/validate` with role authentication.
- **P1.1:** Resolve duplicate `audit_log` schema in `database.py`, add `request_id` column, and increment schema version to 3 with explicit migration.
- **P1.2:** Update `Permissions-Policy` in `app.py` to allow `camera=(self), microphone=(self)`.
- **P1.3:** Enforce `ScreeningStateMachine` transitions in `update_screening_session_state()`.
- **P1.4:** Add missing states (`LATERALITY_CONFLICT`, `SCREENING_PENDING`, `MODEL_FAILURE`, `REFERRAL_PENDING`) to `ScreeningState` and transition graph.
- **P1.5:** Fix `nginx.conf` `/results/` proxy and deployment config keys (`FLASK_SECRET_KEY`).
- **P1.6:** Inject request correlation IDs (`request_id`) in middleware and audit logs.
- **P1.7:** Add Authorization headers to frontend API requests in `MedicalDataContext.tsx`.
