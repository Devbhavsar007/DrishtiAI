# DrishtiAI System Architecture Specification
## Production-Hardened Retinal Screening & Decision-Support Platform

---

## 1. Architectural Philosophy & Clinical Positioning

**DrishtiAI** is architected as an **AI-powered retinal screening and clinical decision-support platform** designed for deployment in resource-constrained environments (such as primary health centers, rural vision centers, and diabetic clinics).

### Core Principles
1. **Screening and Triage, Not Autonomous Diagnosis:** DrishtiAI does not render definitive medical diagnoses autonomously. The platform evaluates fundus photographs, assesses image quality and anatomical validity, computes risk profiles, and provides structured clinical triage to support human healthcare providers and ophthalmologists.
2. **Deterministic Governance Over Probabilistic Inference:** Probabilistic AI models (convolutional networks, vision-language models) serve solely as evidence generators (emitting probabilities, attention heatmaps, and lesion segmentations). All state transitions, referral decisions, clinical escalations, and persistence operations are governed by deterministic, versioned policy engines.
3. **Failure as a First-Class State:** The system explicitly models failure, ambiguity, interruption, and conflict states across the end-to-end lifecycle.
4. **Offline-First Resilience:** The system runs completely autonomously on local hardware with zero active internet connection, maintaining an append-only local ledger that idempotently synchronizes with the central cloud upon reconnection without silently overwriting local records.

---

## 2. System Topology

```
                         ┌─────────────────────────────────────────┐
                         │               DRISHTIAI                 │
                         └────────────────────┬────────────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
       ┌─────────────────────────┐                         ┌─────────────────────────┐
       │   LOCAL EDGE RUNTIME    │                         │      CLOUD BACKBONE     │
       │   (Clinic Workstation)  │                         │       (Centralized)     │
       │                         │                         │                         │
       │ • Local AI Inference    │                         │ • Medical RAG Engine    │
       │ • Safety Decision Engine│                         │ • Central Patient EMR   │
       │ • Local SQLite Outbox   │                         │ • Aggregated Analytics  │
       │ • Camera Ingestion      │                         │ • Cohort MLOps & Drift  │
       │ • Deterministic Triage  │                         │ • Tele-Ophthalmology    │
       └────────────┬────────────┘                         └────────────┬────────────┘
                    │                                                   │
                    └─────────────────────────┬─────────────────────────┘
                                              │
                                              ▼
                                 [Idempotent Sync Ledger]
                            (Offline Outbox + Conflict Review)
```

---

## 3. Three-Tier Architectural Scope

To prevent over-engineering and guarantee production reliability, system capabilities are partitioned into three distinct tiers:

### Tier 1: Live Golden Path (Must Work End-to-End)
* **Patient Context:** Demographic intake, HbA1c, fasting glucose, diabetes duration.
* **Capture/Upload:** Direct camera ingestion or high-resolution file upload.
* **Image Validation:** Magic-byte validation, corrupt image rejection, blank image guard, decompression bomb protection (`MAX_IMAGE_PIXELS = 25,000,000`).
* **Quality Gate:** Focus, brightness, contrast, and field-of-view (FOV) assessment.
* **Primary AI Screening:** EfficientNet-B3 DR grading with calibrated probabilities.
* **Explainability:** Grad-CAM saliency heatmaps, anatomical quadrant density, vessel tortuosity.
* **Clinical Triage:** ICMR/AAO-aligned referral urgency and recommended follow-up window.
* **Clinician Review:** Doctor review sign-off, clinical notes, and prescription/referral lock.
* **Report Generation:** Patient-facing and clinician-facing structured report with multi-lingual support.

### Tier 2: Safety Infrastructure & Resilience
* **Centralized Safety Decision Engine:** Multi-signal evaluation combining image quality, anatomical laterality, distribution shift, and model uncertainty.
* **Operator Session Binding:** Enforces `(patient_id, operator_id, eye, screening_id)` integrity.
* **Duplicate Prevention:** SHA-256 hash tracking prevents re-analysis of identical images.
* **Multi-Model Consensus:** Disagreement evaluation between primary and secondary lightweight models.
* **Resilient State Machine:** First-class modeling of failures, retakes, and operator overrides.
* **Offline Ledger & Sync:** SQLite write-ahead logging (WAL), local outbox queue, and conflict resolution routing.

### Tier 3: Architecture-Ready / Experimental (Honest Clinical Boundaries)
* **Longitudinal Progression:** Architecture in place for multi-visit comparison. System explicitly yields `LIMITED_LONGITUDINAL_HISTORY` unless validated longitudinal scans ($\ge 2$ scans with regular time intervals) exist. Fabricated 6-month curves are strictly forbidden.
* **OOD Distribution Shift Signal:** Feature-space statistical distance monitoring flagged as an experimental advisory signal.
* **RAG Guideline Contextualization:** Structured citation retrieval (`source_version`, `publication_date`, `authority`) with deterministic template fallbacks.
* **Prospective Validation Protocols:** Formal telemetry for hospital-based clinical trials.

---

## 4. Centralized Safety Decision Engine

Safety arbitration is decoupled from individual inference models and consolidated into `engine/safety/decision_engine.py`:

```
                 SAFETY DECISION ENGINE
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   Image Quality    OOD Signal      Model Entropy
   (Focus/FOV)    (Shift Score)     (Uncertainty)
        │                │                │
        └────────────────┼────────────────┘
                         │
              Laterality Consistency
              (Operator vs Landmarks)
                         │
              Multi-Model Agreement
             (Primary vs Secondary)
                         │
             Operator & Identity Binding
                         │
                         ▼
        SAFETY STATE & AUTOMATION LEVEL OUTPUT
```

### Deterministic Output Contract
```json
{
  "screening_eligibility": "ELIGIBLE",
  "safety_state": "VERIFIED",
  "automation_level": "AUTOMATED_ASSISTANCE",
  "human_review_required": false,
  "confidence_score": 0.884,
  "safety_policy_version": "SAFE-1.0",
  "triage_policy_version": "TRIAGE-1.1",
  "reason_codes": [],
  "mitigation_instructions": null
}
```

### Supported Reason Codes
* `LOW_CONFIDENCE`: Model classification confidence below configured threshold.
* `MODEL_DISAGREEMENT`: Primary and secondary models disagree by $\ge 2$ stages or high entropy.
* `OOD_SUSPECTED`: Image characteristics deviate from training fundus distribution.
* `LIMITED_IMAGE_QUALITY`: Focus, lighting, or FOV suboptimal.
* `LATERALITY_MISMATCH_SUSPECTED`: Anatomical landmarks (disc/fovea) contradict operator eye selection.
* `DUPLICATE_IMAGE_SUBMISSION`: Image SHA-256 matches a prior scan.
* `OPERATOR_CONFIRMATION_REQUIRED`: Critical clinical discrepancy requiring human sign-off.

---

## 5. Screening Lifecycle State Machine

The screening lifecycle is managed as a formal finite state machine with explicit failure, recovery, and cancellation states:

```
[CREATED] ──► [CAPTURED] ──► [VALIDATING_IMAGE]
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
          [ANATOMY_VALIDATED]                 [QUALITY_FAILED] ──► [RECAPTURE_REQUESTED]
                  │                           [ANATOMY_FAILED] ──► [OPERATOR_OVERRIDE_PENDING]
                  ▼
          [SCREENING_RUNNING]
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
[SCREENING_COMPLETED] [SCREENING_UNCERTAIN] ──► [OOD_REVIEW]
        │                   │
        ▼                   ▼
 [RISK_ASSESSED] ──► [DOCTOR_REVIEW] ──► [FINALIZED]
                            │                    │
                            ▼                    ▼
                   [RECOVERY_REQUIRED]   [SYNC_PENDING] ──► [SYNCED]
                            │                    │
                            ▼                    ▼
                       [CANCELLED]          [SYNC_FAILED] ──► [CONFLICT_REQUIRES_REVIEW]
```

### State Definitions
* `CREATED`: Session initiated with operator and patient binding.
* `CAPTURED`: Raw image uploaded and verified against magic bytes and size limits.
* `QUALITY_FAILED`: Image rejected due to poor focus, underexposure, or occlusion. Prompts recapture.
* `ANATOMY_FAILED`: Landmarks indicate invalid anatomy or laterality conflict.
* `SCREENING_COMPLETED`: Inference executed and verified by Safety Decision Engine.
* `SCREENING_UNCERTAIN`: Inference produced borderline entropy or model disagreement; routed for review.
* `OOD_REVIEW`: Image flagged as possible non-fundus or anomalous domain.
* `DOCTOR_REVIEW`: Clinician sign-off pending.
* `FINALIZED`: Clinician has signed off or automated screening completed within allowed policy.
* `SYNC_FAILED`: Network interruption during sync; event persisted in outbox for retry.
* `CONFLICT_REQUIRES_REVIEW`: Cloud version differs from local edit; requires manual reconciliation.

---

## 6. Offline Data Architecture & Sync Ledger

### Database Structure
* Local SQLite database with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`).
* Schema version tracking table: `schema_migrations`.
* Outbox queue table: `sync_outbox`.

### Conflict Handling Policy
1. Clinical records edited locally during offline operation are **never** silently overwritten by incoming cloud responses.
2. In the event of a conflicting update, the event is marked `CONFLICT_REQUIRES_REVIEW` and surfaced on the clinic dashboard.
3. Every sync event includes `device_id`, `sync_attempt`, `last_sync_at`, and `client_timestamp`.

---

## 7. Versioning & Governance

Every analysis and report records:
* `model_version`: e.g. `DR-EFFICIENTNET-B3-V1.2`
* `secondary_model_version`: e.g. `TANWAR12-ONNX-V1.0`
* `safety_policy_version`: `SAFE-1.0`
* `triage_policy_version`: `TRIAGE-1.1`
* `report_template_version`: `REPORT-2.0`
