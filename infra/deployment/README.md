# DrishtiAI Deployment Configuration

## Environments
- **development**: Local SQLite, debug mode, demo data
- **staging**: PostgreSQL-compatible, staging model artifacts
- **production**: PostgreSQL, verified model artifacts, audit logging enforced

## Model Deployment
Model deployment is decoupled from application deployment.
- Application version: `2.3.x` (frontend + backend)
- Model version: `1.x.x` (vision model weights)
- RAG version: `2026.MM` (clinical guidelines corpus)

A model-only update does NOT require a frontend redeployment.
