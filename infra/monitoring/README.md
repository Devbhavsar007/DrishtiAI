# DrishtiAI Monitoring & Observability

## Health Endpoints
- `GET /api/health` — Clinical platform health check
- `GET /api/admin/system` — Intelligence Control Plane system status

## Key Metrics to Monitor

### Clinical
- Inference latency (p50, p95, p99)
- Image quality rejection rate
- OOD detection rate
- Sync failure rate

### MLOps
- Training job duration and failure rate
- Dataset build success rate
- Drift severity (NORMAL / WATCH / DETECTED / CRITICAL)
- Model candidate pipeline throughput
- Deployment rollback frequency

## Structured Logging
All components use Python `logging` with structured JSON-compatible output.
Correlation IDs (`request_id`) flow through clinical and admin API requests.
