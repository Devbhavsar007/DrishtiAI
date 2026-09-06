"""
Baseline Legacy Regression Test Suite for DrishtiAI.
Guarantees zero breaking changes across all legacy and established endpoints:
  - /api/health
  - /api/dashboard
  - /api/patients (CRUD)
  - /analyze (Legacy v1.0 pipeline)
  - /api/analyze-v2 (v2 Full clinical pipeline)
  - /api/analyze-v3 (OptiGemma edge+cloud pipeline in offline mode)
"""

import os
import io
import unittest
from app import app, limiter
import engine.gemma_report


class TestLegacyEndpointsRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.limiter_was_enabled = getattr(limiter, "enabled", True)
        limiter.enabled = False
        cls.client = app.test_client()

        # Enforce deterministic offline report generation to avoid external API delays
        cls.original_offline = engine.gemma_report.OFFLINE_MODE
        engine.gemma_report.OFFLINE_MODE = True

        # Path to valid test fundus image
        cls.test_image_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "sample_data",
            "test_fundus.jpg"
        )
        if not os.path.exists(cls.test_image_path):
            raise FileNotFoundError(f"Test image not found at {cls.test_image_path}")
        with open(cls.test_image_path, "rb") as f:
            cls.test_image_bytes = f.read()

    @classmethod
    def tearDownClass(cls):
        limiter.enabled = cls.limiter_was_enabled
        engine.gemma_report.OFFLINE_MODE = cls.original_offline

    def test_01_api_health_contract(self):
        """Verify /api/health returns HTTP 200 with required health keys."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "DrishtiAI")
        self.assertIn("version", data)
        self.assertIn("timestamp", data)

    def test_02_api_dashboard_contract(self):
        """Verify /api/dashboard returns HTTP 200 with stats structure."""
        res = self.client.get("/api/dashboard")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_patients", data)
        self.assertIn("total_scans", data)
        self.assertIn("stage_distribution", data)

    def test_03_api_patients_crud_contract(self):
        """Verify /api/patients supports standard CRUD lifecycle."""
        # 1. Create Patient
        create_payload = {
            "name": "Regression Test Patient",
            "age": 58,
            "gender": "Female",
            "diabetes_duration": 12,
            "sugar_level": 170.5,
            "hba1c": 8.1,
            "notes": "Regression baseline validation",
        }
        res_create = self.client.post("/api/patients", json=create_payload)
        self.assertEqual(res_create.status_code, 200)
        created_data = res_create.get_json()
        self.assertTrue(created_data.get("success", False))
        patient = created_data.get("patient", {})
        self.assertIn("id", patient)
        patient_id = patient["id"]

        try:
            # 2. Get Patient Detail
            res_get = self.client.get(f"/api/patients/{patient_id}")
            self.assertEqual(res_get.status_code, 200)
            patient_detail_resp = res_get.get_json()
            self.assertTrue(patient_detail_resp.get("success", False))
            patient_detail = patient_detail_resp.get("patient", {})
            self.assertEqual(patient_detail["name"], "Regression Test Patient")
            self.assertEqual(patient_detail["age"], 58)

            # 3. Update Patient
            update_payload = {"notes": "Updated regression notes"}
            res_update = self.client.put(f"/api/patients/{patient_id}", json=update_payload)
            self.assertEqual(res_update.status_code, 200)

            # 4. List Patients contains newly created
            res_list = self.client.get("/api/patients")
            self.assertEqual(res_list.status_code, 200)
            list_resp = res_list.get_json()
            self.assertTrue(list_resp.get("success", False))
            patients = list_resp.get("patients", [])
            self.assertTrue(any(p["id"] == patient_id for p in patients))
        finally:
            # 5. Delete Patient
            res_del = self.client.delete(f"/api/patients/{patient_id}")
            self.assertEqual(res_del.status_code, 200)

    def test_04_analyze_legacy_validation_and_inference(self):
        """Verify POST /analyze: 400 on empty/bad file, 200 on valid image."""
        # A. Missing image payload -> 400
        res_empty = self.client.post("/analyze")
        self.assertEqual(res_empty.status_code, 400)
        self.assertIn("error", res_empty.get_json())

        # B. Invalid file type -> 400
        bad_file = (io.BytesIO(b"not an image text"), "malicious.exe")
        res_bad = self.client.post(
            "/analyze",
            data={"image": bad_file},
            content_type="multipart/form-data"
        )
        self.assertEqual(res_bad.status_code, 400)
        self.assertIn("error", res_bad.get_json())

        # C. Valid image analysis
        valid_file = (io.BytesIO(self.test_image_bytes), "test_fundus.jpg")

        res_valid = self.client.post(
            "/analyze",
            data={"image": valid_file, "age": "55", "sugar_level": "160"},
            content_type="multipart/form-data"
        )
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.get_json()

        # Contract assertion
        self.assertTrue(data.get("success", False))
        self.assertIn("analysis_id", data)
        self.assertIn("detection", data)
        self.assertIn("heatmap_analysis", data)
        self.assertIn("vessel_stats", data)
        self.assertIn("report", data)
        self.assertIn("images", data)
        self.assertIn("processing_time", data)

        detection = data["detection"]
        self.assertIn("stage", detection)
        self.assertIn("stage_name", detection)
        self.assertIn("confidence", detection)

    def test_05_analyze_v2_endpoint_contract(self):
        """Verify POST /api/analyze-v2 runs the v2 multi-stage pipeline."""
        # A. Missing image -> 400
        res_empty = self.client.post("/api/analyze-v2")
        self.assertEqual(res_empty.status_code, 400)

        # B. Valid image
        valid_file = (io.BytesIO(self.test_image_bytes), "test_fundus.jpg")

        res_valid = self.client.post(
            "/api/analyze-v2",
            data={"image": valid_file},
            content_type="multipart/form-data"
        )
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.get_json()

        self.assertIn("analysis_id", data)
        self.assertIn("iqa", data)
        if data.get("status") != "REJECTED":
            self.assertIn("structures", data)
            self.assertIn("detection", data)
            self.assertIn("report", data)

    def test_06_analyze_v3_offline_endpoint_contract(self):
        """Verify POST /api/analyze-v3 runs two-tier pipeline in offline mode."""
        # A. Missing image -> 400
        res_empty = self.client.post("/api/analyze-v3")
        self.assertEqual(res_empty.status_code, 400)

        # B. Valid image with force_offline=true
        valid_file = (io.BytesIO(self.test_image_bytes), "test_fundus.jpg")

        res_valid = self.client.post(
            "/api/analyze-v3",
            data={"image": valid_file, "offline": "true"},
            content_type="multipart/form-data"
        )
        self.assertEqual(res_valid.status_code, 200)
        data = res_valid.get_json()

        self.assertIn("analysis_id", data)
        self.assertIn("status", data)
        self.assertIn("detection", data)
        self.assertIn("explanation", data)
        self.assertIn("grading", data)
        self.assertIn("structures", data)
        self.assertIn("report", data)
        self.assertIn("tier_executed", data)


if __name__ == "__main__":
    unittest.main()
