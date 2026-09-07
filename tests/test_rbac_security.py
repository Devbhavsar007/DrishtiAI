"""Unit tests for DrishtiAI Role-Based Access Control (RBAC) and Observability Metrics."""

import unittest
import time
import uuid
from app import app
from config import DOCTOR_SECRET
from engine.security.auth import Role, create_access_token, verify_token
from database import create_patient, delete_patient, save_scan, get_db


class TestRBACAndObservability(unittest.TestCase):
    def setUp(self):
        self.patient = create_patient(
            name="RBAC Test Patient",
            age=55,
            gender="Female",
            diabetes_duration=10,
            sugar_level=160.0,
            hba1c=7.8,
            notes="Testing RBAC enforcement",
        )
        self.patient_id = self.patient["id"]
        self.scan_id = f"rbac-scan-{uuid.uuid4().hex[:8]}"

        save_scan(
            scan_id=self.scan_id,
            patient_id=self.patient_id,
            detection_result={"stage": 3, "stage_name": "Severe NPDR", "confidence": 89.0, "severity": "severe", "color": "#DC2626"},
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={"original": "test.png"},
            processing_time=0.35,
        )

    def tearDown(self):
        delete_patient(self.patient_id)
        with get_db() as conn:
            conn.execute("DELETE FROM doctor_reviews WHERE scan_id = ?", (self.scan_id,))
            conn.commit()

    def test_token_creation_and_verification(self):
        token = create_access_token(user_id="doc-123", role="DOCTOR", expires_in_seconds=3600)
        self.assertTrue(token.startswith("dr1."))

        payload = verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["sub"], "doc-123")
        self.assertEqual(payload["role"], "DOCTOR")

    def test_tampered_token_rejected(self):
        token = create_access_token(user_id="doc-123", role="DOCTOR", expires_in_seconds=3600)
        tampered = token[:-4] + "abcd"
        self.assertIsNone(verify_token(tampered))

    def test_expired_token_rejected(self):
        token = create_access_token(user_id="doc-123", role="DOCTOR", expires_in_seconds=-10)
        self.assertIsNone(verify_token(token))

    def test_auth_login_and_me_endpoints(self):
        client = app.test_client()

        # Unauthenticated Doctor role elevation attempt -> 401
        res_unauth = client.post("/api/auth/login", json={"user_id": "dr-sharma", "role": "DOCTOR"})
        self.assertEqual(res_unauth.status_code, 401)

        # Login as Doctor with valid secret -> 200
        res = client.post("/api/auth/login", json={"user_id": "dr-sharma", "role": "DOCTOR", "secret": DOCTOR_SECRET})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        token = data["token"]

        # Call /api/auth/me with Bearer token
        me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.get_json()
        self.assertEqual(me_data["actor"]["actor_id"], "dr-sharma")
        self.assertEqual(me_data["actor"]["actor_role"], "DOCTOR")

    def test_role_enforcement_doctor_review(self):
        client = app.test_client()

        # 1. Patient role should be FORBIDDEN (403)
        patient_token = create_access_token(user_id="pat-1", role="PATIENT")
        forbidden_res = client.post(
            f"/api/scans/{self.scan_id}/doctor-review",
            json={
                "decision": "APPROVED",
                "clinical_notes": "Attempted patient review",
            },
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        self.assertEqual(forbidden_res.status_code, 403)

        # 2. Doctor role should be ALLOWED (200)
        doc_token = create_access_token(user_id="doc-specialist", role="DOCTOR")
        allowed_res = client.post(
            f"/api/scans/{self.scan_id}/doctor-review",
            json={
                "doctor_id": "doc-specialist",
                "decision": "APPROVED",
                "adjusted_stage": 3,
                "approved_priority": "URGENT",
                "clinical_notes": "Confirmed stage 3 severe NPDR with retinal hemorrhages.",
            },
            headers={"Authorization": f"Bearer {doc_token}"}
        )
        self.assertEqual(allowed_res.status_code, 200)
        self.assertTrue(allowed_res.get_json()["success"])

    def test_observability_metrics_endpoint(self):
        client = app.test_client()
        token = create_access_token("dr-sharma", Role.DOCTOR.value)
        res = client.get("/api/analytics/metrics", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

        metrics = data["metrics"]
        self.assertEqual(metrics["system"], "DrishtiAI")
        self.assertIn("throughput", metrics)
        self.assertIn("epidemiology", metrics)
        self.assertIn("clinical_triage", metrics)
        self.assertIn("human_oversight", metrics)
        self.assertIn("edge_sync", metrics)


if __name__ == "__main__":
    unittest.main()
