# Model Registry & Artifact Management

## 1. Registry Architecture
The Model Registry (`models/registry/` and table `model_versions`) guarantees end-to-end lineage from data ingestion to active inference weights.

## 2. State Progression
```
EXPERIMENTAL ────> TRAINED ────> EVALUATED ────> CANDIDATE
                                                     │
                                                     ▼
PRODUCTION <──── STAGED <──── APPROVED <────────────┘
    │
    ▼
 ARCHIVED
```

## 3. Artifact Security
- Checkpoints are hashed with SHA-256 upon registration.
- Before inference loading or production deployment, the file digest must match `weights_checksum` in the database, preventing unauthorized weight tampering or bitrot.
