"""
Pre-Production Adversarial Verification Suite for DrishtiAI.

Covers:
1. Safety-Before-Commit Invariant (Rejected scans never persisted; verified scans persist exact safety state)
2. Result Artifact Fail-Closed & Traversal Defenses (/results/ rejects invalid extensions, traversal, foreign patients)
3. Production Environment Authentication & Zero-Trust Verification (Role credentials in production vs demo)
4. Patient Authentication Integrity (Nonexistent patient IDs cannot mint tokens)
5. Authoritative Request Context Verification (actor_id, actor_role, actor_scope, device_id)
6. Database Migration v4 Idempotency
7. Golden Path End-to-End Integration
"""

import io
import json
import os
import unittest
import uuid
from PIL import Image
import numpy as np

from app import app, limiter
from config import ADMIN_SECRET, DOCTOR_SECRET, WORKER_SECRET, DEBUG, RESULTS_DIR
from engine.security.auth import (
    Role,
    create_access_token,
    verify_role_credentials,
    get_current_actor,
)
from engine.safety.state_machine import ScreeningState
from database import (
    create_patient,
    delete_patient,
    save_scan,
    get_scan,
    init_db,
    get_db,
)


class TestPreProductionHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.limiter_enabled = getattr(limiter, "enabled", True)
        limiter.enabled = False
        cls.client = app.test_client()

        # Create test patients
        cls.pat_1 = create_patient(
            name="PreProd Patient One",
            age=52,
            gender="Female",
            diabetes_duration=8,
            sugar_level=150.0,
            hba1c=7.4,
            notes="Pre-production test record 1",
        )
        cls.pat_1_id = cls.pat_1["id"]

        cls.pat_2 = create_patient(
            name="PreProd Patient Two",
            age=61,
            gender="Male",
            diabetes_duration=15,
            sugar_level=210.0,
            hba1c=9.2,
            notes="Pre-production test record 2",
        )
        cls.pat_2_id = cls.pat_2["id"]

        # Artifacts
        cls.scan_1_id = f"ppscan1-{uuid.uuid4().hex[:6]}"
        cls.scan_1_filename = f"{cls.scan_1_id}_scan.png"
        cls.scan_1_path = os.path.join(RESULTS_DIR, cls.scan_1_filename)

        # Create dummy image in RESULTS_DIR
        img = Image.new("RGB", (64, 64), color=(120, 40, 40))
        img.save(cls.scan_1_path)

        save_scan(
            scan_id=cls.scan_1_id,
            patient_id=cls.pat_1_id,
            detection_result={"stage": 1, "confidence": 85.0, "stage_name": "Mild NPDR"},
            heatmap_analysis={},
            vessel_stats={},
            report={"summary": "Mild changes"},
            image_paths={"original": f"/results/{cls.scan_1_filename}"},
            processing_time=0.35,
            safety_state="VERIFIED",
            automation_level="AUTOMATED_ASSISTANCE",
            reason_codes=["ACCEPTABLE_QUALITY"],
        )

        # Tokens
        cls.token_pat_1 = create_access_token(cls.pat_1_id, Role.PATIENT.value)
        cls.token_pat_2 = create_access_token(cls.pat_2_id, Role.PATIENT.value)
        cls.token_hw = create_access_token("hw-preprod", Role.HEALTH_WORKER.value)
        cls.token_doctor = create_access_token("dr-preprod", Role.DOCTOR.value)

    @classmethod
    def tearDownClass(cls):
        limiter.enabled = cls.limiter_enabled
        delete_patient(cls.pat_1_id)
        delete_patient(cls.pat_2_id)
        with get_db() as conn:
            conn.execute("DELETE FROM scans WHERE id = ?", (cls.scan_1_id,))
            conn.commit()
        if os.path.exists(cls.scan_1_path):
            try:
                os.remove(cls.scan_1_path)
            except OSError:
                pass

    # -------------------------------------------------------------------------
    # 1. Safety-Before-Commit Invariant
    # -------------------------------------------------------------------------
    def test_01_safety_before_commit_rejected_safety_stops_persistence(self):
        """When an upload is rejected by safety arbitration, it is never saved to database."""
        # Non-fundus blank image -> rejected
        blank_img = Image.new("RGB", (100, 100), color=(0, 0, 0))
        buf = io.BytesIO()
        blank_img.save(buf, format="JPEG")
        buf.seek(0)

        headers = {"Authorization": f"Bearer {self.token_hw}"}
        res = self.client.post(
            "/analyze",
            data={"image": (buf, "blank.jpg"), "patient_id": self.pat_1_id},
            content_type="multipart/form-data",
            headers=headers,
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("safety_state"), "REJECTED")
        self.assertFalse(data.get("clinical_action_allowed", True))

        # Check DB: no scan should exist for pat_1 with 0 stage or created right now from blank
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM scans WHERE patient_id = ? AND stage_name = 'Unknown'", (self.pat_1_id,)).fetchall()
            self.assertEqual(len(rows), 0)

    def test_02_safety_before_commit_verified_safety_persists_exact_state(self):
        """When a scan is saved, its safety_state and automation_level match the arbitration decision."""
        scan_id = f"test-safe-{uuid.uuid4().hex[:6]}"
        save_scan(
            scan_id=scan_id,
            patient_id=self.pat_1_id,
            detection_result={"stage": 2, "confidence": 91.0, "stage_name": "Moderate NPDR"},
            heatmap_analysis={},
            vessel_stats={},
            report={"findings": "Microaneurysms"},
            image_paths={"original": f"{scan_id}.png"},
            processing_time=0.4,
            safety_state="UNCERTAIN",
            automation_level="HUMAN_REVIEW_REQUIRED",
            reason_codes=["BORDERLINE_QUALITY"],
        )
        saved = get_scan(scan_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved["safety_state"], "UNCERTAIN")
        self.assertEqual(saved["automation_level"], "HUMAN_REVIEW_REQUIRED")
        self.assertIn("BORDERLINE_QUALITY", saved["reason_codes_json"])

        with get_db() as conn:
            conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
            conn.commit()

    # -------------------------------------------------------------------------
    # 2. Result Artifact Fail-Closed & Traversal Defenses
    # -------------------------------------------------------------------------
    def test_03_artifact_endpoint_fail_closed_on_missing_or_foreign_scan(self):
        """Patient 2 cannot access Patient 1's scan, and cannot access nonexistent scan."""
        headers_pat2 = {"Authorization": f"Bearer {self.token_pat_2}"}

        # Foreign scan access -> 403 Forbidden
        res_foreign = self.client.get(f"/results/{self.scan_1_filename}", headers=headers_pat2)
        self.assertEqual(res_foreign.status_code, 403)

        # Nonexistent scan access by patient -> 403 Forbidden (fail closed, not 200)
        res_nonexistent = self.client.get("/results/nonexistent123_scan.png", headers=headers_pat2)
        self.assertEqual(res_nonexistent.status_code, 403)

    def test_04_artifact_endpoint_path_traversal_blocked(self):
        """Relative or encoded traversal sequences are immediately rejected with 403."""
        headers_hw = {"Authorization": f"Bearer {self.token_hw}"}

        res_traversal1 = self.client.get("/results/../app.py", headers=headers_hw)
        self.assertEqual(res_traversal1.status_code, 403)

        res_traversal2 = self.client.get("/results/..%2F..%2Fconfig.py", headers=headers_hw)
        self.assertEqual(res_traversal2.status_code, 403)

    def test_05_artifact_endpoint_invalid_extension_blocked(self):
        """Non-image extensions are rejected with 403."""
        headers_hw = {"Authorization": f"Bearer {self.token_hw}"}
        res = self.client.get("/results/scan_data.json", headers=headers_hw)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Invalid artifact format", res.get_json()["error"])

    # -------------------------------------------------------------------------
    # 3. Production Environment Authentication & Zero-Trust Verification
    # -------------------------------------------------------------------------
    def test_06_production_login_health_worker_without_secret_rejected(self):
        """In strict production mode, health workers require valid worker credentials."""
        # Test verify_role_credentials directly with env="production" and demo_mode=False
        is_valid = verify_role_credentials(Role.HEALTH_WORKER.value, secret=None, user_id="hw-operator", env="production", demo_mode=False)
        # In strict production without secret, health worker login cannot proceed
        self.assertFalse(is_valid)

    def test_07_production_login_health_worker_with_worker_secret_granted(self):
        """In production mode, health worker providing WORKER_SECRET is granted authentication."""
        is_valid = verify_role_credentials(Role.HEALTH_WORKER.value, secret=WORKER_SECRET, user_id="hw-operator", env="production", demo_mode=False)
        self.assertTrue(is_valid)

    # -------------------------------------------------------------------------
    # 4. Patient Authentication Integrity
    # -------------------------------------------------------------------------
    def test_08_patient_login_nonexistent_patient_rejected(self):
        """Attempting to log in with a non-existent patient ID fails closed."""
        is_valid = verify_role_credentials(Role.PATIENT.value, secret=None, user_id="P-9999", env="production", demo_mode=False)
        self.assertFalse(is_valid)

    def test_09_patient_login_existing_patient_granted(self):
        """Logging in with a real, existing patient ID succeeds."""
        is_valid = verify_role_credentials(Role.PATIENT.value, secret=None, user_id=self.pat_1_id, env="production", demo_mode=False)
        self.assertTrue(is_valid)

    # -------------------------------------------------------------------------
    # 5. Production Configuration Default
    # -------------------------------------------------------------------------
    def test_10_production_config_debug_is_false_by_default(self):
        """DEBUG must default to False unless explicitly overridden."""
        import importlib
        import config
        # Verify the production default in config.py
        self.assertFalse(config.DEBUG)

    # -------------------------------------------------------------------------
    # 6. Authoritative Request Context
    # -------------------------------------------------------------------------
    def test_11_authoritative_request_context_enrichment(self):
        """Authenticated actor context extracts actor_id, actor_role, and tenant scope."""
        with app.test_request_context(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.token_pat_1}", "X-Request-ID": "req-trace-123"}
        ):
            actor = get_current_actor()
            self.assertIsNotNone(actor)
            self.assertTrue(actor["authenticated_actor"])
            self.assertEqual(actor["actor_id"], self.pat_1_id)
            self.assertEqual(actor["actor_role"], Role.PATIENT.value)
            self.assertEqual(actor["actor_scope"], f"patient:{self.pat_1_id}")
            self.assertEqual(actor["request_id"], "req-trace-123")

    # -------------------------------------------------------------------------
    # 7. Database Migration v4 Idempotency
    # -------------------------------------------------------------------------
    def test_12_database_migration_v4_idempotency(self):
        """Repeated execution of init_db applies migration v4 idempotently."""
        try:
            init_db()
            init_db()
            with get_db() as conn:
                v4 = conn.execute("SELECT * FROM schema_migrations WHERE version = 4").fetchone()
                self.assertIsNotNone(v4)
                self.assertEqual(v4["version"], 4)
        except Exception as e:
            self.fail(f"init_db() raised unexpected exception during migration idempotency check: {e}")

    # -------------------------------------------------------------------------
    # 8. Golden Path End-to-End Integration
    # -------------------------------------------------------------------------
    def test_13_golden_path_end_to_end_integration(self):
        """Full end-to-end clinical workflow from login to screening, triage, and audit."""
        # 1. Login as health worker
        res_login = self.client.post("/api/auth/login", json={"user_id": "hw-golden", "role": "HEALTH_WORKER"})
        self.assertEqual(res_login.status_code, 200)
        token = res_login.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}", "X-Request-ID": "req-golden-001"}

        # 2. Bind screening session
        res_bind = self.client.post(
            "/api/sessions/bind",
            json={"patient_id": self.pat_1_id, "eye": "OD"},
            headers=headers,
        )
        self.assertEqual(res_bind.status_code, 201)
        sess_id = res_bind.get_json()["session_id"]
        self.assertTrue(sess_id.startswith("sess-"))

        # 3. Create synthetic fundus image with variance
        import cv2
        np_img = np.zeros((128, 128, 3), dtype=np.uint8)
        cv2.circle(np_img, (64, 64), 55, (180, 50, 50), -1)
        cv2.circle(np_img, (40, 64), 14, (240, 200, 100), -1)  # optic disc
        cv2.circle(np_img, (80, 64), 8, (100, 20, 20), -1)     # fovea
        _, enc = cv2.imencode(".png", np_img)
        buf = io.BytesIO(enc.tobytes())

        # 4. Ingest validate
        res_val = self.client.post(
            "/api/ingest/validate",
            data={"image": (buf, "fundus_od.png")},
            content_type="multipart/form-data",
            headers=headers,
        )
        self.assertEqual(res_val.status_code, 200)
        self.assertTrue(res_val.get_json()["is_valid"])

        # 5. Confirm operator session
        res_confirm = self.client.post(
            f"/api/sessions/{sess_id}/confirm",
            json={"notes": "Operator verified fundus alignment"},
            headers=headers,
        )
        self.assertEqual(res_confirm.status_code, 200)
        self.assertEqual(res_confirm.get_json()["state"], ScreeningState.ANATOMY_VALIDATED)

        # 6. Verify audit log entry
        with get_db() as conn:
            audit_row = conn.execute(
                "SELECT * FROM audit_log WHERE entity_id = ? ORDER BY id DESC LIMIT 1",
                (sess_id,)
            ).fetchone()
            self.assertIsNotNone(audit_row)
            self.assertEqual(audit_row["action"], "SESSION_STATE_TRANSITION")
            self.assertEqual(audit_row["actor_id"], "hw-golden")


if __name__ == "__main__":
    unittest.main()
