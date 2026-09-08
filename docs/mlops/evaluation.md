# Model Evaluation & Clinical Safety Gates

## 1. Safety Thresholds
Before any candidate model can be deemed promotion-eligible, it must be evaluated on the locked held-out test split against these non-negotiable safety criteria:

| Safety Gate | Required Threshold | Clinical Rationale |
|---|---|---|
| **Referable DR Sensitivity** | $\ge 85.0\%$ | Prevents missing patients needing urgent specialist care |
| **Referable DR Specificity** | $\ge 80.0\%$ | Prevents overburdening tertiary ophthalmology centers |
| **Overall Accuracy** | $\ge 75.0\%$ | Baseline diagnostic reliability across all 5 stages |
| **Quadratic Weighted Kappa (QWK)** | $\ge 0.70$ | Penalizes severe inter-stage misclassification distance |
| **Expected Calibration Error (ECE)** | $\le 15.0\%$ | Guarantees model confidence reflects true probability |
| **False Negative Rate (FNR)** | $\le 10.0\%$ | Hard ceiling on severe DR misdiagnosed as mild/none |

## 2. Regression Testing Against Production
A candidate cannot be promoted if its metrics degrade beyond acceptable bounds compared to the currently deployed production baseline:
- Sensitivity degradation: $\le -2.0\%$
- Specificity degradation: $\le -3.0\%$
- QWK degradation: $\le -4.0\%$
- Any statistically significant jump in Stage 4 false negatives immediately blocks release.
