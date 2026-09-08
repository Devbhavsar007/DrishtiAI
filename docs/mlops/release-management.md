# Release Management, Staging & Rollbacks

## 1. Release Progression Rules
No model can transition directly from training to production. The path is strictly sequential:
1. `TRAINED`: Training run completed, checkpoint exported.
2. `EVALUATED`: Standalone evaluator calculated metrics across test split.
3. `CANDIDATE`: Passed all 6 mandatory clinical safety gates and regression comparisons.
4. `APPROVED`: Independent clinical reviewer signed off (separation of duties enforced).
5. `STAGED`: Deployed in non-clinical environment for smoke/canary validation.
6. `PRODUCTION`: Active inference model serving patients.

## 2. Emergency Rollback Protocol
In the event of:
- A sudden surge in clinical discordance rate (> 35%),
- An unexpected rise in false negatives flagged by hospital staff, or
- Hardware inference corruption,

An authorized `SECURITY_ADMIN` or `SUPER_ADMIN` can execute an immediate rollback via:
- Admin UI ("Emergency Rollback" button) or
- API: `POST /api/admin/releases/rollback`

The system instantly restores the previous validated stable checkpoint in `models/production/` and logs an audited incident record in `deployments`.
