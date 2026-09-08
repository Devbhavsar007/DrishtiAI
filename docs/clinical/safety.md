# Clinical Safety Framework

## Core Safety Invariants
1. **Conservative Bias**: In uncertain cases (borderline confidence, severe image artifacts, or conflicting lesion distributions), the system errs on the side of referral rather than false-negative clearance.
2. **Deterministic Triage Policy**: Progression risk and referral urgency are governed by deterministic rule sets (`engine/clinical/referral.py` and `engine/clinical/progression.py`), not ungrounded neural net text generation.
3. **Out-of-Distribution (OOD) Protection**: Images exhibiting anomalous embedding distance from normative fundus distributions automatically enter the `UNCERTAIN` safety state.
4. **Safety State Machine Transitions**:
   - `INITIAL` → `IQA_CHECK` → `FEATURE_EXTRACTION` → `INFERENCE` → `EXPLAINABILITY` → `VERIFIED` | `UNCERTAIN` | `REJECTED`.
   - Any failure in pipeline stages transitions the screening state to `ERROR` or `REJECTED`, requiring technician review.
