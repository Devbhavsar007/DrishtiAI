import unittest
import uuid
from app import app
from engine.security.auth import create_access_token, Role
from database import (
    create_patient,
    delete_patient,
    save_scan,
    save_progression_assessment,
    get_progression_assessment,
    save_referral,
    get_referral,
    get_patient_timeline,
    get_db,
)


class TestPersistenceAndTimeline(unittest.TestCase):
    def setUp(self):
        self.patient = create_patient(
            name="Timeline Unit Test Patient",
            age=54,
            gender="Female",
            diabetes_duration=8,
            sugar_level=155.0,
            hba1c=7.8,
            notes="Testing timeline integration",
        )
        self.patient_id = self.patient["id"]
        self.scan_id_1 = f"test-scan-{uuid.uuid4().hex[:8]}"
        self.scan_id_2 = f"test-scan-{uuid.uuid4().hex[:8]}"

        save_scan(
            scan_id=self.scan_id_1,
            patient_id=self.patient_id,
            detection_result={"stage": 1, "stage_name": "Mild NPDR", "confidence": 88.0, "severity": "mild", "color": "#D97706"},
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={"original": "test1.png"},
            processing_time=0.4,
        )

        save_scan(
            scan_id=self.scan_id_2,
            patient_id=self.patient_id,
            detection_result={"stage": 2, "stage_name": "Moderate NPDR", "confidence": 85.0, "severity": "moderate", "color": "#EA580C"},
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={"original": "test2.png"},
            processing_time=0.5,
        )

    def tearDown(self):
        delete_patient(self.patient_id)
        with get_db() as conn:
            conn.execute("DELETE FROM progression_assessments WHERE patient_id = ?", (self.patient_id,))
            conn.execute("DELETE FROM referrals WHERE patient_id = ?", (self.patient_id,))
            conn.commit()

    def test_save_and_retrieve_progression_assessment(self):
        prog_data = {
            "engine": "deterministic_progression_v1",
            "predicted_risk": {
                "risk_category": "MODERATE",
                "six_month_risk": 0.45,
                "twelve_month_risk": 0.55,
                "supporting_factors": ["elevated blood glucose"],
                "uncertainty_flags": [],
            },
        }
        saved = save_progression_assessment(self.scan_id_1, self.patient_id, prog_data)
        self.assertEqual(saved["risk_category"], "MODERATE")

        retrieved = get_progression_assessment(self.scan_id_1)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["risk_category"], "MODERATE")
        self.assertAlmostEqual(retrieved["six_month_risk"], 0.45)

    def test_save_and_retrieve_referral(self):
        triage_data = {
            "priority": "EARLY",
            "reasonCodes": ["STAGE_REFERABLE", "DOCTOR_REVIEW_PENDING"],
            "humanReviewRequired": True,
        }
        saved = save_referral(self.scan_id_2, self.patient_id, triage_data)
        self.assertEqual(saved["priority"], "EARLY")

        retrieved = get_referral(self.scan_id_2)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["priority"], "EARLY")
        self.assertIn("STAGE_REFERABLE", retrieved["reason_codes"])

    def test_get_patient_timeline_chronological_order(self):
        timeline = get_patient_timeline(self.patient_id)
        self.assertEqual(timeline["total_events"], 2)
        events = timeline["events"]
        self.assertEqual(events[0]["scan_id"], self.scan_id_1)
        self.assertEqual(events[1]["scan_id"], self.scan_id_2)
        self.assertEqual(events[1]["stage_delta"], 1)

    def test_timeline_endpoint(self):
        client = app.test_client()
        token = create_access_token("test-hw", Role.HEALTH_WORKER.value)
        res = client.get(
            f"/api/patients/{self.patient_id}/timeline",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["timeline"]["total_events"], 2)


if __name__ == "__main__":
    unittest.main()
