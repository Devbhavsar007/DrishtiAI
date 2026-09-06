"""
Unit Tests for Gate 3: Clinical Intelligence, Deterministic Triage & Honest Progression.
Validates:
  1. 3-state longitudinal progression risk analyzer (honest handling of sparse data)
  2. ICMR/AAO-aligned deterministic referral and triage policies
  3. Structured Medical RAG retrieval with provenance and insufficient-evidence fallback
  4. Multi-model consensus and entropy-aware safety evaluation
"""

import unittest
from engine.clinical.progression import assess_progression_risk
from engine.clinical.referral import decide_referral
from engine.clinical.rag import MedicalRAGRetriever
from engine.clinical.safety import evaluate_safety


class TestClinicalIntelligence(unittest.TestCase):
    def setUp(self):
        self.rag = MedicalRAGRetriever()

    def test_01_progression_single_scan_emits_limited_history(self):
        """Single scan must explicitly return LIMITED_LONGITUDINAL_HISTORY and honest message."""
        result = assess_progression_risk(
            current_scan={"id": "scan-1", "stage": 1, "confidence": 88.0},
            previous_scans=[],
            patient_profile={"hba1c": 7.5, "diabetes_duration": 5, "sugar_level": 150},
        )

        self.assertEqual(result["longitudinal_state"], "LIMITED_LONGITUDINAL_HISTORY")
        self.assertIn("insufficient longitudinal data", result["progression_availability_message"])
        self.assertFalse(result["is_individualized_prediction"])
        self.assertIn("limited longitudinal history", result["predicted_risk"]["uncertainty_flags"])

    def test_02_progression_multi_scan_supported(self):
        """Sequential scans provide valid longitudinal baseline."""
        result = assess_progression_risk(
            current_scan={"id": "scan-2", "stage": 2, "confidence": 84.0},
            previous_scans=[{"id": "scan-1", "stage": 1, "confidence": 89.0}],
            patient_profile={"hba1c": 8.5, "diabetes_duration": 10, "sugar_level": 180},
        )

        self.assertEqual(result["longitudinal_state"], "LONGITUDINAL_SUPPORTED")
        self.assertIsNone(result["progression_availability_message"])
        self.assertTrue(result["is_individualized_prediction"])
        self.assertEqual(result["observed_data"]["stage_delta"], 1)

    def test_03_referral_policy_icmr_triage(self):
        """Deterministic referral policy maps stages and progression into prioritized clinical action."""
        # A. Proliferative DR -> URGENT
        triage_pdr = decide_referral(screening={"stage": 4, "confidence": 92.0})
        self.assertEqual(triage_pdr["priority"], "URGENT")
        self.assertIn("STAGE_PROLIFERATIVE", triage_pdr["reasonCodes"])
        self.assertTrue(triage_pdr["humanReviewRequired"])

        # B. Moderate NPDR -> EARLY
        triage_mod = decide_referral(screening={"stage": 2, "confidence": 85.0})
        self.assertEqual(triage_mod["priority"], "EARLY")
        self.assertIn("STAGE_REFERABLE", triage_mod["reasonCodes"])

        # C. Low confidence (<70%) -> Human Review Required
        triage_low_conf = decide_referral(screening={"stage": 0, "confidence": 62.0})
        self.assertTrue(triage_low_conf["humanReviewRequired"])
        self.assertIn("LOW_MODEL_CONFIDENCE", triage_low_conf["reasonCodes"])

    def test_04_medical_rag_structured_citations(self):
        """RAG engine must return structured citations with authority and year."""
        res = self.rag.query("What is the screening interval for mild NPDR?", clinical_context={"stage": 1})
        self.assertTrue(res.evidence_found)
        self.assertGreater(len(res.citations), 0)

        top_citation = res.citations[0]
        self.assertTrue(len(top_citation.organization) > 0)
        self.assertGreaterEqual(top_citation.year, 2020)
        self.assertTrue(len(top_citation.section) > 0)

    def test_05_medical_rag_insufficient_evidence_fallback(self):
        """Out-of-scope query must safely return insufficient evidence without fabricating clinical facts."""
        res = self.rag.query("How to perform open heart coronary bypass surgery?")
        self.assertFalse(res.evidence_found)
        self.assertEqual(len(res.citations), 0)
        self.assertIn("insufficient evidence", res.answer.lower())

    def test_06_safety_engine_consensus_evaluation(self):
        """Inter-model disagreement delta >= 2 stages flags uncertainty."""
        sec_res = evaluate_safety(
            quality_assessment={"decision": "ACCEPT", "quality_score": 0.90},
            primary_prediction={"stage": 1, "confidence": 85.0},
            secondary_prediction={"stage": 3, "confidence": 80.0},
        )
        self.assertEqual(sec_res.status, "UNCERTAIN")
        self.assertTrue(sec_res.human_review_required)
        self.assertIn("MODEL_DISAGREEMENT_SIGNIFICANT", sec_res.reasons)


if __name__ == "__main__":
    unittest.main()
