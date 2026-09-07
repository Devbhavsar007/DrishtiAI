"""Comprehensive Adversarial and Security Hardening Verification Suite for DrishtiAI.

Covers:
1. Header & Body Authentication Spoofing (Zero-Trust)
2. Directory Traversal & Unauthenticated Static File Access
3. Triage Status Manipulation & Database Identity Binding
4. Doctor Review Actor Impersonation
5. Out-of-Bounds & Malformed Patient Clinical Metrics
6. Offline Sync Batch Replay Idempotency
7. Detector Fallback Honesty & Safety Gating
8. Missing != Zero Glycemic Risk Invariants
9. Edge Device HMAC Authentication & Anti-Replay Bounds
"""

import unittest
import uuid
import time
import os
import json
import hmac
import hashlib
from app import app
from engine.security.auth import (
    Role,
    create_access_token,
    verify_token,
    create_edge_signature,
    verify_edge_signature,
)
from config import EDGE_DEVICE_SECRET
from database import (
    create_patient,
    update_patient,
    delete_patient,
    save_scan,
    get_db,
    get_doctor_review,
    reconcile_sync_batch,
    save_doctor_review,
)
from engine.detector import _mock_prediction, validate_model_output, predict
from engine.safety.decision_engine import SafetyDecisionEngine
from engine.safety.image_validator import ImageValidationResult
from engine.clinical.safety import evaluate_safety
from engine.clinical.progression import assess_progression_risk


class TestAdversarialSecurityHardening(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.patient = create_patient(
            name="Security Hardening Subject",
            age=52,
            gender="Female",
            diabetes_duration=8,
            sugar_level=180.0,
            hba1c=8.2,
            notes="Subject for adversarial security tests",
        )
        self.patient_id = self.patient["id"]
        self.scan_id = f"adv-scan-{uuid.uuid4().hex[:8]}"

        save_scan(
            scan_id=self.scan_id,
            patient_id=self.patient_id,
            detection_result={
                "stage": 2,
                "stage_name": "Moderate NPDR",
                "confidence": 84.5,
                "severity": "moderate",
                "color": "#F59E0B",
            },
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={"original": "test.png"},
            processing_time=0.25,
        )

    def tearDown(self):
        try:
            delete_patient(self.patient_id)
        except Exception:
            pass
        with get_db() as conn:
            conn.execute("DELETE FROM doctor_reviews WHERE scan_id = ?", (self.scan_id,))
            conn.execute("DELETE FROM sync_events WHERE entity_id LIKE 'adv-%'")
            conn.commit()

    def test_01_spoofed_role_header_rejected_unauthenticated(self):
        """Attacker sends X-Drishti-Role: ADMIN without a valid token. Must return 401."""
        res = self.client.get("/api/dashboard", headers={"X-Drishti-Role": "ADMIN"})
        self.assertEqual(res.status_code, 401, "Spoofed X-Drishti-Role must not bypass authentication")

    def test_02_body_doctor_id_backdoor_rejected_unauthenticated(self):
        """Attacker sends doctor review with doctor_id in body but no Bearer token. Must return 401."""
        res = self.client.post(
            f"/api/scans/{self.scan_id}/doctor-review",
            json={
                "doctor_id": "dr-attacker",
                "decision": "APPROVED",
                "adjusted_stage": 0,
                "approved_priority": "ROUTINE",
                "clinical_notes": "Attempted forged doctor approval",
            },
        )
        self.assertEqual(res.status_code, 401, "Body doctor_id must not grant unauthenticated access")

    def test_03_unauthenticated_results_access_rejected(self):
        """Unauthenticated request to /results/<filename> must return 401."""
        res = self.client.get("/results/test.png")
        self.assertEqual(res.status_code, 401, "Static results must not be accessible unauthenticated")

    def test_04_results_path_traversal_blocked(self):
        """Authenticated caller attempting directory traversal via /results must be blocked."""
        token = create_access_token("doc-1", Role.DOCTOR.value)
        headers = {"Authorization": f"Bearer {token}"}

        # Test double dot traversal attempts
        res1 = self.client.get("/results/../../app.py", headers=headers)
        self.assertIn(res1.status_code, [400, 403, 404])

        res2 = self.client.get("/results/..%2F..%2Fapp.py", headers=headers)
        self.assertIn(res2.status_code, [400, 403, 404])

    def test_05_triage_referral_client_tamper_rejected(self):
        """Client supplying doctor_review_present=True must be ignored if DB has no review."""
        token = create_access_token("hw-1", Role.HEALTH_WORKER.value)
        headers = {"Authorization": f"Bearer {token}"}

        # Ensure no review exists in DB
        self.assertIsNone(get_doctor_review(self.scan_id))

        res = self.client.post(
            f"/api/scans/{self.scan_id}/triage",
            json={
                "doctor_review_present": True,
                "doctor_decision": "APPROVED",
                "notes": "Client attempting to forge doctor review presence",
            },
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        referral = data.get("referral", {})
        # Referral must NOT be marked approved; must remain PENDING
        self.assertNotEqual(
            referral.get("status"),
            "APPROVED",
            "Referral status cannot be APPROVED without a canonical DB doctor review",
        )

    def test_06_doctor_impersonation_blocked(self):
        """Doctor Alice authenticates but submits a review with doctor_id='dr-bob'. Must return 403."""
        alice_token = create_access_token("dr-alice", Role.DOCTOR.value)
        res = self.client.post(
            f"/api/scans/{self.scan_id}/doctor-review",
            json={
                "doctor_id": "dr-bob",
                "decision": "APPROVED",
                "adjusted_stage": 2,
                "approved_priority": "ROUTINE",
                "clinical_notes": "Attempting to impersonate Dr. Bob",
            },
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        self.assertEqual(res.status_code, 403, "Doctor Alice must not be permitted to submit as Dr. Bob")
        self.assertIn("identity mismatch", res.get_json().get("error", "").lower())

    def test_07_patient_metrics_validation_bounds(self):
        """Database and API must reject impossible or dangerous physiological values."""
        # Age out of bounds
        with self.assertRaises(ValueError):
            create_patient("Bad Age Negative", age=-1, gender="Male")
        with self.assertRaises(ValueError):
            create_patient("Bad Age High", age=135, gender="Male")

        # Empty name
        with self.assertRaises(ValueError):
            create_patient("   ", age=45, gender="Female")

        # Sugar out of bounds
        with self.assertRaises(ValueError):
            create_patient("Bad Sugar Low", age=45, gender="Female", sugar_level=15.0)
        with self.assertRaises(ValueError):
            create_patient("Bad Sugar High", age=45, gender="Female", sugar_level=1200.0)

        # HbA1c out of bounds
        with self.assertRaises(ValueError):
            create_patient("Bad HbA1c Low", age=45, gender="Female", hba1c=2.5)
        with self.assertRaises(ValueError):
            create_patient("Bad HbA1c High", age=45, gender="Female", hba1c=25.0)

        # Diabetes duration out of bounds
        with self.assertRaises(ValueError):
            create_patient("Bad Duration", age=45, gender="Female", diabetes_duration=-2)

    def test_08_sync_batch_replay_idempotency(self):
        """Replaying identical sync events must not create duplicate entities or crash."""
        entity_id = f"adv-scan-{uuid.uuid4().hex[:8]}"
        sync_batch = [
            {
                "id": f"adv-evt-{uuid.uuid4().hex[:8]}",
                "device_id": "edge-pi-1",
                "entity_type": "scan",
                "entity_id": entity_id,
                "action": "CREATE",
                "version": 1,
                "payload": {
                    "patient_id": self.patient_id,
                    "stage": 1,
                    "confidence": 75.0,
                },
            }
        ]

        # First sync
        res1 = reconcile_sync_batch(sync_batch)
        self.assertEqual(res1["synced_count"], 1)
        self.assertEqual(res1["conflict_count"], 0)

        # Second sync with identical events (replay attack or network retry)
        res2 = reconcile_sync_batch(sync_batch)
        self.assertEqual(res2["conflict_count"], 0)

        # Idempotency check: verify that only 1 record exists in the ledger
        with get_db() as conn:
            cnt = conn.execute("SELECT COUNT(*) as cnt FROM sync_events WHERE entity_id = ?", (entity_id,)).fetchone()["cnt"]
            self.assertEqual(cnt, 1, "Duplicate sync events must not duplicate ledger records")

    def test_09_detector_honest_failure_and_safety_gating(self):
        """When detector runs in fallback/unclassified mode, safety engine must flag MODEL_FALLBACK_ACTIVE."""
        mock_pred = _mock_prediction()
        # Verify mock prediction contract
        self.assertEqual(mock_pred["status"], "UNABLE_TO_CLASSIFY")
        self.assertFalse(mock_pred["model_available"])
        self.assertTrue(mock_pred["_deterministic_fallback"])

        # Feed to unified evaluate_safety (which delegates to SafetyDecisionEngine)
        decision = evaluate_safety(
            quality_assessment={"quality_score": 0.95, "decision": "ACCEPT"},
            primary_prediction=mock_pred,
        )

        # Safety engine must flag fallback and prevent automated clinical action
        self.assertIn("MODEL_FALLBACK_ACTIVE", decision.reasons)
        self.assertFalse(decision.clinical_action_allowed)
        self.assertTrue(decision.human_review_required)
        self.assertEqual(decision.automation_level, "HUMAN_REVIEW_REQUIRED")

    def test_10_missing_vs_zero_glycemic_risk(self):
        """None sugar/hba1c must NOT be treated as 0.0 (which would falsify normal glycemic risk)."""
        scan = {"id": "scan-curr", "stage": 2, "confidence": 85.0}
        prev_scans = [{"id": "scan-prev", "stage": 1, "confidence": 88.0}]

        patient_none = {
            "age": 60,
            "gender": "Male",
            "diabetes_duration": 15,
            "sugar_level": None,
            "hba1c": None,
        }
        patient_high = {
            "age": 60,
            "gender": "Male",
            "diabetes_duration": 15,
            "sugar_level": 250.0,
            "hba1c": 9.5,
        }

        risk_none = assess_progression_risk(
            current_scan=scan,
            previous_scans=prev_scans,
            patient_profile=patient_none,
        )
        risk_high = assess_progression_risk(
            current_scan=scan,
            previous_scans=prev_scans,
            patient_profile=patient_high,
        )

        # High glycemia must elevate risk over missing metrics
        self.assertGreater(
            risk_high["predicted_risk"]["six_month_risk"],
            risk_none["predicted_risk"]["six_month_risk"],
        )
        self.assertIn(
            "poor glycemic control (HbA1c >= 9.0)",
            risk_high["predicted_risk"]["supporting_factors"],
        )
        self.assertNotIn(
            "poor glycemic control (HbA1c >= 9.0)",
            risk_none["predicted_risk"]["supporting_factors"],
        )

    def test_11_edge_device_hmac_authentication_and_anti_replay(self):
        """Valid HMAC signature succeeds; expired or tampered signatures fail with 401."""
        device_id = "edge-pi-adversarial"
        role = Role.HEALTH_WORKER.value
        now = int(time.time())

        # Valid signature function check
        sig = create_edge_signature(device_id, role, now, EDGE_DEVICE_SECRET)
        self.assertTrue(verify_edge_signature(device_id, role, now, sig, EDGE_DEVICE_SECRET))

        # Expired signature (drift > 300s)
        expired_ts = now - 400
        expired_sig = create_edge_signature(device_id, role, expired_ts, EDGE_DEVICE_SECRET)
        self.assertFalse(verify_edge_signature(device_id, role, expired_ts, expired_sig, EDGE_DEVICE_SECRET))

        # Future drift > 300s
        future_ts = now + 400
        future_sig = create_edge_signature(device_id, role, future_ts, EDGE_DEVICE_SECRET)
        self.assertFalse(verify_edge_signature(device_id, role, future_ts, future_sig, EDGE_DEVICE_SECRET))

        # Tampered signature
        tampered_sig = sig[:-4] + "dead"
        self.assertFalse(verify_edge_signature(device_id, role, now, tampered_sig, EDGE_DEVICE_SECRET))

        # Test against actual API endpoint with edge headers
        valid_headers = {
            "X-Drishti-Edge-Device-Id": device_id,
            "X-Drishti-Edge-Role": role,
            "X-Drishti-Edge-Timestamp": str(now),
            "X-Drishti-Edge-Signature": sig,
        }
        res = self.client.get("/api/auth/me", headers=valid_headers)
        self.assertEqual(res.status_code, 200)
        actor = res.get_json()["actor"]
        self.assertEqual(actor["actor_id"], device_id)
        self.assertEqual(actor["actor_role"], role)

        # Test against API with expired signature (rejected with 401)
        expired_headers = {
            "X-Drishti-Edge-Device-Id": device_id,
            "X-Drishti-Edge-Role": role,
            "X-Drishti-Edge-Timestamp": str(expired_ts),
            "X-Drishti-Edge-Signature": expired_sig,
        }
        res_expired = self.client.get("/api/auth/me", headers=expired_headers)
        self.assertEqual(res_expired.status_code, 401)


if __name__ == "__main__":
    unittest.main()
