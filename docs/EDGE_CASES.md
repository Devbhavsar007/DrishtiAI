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

---

## 4. Remaining Edge-Case Closure Audit Table (Phases 1–18)

The following matrix documents the baseline behavior vs. the hardened safety architecture implemented during the Remaining Edge-Cases Closure pass:

| Phase / Edge Case | Baseline Behavior (Before) | Hardened Behavior (After) | Enforcement Test | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1: Anatomy Failure Propagation** | Missing optic disc or fovea localization was logged as warning; `decision_engine` lacked `valid_anatomy` gate, permitting normal `VERIFIED` report. | Missing landmarks or geometry failure forces `valid_anatomy=False`, `inferred_laterality="UNKNOWN"`. Gate 2b halts pipeline: `safety_state="ANATOMY_FAILED"`, `screening_eligibility="INELIGIBLE"`, `clinical_action_allowed=False`. Referral triage suppresses `STAGE_LOW` and routes to `RETAKE_OR_SPECIALIST_EVALUATION`. | `test_anatomy_failure_blocks_verification` | **HARDENED** |
| **Phase 2: Landmark Boundary / Extrusion** | Optic disc located on image border ($x \le 0$ or $x \ge W-1$) passed through unflagged. | Optic disc centroid within 5% edge boundary margin ($cx < 0.05W$ or $cx > 0.95W$) triggers `DISC_ON_IMAGE_BOUNDARY` and invalidates anatomy. | `test_boundary_disc_invalidates_anatomy` | **HARDENED** |
| **Phase 3: Implausible Disc-Fovea Distance** | Disc and fovea could be located at 0 px or opposite corners without geometric sanity check. | Euclidean distance enforced between $[0.8 \times \text{expected\_dd}, 4.5 \times \text{expected\_dd}]$. Violations trigger `IMPLAUSIBLE_DISC_FOVEA_GEOMETRY` and invalidate anatomy. | `test_implausible_geometry_invalidates_anatomy` | **HARDENED** |
| **Phase 4: Orientation & Vertical Inversion** | $90^\circ, 180^\circ, 270^\circ$ rotated or vertically inverted fundus images passed to classifier as standard horizontal view. | Vertical landmark displacement $|\Delta y| > 1.25 \times |\Delta x|$ triggers `ORIENTATION_ANOMALY_SUSPECTED`, forces `valid_anatomy=False`, and prevents silent laterality inference. EXIF orientation tag 274 inspected. | `test_vertical_orientation_anomaly` | **HARDENED** |
| **Phase 5: Workflow Cross-Patient Duplicates** | Exact same image uploaded under a different `patient_id` was processed as a new independent diagnosis. | SHA-256 and 64-bit dHash perceptual hash checked against patient scan registry. Matching image on different patient raises `CROSS_PATIENT_DUPLICATE_IMAGE_DETECTED` warning and escalates for doctor review. | `test_cross_patient_duplicate_detected` | **HARDENED** |
| **Phase 6: Cross-Eye Image Reuse** | Operator could submit OD image into an OS session without automated duplicate detection. | Image hash matching identical image under opposite eye (`OD` vs `OS`) raises `CROSS_EYE_IMAGE_REUSE_DETECTED`. | `test_cross_eye_duplicate_detected` | **HARDENED** |
| **Phase 7: Camera & Lighting Extremes** | High gain / extreme saturation could cause boundary edge effects or clip confidence. | Threshold boundary tests evaluate $T - \epsilon, T, T + \epsilon$ behavior. Zero-division and NaN protection in all color / sharpness metrics. | `test_threshold_boundary_continuity` | **HARDENED** |
| **Phase 8: Partial Pipeline Isolation (Auxiliary Failures)** | Grad-CAM, vessel segmentation, or Gemma narrative failure threw uncaught 500 error or crashed the analysis endpoint. | Auxiliary modules wrapped in isolated try-except blocks. Failure sets `status="EXPLANATION_UNAVAILABLE"`, `report["status"]="REPORT_UNAVAILABLE"`, while primary classification remains deterministic. | `test_auxiliary_failure_isolation` | **HARDENED** |
| **Phase 9: Model Output Numerical Invariants (NaN/Inf)** | In Python, `float('nan') < 70.0` is `False`. NaN model confidence bypassed low-confidence check and could produce silent passes. | Explicit `math.isnan(conf)` and `math.isinf(conf)` validation. Any non-finite float triggers `BLOCKED` with `NUMERICAL_INSTABILITY_DETECTED`. Stage bounds $0..4$ and probability sum $1.0 \pm 0.05$ strictly validated. | `test_nan_model_confidence_blocked` | **HARDENED** |
| **Phase 10: Disease Scope & Non-DR Pathology** | Non-DR ocular disease (macular degeneration, retinal detachment, RVO) with low DR grade could be discharged as "healthy normal". | Suspected non-DR pathology reason code triggers `DOCTOR_REVIEW`, prevents automated normal discharge, and explicitly notes that DrishtiAI is validated solely for diabetic retinopathy screening. | `test_disease_scope_non_dr_pathology` | **HARDENED** |
| **Phase 11: Longitudinal Sanity & Cross-Eye Filtering** | `_latest_previous_scan` compared OD against OS, producing invalid cross-eye progression metrics; consumed rejected/invalid scans. | Previous scan filtering strictly enforces matching laterality (`OD` == `OD`, `OS` == `OS`), passing safety state, and valid anatomy. Scan interval $< 7$ days suppresses acute duplicate noise; $> 36$ months flags reduced fidelity; $4 \to 0$ flags rapid regression anomaly. | `test_longitudinal_cross_eye_filtering` | **HARDENED** |
| **Phase 12: Deterministic Report Consistency** | LLM narrative could declare "Normal retina" even when safety gate was `UNCERTAIN` or `BLOCKED`. | Authoritative override in `gemma_report.py` and `offline_report.py`: if `safety_state != 'VERIFIED'`, diagnosis is replaced with unverified disclaimer and action plan directs to clinical re-examination. | `test_report_safety_consistency` | **HARDENED** |
| **Phase 13: Persistence Invariants** | Ungradeable / rejected scans could be saved as normal cleared records if patient ID was supplied. | Persistence gate checks `safety_state not in ("REJECTED", "ANATOMY_FAILED")`. Database layer enforces idempotent upsert on `scan_id` and rejects conflicting overwrites. | `test_persistence_invariants` | **HARDENED** |
| **Phase 14: State Machine Invariants** | Unverified screening could transition directly to `SCREENING_COMPLETED`. | State transitions mapped explicitly to `ANATOMY_FAILED`, `QUALITY_FAILED`, `MODEL_FAILURE`, or `SCREENING_UNCERTAIN`. Direct transition to `SCREENING_COMPLETED` forbidden when safety gate fails. | `test_state_machine_safety_invariants` | **HARDENED** |
| **Phase 15: Offline Sync Idempotency** | Retrying failed network sync could insert duplicate scan records or cause ledger corruption. | Sync ledger uses deterministic scan ID primary key with upsert semantics; duplicate uploads return existing scan without duplicate row creation. | `test_offline_sync_idempotency` | **HARDENED** |
| **Phase 16: Frontend State Machine Alignment** | Frontend checked `=== 'PASS'`, rendering amber warning icon for `VERIFIED` scans; failure states lacked distinct visual badges. | Full enum alignment in `src/types.ts` (`ANATOMY_FAILED`, `QUALITY_FAILED`, `MODEL_FAILURE`, `LATERALITY_CONFLICT`, `OOD_REVIEW`). `NewScanView.tsx` updated with distinct colors (emerald, amber, rose) and icons. | `src/types.ts`, `NewScanView.tsx` | **HARDENED** |
| **Phase 17: Red-Team Failure Injection** | Corrupted images, synthetic all-zero arrays, and NaN outputs could cause unhandled exceptions. | Validated under synthetic adversarial injection test suite covering boundary cases and corrupted payloads. | `test_failure_injection_resilience` | **HARDENED** |
| **Phase 18: Clinical Truth & Limitations Documentation** | Documentation did not clearly distinguish software unit-test coverage from prospective clinical validation. | Comprehensive categorization across Software Edge Cases, Heuristics, Required Clinical Validation, Camera Validation, and Out-of-Scope boundaries. | `docs/LIMITATIONS.md` | **HARDENED** |

---

## 5. Algorithmic Parameters, Boundary Thresholds, & Rationales

The following table details every critical numerical threshold introduced or hardened in the safety architecture:

| Parameter | Value / Range | Engineering Rationale | Boundary Behavior ($T \pm \epsilon$) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Optic Disc Margin** | $0.05 \times W, 0.05 \times H$ | Centroid located closer than 5% to image edge indicates partial field-of-view, truncation, or false-positive edge artifact. | If $cx = 0.049W \to$ `DISC_ON_IMAGE_BOUNDARY` (rejected). If $cx = 0.051W \to$ accepted. | **HEURISTIC** |
| **Disc-Fovea Min Distance** | $0.8 \times \text{expected\_dd}$ | Disc and fovea cannot anatomically overlap; minimum distance corresponds to $\sim 1.6$ mm on the retina. | Distance $< 0.8 \times \text{expected\_dd} \to$ `IMPLAUSIBLE_DISC_FOVEA_GEOMETRY`. | **HEURISTIC** |
| **Disc-Fovea Max Distance** | $4.5 \times \text{expected\_dd}$ | For a standard $45^\circ$ fundus photograph, the distance from disc center to fovea center is $2.0 - 3.0 \times \text{disc diameter}$. Anything exceeding $4.5\times$ indicates landmark mislocalization. | Distance $> 4.5 \times \text{expected\_dd} \to$ `IMPLAUSIBLE_DISC_FOVEA_GEOMETRY`. | **HEURISTIC** |
| **Vertical Displacement Ratio** | $|\Delta y| > 1.25 \times |\Delta x|$ | In standard fundus imaging, the optic disc and fovea lie nearly horizontal ($|\theta| \le 15^\circ$). A vertical displacement ratio $> 1.25$ corresponds to $|\theta| > 51.3^\circ$, indicating substantial camera rotation ($90^\circ / 270^\circ$) or inversion. | Ratio $1.24 \to$ accepted with warning. Ratio $1.26 \to$ `ORIENTATION_ANOMALY_SUSPECTED`. | **HEURISTIC** |
| **Perceptual dHash Threshold** | Hamming distance $\le 6$ (of 64 bits) | Normalized $8\times 8$ difference hash detects visually identical or re-compressed fundus images despite lossy compression artifacts or slight brightness shifts. | Hamming distance $\le 6 \to$ matched duplicate. $> 6 \to$ distinct image. | **HEURISTIC** |
| **Model Confidence Threshold** | $70.0\%$ | Calibrated threshold below which predictions exhibit elevated entropy and require physician review. Non-finite values (NaN/Inf) fail closed. | Confidence $69.9\% \to$ `LOW_CONFIDENCE` (uncertain). $70.0\% \to$ eligible for verified. | **VALIDATED** |
| **Probability Sum Tolerance** | $1.0 \pm 0.05$ ($95.0\% - 105.0\%$) | Softmax probability distributions must sum to 1. Deviations $> 5\%$ indicate corrupted logits or model execution failure. | Sum $< 95.0\%$ or $> 105.0\% \to$ `NUMERICAL_INSTABILITY_DETECTED`. | **SOFTWARE GUARD** |
| **Acute Repeat Interval** | $< 7$ days | Diabetic retinopathy does not progress clinically within 7 days. Repeated scans within 7 days represent duplicate screening attempts or acute retakes; progression delta is suppressed to prevent noise amplification. | Interval 6 days $\to$ `ACUTE_REPEAT_SCAN_SUPPRESSED`. Interval 8 days $\to$ evaluated. | **CLINICAL HEURISTIC** |
| **Max Longitudinal Interval** | $> 36$ months | Scans separated by $> 3$ years without intervening records exhibit significantly degraded predictive fidelity due to unobserved glycemic events. | Interval $> 36$ months $\to$ `EXTENDED_GAP_REDUCED_FIDELITY`. | **CLINICAL HEURISTIC** |
| **Max Stage Regression** | Stage $4 \to 0$ | Proliferative diabetic retinopathy cannot spontaneously regress to completely normal fundus without intensive intervention (pan-retinal photocoagulation or vitrectomy). Spontaneous $4 \to 0$ indicates potential patient identity confusion. | Stage $4 \to 0$ jump $\to$ `ANOMALOUS_RAPID_REGRESSION_DETECTED`. | **SAFETY FLAG** |

