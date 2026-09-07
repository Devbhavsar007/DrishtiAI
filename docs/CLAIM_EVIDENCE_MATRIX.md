# DrishtiAI — Claim Evidence & Clinical Verification Matrix

This matrix independently audits and substantiates every claim presented in `README.md`, technical specifications, UI components, and API documentation for **DrishtiAI** (OptiGemma).

Allowed statuses:
- `IMPLEMENTED_AND_TESTED`: Fully implemented, covered by automated negative/positive tests in the active regression suite.
- `IMPLEMENTED_NOT_CLINICALLY_VALIDATED`: Algorithmic implementation complete and functionally tested, but lacking prospective multi-center clinical trials.
- `EXPERIMENTAL`: Research prototype or experimental pipeline; not intended for unmonitored production usage.
- `ARCHITECTURE_READY`: Architectural scaffolding, interfaces, and safety gates established; waiting on external certified model weights or hardware integration.
- `UNSUPPORTED_CLAIM`: Deprecated or unsubstantiated claim; explicitly downgraded.

---

| # | System Claim | Implementation | Runtime Evidence | Automated Test | Limitations | Verified Status |
|---|---|---|---|---|---|---|
| **1** | **SaMD Class II Clinical Decision Support (Non-Autonomous)** | `app.py`, `engine/clinical/safety.py`, `engine/safety/decision_engine.py` | Safety state machine returns `automation_level="DECISION_SUPPORT"` / `"HUMAN_REVIEW_REQUIRED"`. Clinical action blocked without clinician sign-off. | `tests/test_safety_engine.py`, `tests/test_failure_injection.py` | Software architecture conforms to IEC 62304 / FDA SaMD principles, but has not received formal 510(k) or CE regulatory clearance. | `IMPLEMENTED_NOT_CLINICALLY_VALIDATED` |
| **2** | **5-Gate Safety Decision Core** | `engine/safety/image_validator.py`, `engine/safety/anatomy.py`, `engine/safety/ood.py`, `engine/detector.py`, `engine/safety/decision_engine.py` | 1. Ingest hygiene (magic bytes, 25 MP limit, blank rejection); 2. Anatomy/Laterality check; 3. OOD domain filter; 4. Multi-model consensus; 5. Finite state machine. | `tests/test_safety_core.py`, `tests/test_failure_injection.py`, `tests/test_state_machine.py` | Anatomy and laterality use heuristic bounding and thresholding; not a substitute for stereo funduscopy. | `IMPLEMENTED_AND_TESTED` |
| **3** | **Zero-Trust Role-Based Access Control (RBAC)** | `engine/security/auth.py`, `app.py` | HMAC-SHA256 signed JWTs (`dr1.<payload>.<sig>`) and signed edge device headers. Privileged roles (`ADMIN`, `DOCTOR`) require cryptographic credentials. | `tests/test_rbac_security.py`, `tests/test_adversarial_p0_p1.py` | Process-local secret key rotation in development; production requires distributed KMS. | `IMPLEMENTED_AND_TESTED` |
| **4** | **BOLA / IDOR Cross-Tenant Isolation** | `app.py` (`/results/<filename>`, `/api/patients/<id>`, `/api/scans/<id>`, timelines) | Patient callers cannot access foreign scans or artifacts. Unauthorized access returns `403 Forbidden` fail-closed. | `tests/test_adversarial_p0_p1.py` (Tests 06, 07) | Applies to patient tenant isolation; clinicians retain clinic roster visibility. | `IMPLEMENTED_AND_TESTED` |
| **5** | **Safety Before Commit (No Raw AI Commits)** | `app.py` (`/analyze`, `/api/analyze-v2`, `/api/analyze-v3`) | `safety_engine.evaluate` executes before database insertion. `REJECTED` scans are never saved as valid clinical records. | `tests/test_preproduction_hardening.py` | Edge network drops before audit commit trigger local SQLite rollback. | `IMPLEMENTED_AND_TESTED` |
| **6** | **Offline Camp Resilience & Outbox Ledger** | `database.py`, `engine/sync/sync_ledger.py`, `app.py` (`/api/sync`) | Outbox table logs offline mutations; `/api/sync` reconciles batches with monotonic version tracking and `CONFLICT_REQUIRES_REVIEW` protection. | `tests/test_offline_sync.py`, `tests/test_sync_engine.py` | SQLite local database concurrency is single-process per outreach terminal. | `IMPLEMENTED_AND_TESTED` |
| **7** | **Deterministic Scientific Progression Protocol** | `engine/clinical/progression.py` | Rejects synthesizing continuous progression curves from a single baseline photograph. Flags single-point visits as `LIMITED_LONGITUDINAL_HISTORY`. | `tests/test_persistence_timeline.py`, `tests/test_failure_injection.py` | Long-term risk predictions are deterministic clinical heuristics, not personalized longitudinal deep models. | `IMPLEMENTED_AND_TESTED` |
| **8** | **Multimodal Explainability Triptych (Grad-CAM & Frangi)** | `engine/gradcam.py`, `engine/segmentor.py`, `engine/pipeline/hirescam.py` | Computes Grad-CAM heatmaps and multi-scale Frangi vessel masks. If explanation computation fails, flags `UNAVAILABLE`. | `tests/test_legacy_regression.py`, `tools/gradcam_validation_sheet.py` | Saliency maps provide visual correlation, not causative pathological proof. | `IMPLEMENTED_AND_TESTED` |
| **9** | **Gemma-4 Multilingual Report Generation** | `engine/gemma_report.py`, `engine/pipeline/medgemma_report.py` | Generates clinical summaries; falls back to structured offline deterministic templates when cloud API keys are absent. | `tests/test_medical_rag.py`, `tests/test_legacy_regression.py` | Live generative outputs depend on Google Gemini/Gemma API availability; offline mode uses deterministic templates. | `IMPLEMENTED_NOT_CLINICALLY_VALIDATED` |
| **10** | **WCAG 2.1 AAA Accessibility** | `src/components/AccessibilityToolbar.tsx`, `src/index.css` | High-contrast modes, scalable typography, screen-reader dual-coded status badges, keyboard navigation hooks. | `npm run lint` (frontend type-check clean) | Color contrast satisfies 7:1 ratio on primary components; full automated axe-core audit needed for AAA formal certificate. | `IMPLEMENTED_NOT_CLINICALLY_VALIDATED` |
| **11** | **Out-of-Distribution (OOD) Rejection** | `engine/safety/ood.py` | Evaluates Fourier spectrum, color channel variance, and circular mask entropy. Rejects non-fundus images (pets, documents, natural scenes). | `tests/test_safety_core.py`, `tests/test_failure_injection.py` | Heuristic spectrum and texture filters catch non-fundus domains; subtle retinal domain shifts require deep latent OOD models. | `IMPLEMENTED_AND_TESTED` |
| **12** | **Thread-Safe Monotonic Patient ID Generation** | `database.py` (`_patient_id_lock`) | Global mutex locks database sequence allocation during concurrent patient registration, preventing race conditions or duplicated IDs. | `tests/test_adversarial_p0_p1.py` (Test 11) | Scoped to the local SQLite database file instance. | `IMPLEMENTED_AND_TESTED` |
| **13** | **1-Click Hackathon Red-Team Simulator** | `engine/demo/demo_engine.py`, `app.py` (`/api/demo/run`) | 10 canonical edge cases executed in an isolated `DEMO-SIM-*` patient namespace. Cannot corrupt production records. | `tests/test_failure_injection.py` | Active only when `DEMO_MODE=True`. Fails closed in strict production mode. | `IMPLEMENTED_AND_TESTED` |
| **14** | **Two-Tiered Edge/Cloud Architecture (HiResCAM + MedGemma 27B)** | `engine/pipeline/two_tier_runner.py`, `app.py` (`/api/analyze-v3`) | Tier 1 runs local edge inference; Tier 2 delegates complex cases to cloud MedGemma 27B with graceful timeout fallback. | `tests/test_legacy_regression.py`, `tools/test_two_tier_verification.py` | MedGemma 27B remote VLM requires active cloud connection and credentials; offline fallback operates on local weights. | `ARCHITECTURE_READY` |
| **15** | **Automated Diagnostic Autonomy** | N/A (Explicitly Disclaimed) | Software explicitly blocks autonomous medical actions (`clinical_action_allowed: False` on uncertain/unreviewed predictions). | `tests/test_safety_engine.py`, `tests/test_safety_core.py` | System is strictly non-autonomous decision support; claims of automated diagnosis are unsupported. | `UNSUPPORTED_CLAIM` |

---

## Audit Conclusions

- **Total Claims Audited**: 15
- **Implemented & Tested**: 10
- **Implemented (Awaiting Clinical Validation)**: 3
- **Architecture Ready**: 1
- **Explicitly Unsupported / Disclaimed**: 1 (Autonomous Diagnosis)
- **Zero Ambiguity**: No unsupported claims are marketed as validated clinical capabilities.
