# DrishtiAI Clinical Platform — Architecture

## 1. Overview
The **DrishtiAI Clinical Platform** is a medical-grade diagnostic assistance and tele-ophthalmology screening system engineered for edge devices, rural community health camps, and tertiary eye hospitals.

## 2. Core Stakeholders & Personas
- **Patients**: Receive instant plain-language risk evaluations, visual heatmaps, and multilingual educational guidance (English, Hindi, Gujarati).
- **Technicians / Vision Screening Operators**: Fast batch acquisition, real-time image quality assessment (IQA), laterality detection (OD/OS), and offline sync queuing.
- **Ophthalmologists / Doctors**: Longitudinal progression tracking, second-read verification, priority referral assignment, and clinical review sign-off.

## 3. End-to-End Clinical Data Flow
```mermaid
flowchart LR
    A[Fundus Camera / Upload] --> B[IQA & Image Validation]
    B --> C[Safety State Machine]
    C --> D[ResNet50 / Pipeline v3 Inference]
    D --> E[HiResCAM / Grad-CAM Attention]
    E --> F[U-Net Vessel Segmentation]
    F --> G[Referral Decision Engine]
    G --> H[Patient Report Generation]
    H --> I[Doctor Review & Confirmation]
```

## 4. Key Components
- **Inference Engine (`engine/pipeline/`)**: Two-tier architecture with instantaneous fast-path classification and deep clinical explanation.
- **Safety Subsystem (`engine/safety/`)**: Deterministic state machine (`ScreeningStateMachine`) preventing dangerous misclassification on out-of-distribution (OOD) or non-retinal artifacts.
- **Offline Sync Outbox (`engine/sync/`)**: Cryptographically signed local SQLite outbox with conflict resolution for rural offline eye screening camps.
