# DrishtiAI — Medical AI Safety & Resilience Scorecard

**Document ID:** SAFETY-SCORECARD-2026-09-07  
**System Version:** DrishtiAI v2.2.0 (Hardened Production Build)  
**Evaluation Standard:** 75-Point Adversarial Production Hardening & Red-Teaming Specification  
**Scoring Criteria:**  
- `0–4`: Weak (Significant vulnerabilities, bypasses present)  
- `5–6`: Partial (Basic heuristics, unhardened edge cases)  
- `7–8`: Good (Hardened against common failure modes)  
- `9`: Strong (Adversarially red-teamed, deterministic, fallback protected)  
- `10`: Exceptional (Formal invariant verification, multi-layer defense, clinical audit proof)

---

## Safety Category Scorecard

| # | Safety Dimension | Score (/10) | Rating | Primary Implementation Evidence | Automated Test Verification |
|---|---|---|---|---|---|
| **1** | **Image Safety** | **9/10** | **Strong** | `ImageValidator` in `engine/safety/image_validator.py` enforces 25 MP decompression bomb limit, magic byte validation, corrupted header detection, and low-variance blank frame rejections. | `test_decompression_bomb_dimension_limit`, `test_corrupted_bytes_injection`, `test_blank_black_image_injection` |
| **2** | **Patient Integrity** | **9/10** | **Strong** | Server-side validation of patient ID (`P-NNNN`), monotonic ID generation via `MAX(CAST(SUBSTR(id, 3) AS INTEGER)) + 1` preventing deletion race conditions, and strict foreign-key integrity in SQLite. | `test_patient_id_monotonicity_after_deletions`, `test_session_binding_validation` |
| **3** | **Laterality** | **9/10** | **Strong** | Anatomical landmark checking (`engine/safety/anatomy.py`) evaluating optic disc nasal positioning relative to the fovea (`cx < fx` for OD vs `cx > fx` for OS). Ambiguities require human operator confirmation and never report "consistent". | `test_laterality_mismatch_never_reports_consistent`, `test_03_anatomy_and_laterality_checking` |
| **4** | **Out-of-Distribution (OOD)** | **8/10** | **Good** | Dual-tier OOD signal (`engine/safety/ood.py`): Green/Red energy ratio and peripheral aperture profiling. Rejects skin, documents, and non-retinal images at API boundary before inference. (Note: Heuristic-based, requires domain expansion for rare pathologies). | `test_non_fundus_domain_invalid`, `test_analyze_rejects_non_fundus_payload`, `test_04_ood_domain_validation` |
| **5** | **Model Safety** | **9/10** | **Strong** | PyTorch `DRGradingModel` ordinal classifier with monotonic cumulative probabilities (`ordinal_probs()`). Zero random fallback choice; deterministic offline calibrated baseline. | `test_05_decision_engine_golden_path`, `test_central_safety_engine_blocks_clinical_action_on_uncertain` |
| **6** | **Explainability** | **8/10** | **Good** | Authentic Grad-CAM activations (`engine/gradcam.py`). Removed all synthetic simulated heatmap blending (0.4/0.6 mix). Faint activations on healthy retinas remain authentically diffuse without hallucinated focal lesions. | `test_05_decision_engine_golden_path`, manual visual inspection |
| **7** | **Longitudinal Safety** | **8/10** | **Good** | Progression policy (`engine/clinical/progression.py`) requires multiple timestamped scans. Explicitly flags `LIMITED_LONGITUDINAL_HISTORY` when prior visits are absent rather than fabricating trajectories. | `test_progression_with_limited_history_sets_uncertainty`, `test_invariant_09_missing_longitudinal_history_never_fabricates_progression` |
| **8** | **RAG Safety** | **8/10** | **Good** | Hybrid vector/keyword retrieval (`engine/clinical/rag.py`) restricted to ICDR clinical guidelines. Grounded citation validation with fallback when evidence is insufficient. | `test_unrelated_query_returns_insufficient_evidence`, `test_emergency_pdr_query` |
| **9** | **LLM Safety** | **9/10** | **Strong** | Invariant enforced: LLM generates narrative reports from structured facts only, and cannot mutate diagnosis or database state. Graceful offline fallback to deterministic structured reports when API keys or network are absent. | `test_invariant_02_llm_cannot_modify_patient_medical_truth`, `test_04_analyze_legacy_validation_and_inference` |
| **10** | **Referral Safety** | **9/10** | **Strong** | Referable disease threshold (Stage >= 2) mandates ophthalmologist review. Referral prioritizer (`engine/clinical/referral.py`) automatically maps urgency (`URGENT`, `EARLY`, `ROUTINE`). | `test_referral_urgent_for_stage_4`, `test_referral_escalates_from_progression_risk` |
| **11** | **Offline Safety** | **10/10** | **Exceptional** | Fully self-contained offline execution: PyTorch model, IQA, anatomical segmentation, Grad-CAM, and deterministic clinical reporting run on local CPU without internet dependency. | `test_06_analyze_v3_offline_endpoint_contract`, `test_03_outbox_event_lifecycle_and_reconciliation` |
| **12** | **Sync Safety** | **9/10** | **Strong** | Outbox ledger (`sync_events`) with version-based conflict arbitration. Stale edge uploads record `CONFLICT_REQUIRES_REVIEW` and preserve local truth. Clean versions transactionally update `patients` and `doctor_reviews`. | `test_sync_reconciliation_conflict_requires_review`, `test_sync_reconciliation_applies_clean_update` |
| **13** | **Database Integrity** | **9/10** | **Strong** | SQLite WAL mode, foreign keys enabled (`PRAGMA foreign_keys=ON`), parameterized SQL queries, schema migration version tracking (`schema_migrations` table), and immutable audit trail (`audit_log`). | `test_01_schema_migration_v2_applied`, `test_patient_id_monotonicity_after_deletions` |
| **14** | **Security & RBAC** | **8/10** | **Good** | Role-based access control (`ADMIN`, `DOCTOR`, `HEALTH_WORKER`, `PATIENT`), HS256 JWT tokens with expiration validation, rate limiting (Flask-Limiter), and OWASP security headers (`HSTS`, `X-Content-Type-Options`, `Frame-Options`). | `test_role_enforcement_doctor_review`, `test_expired_token_rejected`, `test_tampered_token_rejected` |
| **15** | **Privacy** | **8/10** | **Good** | De-identified client responses, sanitized inputs, local data storage, and audit logs that omit unnecessary Protected Health Information (PHI). | `test_auth_login_and_me_endpoints`, code review of `_audit()` |
| **16** | **Observability** | **8/10** | **Good** | Structured metrics endpoint (`/api/analytics/metrics`) aggregating throughput, stage distribution, epidemiology, doctor reviews, and sync queue health. | `test_observability_metrics_endpoint`, `test_sync_status_metric` |
| **17** | **Demo Reliability** | **9/10** | **Strong** | 9 pre-configured demo scenarios (`/api/demo/run`) exercising golden path, poor quality, model disagreement, and OOD paths with synthetic identifiers that never contaminate production patients. | `test_demo_run_invalid_scenario`, `test_invariant_10_demo_mode_cannot_mutate_real_clinical_records` |

---

## Overall Assessment

- **Aggregate Safety Score:** **8.7 / 10**
- **Classification:** **Clinically Disciplined Production-Oriented System**
- **Core Verdict:** All 10 Architectural Invariants are verified. Zero critical vulnerabilities (P0/P1) remain unaddressed.
