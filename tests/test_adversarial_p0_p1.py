"""
Adversarial Verification Suite for P0 and P1 Production Hardening in DrishtiAI.

Covers:
1. P0 Privilege Escalation Prevention (/api/auth/login requires secrets for ADMIN and DOCTOR)
2. P0 Zero-Trust Endpoint Protection (/api/sessions/bind, /confirm, /api/ingest/validate require auth)
3. P0 Identity Anti-Spoofing (Actor ID strictly derived from JWT claims, ignoring client payload)
4. P0 Broken Object-Level Authorization / IDOR Protection (Patients cannot access other patients' scans, timeline, or artifacts)
5. P1 State Machine Illegal Transition Defense (Blocks lifecycle bypasses)
6. P1 Security Headers & Request Correlation (Permissions-Policy allows self camera/mic, X-Request-ID trace)
"""

import io
import json
import unittest
import uuid
from PIL import Image
import numpy as np

from app import app, limiter
from config import ADMIN_SECRET, DOCTOR_SECRET
from engine.security.auth import Role, create_access_token, verify_role_credentials
from engine.safety.state_machine import ScreeningState, InvalidStateTransitionError
from database import (
    create_patient,
    delete_patient,
    save_scan,
    create_or_update_screening_session,
    get_screening_session,
    update_screening_session_state,
    get_db,
)


class TestAdversarialP0P1Hardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.limiter_enabled = getattr(limiter, "enabled", True)
        limiter.enabled = False
        cls.client = app.test_client()

        # Create two separate test patients for IDOR verification
        cls.pat_a = create_patient(
            name="Patient Alice",
            age=45,
            gender="Female",
            diabetes_duration=5,
            sugar_level=140.0,
            hba1c=7.0,
            notes="Patient A record",
        )
        cls.pat_a_id = cls.pat_a["id"]

        cls.pat_b = create_patient(
            name="Patient Bob",
            age=58,
            gender="Male",
            diabetes_duration=12,
            sugar_level=180.0,
            hba1c=8.5,
            notes="Patient B confidential record",
        )
        cls.pat_b_id = cls.pat_b["id"]

        cls.scan_b_id = f"scan-b-{uuid.uuid4().hex[:6]}"
        save_scan(
            scan_id=cls.scan_b_id,
            patient_id=cls.pat_b_id,
            detection_result={"stage": 2, "confidence": 92.0, "stage_name": "Moderate NPDR"},
            heatmap_analysis={},
            vessel_stats={},
            report={"findings": "Microaneurysms detected"},
            image_paths={"original": f"{cls.scan_b_id}_scan.png"},
            processing_time=0.4,
        )

        # Tokens
        cls.token_pat_a = create_access_token(cls.pat_a_id, Role.PATIENT.value)
        cls.token_pat_b = create_access_token(cls.pat_b_id, Role.PATIENT.value)
        cls.token_hw = create_access_token("hw-ashok", Role.HEALTH_WORKER.value)
        cls.token_doctor = create_access_token("dr-sharma", Role.DOCTOR.value)

    @classmethod
    def tearDownClass(cls):
        limiter.enabled = cls.limiter_enabled
        delete_patient(cls.pat_a_id)
        delete_patient(cls.pat_b_id)
        with get_db() as conn:
            conn.execute("DELETE FROM scans WHERE id = ?", (cls.scan_b_id,))
            conn.commit()

    # -------------------------------------------------------------------------
    # 1. P0 Privilege Escalation Defenses
    # -------------------------------------------------------------------------
    def test_01_privileged_role_login_without_secret_rejected(self):
        """Attacker sending role=ADMIN or DOCTOR without credentials receives 401."""
        # A. Attacker asks for ADMIN without secret -> 401
        res_admin = self.client.post("/api/auth/login", json={"user_id": "attacker", "role": "ADMIN"})
        self.assertEqual(res_admin.status_code, 401)
        self.assertFalse(res_admin.get_json()["success"])
        self.assertIn("Privileged role", res_admin.get_json()["error"])

        # B. Attacker asks for DOCTOR without secret -> 401
        res_doc = self.client.post("/api/auth/login", json={"user_id": "attacker", "role": "DOCTOR"})
        self.assertEqual(res_doc.status_code, 401)
        self.assertFalse(res_doc.get_json()["success"])

        # C. Attacker provides wrong secret -> 401
        res_wrong = self.client.post(
            "/api/auth/login",
            json={"user_id": "attacker", "role": "ADMIN", "secret": "wrong-secret-123"}
        )
        self.assertEqual(res_wrong.status_code, 401)

    def test_02_privileged_role_login_with_valid_secret_granted(self):
        """Legitimate admins and doctors providing valid secrets receive tokens."""
        res_admin = self.client.post(
            "/api/auth/login",
            json={"user_id": "sysadmin-01", "role": "ADMIN", "secret": ADMIN_SECRET}
        )
        self.assertEqual(res_admin.status_code, 200)
        self.assertTrue(res_admin.get_json()["success"])
        self.assertEqual(res_admin.get_json()["user"]["role"], "ADMIN")

        res_doc = self.client.post(
            "/api/auth/login",
            json={"user_id": "dr-natarajan", "role": "DOCTOR", "secret": DOCTOR_SECRET}
        )
        self.assertEqual(res_doc.status_code, 200)
        self.assertTrue(res_doc.get_json()["success"])
        self.assertEqual(res_doc.get_json()["user"]["role"], "DOCTOR")

    def test_03_non_privileged_roles_login_without_secret_permitted(self):
        """Front-line health workers and patients can establish sessions without admin secrets."""
        res_hw = self.client.post(
            "/api/auth/login",
            json={"user_id": "hw-anita", "role": "HEALTH_WORKER"}
        )
        self.assertEqual(res_hw.status_code, 200)
        self.assertEqual(res_hw.get_json()["user"]["role"], "HEALTH_WORKER")

    # -------------------------------------------------------------------------
    # 2. P0 Zero-Trust Endpoint Protection
    # -------------------------------------------------------------------------
    def test_04_session_and_ingest_endpoints_fail_closed_without_auth(self):
        """Unauthenticated requests to session binding, get, confirm, and ingest validate fail with 401."""
        # Bind
        res_bind = self.client.post("/api/sessions/bind", json={"patient_id": self.pat_a_id, "eye": "OD"})
        self.assertEqual(res_bind.status_code, 401)

        # Get
        res_get = self.client.get("/api/sessions/sess-any")
        self.assertEqual(res_get.status_code, 401)

        # Confirm
        res_confirm = self.client.post("/api/sessions/sess-any/confirm", json={"notes": "override"})
        self.assertEqual(res_confirm.status_code, 401)

        # Ingest Validate
        img_bytes = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
        res_ingest = self.client.post(
            "/api/ingest/validate",
            data={"image": (img_bytes, "test.jpg")},
            content_type="multipart/form-data"
        )
        self.assertEqual(res_ingest.status_code, 401)

    # -------------------------------------------------------------------------
    # 3. P0 Operator Identity Anti-Spoofing
    # -------------------------------------------------------------------------
    def test_05_operator_identity_strictly_bound_to_jwt(self):
        """Client-supplied operator_id is ignored in favor of verified JWT sub claim."""
        # Health worker token with sub="hw-ashok" attempts to claim operator_id="dr-evil"
        headers = {"Authorization": f"Bearer {self.token_hw}"}
        res = self.client.post(
            "/api/sessions/bind",
            json={
                "patient_id": self.pat_a_id,
                "eye": "OS",
                "operator_id": "dr-evil-impersonator"
            },
            headers=headers
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        # Must match JWT identity 'hw-ashok', NOT spoofed client string
        self.assertEqual(data["operator_id"], "hw-ashok")

    # -------------------------------------------------------------------------
    # 4. P0 Broken Object-Level Authorization (IDOR) Protection
    # -------------------------------------------------------------------------
    def test_06_patient_cannot_access_another_patients_records(self):
        """Patient Alice cannot access Patient Bob's record, timeline, or scan."""
        headers_alice = {"Authorization": f"Bearer {self.token_pat_a}"}

        # A. Patient detail IDOR
        res_detail = self.client.get(f"/api/patients/{self.pat_b_id}", headers=headers_alice)
        self.assertEqual(res_detail.status_code, 403)

        # B. Patient timeline IDOR
        res_timeline = self.client.get(f"/api/patients/{self.pat_b_id}/timeline", headers=headers_alice)
        self.assertEqual(res_timeline.status_code, 403)

        # C. Scan detail IDOR
        res_scan = self.client.get(f"/api/scans/{self.scan_b_id}", headers=headers_alice)
        self.assertEqual(res_scan.status_code, 403)

    def test_07_patient_can_access_own_records_and_clinicians_can_access_both(self):
        """Patient Alice can access her own record; Doctor can access all patients."""
        headers_alice = {"Authorization": f"Bearer {self.token_pat_a}"}
        res_own = self.client.get(f"/api/patients/{self.pat_a_id}", headers=headers_alice)
        self.assertEqual(res_own.status_code, 200)
        self.assertEqual(res_own.get_json()["patient"]["id"], self.pat_a_id)

        # Doctor has clinical access
        headers_doc = {"Authorization": f"Bearer {self.token_doctor}"}
        res_doc = self.client.get(f"/api/patients/{self.pat_b_id}", headers=headers_doc)
        self.assertEqual(res_doc.status_code, 200)
        self.assertEqual(res_doc.get_json()["patient"]["id"], self.pat_b_id)

    # -------------------------------------------------------------------------
    # 5. P1 State Machine Illegal Transition Enforcement
    # -------------------------------------------------------------------------
    def test_08_illegal_session_transition_rejected(self):
        """Direct illegal lifecycle transition raises InvalidStateTransitionError."""
        sess_id = f"sess-test-{uuid.uuid4().hex[:6]}"
        create_or_update_screening_session(
            session_id=sess_id,
            patient_id=self.pat_a_id,
            operator_id="hw-ashok",
            eye="OD",
            current_state=ScreeningState.CREATED,
        )

        # Attempting CREATED -> SYNCED directly without screening is illegal
        with self.assertRaises(InvalidStateTransitionError):
            update_screening_session_state(
                session_id=sess_id,
                new_state=ScreeningState.SYNCED,
                actor_id="hw-ashok",
            )

    # -------------------------------------------------------------------------
    # 6. P1 Security Headers & Request Tracing
    # -------------------------------------------------------------------------
    def test_09_permissions_policy_allows_camera_and_x_request_id_present(self):
        """Response headers allow same-origin camera/microphone for fundus capture and attach X-Request-ID."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)

        # Permissions Policy allows self for camera and microphone
        pp = res.headers.get("Permissions-Policy", "")
        self.assertIn("camera=(self)", pp)
        self.assertIn("microphone=(self)", pp)

        # X-Request-ID present
        req_id = res.headers.get("X-Request-ID", "")
        self.assertTrue(len(req_id) > 0)
        self.assertTrue(req_id.startswith("req-"))

    # -------------------------------------------------------------------------
    # 7. P2 & P3 Hardening: Reason Codes, Concurrency, PHI Cache-Control
    # -------------------------------------------------------------------------
    def test_10_safety_decision_engine_dual_codes_interoperability(self):
        """Unified safety engine preserves canonical and alias reason codes."""
        from engine.clinical.safety import evaluate_safety
        decision = evaluate_safety(
            quality_assessment={"decision": "ACCEPT", "quality_score": 0.9},
            primary_prediction={"stage": 1, "confidence": 55.0},  # Low confidence < 70%
        )
        self.assertEqual(decision.status, "UNCERTAIN")
        self.assertIn("LOW_CONFIDENCE", decision.reasons)
        self.assertIn("LOW_MODEL_CONFIDENCE", decision.reasons)

    def test_11_concurrent_patient_id_allocation_atomicity(self):
        """Concurrent patient creations across threads produce unique, collision-free IDs."""
        import concurrent.futures
        from database import create_patient, delete_patient

        created_pids = []

        def create_worker(idx):
            p = create_patient(
                name=f"Concurrent Patient {idx}",
                age=40 + idx,
                gender="Other",
                diabetes_duration=2,
                sugar_level=120.0,
                hba1c=6.5,
            )
            return p["id"]

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(create_worker, i) for i in range(12)]
                created_pids = [f.result() for f in futures]

            # All created patient IDs must be distinct
            self.assertEqual(len(created_pids), len(set(created_pids)))
            for pid in created_pids:
                self.assertTrue(pid.startswith("P-"))
        finally:
            for pid in created_pids:
                delete_patient(pid)

    def test_12_doctor_review_identity_enforcement(self):
        """Doctor review forbids signed-in clinician from spoofing another doctor's ID."""
        headers_doc = {"Authorization": f"Bearer {self.token_doctor}"}  # sub="dr-sharma"

        # Attempt to sign off as Dr. Gupta -> 403
        res_spoof = self.client.post(
            f"/api/scans/{self.scan_b_id}/doctor-review",
            json={"doctor_id": "dr-gupta", "decision": "APPROVED"},
            headers=headers_doc,
        )
        self.assertEqual(res_spoof.status_code, 403)
        self.assertIn("Identity mismatch", res_spoof.get_json()["error"])

    def test_13_referral_dual_naming_parity(self):
        """Referral policy returns both camelCase and snake_case field keys."""
        from engine.clinical.referral import decide_referral
        ref = decide_referral(
            screening={"stage": 3, "confidence": 88.0},
            progression={"predicted_risk": {"risk_category": "HIGH"}},
            doctor_review_present=False,
        )
        self.assertIn("reasonCodes", ref)
        self.assertIn("reason_codes", ref)
        self.assertEqual(ref["reasonCodes"], ref["reason_codes"])
        self.assertIn("humanReviewRequired", ref)
        self.assertIn("human_review_required", ref)

    def test_14_phi_cache_control_headers_enforced(self):
        """PHI and scan endpoints inject strict anti-caching headers to protect patient privacy."""
        headers_doc = {"Authorization": f"Bearer {self.token_doctor}"}
        res = self.client.get(f"/api/patients/{self.pat_a_id}", headers=headers_doc)
        self.assertEqual(res.status_code, 200)

        cache_control = res.headers.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("no-cache", cache_control)
        self.assertEqual(res.headers.get("Pragma"), "no-cache")


if __name__ == "__main__":
    unittest.main()
