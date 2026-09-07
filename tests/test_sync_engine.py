"""Unit tests for DrishtiAI offline sync ledger and edge reconciliation."""

import unittest
import uuid
import time
from app import app
from engine.security.auth import create_access_token, Role, create_edge_signature
from database import (
    record_sync_event,
    get_pending_sync_events,
    reconcile_sync_batch,
    get_sync_status,
    get_db,
)


class TestSyncEngine(unittest.TestCase):
    def setUp(self):
        self.device_id = f"edge-node-{uuid.uuid4().hex[:6]}"
        self.entity_id = f"P-TEST-{uuid.uuid4().hex[:4]}"

    def tearDown(self):
        with get_db() as conn:
            conn.execute("DELETE FROM sync_events WHERE device_id = ? OR entity_id = ?", (self.device_id, self.entity_id))
            conn.commit()

    def test_record_and_get_pending_sync_events(self):
        event_id = record_sync_event(
            device_id=self.device_id,
            entity_type="PATIENT",
            entity_id=self.entity_id,
            action="CREATE",
            payload={"name": "Offline Subject", "age": 52},
            version=1,
        )

        self.assertTrue(event_id.startswith("sync-"))
        pending = get_pending_sync_events(device_id=self.device_id)
        self.assertTrue(any(e["id"] == event_id for e in pending))
        target = next(e for e in pending if e["id"] == event_id)
        self.assertEqual(target["payload"]["name"], "Offline Subject")

    def test_reconcile_sync_batch_with_conflict_resolution(self):
        # 1. Simulate server having version 2 already
        record_sync_event(
            device_id="central-server",
            entity_type="PATIENT",
            entity_id=self.entity_id,
            action="UPDATE",
            payload={"name": "Server Updated Name"},
            version=2,
        )

        # 2. Incoming edge batch with an older version 1 (should conflict)
        batch = [
            {
                "id": f"sync-{uuid.uuid4().hex[:8]}",
                "device_id": self.device_id,
                "entity_type": "PATIENT",
                "entity_id": self.entity_id,
                "action": "UPDATE",
                "version": 1,
                "payload": {"name": "Edge Stale Name"},
            },
            {
                "id": f"sync-{uuid.uuid4().hex[:8]}",
                "device_id": self.device_id,
                "entity_type": "SCAN",
                "entity_id": f"scan-{uuid.uuid4().hex[:6]}",
                "action": "CREATE",
                "version": 1,
                "payload": {"stage": 1},
            }
        ]

        result = reconcile_sync_batch(batch)
        self.assertEqual(result["conflict_count"], 1)
        self.assertIn(self.entity_id, result["conflict_ids"])
        self.assertEqual(result["synced_count"], 1)

    def test_sync_status_metric(self):
        status = get_sync_status()
        self.assertIn("pending_events", status)
        self.assertIn("synced_events", status)
        self.assertIn("conflicts", status)
        self.assertIn("is_synced", status)

    def test_sync_api_endpoints(self):
        client = app.test_client()
        hw_token = create_access_token("hw-1", Role.HEALTH_WORKER.value)

        # Status check
        status_res = client.get(
            "/api/sync/status",
            headers={"Authorization": f"Bearer {hw_token}"}
        )
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.get_json()
        self.assertTrue(status_data["success"])
        self.assertIn("is_synced", status_data["status"])

        # Batch reconciliation endpoint with HMAC-signed edge device headers
        now = int(time.time())
        sig = create_edge_signature(self.device_id, Role.HEALTH_WORKER.value, now)
        edge_headers = {
            "X-Drishti-Edge-Device-Id": self.device_id,
            "X-Drishti-Edge-Role": Role.HEALTH_WORKER.value,
            "X-Drishti-Edge-Timestamp": str(now),
            "X-Drishti-Edge-Signature": sig,
        }

        incoming_batch = {
            "events": [
                {
                    "device_id": self.device_id,
                    "entity_type": "REFERRAL",
                    "entity_id": f"ref-{uuid.uuid4().hex[:6]}",
                    "action": "CREATE",
                    "version": 1,
                    "payload": {"priority": "URGENT"},
                }
            ]
        }
        res = client.post(
            "/api/sync",
            json=incoming_batch,
            headers=edge_headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["reconciliation"]["synced_count"], 1)


if __name__ == "__main__":
    unittest.main()
