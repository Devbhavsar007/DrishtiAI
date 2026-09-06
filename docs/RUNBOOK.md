# DrishtiAI Operator & Field Runbook

**Deployment:** Edge Node & Rural Outreach Camp  
**Platform:** DrishtiAI v2.4.0 (Production-Hardened Prototype)

---

## 1. System Requirements & Environment

### Hardware
- **Processor:** Intel Core i5 / AMD Ryzen 5 (4+ cores) or Apple M-series
- **Memory:** 8 GB RAM minimum (16 GB recommended for multi-worker inference)
- **Storage:** 2 GB available SSD storage for model weights and local SQLite cache

### Software & Runtimes
- **Python:** 3.10 to 3.12 (Tested on Python 3.11.9)
- **Node.js:** v18.0+ or v20.0+ (Tested on Node.js v20.x)
- **Database:** SQLite 3 (Bundled with Python, schema auto-migrated)

---

## 2. Quickstart Execution

### Backend Initialization
```bash
# Activate virtual environment if configured
python app.py
```
*Output confirmation:*
```
 * Running on http://127.0.0.1:5000
 * DrishtiAI Hardened Core Initialized [Policy: SAFE-1.0, Schema: v2]
```

### Frontend Initialization
```bash
npm run dev
```
*Vite local server starts at `http://localhost:5173` (proxied to port 5000).*

---

## 3. Configuration & Feature Flags (`config.py`)

All behavioral switches and policies are managed centrally:

| Environment Variable / Flag | Default | Description |
|---|---|---|
| `DEMO_MODE` | `True` | Activates `/api/demo/*` endpoints and isolated `DEMO-SIM-` sandbox. Set to `False` in clinical production. |
| `OFFLINE_MODE` | `False` | Forces deterministic offline Gemma clinical reporting and suppresses cloud API calls. |
| `ENABLE_OOD` | `True` | Enables 3-tier Out-of-Distribution rejection pipeline. |
| `ENABLE_LATERALITY` | `True` | Enforces anatomical disc/fovea laterality cross-checking. |
| `SAFETY_POLICY_VERSION` | `"SAFE-1.0"` | Embedded in all screening session payloads and audit logs. |
| `TRIAGE_POLICY_VERSION` | `"TRIAGE-1.1"` | Governs ICMR/AAO deterministic referral intervals. |

---

## 4. Operational Workflows

### A. Offline Camp Screening Routine
1. **Departure to Field:** Ensure laptop/edge device is running with `OFFLINE_MODE=True`.
2. **Patient Registration:** Register subjects via Quick Camp Outreach mode. Temporary IDs (e.g. `PAT-XXXX`) are automatically created.
3. **Session Binding:** Select laterality (`OD` for Right Eye, `OS` for Left Eye) before acquiring scan.
4. **Acquisition & Decision Support:** Run analysis. Results, explainability heatmaps, and audit logs persist locally in `data.db`.
5. **Return to Hospital:** Connect to hospital network. Navigate to Offline Sync Manager and push outbox queue. Any concurrent record changes trigger `CONFLICT_REQUIRES_REVIEW` rather than destructive overwrites.

### B. Disaster Recovery & Database Maintenance
- **Database Backup:** The entire database resides in `data.db`. Create a snapshot via:
  ```bash
  sqlite3 data.db ".backup 'data_backup_$(date +%Y%m%d).db'"
  ```
- **Migration Verification:** If updating code versions, restart `app.py`. The built-in migration runner will check `PRAGMA user_version` and apply schema deltas cleanly.

---

## 5. Troubleshooting Matrix

| Symptom | Probable Cause | Action |
|---|---|---|
| Image rejected with `DIMENSIONS_EXCEED_LIMIT` | Uploaded raw TIFF/JPEG exceeds 25 megapixels | Downsample image on camera workstation before submission. |
| Analysis reports `LATERALITY_MISMATCH` | Operator selected OD for OS eye, or optic disc obscured | Verify fundus orientation. If anatomically correct, confirm via Human Override modal. |
| Gemma report timeout (>30s) | Cloud API rate limit or no internet | Switch `OFFLINE_MODE = True` in `config.py` for sub-second deterministic reporting. |
| Outbox sync indicates `CONFLICT_REQUIRES_REVIEW` | Patient record modified both locally and on server | Click "Resolve Conflict" in doctor review panel to select authoritative fields. |
