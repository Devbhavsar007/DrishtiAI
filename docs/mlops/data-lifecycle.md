# MLOps Data Lifecycle

## 1. Candidate Ingestion
Every fundus scan captured in the field undergoes automated IQA and anatomical validity checks. Scans reviewed and confirmed by licensed doctors receive high label provenance (`DOCTOR_CONFIRMED`).

## 2. Eligibility Criteria
A screening image is only eligible for training dataset compilation if:
1. It is marked `gradable = True` with high structural confidence.
2. It passes resolution minimums (>= 300x300) and brightness bounds.
3. It has no duplicate image hash in the existing training registry.
4. The patient is not in a quarantined or opted-out cohort.
5. The scan possesses ground-truth label provenance.

## 3. Provenance Hierarchy
- `SECOND_REVIEW_CONFIRMED`: Two independent ophthalmologists agreed (highest weight).
- `DOCTOR_CONFIRMED`: Single ophthalmologist reviewed and signed off.
- `REFERENCE_DATASET`: External gold-standard benchmark (e.g., APTOS 2019, EyePACS).
- `AI_ONLY`: Automatically classified without doctor override (excluded from supervised ground truth unless pseudo-labeled under active learning).
