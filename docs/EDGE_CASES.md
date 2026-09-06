# DrishtiAI Edge-Case & Failure Mode Engineering Matrix
## Rigorous Failure Analysis, Triage Severity, and Mitigation Controls

---

## 1. Severity Classification & Engineering Controls

Every failure mode in DrishtiAI is classified according to strict healthcare-engineering severity criteria:

| Severity | Definition | Engineering Enforcement Rule |
| :--- | :--- | :--- |
| **P0 (Critical)** | Patient safety hazard, misdiagnosis risk, silent data corruption, unauthenticated state change. | **Zero unresolved items permitted.** System cannot be designated "Production-Hardened" if any P0 exists. |
| **P1 (High)** | Severe workflow disruption, uncalibrated uncertainty, failure to escalate borderline case, data sync conflict. | **Zero unresolved items permitted.** Requires deterministic fallback and explicit audit log. |
| **P2 (Medium)** | Suboptimal user experience, degraded explanation fidelity, unsupported camera sensor. | May ship with documented limitations and operational mitigations. |
| **P3 (Low)** | Minor cosmetic issue, formatting inconsistency, non-critical telemetry delay. | Documented in product backlog for post-hackathon sprint. |

---

## 2. Comprehensive Edge-Case Matrix

### P0: Patient Safety & Data Integrity

| ID | Edge Case | Trigger Condition | System Behavior & Mitigation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **P0-1** | **Wrong Patient / Wrong Eye Ingestion** | Operator uploads OS image into OD session or assigns image to wrong patient ID. | 1. Strict four-way session binding: `(patient_id, operator_id, eye, session_id)`.<br>2. AI landmark laterality consistency check (disc vs. fovea spatial orientation).<br>3. Discrepancy flags `LATERALITY_MISMATCH_SUSPECTED` and halts automated commit until operator explicitly confirms. | **VERIFIED** |
| **P0-2** | **Non-Fundus Image Upload** | Operator uploads an arbitrary image (e.g. skin lesion, document, blank, or animal eye). | 1. Magic-byte verification rejects non-image binaries.<br>2. Image quality gate checks circular retinal mask, vascular contrast, and brightness distribution.<br>3. Input domain validator detects non-fundus features, rejects analysis with status `INELIGIBLE`, and emits `NON_FUNDUS_REJECTED`. | **VERIFIED** |
| **P0-3** | **Referable Model Disagreement** | Primary model grades Stage 1 (Non-Referable), Secondary model grades Stage 3 (Referable). | 1. Consensus policy checks grade disparity $\Delta \ge 2$ or categorical referable split.<br>2. Safety Decision Engine sets `safety_state = UNCERTAIN`, locks `automation_level = HUMAN_REVIEW_REQUIRED`, and emits `MODEL_DISAGREEMENT`.<br>3. Triage policy automatically escalates case to specialist review queue. | **VERIFIED** |
| **P0-4** | **Decompression Bomb / Malicious Payload** | Attacker uploads crafted 1GB uncompressed TIFF/PNG or malformed EXIF metadata. | 1. Maximum file size capped at 16 MB.<br>2. Pillow pixel decompression limit enforced (`MAX_IMAGE_PIXELS = 25,000,000`).<br>3. Filename sanitization via `werkzeug.secure_filename` prevents path traversal. | **VERIFIED** |
| **P0-5** | **Power Interruption / Abrupt Shutdown** | Power fails mid-inference or during local SQLite transaction. | 1. SQLite configured in WAL mode (`PRAGMA journal_mode=WAL;`).<br>2. Atomic transactions ensure partially written scans rollback cleanly.<br>3. On restart, state machine checks for unfinalized sessions and marks them `RECOVERY_REQUIRED`. | **VERIFIED** |

---

### P1: Clinical Robustness & Operational Safety

| ID | Edge Case | Trigger Condition | System Behavior & Mitigation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **P1-1** | **Borderline / Low Confidence Inference** | AI confidence score $\le 70\%$ or high prediction entropy across adjacent stages. | 1. Safety Decision Engine emits `LOW_CONFIDENCE` reason code.<br>2. `automation_level` set to `HUMAN_REVIEW_REQUIRED`.<br>3. Report highlights confidence bounds and requires clinician sign-off before patient discharge. | **VERIFIED** |
| **P1-2** | **Screen / Monitor Photograph Artifacts** | Operator takes photograph of a monitor displaying fundus scan (inducing moiré lines). | 1. Frequency-domain periodic line filter flags `POSSIBLE_SCREEN_CAPTURE`.<br>2. **Soft warning rule:** Does *not* hard-reject image (preventing false rejections of valid low-res scans).<br>3. Increments OOD risk score and notifies clinician of possible capture artifact. | **VERIFIED** |
| **P1-3** | **Suboptimal Illumination / Cataract Haze** | Patient has dense cataract or undilated pupil causing severe glare or low contrast. | 1. IQA gate evaluates Laplacian variance (sharpness), histogram entropy, and illumination uniformity.<br>2. If unrecoverable, transitions to `QUALITY_FAILED` with specific actionable feedback: *"Image underexposed and out of focus — increase camera flash and re-center fovea."* | **VERIFIED** |
| **P1-4** | **Network Drop During Doctor Sign-Off** | Internet connection drops while doctor signs off on referral recommendation. | 1. Review decision is saved immediately to local SQLite ledger.<br>2. Event queued into `sync_outbox` with status `PENDING`.<br>3. UI shows *"Saved locally — will synchronize when online"*. | **VERIFIED** |
| **P1-5** | **Duplicate Image Re-submission** | Operator accidentally re-submits the exact same fundus image under different patient IDs. | 1. System computes SHA-256 hash of normalized image bytes.<br>2. If hash matches existing scan within 30 days, warns operator of duplicate submission with `DUPLICATE_IMAGE_SUBMISSION`. | **VERIFIED** |

---

### P2: Clinical Boundaries & Domain Adaptability

| ID | Edge Case | Trigger Condition | System Behavior & Mitigation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **P2-1** | **Sparse Longitudinal Data** | Patient has only one scan or scans separated by irregular $> 18$-month intervals. | 1. System refuses to fabricate numerical 6-month progression curves.<br>2. Emits state `LIMITED_LONGITUDINAL_HISTORY`.<br>3. UI displays: *"Progression prediction unavailable: insufficient longitudinal data."* | **VERIFIED** |
| **P2-2** | **Unseen Camera Sensor / OOD Domain Shift** | Scan captured with a smartphone handheld fundus adapter not present in training data. | 1. Statistical distance in deep feature space computed against reference training distribution.<br>2. Flagged as experimental distribution-shift signal (`OOD_SUSPECTED`).<br>3. Increases triage review priority without blocking workflow. | **VERIFIED** |
| **P2-3** | **Multilingual Medical Translation Distortion** | Report translated into Hindi or Gujarati loses clinical nuance or translates critical terms. | 1. Translation prompt locks standard medical terminology (e.g. *NPDR*, *PDR*, *HbA1c*, *mg/dL*, *Macular Edema*) in English.<br>2. Only patient instructions, lifestyle recommendations, and summaries are localized.<br>3. English original is always appended to report. | **VERIFIED** |

---

### P3: Platform Maintenance & Operational Latency

| ID | Edge Case | Trigger Condition | System Behavior & Mitigation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **P3-1** | **Legacy Endpoint API Incompatibility** | External client or older mobile app calls legacy `/analyze` instead of v2/v3. | 1. Legacy routes preserved with 100% backward-compatible schemas.<br>2. Monitored via dedicated regression test suite `tests/test_legacy_regression.py`. | **VERIFIED** |
| **P3-2** | **Edge Hardware Compute Throttling** | High ambient temperature causes CPU throttling during ONNX/PyTorch forward pass. | 1. Processing pipeline reports execution timing in milliseconds (`processing_time`).<br>2. If latency exceeds 45 seconds, system gracefully emits edge results and defers heavy background tasks. | **VERIFIED** |

---

## 3. Engineering Enforcement Checklist

Before any release or hackathon presentation:
- [x] All **P0** items verified via automated unit and integration tests.
- [x] All **P1** items covered with deterministic fallback policies.
- [x] All failure states observable in telemetry and audit trail.
- [x] Zero silent failures: every error returns structured JSON with an actionable error code.
