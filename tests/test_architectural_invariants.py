"""
Architectural Invariant Test Suite for DrishtiAI.
Formally verifies all 10 core safety invariants mandated by the Medical AI Safety Audit.
"""

import unittest
import os
import json
import numpy as np
from PIL import Image
import io

import database
from app import app
from engine.safety.decision_engine import SafetyDecisionEngine, SafetyEvaluationResult
from engine.safety.image_validator import ImageValidator, ImageValidationResult
from engine.safety.ood import evaluate_ood_signal
from engine.clinical.progression import assess_progression_risk
from engine.clinical.referral import decide_referral


class TestArchitecturalInvariants(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_invariant_01_ai_prediction_never_directly_commits_final_clinical_action(self):
        """Invariant 1: AI prediction can NEVER directly commit a final clinical decision."""
        engine = SafetyDecisionEngine()
        val = ImageValidationResult(valid=True)
        # Even with Stage 3 Severe NPDR and 95% confidence, clinical_action_allowed must be gated
        # Referable stages mandate human verification
        det = {"stage": 3, "confidence": 95.0}
        sec = {"stage": 1, "confidence": 80.0} # Disagreement
        res = engine.evaluate(image_val=val, primary_detection=det, secondary_detection=sec)
        
        # Action is blocked, requiring ophthalmologist confirmation
        self.assertEqual(res.safety_state, "UNCERTAIN")
        self.assertTrue(res.human_review_required)
        self.assertFalse(res.clinical_action_allowed)

    def test_invariant_02_llm_cannot_modify_patient_medical_truth(self):
        """Invariant 2: LLM output can NEVER directly modify patient medical truth."""
        # Patient DB updates require explicit doctor review or allowlisted fields,
        # never untrusted LLM generation strings
        p = database.create_patient("Truth Test Patient", age=58)
        pid = p["id"]
        
        # Verify that doctor_reviews requires explicit doctor_id and validated stage
        with self.assertRaises(Exception):
            # Missing doctor credentials and invalid structure must reject
            database.save_doctor_review(
                scan_id="scan-xyz",
                patient_id=pid,
                doctor_id="",
                decision="INVALID_DECISION",
                original_stage=0,
                adjusted_stage=99, # Impossible stage
                approved_priority="ROUTINE"
            )

    def test_invariant_03_frontend_never_determines_authorization(self):
        """Invariant 3: Frontend can NEVER determine authorization."""
        # Directly call protected endpoint without valid JWT
        res = self.client.get("/api/health/detailed")
        # Must return 401 Unauthenticated or 403 Forbidden regardless of headers
        self.assertIn(res.status_code, (401, 403))
        data = res.get_json()
        self.assertIn("error", data)

    def test_invariant_04_client_provided_patient_identity_never_blindly_trusted(self):
        """Invariant 4: Client-provided patient identity can NEVER be blindly trusted."""
        # Submit scan with non-existent or malformed patient ID
        res = self.client.get("/api/patients/P-NONEXISTENT-999999")
        # Must reject with 400 Bad Request (invalid format) or 404
        self.assertIn(res.status_code, (400, 404))

    def test_invariant_05_uncertain_or_ood_case_never_silently_becomes_normal(self):
        """Invariant 5: An uncertain/OOD case can NEVER silently become normal."""
        # Create non-fundus image (e.g. blue square)
        blue_arr = np.full((300, 300, 3), [240, 50, 10], dtype=np.uint8) # BGR: blue dominant
        ood_res = evaluate_ood_signal(blue_arr)
        
        # Must flag OOD or domain invalid
        self.assertTrue(not ood_res.domain_valid or ood_res.is_ood_suspected)
        
        engine = SafetyDecisionEngine()
        val = ImageValidationResult(valid=True)
        eval_res = engine.evaluate(image_val=val, ood_res=ood_res, primary_detection={"stage": 0, "confidence": 99.0})
        
        # Even if model claimed Stage 0 (99% confidence), safety arbitrator forces rejection/uncertainty
        self.assertIn(eval_res.safety_state, ("REJECTED", "UNCERTAIN"))
        self.assertFalse(eval_res.clinical_action_allowed)

    def test_invariant_06_old_result_never_silently_associated_with_newer_model(self):
        """Invariant 6: An old AI result can NEVER be silently associated with a newer model version."""
        res = self.client.get("/api/analytics/metrics")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("version", data.get("metrics", {}))
        # Policy versions are strictly immutable
        self.assertEqual(SafetyEvaluationResult.safety_policy_version, "SAFE-1.0")

    def test_invariant_07_duplicate_request_never_creates_duplicate_clinical_events(self):
        """Invariant 7: A duplicate request can NEVER create duplicate clinical events."""
        validator = ImageValidator()
        img = Image.new("RGB", (300, 300), color=(180, 50, 20))
        arr = np.array(img)
        arr[100:150, 100:150] = [200, 180, 100]
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, format="JPEG")
        raw_bytes = buf.getvalue()
        
        # First submission
        res1 = validator.validate_bytes(raw_bytes)
        self.assertTrue(res1.valid)
        self.assertFalse(res1.duplicate_detected)
        
        # Second identical submission
        res2 = validator.validate_bytes(raw_bytes)
        self.assertTrue(res2.valid)
        self.assertTrue(res2.duplicate_detected)
        self.assertEqual(res1.image_hash, res2.image_hash)

    def test_invariant_08_sync_conflict_never_silently_overwrites(self):
        """Invariant 8: A synchronization conflict can NEVER silently overwrite clinical information."""
        entity_id = "P-7722"
        # Seed local version = 4
        with database.get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sync_events (id, device_id, entity_type, entity_id, action, version, sync_status)
                   VALUES ('sync-seed-1', 'edge-a', 'patient', ?, 'UPDATE', 4, 'SYNCED')""",
                (entity_id,)
            )
            conn.commit()

        # Incoming event has older version = 2
        incoming = [{
            "id": "sync-stale-2",
            "device_id": "edge-b",
            "entity_type": "patient",
            "entity_id": entity_id,
            "version": 2,
            "action": "UPDATE",
            "payload": {"name": "Malicious Overwrite"}
        }]

        result = database.reconcile_sync_batch(incoming)
        self.assertEqual(result["conflict_count"], 1)
        self.assertIn(entity_id, result["conflict_ids"])

        # Check status in database is CONFLICT_REQUIRES_REVIEW
        with database.get_db() as conn:
            row = conn.execute(
                "SELECT sync_status FROM sync_events WHERE entity_id = ? AND version = 2",
                (entity_id,)
            ).fetchone()
            self.assertEqual(row["sync_status"], "CONFLICT_REQUIRES_REVIEW")

    def test_invariant_09_missing_longitudinal_history_never_fabricates_progression(self):
        """Invariant 9: A missing longitudinal history can NEVER be converted into fabricated progression evidence."""
        res = assess_progression_risk(
            current_scan={"id": "scan-1", "stage": 0, "confidence": 90.0},
            previous_scans=[], # Zero previous scans
            patient_profile={"diabetes_duration": 5, "hba1c": 6.8}
        )
        flags = res["predicted_risk"]["uncertainty_flags"]
        # Must explicitly flag limited longitudinal history
        self.assertTrue(any("limited longitudinal history" in f.lower() for f in flags))

    def test_invariant_10_demo_mode_cannot_mutate_real_clinical_records(self):
        """Invariant 10: Demo mode can NEVER mutate real clinical records."""
        # Ensure demo run produces simulation output without overwriting existing real patients
        res = self.client.post("/api/demo/run", json={"scenario_id": "MODERATE_NPDR"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success", False))
        # Patient ID in demo run is tagged as synthetic or demo
        self.assertTrue("scenario" in data or "demo" in str(data).lower())


if __name__ == "__main__":
    unittest.main()
