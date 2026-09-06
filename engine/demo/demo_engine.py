"""
Isolated Demonstration Engine for DrishtiAI.

Hard architectural rules:
  1. Active strictly when DEMO_MODE=True.
  2. Isolated synthetic patient namespace (prefix: DEMO-SIM-).
  3. Impossible to trigger against real patient records.
  4. 10 canonical hackathon / clinical scenarios.
"""

from typing import Dict, List, Any, Optional
import uuid
from config import DEMO_MODE
from engine.safety.image_validator import ImageValidationResult
from engine.safety.anatomy import AnatomyResult
from engine.safety.ood import OODResult
from engine.safety.decision_engine import SafetyDecisionEngine
from engine.clinical.progression import assess_progression_risk
from engine.clinical.referral import decide_referral

# 10 Canonical Scenarios
DEMO_SCENARIOS = {
    "NORMAL": {
        "id": "NORMAL",
        "title": "1. Normal Fundus (Routine Annual Recall)",
        "description": "Clear image, healthy vascular architecture, no microaneurysms.",
        "category": "CLINICAL_STANDARD",
        "patient": {"name": "Demo Subject: Rajesh Kumar", "age": 48, "diabetes_duration": 3, "hba1c": 6.8},
        "stage": 0,
        "stage_name": "No DR",
        "confidence": 95.4,
        "quality": "ACCEPT",
        "operator_eye": "OD",
        "inferred_eye": "OD",
    },
    "MILD_NPDR": {
        "id": "MILD_NPDR",
        "title": "2. Mild NPDR (6-12 Month Follow-up)",
        "description": "Few isolated microaneurysms, good glycemic management recommended.",
        "category": "CLINICAL_STANDARD",
        "patient": {"name": "Demo Subject: Sunita Devi", "age": 54, "diabetes_duration": 6, "hba1c": 7.4},
        "stage": 1,
        "stage_name": "Mild NPDR",
        "confidence": 89.2,
        "quality": "ACCEPT",
        "operator_eye": "OS",
        "inferred_eye": "OS",
    },
    "MODERATE_NPDR": {
        "id": "MODERATE_NPDR",
        "title": "3. Moderate NPDR (Specialist Referral Required)",
        "description": "Multiple hemorrhages and exudates. Referable DR threshold crossed.",
        "category": "CLINICAL_STANDARD",
        "patient": {"name": "Demo Subject: Mohammed Khan", "age": 62, "diabetes_duration": 12, "hba1c": 8.6},
        "stage": 2,
        "stage_name": "Moderate NPDR",
        "confidence": 86.8,
        "quality": "ACCEPT",
        "operator_eye": "OD",
        "inferred_eye": "OD",
    },
    "SEVERE_PDR": {
        "id": "SEVERE_PDR",
        "title": "4. Proliferative DR (Urgent Vitreoretinal Escalation)",
        "description": "Neovascularization detected. Sight-threatening emergency requiring laser/anti-VEGF.",
        "category": "CLINICAL_STANDARD",
        "patient": {"name": "Demo Subject: Anand Verma", "age": 59, "diabetes_duration": 18, "hba1c": 10.2},
        "stage": 4,
        "stage_name": "Proliferative DR",
        "confidence": 93.1,
        "quality": "ACCEPT",
        "operator_eye": "OS",
        "inferred_eye": "OS",
    },
    "POOR_QUALITY": {
        "id": "POOR_QUALITY",
        "title": "5. Image Quality Gate Trigger (Recapture Request)",
        "description": "Severe cataract haze and underexposure. System blocks inference and requests clean retake.",
        "category": "SAFETY_GATE",
        "patient": {"name": "Demo Subject: Kamala Bai", "age": 70, "diabetes_duration": 15, "hba1c": 8.0},
        "quality": "REJECT",
        "quality_feedback": ["Severe motion blur", "Underexposed nasal field"],
    },
    "LOW_CONFIDENCE": {
        "id": "LOW_CONFIDENCE",
        "title": "6. Low Confidence / Borderline Classification",
        "description": "Model confidence is 58%. Safety Engine flags UNCERTAIN and requires human review.",
        "category": "SAFETY_GATE",
        "patient": {"name": "Demo Subject: Vikram Singh", "age": 51, "diabetes_duration": 5, "hba1c": 7.9},
        "stage": 1,
        "stage_name": "Mild NPDR",
        "confidence": 58.2,
        "quality": "ACCEPT",
    },
    "OOD_NON_FUNDUS": {
        "id": "OOD_NON_FUNDUS",
        "title": "7. Out-of-Distribution Non-Fundus Rejection",
        "description": "Operator accidentally uploaded a document/pet photograph. Safe rejection without pipeline crash.",
        "category": "SAFETY_GATE",
        "patient": {"name": "Demo Subject: Test Ingestion", "age": 30, "diabetes_duration": 1, "hba1c": 5.5},
        "ood_domain_invalid": True,
        "rejection_reason": "Non-fundus photograph detected: missing retinal vascular architecture.",
    },
    "MODEL_DISAGREEMENT": {
        "id": "MODEL_DISAGREEMENT",
        "title": "8. Multi-Model Disagreement Consensus Escalation",
        "description": "Primary model grades Stage 1, Secondary model grades Stage 3. Triggers MODEL_DISAGREEMENT.",
        "category": "SAFETY_GATE",
        "patient": {"name": "Demo Subject: Fatima Sheikh", "age": 65, "diabetes_duration": 14, "hba1c": 9.1},
        "stage_primary": 1,
        "stage_secondary": 3,
        "confidence": 84.0,
    },
    "LATERALITY_MISMATCH": {
        "id": "LATERALITY_MISMATCH",
        "title": "9. Anatomical Laterality Conflict Warning",
        "description": "Operator selected Right Eye (OD), but disc-fovea geometry indicates Left Eye (OS). Operator confirmation required.",
        "category": "SAFETY_GATE",
        "patient": {"name": "Demo Subject: Suresh Nair", "age": 57, "diabetes_duration": 8, "hba1c": 7.5},
        "stage": 1,
        "confidence": 88.0,
        "operator_eye": "OD",
        "inferred_eye": "OS",
        "laterality_confidence": 0.92,
    },
    "OFFLINE_SYNC": {
        "id": "OFFLINE_SYNC",
        "title": "10. Offline Queueing & Conflict-Free Cloud Sync",
        "description": "Screening performed in rural disconnected camp, saved to local outbox, synchronized seamlessly upon reconnection.",
        "category": "RELIABILITY",
        "patient": {"name": "Demo Subject: Ganga Ram (Rural Camp)", "age": 60, "diabetes_duration": 11, "hba1c": 8.3},
        "stage": 2,
        "confidence": 87.5,
        "offline_sync_demo": True,
    },
}


def list_demo_scenarios() -> List[Dict[str, Any]]:
    """Return all 10 available demonstration scenarios."""
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "description": s["description"],
            "category": s["category"],
        }
        for s in DEMO_SCENARIOS.values()
    ]


class DemoScenarioRunner:
    """Executes pre-configured demonstration scenarios in strict isolation."""

    def __init__(self):
        self.safety_engine = SafetyDecisionEngine()

    def run(self, scenario_id: str, custom_patient_id: Optional[str] = None) -> Dict[str, Any]:
        if not DEMO_MODE:
            raise PermissionError("Demo scenario execution is forbidden when DEMO_MODE is False.")

        scenario = DEMO_SCENARIOS.get(scenario_id.upper())
        if not scenario:
            raise ValueError(f"Unknown demo scenario '{scenario_id}'. Available: {list(DEMO_SCENARIOS.keys())}")

        # Enforce isolated synthetic patient ID namespace
        sim_patient_id = custom_patient_id or f"DEMO-SIM-{uuid.uuid4().hex[:6]}"
        if not sim_patient_id.startswith("DEMO-SIM-"):
            raise ValueError(f"Demo operations are restricted to DEMO-SIM- namespace; rejected '{sim_patient_id}'.")

        # ── 1. Image Quality / Validation Simulation ──
        if scenario.get("quality") == "REJECT":
            val_res = ImageValidationResult(
                valid=False,
                error="Image quality below screening threshold: " + "; ".join(scenario.get("quality_feedback", [])),
                warnings=scenario.get("quality_feedback", []),
            )
            decision = self.safety_engine.evaluate(image_val=val_res, patient_id=sim_patient_id)
            return {
                "scenario": scenario,
                "patient_id": sim_patient_id,
                "status": "QUALITY_FAILED",
                "safety_evaluation": decision.to_dict(),
                "triage": None,
                "progression": None,
                "message": "Image rejected at quality gate. Please recapture with steady focus.",
            }

        # ── 2. OOD Non-Fundus Simulation ──
        if scenario.get("ood_domain_invalid"):
            val_res = ImageValidationResult(valid=True, image_hash=f"demo-{uuid.uuid4().hex[:8]}")
            ood_res = OODResult(
                domain_valid=False,
                rejection_reason=scenario.get("rejection_reason"),
                level_triggered=1,
            )
            decision = self.safety_engine.evaluate(image_val=val_res, ood_res=ood_res, patient_id=sim_patient_id)
            return {
                "scenario": scenario,
                "patient_id": sim_patient_id,
                "status": "REJECTED_NON_FUNDUS",
                "safety_evaluation": decision.to_dict(),
                "triage": None,
                "progression": None,
                "message": decision.mitigation_instructions,
            }

        # ── 3. Multi-Model Disagreement Simulation ──
        if "stage_primary" in scenario and "stage_secondary" in scenario:
            val_res = ImageValidationResult(valid=True, image_hash=f"demo-{uuid.uuid4().hex[:8]}")
            primary = {"stage": scenario["stage_primary"], "confidence": scenario["confidence"]}
            secondary = {"stage": scenario["stage_secondary"], "confidence": scenario["confidence"]}
            decision = self.safety_engine.evaluate(
                image_val=val_res,
                primary_detection=primary,
                secondary_detection=secondary,
                patient_id=sim_patient_id,
            )
            triage = decide_referral(screening=primary, doctor_review_present=False)
            return {
                "scenario": scenario,
                "patient_id": sim_patient_id,
                "status": "SCREENING_UNCERTAIN",
                "safety_evaluation": decision.to_dict(),
                "primary_model": primary,
                "secondary_model": secondary,
                "triage": triage,
                "message": "Specialist review required due to model disagreement across referable boundary.",
            }

        # ── 4. Laterality Conflict Simulation ──
        if scenario.get("operator_eye") and scenario.get("inferred_eye") and scenario["operator_eye"] != scenario["inferred_eye"]:
            val_res = ImageValidationResult(valid=True, image_hash=f"demo-{uuid.uuid4().hex[:8]}")
            anat_res = AnatomyResult(
                valid_anatomy=True,
                operator_selected_eye=scenario["operator_eye"],
                inferred_laterality=scenario["inferred_eye"],
                laterality_confidence=scenario.get("laterality_confidence", 0.90),
                laterality_mismatch=True,
                human_confirmation_required=True,
            )
            primary = {"stage": scenario.get("stage", 1), "confidence": scenario.get("confidence", 85.0)}
            decision = self.safety_engine.evaluate(
                image_val=val_res,
                anatomy_res=anat_res,
                primary_detection=primary,
                patient_id=sim_patient_id,
            )
            return {
                "scenario": scenario,
                "patient_id": sim_patient_id,
                "status": "OPERATOR_CONFIRMATION_REQUIRED",
                "safety_evaluation": decision.to_dict(),
                "anatomy": anat_res.to_dict(),
                "message": "Landmarks indicate eye opposite to operator selection. Confirmation gate active.",
            }

        # ── 5. Standard Screening Flow (Normal, Mild, Moderate, Severe, Low Conf) ──
        val_res = ImageValidationResult(valid=True, image_hash=f"demo-{uuid.uuid4().hex[:8]}")
        stage = scenario.get("stage", 0)
        confidence = scenario.get("confidence", 90.0)
        primary = {
            "stage": stage,
            "stage_name": scenario.get("stage_name", "Analyzed"),
            "confidence": confidence,
        }
        decision = self.safety_engine.evaluate(
            image_val=val_res,
            primary_detection=primary,
            patient_id=sim_patient_id,
        )

        prog = assess_progression_risk(
            current_scan={"id": f"demo-scan-{uuid.uuid4().hex[:6]}", "stage": stage, "confidence": confidence},
            previous_scans=[],
            patient_profile=scenario.get("patient"),
        )
        triage = decide_referral(screening=primary, progression=prog, doctor_review_present=False)

        return {
            "scenario": scenario,
            "patient_id": sim_patient_id,
            "status": "SUCCESS",
            "safety_evaluation": decision.to_dict(),
            "detection": primary,
            "progression": prog,
            "triage": triage,
            "offline_synced": scenario.get("offline_sync_demo", False),
        }


def run_demo_scenario(scenario_id: str, custom_patient_id: Optional[str] = None) -> Dict[str, Any]:
    """Top-level helper to execute a demo scenario."""
    runner = DemoScenarioRunner()
    return runner.run(scenario_id, custom_patient_id)
