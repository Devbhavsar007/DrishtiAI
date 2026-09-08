# DrishtiAI Security: Threat Model

## 1. Assets & Critical Data
* **Protected Health Information (PHI)**: Patient names, ages, diabetes histories, fundus photographs, diagnoses.
* **Clinical Safety State**: Stage predictions, referral priorities, doctor reviews, audit trails.
* **Model Artifacts & Checkpoints**: PyTorch model weights, ONNX exports, calibration mappings.
* **Training Datasets & Ground Truth**: Versioned datasets, manifests, checksums.

## 2. Threat Scenarios & Mitigations

### Threat A: Data Poisoning & Unvalidated Clinical Feedback
* **Vector**: Adversarial or erroneous AI predictions ingested into subsequent training datasets.
* **Mitigation**: AI predictions are strictly tagged `AI_ONLY` or `PSEUDO_LABEL`. Only `DOCTOR_CONFIRMED` or `SECOND_REVIEW_CONFIRMED` labels can satisfy training candidate eligibility.

### Threat B: Silent Model Regression or Tampering
* **Vector**: Unauthorized or malicious replacement of production model weights.
* **Mitigation**: Immutable model registry (`model_versions`), SHA-256 weights checksum verification, non-negotiable safety gates, regression testing delta ≤ 0.03, and mandatory two-person separation of duties.

### Threat C: Patient Cross-Split Leakage
* **Vector**: The same patient appears in both training and test sets, artificially inflating validation metrics.
* **Mitigation**: Patient-stratified splitting (`patient_level_split`) with automated isolation verification (`verify_patient_isolation`).

### Threat D: Offline Ledger Replay / Tampering
* **Vector**: Replaying outbox events or injecting manipulated screening records during synchronization.
* **Mitigation**: Idempotent UUID event tracking, SHA-256 image hashing, and device authentication credentials.
