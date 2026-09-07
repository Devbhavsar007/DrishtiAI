"""
DrishtiAI — Offline Report Generator (Zero-API, Template-Based)

Generates the same JSON schema as gemma_report.py but without any cloud
API calls. Uses deterministic, literature-derived rules enriched with
lesion-level data from the structures pipeline.

This is the fallback for rural deployments where internet is unavailable.
"""

from __future__ import annotations

import json
from config import DR_STAGES

# Published DR progression rates (UKPDS, WESDR, ETDRS)
_PROGRESSION_RATES = {
    0: {"6m": "3-5%",   "12m": "5-10%",  "urgency": "ROUTINE",   "followup": "Annual retinal screening"},
    1: {"6m": "8-12%",  "12m": "15-25%", "urgency": "ROUTINE",   "followup": "Repeat screening in 9-12 months"},
    2: {"6m": "12-18%", "12m": "20-30%", "urgency": "SOON",      "followup": "Ophthalmologist referral within 3-6 months"},
    3: {"6m": "20-30%", "12m": "30-50%", "urgency": "URGENT",    "followup": "Ophthalmologist referral within 1 month"},
    4: {"6m": "N/A",    "12m": "N/A",    "urgency": "EMERGENCY", "followup": "Immediate referral for laser/surgical treatment"},
}

_PLAIN_DESCRIPTIONS = {
    0: "The AI screening indicates no signs of diabetic retinopathy at this time. The retina appears healthy with normal blood vessel patterns.",
    1: "The screening suggests early, mild signs of diabetic retinopathy. Small changes (microaneurysms) in retinal blood vessels are beginning to appear.",
    2: "The analysis indicates moderate non-proliferative diabetic retinopathy. Blood vessels in the retina are showing noticeable damage, with evidence of leakage and deposits.",
    3: "The screening reveals severe non-proliferative diabetic retinopathy. Significant blood vessel damage is present, and the retina is at high risk of progressing to the most advanced stage.",
    4: "The analysis indicates proliferative diabetic retinopathy — the most advanced stage. New, abnormal blood vessels are growing, which requires immediate medical attention to prevent vision loss.",
}


def _apply_risk_modifiers(base_risk_str: str, patient_info: dict | None) -> str:
    """Adjust a risk-range string based on patient risk modifiers."""
    if not patient_info or base_risk_str == "N/A":
        return base_risk_str
    # Parse range
    try:
        parts = base_risk_str.replace("%", "").split("-")
        lo, hi = float(parts[0]), float(parts[1])
    except (ValueError, IndexError):
        return base_risk_str

    multiplier = 1.0
    hba1c = patient_info.get("hba1c")
    if hba1c:
        try:
            if float(hba1c) > 8.0:
                multiplier *= 1.5
        except ValueError:
            pass

    duration = patient_info.get("diabetes_duration")
    if duration:
        try:
            if float(duration) > 10:
                multiplier *= 1.3
        except ValueError:
            pass

    age = patient_info.get("age")
    if age:
        try:
            if float(age) > 60:
                multiplier *= 1.1
        except ValueError:
            pass

    lo = min(lo * multiplier, 95.0)
    hi = min(hi * multiplier, 99.0)
    return f"{lo:.0f}-{hi:.0f}%"


def _lesion_summary(structures: dict | None) -> str:
    """Build a plain-language lesion summary from structures pipeline output."""
    if not structures:
        return "Lesion-level analysis not available."

    parts = []
    ma = structures.get("microaneurysms", 0)
    if ma > 0:
        parts.append(f"{ma} microaneurysm{'s' if ma != 1 else ''} detected")

    hm = structures.get("hemorrhages", 0)
    if hm > 0:
        parts.append(f"{hm} hemorrhage{'s' if hm != 1 else ''} identified")

    ex = structures.get("exudate_area_px", 0)
    if ex > 0:
        parts.append(f"exudate deposits present (area: {ex} px)")

    nv = structures.get("nv_suspicion", False)
    if nv:
        parts.append("⚠ neovascularization suspected — peripapillary vessel density elevated")

    if not parts:
        return "No significant lesions detected in the retinal image."
    return "; ".join(parts) + "."


def _vessel_summary(structures: dict | None) -> str:
    """Build vessel analysis narrative."""
    if not structures:
        return "Vessel analysis not available."
    density = structures.get("vessel_density", 0)
    tort = structures.get("tortuosity", 0)

    if density > 0.08:
        text = "Dense vascular network observed — may indicate neovascularization."
    elif density > 0.04:
        text = "Normal vascular density and distribution."
    elif density > 0.02:
        text = "Reduced vascular density — possible vessel dropout in some quadrants."
    else:
        text = "Significantly sparse vasculature — indicates advanced retinal damage."

    if tort > 1.5:
        text += " Vessel tortuosity is elevated, suggesting vascular stress."
    return text


def generate_offline_report(
    detection_result: dict,
    heatmap_analysis: dict | None,
    vessel_stats: dict | None,
    patient_info: dict | None = None,
    structures: dict | None = None,
    safety_state: str | None = None,
    safety_eval: dict | None = None,
) -> tuple[dict, str]:
    """
    Generate a complete report offline using deterministic rules.

    Returns:
        (report_dict, source_description)
    """
    # Authoritative safety override: Never claim normal/healthy when safety is not verified
    effective_safety = safety_state or (safety_eval.get("safety_state") if isinstance(safety_eval, dict) else None)
    if effective_safety and effective_safety != "VERIFIED":
        return {
            "current_diagnosis": {
                "stage": -1,
                "stage_name": f"Inconclusive ({effective_safety})",
                "confidence": "N/A",
                "plain_language": (
                    f"Automated AI screening could not establish a reliable clinical result (Safety State: {effective_safety}). "
                    "This screening must NOT be interpreted as normal or negative. "
                    "Clinical evaluation by an ophthalmologist or image recapture is required."
                ),
            },
            "visual_findings": {
                "heatmap_summary": "Activation map unverified due to safety state.",
                "vessel_analysis": "Vessel analysis deferred.",
                "lesion_summary": "Lesion grading unverified.",
            },
            "risk_prediction": {
                "6_month": {
                    "progression_risk_percent": "N/A",
                    "scenario_if_untreated": "Longitudinal prediction unavailable for inconclusive screening.",
                    "scenario_if_managed": "Longitudinal prediction unavailable for inconclusive screening.",
                },
                "12_month": {
                    "progression_risk_percent": "N/A",
                    "scenario_if_untreated": "Longitudinal prediction unavailable for inconclusive screening.",
                    "scenario_if_managed": "Longitudinal prediction unavailable for inconclusive screening.",
                },
            },
            "action_plan": [
                "Schedule in-person comprehensive ophthalmology examination",
                "Do NOT rely on automated screening output for clinical discharge",
                "Recapture retinal image if image quality or anatomical landmarks failed",
            ],
            "urgency": "HUMAN_REVIEW_REQUIRED",
            "recommended_follow_up": "Ophthalmology clinical review or immediate recapture",
            "_offline_fallback": True,
            "_source": "deterministic_safety_fallback",
        }, "Offline deterministic safety report"

    stage = detection_result["stage"]
    stage_info = DR_STAGES.get(stage, DR_STAGES[0])
    rates = _PROGRESSION_RATES[stage]

    # Enrich description with lesion data
    base_desc = _PLAIN_DESCRIPTIONS[stage]
    lesion_text = _lesion_summary(structures)
    if lesion_text and "not available" not in lesion_text.lower():
        base_desc += " " + lesion_text

    # Risk prediction with patient-specific modifiers
    risk_6m = _apply_risk_modifiers(rates["6m"], patient_info)
    risk_12m = _apply_risk_modifiers(rates["12m"], patient_info)

    # Heatmap summary
    heatmap_text = "Heatmap analysis not available."
    if heatmap_analysis:
        region = heatmap_analysis.get("most_affected_region", "central")
        intensity = heatmap_analysis.get("activity_intensity", "moderate")
        heatmap_text = (
            f"AI activation map shows {intensity} activity concentrated in the "
            f"{region} region, consistent with Stage {stage} findings."
        )

    # Vessel summary from structures or fallback stats
    vessel_text = _vessel_summary(structures)
    if vessel_text == "Vessel analysis not available." and vessel_stats:
        vessel_text = vessel_stats.get("vessel_health_text", vessel_text)

    # Action plan tailored by stage
    actions = {
        0: [
            "Continue annual retinal screening",
            "Monitor blood sugar levels daily (fasting + post-meal)",
            "Maintain HbA1c below 7.0%",
            "Follow a balanced diet rich in leafy greens and omega-3",
            "30 minutes of daily walking or moderate exercise",
        ],
        1: [
            "Schedule follow-up retinal screening in 9-12 months",
            "Tighten blood sugar control — target HbA1c < 7.0%",
            "Monitor blood pressure (target < 130/80 mmHg)",
            "Increase intake of antioxidant-rich foods",
            "Avoid smoking and excessive alcohol",
        ],
        2: [
            "Referral to ophthalmologist within 3-6 months",
            "Intensive blood sugar monitoring and management",
            "Blood pressure control is critical at this stage",
            "Consider lipid-lowering therapy if indicated",
            "Repeat fundus imaging in 6 months to track progression",
        ],
        3: [
            "Urgent referral to ophthalmologist within 1 month",
            "Immediate intensive glycemic control",
            "Discuss laser photocoagulation or anti-VEGF treatment options",
            "Monthly blood sugar and BP monitoring",
            "Avoid strenuous physical activity until specialist review",
        ],
        4: [
            "EMERGENCY: Immediate referral for retinal specialist evaluation",
            "Prepare for possible laser treatment or vitrectomy",
            "Do not delay — risk of permanent vision loss is high",
            "Intensive insulin therapy may be required",
            "Psychological support and low-vision rehabilitation referral",
        ],
    }

    report = {
        "current_diagnosis": {
            "stage": stage,
            "stage_name": stage_info["name"],
            "confidence": f"{detection_result['confidence']}%",
            "plain_language": base_desc,
        },
        "visual_findings": {
            "heatmap_summary": heatmap_text,
            "vessel_analysis": vessel_text,
            "lesion_summary": lesion_text,
        },
        "risk_prediction": {
            "6_month": {
                "progression_risk_percent": risk_6m,
                "scenario_if_untreated": f"May progress to Stage {min(stage + 1, 4)} without glycemic control.",
                "scenario_if_managed": "Can stabilize or slow progression with proper management.",
            },
            "12_month": {
                "progression_risk_percent": risk_12m,
                "scenario_if_untreated": f"Higher risk of advancing to Stage {min(stage + 1, 4)} or beyond.",
                "scenario_if_managed": "Good chance of stabilization with lifestyle changes and medication adherence.",
            },
            "_source": "literature_heuristic",
            "_note": (
                "These progression rates are derived from published clinical "
                "literature (UKPDS, WESDR, ETDRS studies), not from a model "
                "trained on longitudinal patient data. They are evidence-informed "
                "estimates, not individualized predictions."
            ),
        },
        "action_plan": actions.get(stage, actions[0]),
        "urgency": rates["urgency"],
        "recommended_follow_up": rates["followup"],
        "diet_recommendations": [
            "Increase leafy green vegetables, berries, and omega-3 rich fish",
            "Reduce refined sugar, white rice, and processed carbohydrates",
            "Stay hydrated — aim for 8 glasses of water daily",
        ],
        "disclaimer": (
            "This is an AI-assisted screening tool developed for preliminary "
            "assessment. It is NOT a substitute for professional medical "
            "diagnosis. Please consult a qualified ophthalmologist for "
            "definitive evaluation and treatment planning."
        ),
        "_offline": True,
        "_report_version": "drishtiai-offline-v1",
    }

    return report, "offline_template_report"
