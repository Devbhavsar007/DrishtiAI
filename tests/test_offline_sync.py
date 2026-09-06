"""
Unit Tests for Gate 4: Offline Synchronization Ledger & Conflict Review.
Validates:
  1. Transactional outbox event recording
  2. Conflict handling: Server conflict sets CONFLICT_REQUIRES_REVIEW (never silently overwrites)
  3. Retry mechanics and failure recording (retry_count, sync_attempt)
  4. Database schema migration v2 verification
"""

import unittest
import uuid
from database import (
    init_db,
    get_db,
    create_or_update_screening_session,
    get_screening_session,
    update_screening_session_state,
)
from engine.sync.sync_ledger import (
    record_outbox_event,
    get_outbox_pending_events,
    reconcile_outbox_event,
    mark_event_failed,
    SyncConflictPolicy,
)


class TestOfflineSyncLedger(unittest.TestCase):
    def setUp(self):
        init_db()
        self.patient_id = f"P-99{uuid.uuid4().hex[:2]}"
        self.session_id = f"sess-{uuid.uuid4().hex[:8]}"

    def test_01_schema_migration_v2_applied(self):
        """Verify schema_migrations table records migration versions 1 and 2."""
        with get_db() as conn:
            cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC")
            versions = [r[0] for r in cursor.fetchall()]
            self.assertIn(1, versions)
            self.assertIn(2, versions)

            # Check new columns in scans table
            cursor_scans = conn.execute("PRAGMA table_info(scans)")
            scan_cols = [r["name"] for r in cursor_scans.fetchall()]
            self.assertIn("laterality", scan_cols)
            self.assertIn("safety_state", scan_cols)
            self.assertIn("automation_level", scan_cols)
            self.assertIn("reason_codes_json", scan_cols)

    def test_02_screening_session_crud(self):
        """Verify screening session creation, retrieval, and state update."""
        create_or_update_screening_session(
            session_id=self.session_id,
            patient_id="P-0001",
            operator_id="operator-ashok",
            eye="OD",
            current_state="CAPTURED",
            safety_state="VERIFIED",
            automation_level="AUTOMATED_ASSISTANCE",
            reason_codes=["QUALITY_PASSED"],
        )

        sess = get_screening_session(self.session_id)
        self.assertIsNotNone(sess)
        self.assertEqual(sess["session_id"], self.session_id)
        self.assertEqual(sess["current_state"], "CAPTURED")
        self.assertEqual(sess["eye"], "OD")
        self.assertIn("QUALITY_PASSED", sess["reason_codes"])

        # Update state
        update_screening_session_state(self.session_id, "FINALIZED", "dr-sharma", "Signed off")
        updated = get_screening_session(self.session_id)
        self.assertEqual(updated["current_state"], "FINALIZED")

    def test_03_outbox_event_lifecycle_and_reconciliation(self):
        """Record outbox event and reconcile with successful cloud response."""
        scan_id = f"scan-{uuid.uuid4().hex[:6]}"
        event_id = record_outbox_event(
            entity_type="scan",
            entity_id=scan_id,
            action="CREATE",
            payload={"stage": 2, "confidence": 85.0},
        )

        pending = get_outbox_pending_events()
        self.assertTrue(any(e["id"] == event_id for e in pending))

        # Reconcile successfully
        rec_res = reconcile_outbox_event(event_id, server_status="SUCCESS")
        self.assertTrue(rec_res["success"])
        self.assertEqual(rec_res["status"], "SYNCED")

    def test_04_conflict_requires_review_policy(self):
        """Cloud version conflict must set CONFLICT_REQUIRES_REVIEW and never overwrite."""
        scan_id = f"scan-{uuid.uuid4().hex[:6]}"
        event_id = record_outbox_event(
            entity_type="scan",
            entity_id=scan_id,
            action="UPDATE",
            payload={"notes": "Local rural clinic update"},
            version=1,
        )

        # Server returned CONFLICT with higher server version
        rec_conflict = reconcile_outbox_event(
            event_id=event_id,
            server_status="CONFLICT",
            server_version=3,
        )

        self.assertFalse(rec_conflict["success"])
        self.assertEqual(rec_conflict["status"], SyncConflictPolicy.REVIEW_REQUIRED)

        # Verify DB state
        with get_db() as conn:
            row = conn.execute("SELECT * FROM sync_events WHERE id = ?", (event_id,)).fetchone()
            self.assertEqual(row["sync_status"], SyncConflictPolicy.REVIEW_REQUIRED)
            self.assertIn("Manual clinical reconciliation required", row["conflict_resolution"])

    def test_05_sync_failure_retry_increment(self):
        """Network failure marks event RETRY_PENDING and increments attempt and retry counters."""
        event_id = record_outbox_event(
            entity_type="referral",
            entity_id=f"ref-{uuid.uuid4().hex[:6]}",
            action="DISPATCH",
            payload={"priority": "URGENT"},
        )

        mark_event_failed(event_id, "Connection refused: cloud endpoint offline")

        with get_db() as conn:
            row = conn.execute("SELECT * FROM sync_events WHERE id = ?", (event_id,)).fetchone()
            self.assertEqual(row["sync_status"], "RETRY_PENDING")
            self.assertEqual(row["sync_attempt"], 1)
            self.assertEqual(row["retry_count"], 1)


if __name__ == "__main__":
    unittest.main()
