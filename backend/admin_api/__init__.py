"""DrishtiAI Intelligence Control Plane — Admin API Blueprint.

Provides governed REST API for MLOps operations:
  - Dataset registry and builder
  - Training job orchestration
  - Evaluation and safety gates
  - Model registry and lifecycle
  - Drift monitoring and alerts
  - Human clinical approvals and separation of duties
  - Model promotion and emergency rollbacks
  - Governance audit logging
"""

from flask import Blueprint

admin_bp = Blueprint("admin_api", __name__)

from backend.admin_api import routes  # noqa: E402, F401
