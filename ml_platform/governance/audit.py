"""Governance audit log and compliance traceability.

Records every administrative and operational action within the Intelligence Control Plane.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from database import get_db

log = logging.getLogger(__name__)


def log_governance_action(
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict[str, Any] | None = None,
) -> str:
    """Record an audited administrative action."""
    log_id = f"aud-{uuid.uuid4().hex[:12]}"
    payload = json.dumps(details or {})

    # Reuse audit_logs table from database.py if available
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO audit_logs
                   (action, user_id, details)
                   VALUES (?, ?, ?)""",
                (
                    f"{action}:{resource_type}:{resource_id}",
                    actor_id,
                    json.dumps({"actor_role": actor_role, "payload": details or {}}),
                ),
            )
            conn.commit()
    except Exception as e:
        log.warning("Could not persist to audit_logs table: %s", e)

    log.info("AUDIT [%s] %s %s on %s:%s - %s", actor_role, actor_id, action, resource_type, resource_id, payload)
    return log_id


def query_governance_audit_trail(limit: int = 100) -> list[dict[str, Any]]:
    """Query recent governance audit events."""
    with get_db() as conn:
        try:
            rows = conn.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []
