# DrishtiAI Clinical Limitations & Scientific Disclaimers
## Operational Boundaries of the Production-Hardened Prototype

---

## 1. Regulatory Status & Non-Autonomous Disclaimer

> [!IMPORTANT]
> **DRISHTIAI IS A PRODUCTION-HARDENED RESEARCH & SCREENING PROTOTYPE.**
> It is designed to assist healthcare providers in rural clinics with preliminary risk stratification, quality verification, and triage decision-support.
> It is **NOT** an autonomous medical diagnostic device and has **NOT** received formal regulatory clearance (such as CDSCO SaMD, US FDA 510(k), or EU CE-MDR Class IIa) for independent diagnostic operation.

* **No Automated Medical Prescription:** All clinical conclusions, referral dispatches, and interventions must be reviewed and signed off by a licensed ophthalmologist or medical officer.
* **Intended Use Environment:** DrishtiAI is intended for primary screening and triage triage in community health centers and diabetic retinopathy prevention camps. It is not designed to replace comprehensive dilated ophthalmic examinations or optical coherence tomography (OCT).

---

## 2. Capability Status: Implemented vs. Validated

In accordance with scientific and engineering integrity, system capabilities are explicitly designated across three levels:

| System Capability | Implementation Status | Scientific & Clinical Validation Level | Defensible Positioning for Hackathon / Reviewers |
| :--- | :--- | :--- | :--- |
| **Image Quality Gate (IQA)** | Fully Implemented | Evaluated on synthetic and public fundus sets (focus, illumination, FOV). | Production-ready heuristic gate. Rejects ungradable images to prevent AI hallucination. |
| **DR Stage Classification** | Fully Implemented | High benchmark accuracy on EyePACS / Messidor / Aptos datasets. | Calibrated screening classifier. Highly effective for referable vs. non-referable triage. |
| **Multi-Model Consensus** | Fully Implemented | Validated on dual-model test harness. | Independent safety signal. Flags discrepancies $\ge 2$ stages as `MODEL_DISAGREEMENT`. |
| **Laterality Checking** | Fully Implemented | Anatomical landmark heuristic (optic disc vs. fovea coordinates). | **Experimental verification signal.** Flags mismatch for human confirmation; does *not* blindly override operator selection. |
| **Out-of-Distribution (OOD) Signal** | Fully Implemented | Input-domain check (valid) + feature-space distance heuristic (experimental). | **Advisory shift indicator.** Detects non-fundus images safely; feature distance raises uncertainty without claiming clinical OOD proof. |
| **Longitudinal Progression** | Fully Implemented | Architecture-ready with strict data gating. | **Honest data policy:** If $\le 1$ scan exists, system emits `LIMITED_LONGITUDINAL_HISTORY`. Numerical 6-month prediction is explicitly withheld. |
| **Medical RAG Retrieval** | Fully Implemented | Curated evidence vectors (ICMR, AAO, WHO guidelines). | **Grounded decision-support.** Emits source version and authority. Deterministic template fallback active when offline. |
| **Offline Synchronization** | Fully Implemented | Transactional SQLite outbox with idempotency and conflict logging. | Production-grade edge architecture. Clinical conflicts flagged as `CONFLICT_REQUIRES_REVIEW`. |

---

## 3. Specific Clinical & Algorithmic Limitations

### A. Longitudinal Progression Forecasting
* **The Reality:** Predicting whether a diabetic retinopathy patient will progress from Mild to Moderate NPDR over 6 or 12 months requires serial, time-calibrated fundus imaging alongside longitudinal systemic parameters (glycemic variability, blood pressure trajectory, renal function, lipid profile).
* **System Boundary:** DrishtiAI refuses to synthesize arbitrary 6-month progression curves from a single cross-sectional scan. If longitudinal history is missing or irregular ($> 18$ months between scans), the system returns:
  ```
  Progression prediction unavailable: insufficient longitudinal data.
  ```
  This protects patients and builds clinical defensibility.

### B. Out-of-Distribution (OOD) Detection
* **The Reality:** A simple statistical distance metric (e.g. Mahalanobis distance or cosine embedding distance) in a deep feature space is an experimental proxy for distribution shift, not a mathematically infallible proof of clinical OOD.
* **System Boundary:** DrishtiAI splits OOD into three distinct levels:
  1. *Level 1 (Domain Validation):* Hard rejection of non-retinal photographs, extreme corruptions, and invalid aspect ratios.
  2. *Level 2 (Distribution Shift Signal):* Computes embedding distance against training centroids to generate an uncertainty multiplier.
  3. *Level 3 (Decision Policy):* High shift scores do *not* output *"This image is definitively OOD"*; instead, they set `safety_state = UNCERTAIN`, increment reason code `OOD_SUSPECTED`, and escalate the case for human clinician review.

### C. Retinal Laterality (OD vs. OS)
* **The Reality:** Retinal orientation in clinical practice is subject to camera field-of-view rotations, operator mirroring, optical inversion, and pathological occlusion of the macula or optic disc.
* **System Boundary:** DrishtiAI never uses a naive geometric disc-fovea rule to unilaterally alter the recorded eye. The operator selection remains primary. An anatomical conflict triggers a `LATERALITY_MISMATCH_SUSPECTED` alert requiring human confirmation before session finalization.

### D. Screen and Monitor Photography
* **The Reality:** Moiré patterns and high-frequency scan lines can appear when fundus images are displayed on computer monitors and re-photographed, but similar high-frequency artifacts can also arise from fundus camera sensor noise, JPEG compression blocks, or laser scars.
* **System Boundary:** Detection of high-frequency periodic patterns emits a `POSSIBLE_SCREEN_CAPTURE` advisory warning and increases the inspection priority, but is **never** used as a hard rejection criterion.

---

## 4. Prospective Path to Clinical Production

For deployment beyond research prototypes into accredited clinical healthcare environments, the following steps are required:
1. **Prospective Clinical Cohort Validation:** Multi-center clinical study across diverse demographic cohorts, skin pigmentations, and cataract severity levels in India.
2. **Camera Hardware Calibration:** Multi-device benchmarking covering desktop fundus cameras (Zeiss, Topcon, Canon) and portable handheld devices (Remidio, Volk, Forus Health).
3. **Institutional Ethics & Compliance Approval:** Formal Institutional Review Board (IRB) approval, HIPAA/ABDM data privacy compliance certification, and ISO 13485 quality management systems.
4. **Regulatory SaMD Clearance:** Central Drugs Standard Control Organisation (CDSCO) approval for AI-assisted diagnostic software.
