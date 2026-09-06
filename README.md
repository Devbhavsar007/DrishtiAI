# 👁️ DrishtiAI

**Production-Hardened AI-Powered Retinal Screening & Clinical Decision-Support Platform**  
*Empowered by Dual-Model Deep Learning, Explainable AI (XAI), and Gemma-4 Clinical Intelligence.*

[![Safety Policy](https://img.shields.io/badge/Safety_Policy-SAFE--1.0-emerald.svg)](docs/SECURITY.md)
[![Triage Policy](https://img.shields.io/badge/Triage_Policy-TRIAGE--1.1-blue.svg)](docs/API.md)
[![Clinical Mode](https://img.shields.io/badge/Clinical_Mode-Decision_Support_(Non--Autonomous)-amber.svg)](docs/LIMITATIONS.md)
[![Tests](https://img.shields.io/badge/Tests-100%25_Passing-brightgreen.svg)](tests/)

---

## ⚠️ Clinical Positioning & Non-Autonomous Scope

> **IMPORTANT CLINICAL NOTICE:**  
> DrishtiAI is architected as an **AI-powered screening and clinical decision-support tool (Software as a Medical Device - SaMD Class II)** designed to assist healthcare professionals in identifying signs of Diabetic Retinopathy (DR). **It is NOT an autonomous diagnostic system and does not replace examination by a licensed ophthalmologist or optometrist.** All AI recommendations enforce `DECISION_SUPPORT` automation levels requiring qualified human review before medical intervention or discharge.

---

## ✨ Key Capabilities & Production Hardening

- 🛡️ **5-Gate Safety Decision Core**:
  1. **Ingest & Binary Hygiene:** Validates magic bytes, blocks decompression bombs (>25 MP), rejects uninformative/blank frames, and caches SHA-256 fingerprints.
  2. **Anatomical & Laterality Verification:** Locates optic disc and fovea landmarks; cross-checks declared laterality (Right Eye OD vs Left Eye OS) and flags conflicts for human confirmation without silent overwrites.
  3. **Out-of-Distribution (OOD) Pipeline:** 3-tier pipeline detecting non-retinal artifacts (documents, pets, skin lesions) and scaling epistemic uncertainty.
  4. **Multi-Model Consensus & Disagreement Escalation:** EfficientNet-B3 primary classifier with secondary consensus evaluation and automatic escalation on conflicting stages.
  5. **Centralized Arbitration State Machine:** Deterministic finite state machine with first-class handling of failure states (`QUALITY_FAILED`, `ANATOMY_FAILED`, `SCREENING_UNCERTAIN`, `CONFLICT_REQUIRES_REVIEW`).
- 🔬 **Multimodal Explainability Triptych**: High-definition fundus view, multi-scale Frangi capillary segmentation mask, and Grad-CAM attention heatmap proving lesion localization.
- 💬 **Gemma-4 Multilingual Intelligence**: Empathetic clinical report generation with one-click screen-reader audio in English, Hindi (हिंदी), and Gujarati (ગુજરાતી), compliant with WCAG 2.1 AAA high-contrast standards.
- 📊 **Scientific Honesty Protocol**: Refuses to synthesize continuous longitudinal progression curves from a single baseline photograph. Explicitly distinguishes between population-risk cohorts and verified multi-visit temporal history (`LIMITED_LONGITUDINAL_HISTORY`).
- 📡 **Offline Camp Resilience & Outbox Ledger**: Designed for disconnected rural outreach camps with local SQLite outbox queueing and conflict-preserving sync (`CONFLICT_REQUIRES_REVIEW` avoids silent data loss).
- 🧪 **1-Click Hackathon & Red-Team Simulator**: 10 canonical scenarios accessible via UI and `/api/demo/run` in an isolated synthetic sandbox (`DEMO-SIM-`).

---

## 🏗️ 3-Tier System Architecture

```mermaid
graph TD
    subgraph Client["Frontend Client (React + Vite)"]
        UI[Accessibility-First UI]
        LateralityToggle[Laterality Selector OD/OS]
        DemoPanel[Red-Team Simulator 10 Scenarios]
        Triptych[Explainability Triptych]
        Audio[Multilingual Speech Engine]
    end

    subgraph Gateway["API & Session Boundary"]
        SessionBind[/api/sessions/bind]
        IngestGate[/api/ingest/validate]
        HealthProbes[/api/health & /ready]
    end

    subgraph Core["Hardened Safety Core"]
        ImgValidator[ImageValidator Decompress/Bomb/Hash]
        Anatomy[Anatomy Engine Disc/Fovea/Laterality]
        OOD[OOD Pipeline Domain Shift]
        StateMachine[Safety State Machine]
    end

    subgraph Inference["AI Inference Pipeline"]
        EfficientNet[EfficientNet-B3 Primary]
        GradCAM[Grad-CAM Saliency]
        Frangi[Frangi Vessel Segmenter]
        Gemma[Gemma-4 Clinical LLM]
    end

    subgraph Storage["Resilient Persistence"]
        DB[(SQLite data.db)]
        SyncLedger[Offline Outbox Ledger]
        AuditLog[Immutable Audit Logs]
    end

    UI --> Gateway
    DemoPanel --> Gateway
    Gateway --> Core
    Core --> Inference
    Core --> Storage
    Inference --> Storage
```

---

## 📁 Repository Structure

```
DrishtiAI / OptiGemma
├── app.py                         # Production Flask API Server & WSGI entrypoint
├── config.py                      # Centralized configuration & environment loader
├── database.py                    # SQLite/PostgreSQL schema, migrations, ORM
│
├── engine/                        # Core Clinical & AI Safety Engine
│   ├── safety/                    # Image validation, Anatomy, OOD, Decision engine
│   ├── clinical/                  # Progression, Referral, Medical RAG, Safety policy
│   ├── pipeline/                  # IQA, Segmentation, Grading, Explainability
│   ├── sync/                      # Offline ledger & reconciliation
│   ├── security/                  # RBAC, JWT, Audit logging
│   └── demo/                      # Sandbox simulation scenarios
│
├── src/                           # Frontend React / TypeScript UI
│   ├── components/                # UI components (Views, Modals, Banners)
│   ├── context/                   # React context providers
│   └── types.ts                   # Shared TypeScript interfaces
│
├── training/                      # ML Training, Calibration & Active Learning
│   ├── grading/                   # Severity grading training & calibration
│   ├── segmentation/              # Vessel/lesion segmentation models
│   ├── loop_trainer.py            # Active learning in-the-loop training engine
│   └── losses.py                  # Custom medical loss functions
│
├── models/                        # Checkpoints, Weights & Calibration Data
│   ├── dr_pipeline/               # EfficientNet-B3 weights & calibration.json
│   ├── onnx/                      # ONNX runtime exports
│   └── vessel_model/              # Vessel segmentation model artifacts
│
├── scripts/                       # Operational, Data, Evaluation & Dev Utilities
│   ├── data/                      # Dataset downloaders & dataset managers
│   ├── eval/                      # Evaluation & benchmarking tools
│   ├── ops/                       # Operational, migration & seeding scripts
│   └── dev/                       # Local developer verification & debug utilities
│
├── tests/                         # Complete Automated Test Suite (74 passing tests)
├── docs/                          # Architecture, Regulatory, API, Security & Runbooks
├── tools/                         # Offline Analysis & Visualization Tools
├── matlab/                        # MATLAB Clinical Algorithms & Stateflow Models
└── simulink/                      # Simulink Telemedicine Simulation models
```

---

## 📚 Documentation Suite

Comprehensive engineering documentation is available in the [`docs/`](docs/) directory:

- 📐 [**Architecture Guide**](docs/ARCHITECTURE.md): Topology, 3-tier boundary, safety state machine, and data flow.
- ⚠️ [**Edge-Case Matrix**](docs/EDGE_CASES.md): P0 through P3 failure mode taxonomy, mitigation vectors, and tests.
- ⚖️ [**Clinical Limitations & SaMD Scope**](docs/LIMITATIONS.md): Regulatory classification, honest longitudinal bounds, and non-autonomous positioning.
- 🔌 [**API Specification**](docs/API.md): Detailed reference for health probes, session binding, analysis endpoints, and sync routes.
- 🔒 [**Security & Threat Model**](docs/SECURITY.md): Threat vectors, defense-in-depth layers, RBAC, and zero cloud leakage.
- 📖 [**Field & Operator Runbook**](docs/RUNBOOK.md): Deployment, configuration flags, disaster recovery, and offline camp operation.
- 🎯 [**Hackathon Evaluator Script**](docs/DEMO_GUIDE.md): 5-minute pitch script, live demo walkthrough, and technical talking points.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.11)
- Node.js 18+ & npm
- SQLite 3

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/Devbhavsar007/DrishtiAI.git
cd DrishtiAI

# Install Python dependencies
pip install -r requirements.txt

# Start Flask Backend (Port 5000)
python app.py
```

### 3. Frontend Setup
```bash
# Install Node dependencies
npm install

# Start Vite Development Server (Port 5173, Proxied to 5000)
npm run dev
```

---

## 🧪 Verification & Test Suite

DrishtiAI includes a comprehensive, multi-layer automated test suite spanning legacy backward compatibility, safety gates, and red-team failure injection:

```bash
# Run all automated tests with pytest
python -m pytest tests/ -v
```

### Test Coverage Highlights:
- `tests/test_legacy_regression.py`: Validates zero regression across legacy endpoints (`/analyze`, `/api/analyze-v2`, `/api/patients`, `/api/dashboard`).
- `tests/test_safety_core.py`: Validates decompression bomb cutoff, corrupted byte rejection, and SHA-256 fingerprinting.
- `tests/test_failure_injection.py`: Red-team suite verifying domain shift rejection, duplicate image caching, and endpoint error handling.
- `tests/test_state_machine.py`: Verifies finite state machine transitions and non-happy-path recovery states.
- `tests/test_clinical_intelligence.py`: Validates deterministic referral rules (ICMR/AAO) and honest longitudinal disclaimers.
- `tests/test_offline_sync.py`: Validates local outbox queuing and `CONFLICT_REQUIRES_REVIEW` conflict preservation.
- `tests/test_security_boundaries.py`: Validates session binding and RBAC diagnostics.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
