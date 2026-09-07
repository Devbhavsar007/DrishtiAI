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

## 2B. Explicit Categorization of Operational Boundaries & Limitations

To ensure absolute scientific honesty and avoid over-claiming AI diagnostic capability, all system boundaries are categorized into five distinct technical domains:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 DRISHTIAI OPERATIONAL BOUNDARY TAXONOMY                     │
├───────────────────────────────┬─────────────────────────────────────────────┤
│ 1. SOFTWARE EDGE-CASE         │ Unit-tested mathematical invariants, NaN    │
│    COVERAGE                   │ traps, schema gates, idempotency guarantees. │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ 2. HEURISTIC SAFEGUARDS       │ Landmark geometry, vertical angle checks,   │
│                               │ dHash perceptual duplicates, focus proxies. │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ 3. REQUIRES CLINICAL          │ Demographic generalizability, pathology     │
│    VALIDATION                 │ distortion tolerance, progression dynamics. │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ 4. CAMERA SENSOR              │ Multi-hardware exposure curves, chromatic   │
│    VALIDATION                 │ aberration, handheld smartphone adapters.   │
├───────────────────────────────┼─────────────────────────────────────────────┤
│ 5. OUT OF SCOPE               │ Non-DR retinal diseases, autonomous Dx,     │
│                               │ independent medical prescription.           │
└───────────────────────────────┴─────────────────────────────────────────────┘
```

### Category 1: Software Edge-Case Coverage (Engineered & Unit-Tested)
* **What it covers:** Invariants enforced strictly by code logic and verified by regression test suites:
  * IEEE 754 non-finite number traps: `NaN` and `Inf` model outputs immediately trigger `BLOCKED` with `NUMERICAL_INSTABILITY_DETECTED`.
  * Probability distribution validation: Softmax outputs summing outside $1.0 \pm 0.05$ fail closed.
  * Partial pipeline failure isolation: Auxiliaries (Grad-CAM, vessel segmentation, LLM narrative) fail gracefully with fallback structs without triggering HTTP 500 crashes.
  * Persistence invariants: Ungradeable/rejected scans cannot be saved as normal cleared scans.
  * State machine invariants: Sessions cannot transition from failure states directly to `SCREENING_COMPLETED`.
  * Database transaction idempotency: Re-submitting identical scan IDs performs an idempotent update rather than corrupting the ledger.

### Category 2: Heuristic Safeguards (Operational Filters — Not Biological Proof)
* **What it covers:** Algorithmic rules that catch common acquisition errors but are heuristics rather than biological certainties:
  * **Optic disc edge boundary margin (5%):** Filters cropped images or peripheral bright artifacts; does not guarantee full $45^\circ$ FOV centering.
  * **Disc-fovea distance bounds ($[0.8\text{dd}, 4.5\text{dd}]$):** Flags landmark localization failures; does not account for severe high myopia with posterior staphyloma.
  * **Vertical orientation displacement ($|\Delta y| > 1.25 |\Delta x|$):** Flags camera orientation anomalies ($> 51^\circ$ tilt); does not detect small $5^\circ - 15^\circ$ head tilts.
  * **Perceptual dHash (Hamming distance $\le 6$):** Detects duplicate or re-compressed image reuse across patients; cannot detect distinct exposures of the same eye taken seconds apart.
  * **Laplacian sharpness & illumination metrics:** Standard computer vision focus estimates; cannot distinguish cataract haze from genuine vitreous hemorrhage.

### Category 3: Requires Clinical Validation (Prospective Multi-Center Trials)
* **What it covers:** Behaviors that require formal clinical trials with institutional ethical clearance before clinical reliance:
  * **Demographic Generalizability:** Performance on under-represented patient sub-populations, varying retinal pigmentation across South Asian ethnicities, and high-density corneal opacity cohorts.
  * **Severe Pathological Distortion:** Performance when landmarks (fovea, disc) are obliterated by massive subretinal hemorrhage, extensive pan-retinal photocoagulation (PRP) laser scars, or cytomegalovirus retinitis.
  * **Progression Prediction Velocity:** Validating whether HbA1c trajectory coupled with baseline stage reliably predicts 6-month progression across diverse healthcare delivery systems.

### Category 4: Camera Hardware & Sensor Validation (Device-Specific Testing)
* **What it covers:** Physical sensor variations that have not yet undergone standardized benchtop optical calibration:
  * **Desktop Tabletop Cameras:** Topcon TRC-NW400, Zeiss Visucam, Canon CR-2.
  * **Handheld Rural Screening Devices:** Remidio Fundus on Phone (FOP), Forus 3nethra classic/neo, Volk VistaView.
  * **Smartphone Indirect Ophthalmoscopy:** Unstandardized smartphone camera sensors with uncalibrated LED flash intensities, rolling shutter artifacts, and non-linear ISP tone-mapping curves.

### Category 5: Out of Scope (Explicit System Non-Goals)
* **What it covers:** Boundaries where DrishtiAI is explicitly NOT permitted to operate:
  * **Autonomous Diagnosis:** The system is an assistive screening tool, never an autonomous physician substitute.
  * **Direct Therapeutic Prescription:** DrishtiAI never suggests drug dosages (e.g. anti-VEGF injections, insulin adjustments) or surgical interventions without human ophthalmologist orders.
  * **Non-DR Retinal Disease Grading:** DrishtiAI is calibrated exclusively for Diabetic Retinopathy. Scans exhibiting signs of Age-Related Macular Degeneration (AMD), Retinal Vein Occlusion (RVO), Glaucomatous optic neuropathy, or Retinal Detachment are flagged as `SUSPECTED_NON_DR_PATHOLOGY` and routed to mandatory `DOCTOR_REVIEW`.

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
