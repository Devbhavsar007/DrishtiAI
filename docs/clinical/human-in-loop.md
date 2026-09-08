# Human-in-the-Loop Clinical Integration

## Principles
1. **Clinician Primacy**: AI output is an assistive preliminary triage recommendation. Final medical responsibility remains with the attending physician or reading center ophthalmologist.
2. **Doctor Review Workflow**:
   - The ophthalmologist evaluates original fundus image alongside lesion segmentation overlays, HiResCAM heatmaps, and AI stage predictions.
   - The clinician explicitly registers an agreement (`AGREE`, `ADJUST`, or `OVERRULE`) and confirms or modifies the DR grade.
   - Clinician adjustments are recorded in the `doctor_reviews` ledger.
3. **Data Flywheel Feedback**:
   - Only clinician-reviewed and validated records enter the training candidate pool.
   - Cases of model-clinician disagreement are assigned elevated priority in the active learning queue (`ml_platform/active_learning/prioritization.py`).
