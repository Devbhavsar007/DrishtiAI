# Runbook: Disaster Recovery & Continuity

## Failure Scenarios & Recovery Strategies

### 1. SQLite Database Corruption or Disk Failure
* **Mitigation**: Database operates in WAL mode (`PRAGMA journal_mode=WAL`).
* **Recovery**:
  1. Halt backend and worker services: `python app.py` and workers.
  2. Restore latest automated snapshot from backup volume.
  3. Run `python -c "from database import init_db; init_db()"` to verify integrity.
  4. Resync uncommitted transactions from edge device outbox ledgers.

### 2. Model Artifact Corruption / Checksum Mismatch
* **Detection**: `ml_platform/registry/artifacts.py` validates SHA-256 before loading weights.
* **Recovery**:
  1. Identify corrupted model version in `model_versions` table.
  2. Restore weights from the immutable artifact store or re-export from training checkpoint.
  3. If artifact is unrecoverable, execute automated rollback to preceding model version.

### 3. Asynchronous Worker Interruption
* **Detection**: Worker heartbeats recorded in `BaseWorker`.
* **Recovery**:
  1. Worker threads automatically recover upon application restart.
  2. In-flight jobs remain in `QUEUED` or `RUNNING` status and are safely retried.
