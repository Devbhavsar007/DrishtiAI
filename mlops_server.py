"""
DrishtiAI — Intelligence Control Plane & MLOps Dedicated Service
Runs on dedicated port (default: 5001).
Serves the full MLOps lifecycle:
- Dataset builder & versioning
- Training orchestration & experiment tracking
- Model registry & safety gate evaluations
- Drift monitoring
- Multi-party approvals, staging, production promotion, and emergency rollback
"""

import os
import sys
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import init_db
from backend.admin_api import admin_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("DrishtiAI.MLOps")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Ensure database is initialized
init_db()

# Register Admin API Blueprint at both /api/admin and /api
app.register_blueprint(admin_bp, url_prefix="/api/admin")

@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def mlops_root():
    return jsonify({
        "service": "DrishtiAI Intelligence Control Plane (MLOps)",
        "status": "OPERATIONAL",
        "plane": "INTELLIGENCE_CONTROL_PLANE",
        "port": 5001,
        "endpoints": {
            "dashboard": "/api/admin/dashboard",
            "data_overview": "/api/admin/data/overview",
            "datasets": "/api/admin/datasets",
            "training": "/api/admin/training",
            "models": "/api/admin/models",
            "drift": "/api/admin/drift",
            "releases": "/api/admin/releases",
            "approvals": "/api/admin/approvals",
            "audit": "/api/admin/audit",
            "system": "/api/admin/system",
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("MLOPS_PORT", 5001))
    host = os.environ.get("MLOPS_HOST", "0.0.0.0")
    log.info("============================================================")
    log.info("  DrishtiAI MLOps Control Plane Server Launching")
    log.info("  Dedicated MLOps Port: %s", port)
    log.info("  URL: http://127.0.0.1:%s", port)
    log.info("============================================================")
    app.run(host=host, port=port, debug=False)
