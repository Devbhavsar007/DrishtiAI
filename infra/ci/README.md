# DrishtiAI CI/CD Pipeline Configuration

## Workflows

### ci.yml (Primary)
Located at `.github/workflows/ci.yml`. Runs on every push/PR:
- Python linting and type checks
- Backend unit tests (`pytest tests/`)
- Frontend build verification (`npm run build`)
- Security dependency audit
- Docker container build validation

### Model Promotion (Separate from CI)
Model promotion is NOT triggered by CI passing.
Model changes follow: TRAINED → EVALUATED → CANDIDATE → APPROVED → STAGED → PRODUCTION
This requires human approval via the Intelligence Control Plane.
