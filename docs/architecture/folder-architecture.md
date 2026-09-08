# DrishtiAI Folder & Package Structure

```
OptiGemma/
├── backend/                  # API routing layer
│   └── admin_api/            # Intelligence Control Plane REST blueprint (/api/admin/*)
│       ├── __init__.py
│       └── routes.py
├── engine/                   # Core Clinical Platform inference & safety
│   ├── clinical/             # Progression risk, referrals, medical RAG
│   ├── contracts/            # Protocol ABC interfaces
│   ├── demo/                 # Canonical synthetic scenario fixtures
│   ├── pipeline/             # Two-tier fast/deep fundus grading runner
│   ├── safety/               # ScreeningStateMachine, IQA, OOD detection
│   ├── security/             # Token auth, RBAC, edge signatures
│   └── sync/                 # Offline synchronization engine
├── ml_platform/              # Intelligence Control Plane domain packages
│   ├── active_learning/      # Uncertainty sampling & annotation queue
│   ├── data/                 # Ingestion, quality, provenance, leakage check
│   ├── datasets/             # Builder, versioning, patient splitting, validation
│   ├── drift/                # Input feature, prediction, & clinical discordance
│   ├── evaluation/           # Metrics, confusion matrix, regression, safety gates
│   ├── governance/           # Human approvals, separation of duties, audit trail
│   ├── registry/             # Model lifecycle, artifact hashes, compatibility
│   ├── release/              # Staging, canary, promotion, and emergency rollback
│   └── training/             # Orchestration, presets, loop trainer hooks
├── workers/                  # Background worker services
│   ├── base.py               # Abstract worker lifecycle & heartbeat
│   ├── training_worker.py    # Retraining job processor
│   ├── evaluation_worker.py  # Evaluation queue runner
│   ├── dataset_worker.py     # Scheduled dataset compilation
│   └── drift_worker.py       # Periodic discordance & drift evaluator
├── src/                      # React 19 Frontend
│   ├── components/
│   │   ├── admin/            # Intelligence Control Plane views
│   │   │   ├── AdminLayout.tsx
│   │   │   ├── AdminDashboard.tsx
│   │   │   ├── DataOverview.tsx
│   │   │   ├── DatasetManager.tsx
│   │   │   ├── TrainingRuns.tsx
│   │   │   ├── ModelRegistry.tsx
│   │   │   ├── DriftMonitor.tsx
│   │   │   ├── ApprovalWorkflow.tsx
│   │   │   ├── AuditLog.tsx
│   │   │   └── SystemHealth.tsx
│   │   └── ...               # Clinical Platform views (NewScan, Dashboard, etc.)
│   ├── App.tsx               # Logical plane router
│   └── types.ts              # Domain type definitions
├── tests/                    # 30+ test suites (Clinical + MLOps)
├── docs/                     # Architecture, MLOps, Security, and Runbooks
├── config.py                 # Core application configuration
├── config_admin.py           # Intelligence Control Plane configuration
└── database.py               # SQLite schema with migrations (v1-v5)
```
