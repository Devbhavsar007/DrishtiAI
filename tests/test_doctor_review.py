import unittest
import uuid
from app import app
from engine.security.auth import create_access_token, Role
from database import (
    create_patient,
    delete_patient,
    save_scan,
    save_referral,
    save_doctor_review,
    get_doctor_review,
    get_referral,
    get_db,
)


class TestDoctorReviewWorkflow(unittest.TestCase):
    def setUp(self):
        self.patient = create_patient(
            name="Doctor Review Test Subject",
            age=61,
            gender="Male",
            diabetes_duration=14,
            sugar_level=185.0,
            hba1c=8.8,
            notes="Testing doctor review sign-off",
        )
        self.patient_id = self.patient["id"]
        self.scan_id = f"doc-scan-{uuid.uuid4().hex[:8]}"

        save_scan(
            scan_id=self.scan_id,
            patient_id=self.patient_id,
            detection_result={"stage": 2, "stage_name": "Moderate NPDR", "confidence": 84.0, "severity": "moderate", "color": "#EA580C"},
            heatmap_analysis={},
            vessel_stats={},
            report={},
            image_paths={"original": "sample.png"},
            processing_time=0.4,
        )

        save_referral(
            scan_id=self.scan_id,
            patient_id=self.patient_id,
            triage_data={"priority": "EARLY", "reasonCodes": ["STAGE_REFERABLE"], "humanReviewRequired": True},
            doctor_review_status="PENDING",
        )

    def tearDown(self):
        delete_patient(self.patient_id)
        with get_db() as conn:
            conn.execute("DELETE FROM doctor_reviews WHERE patient_id = ?", (self.patient_id,))
            conn.commit()

    def test_save_and_retrieve_doctor_review(self):
        saved = save_doctor_review(
            scan_id=self.scan_id,
            patient_id=self.patient_id,
            doctor_id="DR-104",
            doctor_name="Dr. Vikram Sen",
            decision="MODIFIED",
            original_stage=2,
            adjusted_stage=3,
            approved_priority="URGENT",
            clinical_notes="Venous beading visible in inferior nasal quadrant. Escalated to Stage 3.",
            recommended_intervention="Refer for OCT within 2 weeks",
        )
        self.assertEqual(saved["decision"], "MODIFIED")
        self.assertEqual(saved["approved_priority"], "URGENT")

        review = get_doctor_review(self.scan_id)
        self.assertIsNotNone(review)
        self.assertEqual(review["doctor_id"], "DR-104")
        self.assertEqual(review["adjusted_stage"], 3)
        self.assertIn("Venous beading", review["clinical_notes"])

        # Check that referral status was synchronized
        ref = get_referral(self.scan_id)
        self.assertEqual(ref["doctor_review_status"], "MODIFIED")
        self.assertEqual(ref["priority"], "URGENT")

    def test_doctor_review_api_endpoints(self):
        client = app.test_client()
        doc_token = create_access_token(user_id="DR-OPHTH-01", role=Role.DOCTOR.value)
        headers = {"Authorization": f"Bearer {doc_token}"}

        # 1. Post review
        post_res = client.post(
            f"/api/scans/{self.scan_id}/doctor-review",
            json={
                "doctor_id": "DR-OPHTH-01",
                "doctor_name": "Dr. Ananya Roy",
                "decision": "APPROVED",
                "adjusted_stage": 2,
                "approved_priority": "EARLY",
                "clinical_notes": "AI detection confirmed. Moderate NPDR with focal microaneurysms.",
                "recommended_intervention": "Repeat dilated exam in 3 months",
            },
            headers=headers,
        )
        self.assertEqual(post_res.status_code, 200)
        post_data = post_res.get_json()
        self.assertTrue(post_data["success"])
        self.assertEqual(post_data["review"]["decision"], "APPROVED")

        # 2. Get review
        get_res = client.get(
            f"/api/scans/{self.scan_id}/doctor-review",
            headers=headers,
        )
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.get_json()
        self.assertTrue(get_data["success"])
        self.assertEqual(get_data["review"]["doctor_name"], "Dr. Ananya Roy")


if __name__ == "__main__":
    unittest.main()
