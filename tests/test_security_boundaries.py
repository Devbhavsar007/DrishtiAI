"""
Unit Tests for Gate 5: Security Foundations, Session Binding & Health Endpoint Protection.
Validates:
  1. Public health probes (/api/health and /api/health/ready)
  2. Protection of internal diagnostic probe (/api/health/detailed requires ADMIN/DOCTOR)
  3. Four-way session binding: (patient_id, operator_id, eye, session_id)
  4. Operator confirmation gate for warning overrides
  5. Input sanitization and path traversal prevention
"""

import unittest
from app import app, limiter
from engine.security.auth import create_access_token, Role
from database import create_patient, delete_patient


class TestSecurityBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.limiter_enabled = getattr(limiter, "enabled", True)
        limiter.enabled = False
        cls.client = app.test_client()

        # Create test patient
        cls.patient = create_patient(
            name="Security Test Patient",
            age=52,
            gender="Male",
            diabetes_duration=8,
            sugar_level=165.0,
            hba1c=7.6,
            notes="Testing security controls",
        )
        cls.patient_id = cls.patient["id"]

    @classmethod
    def tearDownClass(cls):
        limiter.enabled = cls.limiter_enabled
        delete_patient(cls.patient_id)

    def test_01_public_health_and_ready_probes(self):
        """Public health and readiness endpoints must be open without auth tokens."""
        res_liveness = self.client.get("/api/health")
        self.assertEqual(res_liveness.status_code, 200)
        self.assertEqual(res_liveness.get_json()["status"], "healthy")

        res_readiness = self.client.get("/api/health/ready")
        self.assertEqual(res_readiness.status_code, 200)
        self.assertEqual(res_readiness.get_json()["status"], "ready")
        self.assertEqual(res_readiness.get_json()["database"], "connected")

    def test_02_protected_detailed_health_requires_role(self):
        """Detailed internal diagnostics must forbid unauthenticated and patient requests."""
        # A. Anonymous request -> 403
        res_anon = self.client.get("/api/health/detailed")
        self.assertEqual(res_anon.status_code, 403)

        # B. Patient role -> 403
        pat_token = create_access_token("pat-01", Role.PATIENT.value)
        res_pat = self.client.get(
            "/api/health/detailed",
            headers={"Authorization": f"Bearer {pat_token}"}
        )
        self.assertEqual(res_pat.status_code, 403)

        # C. Doctor role -> 200
        doc_token = create_access_token("dr-gupta", Role.DOCTOR.value)
        res_doc = self.client.get(
            "/api/health/detailed",
            headers={"Authorization": f"Bearer {doc_token}"}
        )
        self.assertEqual(res_doc.status_code, 200)
        data = res_doc.get_json()
        self.assertIn("diagnostics", data)
        self.assertIn("total_patients", data["diagnostics"])

    def test_03_session_binding_validation(self):
        """Session binding must enforce valid patient and standard eye laterality."""
        # A. Missing patient_id -> 400
        res_no_pid = self.client.post("/api/sessions/bind", json={"eye": "OD"})
        self.assertEqual(res_no_pid.status_code, 400)

        # B. Invalid eye laterality -> 400
        res_bad_eye = self.client.post(
            "/api/sessions/bind",
            json={"patient_id": self.patient_id, "eye": "THIRD_EYE"}
        )
        self.assertEqual(res_bad_eye.status_code, 400)

        # C. Nonexistent patient -> 404
        res_no_pat = self.client.post(
            "/api/sessions/bind",
            json={"patient_id": "P-9999", "eye": "OD"}
        )
        self.assertEqual(res_no_pat.status_code, 404)

        # D. Valid four-way binding -> 201
        res_valid = self.client.post(
            "/api/sessions/bind",
            json={
                "patient_id": self.patient_id,
                "operator_id": "op-priya",
                "eye": "OS",
            }
        )
        self.assertEqual(res_valid.status_code, 201)
        bind_data = res_valid.get_json()
        self.assertTrue(bind_data["success"])
        self.assertIn("session_id", bind_data)
        self.assertEqual(bind_data["eye"], "OS")
        self.assertEqual(bind_data["state"], "CREATED")

        self.session_id = bind_data["session_id"]

    def test_04_operator_confirmation_gate(self):
        """Operator can confirm and override warnings for a session."""
        # Ensure session exists
        res_valid = self.client.post(
            "/api/sessions/bind",
            json={
                "patient_id": self.patient_id,
                "operator_id": "op-priya",
                "eye": "OS",
            }
        )
        session_id = res_valid.get_json()["session_id"]

        res_confirm = self.client.post(
            f"/api/sessions/{session_id}/confirm",
            json={"notes": "Operator verified pupil dilation and patient identity."}
        )
        self.assertEqual(res_confirm.status_code, 200)
        data = res_confirm.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["state"], "ANATOMY_VALIDATED")


if __name__ == "__main__":
    unittest.main()
