# DrishtiAI API Specification

**Version:** 2.4.0 (Production-Hardened Prototype)  
**Safety Policy:** SAFE-1.0  
**Triage Policy:** TRIAGE-1.1  
**Medical Positioning:** Clinical Decision Support & Preventive Screening (Non-Autonomous)

---

## 1. Public Infrastructure & Health Probes

### `GET /api/health`
Lightweight, unauthenticated liveness check for load balancers and orchestrators.

- **Authentication:** None
- **Response `200 OK`:**
  ```json
  {
    "status": "alive",
    "timestamp": 1741362000.123
  }
  ```

---

### `GET /api/health/ready`
Readiness probe verifying that internal subsystems (SQLite database, migration state, PyTorch / TFLite runtime) are responsive.

- **Authentication:** None
- **Response `200 OK` (Healthy):**
  ```json
  {
    "status": "ready",
    "database": "ok",
    "schema_version": 2,
    "model_runtime": "ready",
    "timestamp": 1741362000.123
  }
  ```
- **Response `503 Service Unavailable` (Degraded):**
  ```json
  {
    "status": "degraded",
    "database": "error: database is locked",
    "schema_version": 2,
    "model_runtime": "ready"
  }
  ```

---

### `GET /api/health/detailed`
Deep diagnostic check exposing operational telemetry, memory, and sync backlog.

- **Authentication:** Required (`Role.ADMIN` or `Role.DOCTOR`). Header `X-Role: ADMIN` or `Bearer <token>`.
- **Response `200 OK`:**
  ```json
  {
    "status": "operational",
    "environment": {
      "offline_mode": true,
      "demo_mode": true,
      "safety_policy_version": "SAFE-1.0",
      "triage_policy_version": "TRIAGE-1.1"
    },
    "subsystems": {
      "database": {
        "status": "ok",
        "schema_version": 2,
        "patients_count": 12,
        "scans_count": 48
      },
      "sync_engine": {
        "status": "idle",
        "outbox_pending_count": 0,
        "conflict_count": 0
      }
    }
  }
  ```
- **Response `403 Forbidden`:** If caller lacks administrative/clinical privileges.

---

## 2. Ingest & Session Binding

### `POST /api/sessions/bind`
Binds an operator, clinic station, and designated eye (OD/OS) into an auditable screening session before image capture.

- **Request Body:**
  ```json
  {
    "operator_id": "OP-DELHI-04",
    "patient_id": "PAT-2026-001",
    "intended_eye": "OD",
    "station_id": "CAM-STATION-RURAL-1"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "session_id": "SES-8a9d1234-bcde",
    "status": "SESSION_BOUND",
    "intended_eye": "OD",
    "bound_at": "2026-09-06T16:45:00Z"
  }
  ```

---

### `POST /api/ingest/validate`
Pre-inference safety gate. Validates file header magic bytes, dimension limits (<25 MP), image entropy, and computes SHA-256 fingerprint.

- **Request:** `multipart/form-data` with `image` file field.
- **Response `200 OK` (Valid):**
  ```json
  {
    "is_valid": true,
    "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "format": "JPEG",
    "dimensions": [2048, 1536],
    "megapixels": 3.14,
    "duplicate_detected": false,
    "errors": [],
    "warnings": []
  }
  ```
- **Response `400 Bad Request` (Rejected):**
  ```json
  {
    "is_valid": false,
    "rejection_reason": "DIMENSIONS_EXCEED_LIMIT",
    "errors": ["Image dimensions 6000x5000 (30.0 MP) exceed safety threshold of 25.0 MP"],
    "warnings": []
  }
  ```

---

### `POST /api/sessions/<session_id>/confirm`
Closes a screening session, recording operator confirmation or human override if an anatomical mismatch was detected.

- **Request Body:**
  ```json
  {
    "operator_id": "OP-DELHI-04",
    "confirmed_eye": "OD",
    "override_reason": "Temporal vessel geometry manually confirmed by optometrist"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "session_id": "SES-8a9d1234-bcde",
    "status": "CONFIRMED"
  }
  ```

---

## 3. Retinal AI Inference & Decision Support

### `POST /api/analyze-v3` (Recommended Multi-Gate Endpoint)
Performs end-to-end multi-gate clinical screening with Grad-CAM explainability, anatomical verification, and Gemma-4 clinical report.

- **Request:** `multipart/form-data`
  - `image`: Fundus image binary
  - `patient_id`: String (e.g. `PAT-102`)
  - `eye`: `"OD"` | `"OS"`
  - `session_id`: Optional session binding token
- **Response `200 OK`:**
  ```json
  {
    "success": true,
    "session_id": "SES-8a9d1234-bcde",
    "scan_id": "SCN-2026-9912",
    "eye": "OD",
    "safety_state": "PASS",
    "automation_level": "DECISION_SUPPORT",
    "reason_codes": [
      "IMAGE_QUALITY_ACCEPTABLE",
      "ANATOMY_CONFIRMED",
      "MODEL_CONSENSUS_STABLE"
    ],
    "detection": {
      "stage": 1,
      "stage_name": "Mild NPDR",
      "confidence": 89.2
    },
    "anatomy": {
      "inferred_eye": "OD",
      "confidence": 0.94,
      "mismatch_detected": false
    },
    "ood": {
      "is_ood": false,
      "uncertainty_multiplier": 1.0
    },
    "referral": {
      "urgency": "ROUTINE",
      "window": "6-12 Months",
      "guideline_code": "ICMR-DR-T1"
    },
    "longitudinal": {
      "state": "LIMITED_LONGITUDINAL_HISTORY",
      "disclaimer": "Progression prediction unavailable: insufficient longitudinal data. Single-timepoint scan."
    },
    "report": {
      "clinical_summary": "Empathetic clinical report generated via Gemma-4..."
    }
  }
  ```

---

### `POST /analyze` (Legacy Compatibility Endpoint)
Preserves 100% backward compatibility with legacy frontends and automated evaluation scripts.

- **Request:** `multipart/form-data` with `image` file field.
- **Response `200 OK`:**
  ```json
  {
    "stage": 1,
    "stage_name": "Mild NPDR",
    "confidence": 89.2,
    "processing_time": 0.45,
    "analysis": {
      "microaneurysms": true,
      "hemorrhages": false,
      "hard_exudates": false,
      "cotton_wool_spots": false,
      "neovascularization": false
    }
  }
  ```

---

## 4. Offline Sync & Conflict Resolution

### `GET /api/sync/outbox`
Retrieves locally queued screenings awaiting cloud synchronization.

### `POST /api/sync/push`
Transmits queued local mutations to upstream cloud replica.

- **Conflict Behavior:** If a patient or scan has been updated concurrently on the server, the server rejects silent overwrite and marks the session as `CONFLICT_REQUIRES_REVIEW`.

---

## 5. Demonstration & Red-Teaming Sandbox

### `GET /api/demo/scenarios`
Enumerates all 10 canonical demonstration scenarios.

- **Access:** Available when `DEMO_MODE=True`.
- **Response `200 OK`:** Array of scenario manifests.

### `POST /api/demo/run`
Executes an isolated scenario simulation within the `DEMO-SIM-` namespace. Real patient data is never touched or mutated.

- **Request Body:**
  ```json
  {
    "scenario_id": "LATERALITY_MISMATCH"
  }
  ```
- **Response `200 OK`:** Simulated complete scan analysis payload including safety state, mismatch alerts, and reason codes.
