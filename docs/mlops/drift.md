# Drift Surveillance & Discordance Monitoring

## 1. Multi-Tiered Drift Architecture
DrishtiAI monitors three distinct planes of distribution shift:

```mermaid
flowchart TD
    subgraph Input Feature Drift
        I1[Image Sharpness]
        I2[Brightness / Contrast]
        I3[Camera Source / Resolution]
    end

    subgraph Prediction Output Drift
        O1[5-Stage DR Class Frequencies]
        O2[Referral Rate Shifts]
        O3[Mean Confidence Degradation]
    end

    subgraph Clinical Discordance Drift
        C1[Doctor Override Frequency]
        C2[Severity Upgrades / Downgrades]
        C3[Second-Opinion Disagreements]
    end

    I1 & I2 & I3 --> PSI[Population Stability Index PSI]
    O1 & O2 & O3 --> Chi2[Categorical Shift Chi-Square / PSI]
    C1 & C2 & C3 --> DisRate[Discordance Rate Calculation]

    PSI --> Alert{Threshold Check}
    Chi2 --> Alert
    DisRate --> Alert

    Alert -->|Warning > 20%| Evt[Log Drift Event]
    Alert -->|Critical > 35%| Fallback[Emergency Alert & Rollback Recommendation]
```

## 2. Quantitative Thresholds
- **PSI < 0.10**: Stable distribution.
- **0.10 <= PSI < 0.25**: Moderate drift; initiates active learning sampling of drifted clusters.
- **PSI >= 0.25**: Critical drift; alerts administrators and triggers emergency review.
- **Clinical Discordance Rate >= 20%**: Emits WARNING event.
- **Clinical Discordance Rate >= 35%**: Emits CRITICAL event and enables emergency rollback trigger.
