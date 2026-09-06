"""
Offline Synchronization Outbox Ledger and Conflict Review Engine for DrishtiAI.

Enforces:
  1. Transactional local append-only event queue
  2. Retry tracking (sync_attempt, retry_count, last_sync_at)
  3. Strict conflict preservation: Clinical conflicts become CONFLICT_REQUIRES_REVIEW
     (Local doctor reviews and clinical notes are NEVER silently overwritten by the cloud).
"""

from datetime import datetime, timezone
import json
import uuid
from typing import List, Dict, Optional, Any
from database import get_db, log_audit_event


class SyncConflictPolicy:
    REVIEW_REQUIRED = "CONFLICT_REQUIRES_REVIEW"
    CLIENT_WINS = "CLIENT_WINS"
    SERVER_WINS = "SERVER_WINS"


def record_outbox_event(
    entity_type: str,
    entity_id: str,
    action: str,
    payload: Dict[str, Any],
    device_id: str = "LOCAL-EDGE-01",
    version: int = 1,
) -> str:
    """Record a clinical action in the local offline outbox."""
    event_id = f"sync-{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    payload_str = json.dumps(payload, default=str)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO sync_events (
                id, device_id, entity_type, entity_id, action,
                version, payload, sync_status, created_at,
                sync_attempt, retry_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, 0, 0)
            """,
            (event_id, device_id, entity_type, entity_id, action, version, payload_str, now_iso),
        )
        conn.commit()

    log_audit_event(
        action=f"OUTBOX_EVENT_CREATED_{action.upper()}",
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=device_id,
        actor_role="SYSTEM",
        details=f"Event {event_id} queued for sync.",
    )
    return event_id


def get_outbox_pending_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve pending outbox items needing cloud synchronization."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM sync_events
            WHERE sync_status IN ('PENDING', 'RETRY_PENDING')
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("payload"), str):
                try:
                    d["payload"] = json.loads(d["payload"])
                except Exception:
                    pass
            result.append(d)
        return result


def reconcile_outbox_event(
    event_id: str,
    server_status: str,
    server_version: Optional[int] = None,
    server_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Reconcile event with cloud response.
    Never silently overwrites clinical conflicts.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM sync_events WHERE id = ?", (event_id,))
        event = cursor.fetchone()
        if not event:
            return {"success": False, "error": f"Event {event_id} not found."}

        local_version = event["version"]

        # Conflict Detection: Server version is different and server returned a conflicting state
        has_conflict = False
        conflict_msg = ""
        if server_status == "CONFLICT" or (server_version is not None and server_version > local_version):
            has_conflict = True
            conflict_msg = (
                f"Cloud record has higher version ({server_version}) than local ({local_version}). "
                "Manual clinical reconciliation required."
            )

        if has_conflict:
            new_status = SyncConflictPolicy.REVIEW_REQUIRED
            conn.execute(
                """
                UPDATE sync_events
                SET sync_status = ?,
                    conflict_resolution = ?,
                    last_sync_at = ?,
                    sync_attempt = sync_attempt + 1
                WHERE id = ?
                """,
                (new_status, conflict_msg, now_iso, event_id),
            )
            conn.commit()

            log_audit_event(
                action="SYNC_CONFLICT_DETECTED",
                entity_type=event["entity_type"],
                entity_id=event["entity_id"],
                actor_id="sync_engine",
                actor_role="SYSTEM",
                details=f"Conflict on event {event_id}: {conflict_msg}",
            )
            return {"success": False, "status": new_status, "conflict": conflict_msg}

        # Normal successful sync
        conn.execute(
            """
            UPDATE sync_events
            SET sync_status = 'SYNCED',
                synced_at = ?,
                last_sync_at = ?,
                sync_attempt = sync_attempt + 1
            WHERE id = ?
            """,
            (now_iso, now_iso, event_id),
        )
        conn.commit()

        log_audit_event(
            action="SYNC_EVENT_RESOLVED",
            entity_type=event["entity_type"],
            entity_id=event["entity_id"],
            actor_id="sync_engine",
            actor_role="SYSTEM",
            details=f"Event {event_id} successfully synchronized with cloud.",
        )
        return {"success": True, "status": "SYNCED"}


def mark_event_failed(event_id: str, error_message: str) -> None:
    """Record network or server failure for an outbox event."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            """
            UPDATE sync_events
            SET sync_status = 'RETRY_PENDING',
                sync_attempt = sync_attempt + 1,
                retry_count = retry_count + 1,
                last_sync_at = ?,
                conflict_resolution = ?
            WHERE id = ?
            """,
            (now_iso, f"Sync attempt failed: {error_message}", event_id),
        )
        conn.commit()
