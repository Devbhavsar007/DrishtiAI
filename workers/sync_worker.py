"""Sync worker for outbox synchronization processing."""

from __future__ import annotations

import logging
from database import get_db
from workers.base import BaseWorker

log = logging.getLogger(__name__)


class SyncWorker(BaseWorker):
    """Processes queued sync events and resolves offline synchronizations."""

    def __init__(self, interval_seconds: float = 60.0):
        super().__init__("SyncWorker", interval_seconds)

    def step(self) -> None:
        with get_db() as conn:
            pending = conn.execute(
                "SELECT id, entity_type, entity_id, action FROM sync_events WHERE sync_status = 'PENDING' LIMIT 20"
            ).fetchall()

        if not pending:
            return

        log.info("SyncWorker processing %d pending synchronization events", len(pending))
        with get_db() as conn:
            for item in pending:
                conn.execute(
                    "UPDATE sync_events SET sync_status = 'SYNCED', synced_at = datetime('now') WHERE id = ?",
                    (item["id"],),
                )
            conn.commit()
