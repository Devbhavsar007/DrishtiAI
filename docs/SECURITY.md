# DrishtiAI Security, AI Safety & Threat Model

**Status:** Hardened Production Prototype  
**Classification:** Medical AI Software (Class II Clinical Decision Support Architecture)  
**Safety Policy:** `SAFE-1.0`

---

## 1. Threat Model & Attack Surface

DrishtiAI is designed for deployment in diverse clinical environments, ranging from modern tertiary eye hospitals to rural mobile screening vans with intermittent connectivity. Consequently, its threat model accounts for both adversarial attacks and environmental edge cases:

| Threat Category | Attack / Failure Vector | Impact | DrishtiAI Defense Mechanism |
|---|---|---|---|
| **Resource Exhaustion** | Decompression Bomb (e.g. 50MP pixel flood) | Denial of Service, OOM crash | Pre-decode header inspection; strict 25.0 MP cutoff (`ImageValidator`). |
| **Payload Corruption** | Truncated JPEG streams, non-image binaries | Worker process segfault | Magic byte sniffing, strict PIL decode exception isolation. |
| **Replay / Confusion** | Duplicate scan submission within same session | Inadvertent double diagnosis | Per-session SHA-256 fingerprint deduplication cache. |
| **Out-of-Distribution** | Accidental upload of skin lesions, documents, pets | Hallucinatory diagnostic output | Multi-layer heuristic OOD analysis; domain invalidation flag. |
| **Anatomical Swap** | Operator mistakenly selects OD for Left Eye scan | Lateral misdiagnosis, incorrect surgical note | Optic disc / fovea spatial geometry verification; required human confirmation. |
| **Model Hallucination** | Overconfident inference on borderline / unrepresented lesion | Missed sight-threatening DR | Epistemic uncertainty multiplier; secondary consensus model fallback. |
| **Concurrent Mutation** | Simultaneous edits on local edge node & cloud server | Silently overwritten doctor notes | Outbox sync ledger with strict `CONFLICT_REQUIRES_REVIEW` state. |
| **Privilege Escalation** | Field operator accessing detailed system telemetry | Leakage of model internals / hospital config | Strict RBAC (`Role.ADMIN`, `Role.DOCTOR`) on diagnostics endpoints. |

---

## 2. Multi-Layer Defense Architecture

```
[ Incoming Image Payload ]
           │
           ▼
┌───────────────────────────────────────────────────────────┐
│ Layer 1: Ingest & Binary Hygiene (ImageValidator)         │
│  - Magic byte verification (JPEG, PNG, TIFF)              │
│  - Decompression bomb threshold (< 25 MP)                 │
│  - Zero-variance / blank frame filter                     │
│  - SHA-256 fingerprint duplicate cache                    │
└──────────────────────────┬────────────────────────────────┘
                           │ Validated binary
                           ▼
┌───────────────────────────────────────────────────────────┐
│ Layer 2: Anatomical & Laterality Verification             │
│  - Optic disc & fovea spatial localization                │
│  - Vector orientation cross-check against operator eye    │
│  - Flag: LATERALITY_MISMATCH (Never silent auto-override) │
└──────────────────────────┬────────────────────────────────┘
                           │ Verified anatomy
                           ▼
┌───────────────────────────────────────────────────────────┐
│ Layer 3: Out-of-Distribution (OOD) Pipeline               │
│  - Color space distribution & vascular entropy check      │
│  - Domain invalidation (rejects documents, external pics) │
│  - Epistemic uncertainty scaling                          │
└──────────────────────────┬────────────────────────────────┘
                           │ Domain validated
                           ▼
┌───────────────────────────────────────────────────────────┐
│ Layer 4: Multi-Model Inference & Consensus Arbitration    │
│  - Primary classifier (EfficientNet-B3)                   │
│  - Grad-CAM explainability localization                   │
│  - Secondary disagreement check                           │
│  - Gemma-4 empathetic clinical reporting                  │
└──────────────────────────┬────────────────────────────────┘
                           │ Diagnostic output
                           ▼
┌───────────────────────────────────────────────────────────┐
│ Layer 5: Centralized Safety Decision Engine               │
│  - Safety State: PASS | REJECT | REVIEW_REQUIRED          │
│  - Automation Level: DECISION_SUPPORT (Non-Autonomous)    │
│  - Audit log recording to SQLite                          │
└───────────────────────────────────────────────────────────┘
```

---

## 3. Cryptographic Session Binding & Integrity

1. **Screening Sessions:** Prior to image ingestion, operators bind an acquisition session via `/api/sessions/bind`. This generates an ephemeral session token recording operator ID, clinic station ID, and declared laterality.
2. **Audit Trail:** All state transitions, operator overrides, and clinician reviews are logged to the immutable `audit_logs` table in `database.py`.
3. **Data at Rest:** Patient identifiers and scan metadata are stored locally in SQLite (`data.db`) with schema migrations tracked and validated on startup.

---

## 4. Offline Privacy & Zero Cloud Leakage

In rural outreach or offline camp mode:
- All feature extraction, classification, and Grad-CAM generation run locally on device.
- Gemma-4 report generation operates via deterministic localized templates when internet connectivity is severed (`OFFLINE_MODE=True`).
- No patient telemetry or image data leaves the local edge node unless an explicit sync push is authenticated.
