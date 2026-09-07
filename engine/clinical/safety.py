"""Deterministic Safety and Confidence Decision Engine for DrishtiAI."""

from __future__ import annotations

from typing import Any
from engine.contracts.safety import SafetyDecision


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate_safety(
    *,
    quality_assessment: dict[str, Any] | None,
    primary_prediction: dict[str, Any] | None,
    secondary_prediction: dict[str, Any] | None = None,
) -> SafetyDecision:
    """
    Evaluate image quality, prediction confidence, and inter-model agreement
    to produce a deterministic safety decision before triage/reporting.

    Rules:
    1. If quality is REJECT or quality_score < 0.40 -> RETAKE_REQUIRED.
    2. If confidence < 70.0 or quality is ENHANCE (borderline) -> UNCERTAIN.
    3. If secondary model exists and stage disagreement >= 2 -> UNCERTAIN.
    4. When primary stage is referable (>=2), human review is always flagged.
    """
    qa = quality_assessment or {}
    pred = primary_prediction or {}
    sec = secondary_prediction or {}

    quality_decision = str(qa.get("decision", "ACCEPT")).upper()
    quality_score = _to_float(qa.get("quality_score"), 0.85)
    confidence = _to_float(pred.get("confidence"), 0.0)
    primary_stage = int(pred.get("stage", 0) or 0)

    reasons: list[str] = []
    retake_guidance: str | None = None
    human_review_required = False

    # Check image quality gate
    if quality_decision == "REJECT" or quality_score < 0.40:
        status = "RETAKE_REQUIRED"
        human_review_required = True
        reasons.append("QUALITY_REJECTED")

        # Extract operator feedback from IQA
        feedback_list = qa.get("feedback", [])
        if feedback_list:
            reasons.extend([f"IQA_{f.upper().replace(' ', '_')}" for f in feedback_list])
            retake_guidance = (
                "Fundus image quality is insufficient for screening: "
                + "; ".join(feedback_list)
                + ". Please clean lens, ensure steady focus, and recapture in a dim room."
            )
        else:
            retake_guidance = (
                "Image blur or illumination is below clinical diagnostic thresholds. "
                "Please reposition camera, ask patient to keep still, and recapture."
            )

        return SafetyDecision(
            status=status,
            overall_quality_score=round(quality_score, 3),
            model_confidence=round(confidence, 2),
            reasons=sorted(set(reasons)),
            human_review_required=True,
            retake_guidance=retake_guidance,
            safety_state="REJECTED",
            automation_level="UNABLE_TO_CLASSIFY",
            clinical_action_allowed=False,
            screening_eligibility="INELIGIBLE",
            metadata={"quality_decision": quality_decision},
        )

    # Borderline quality
    if quality_decision == "ENHANCE" or quality_score < 0.65:
        reasons.append("QUALITY_BORDERLINE")
        human_review_required = True

    # Low model confidence
    if confidence < 70.0:
        reasons.append("LOW_MODEL_CONFIDENCE")
        human_review_required = True

    # Model agreement check if secondary model available
    if sec and "stage" in sec:
        sec_stage = int(sec.get("stage", 0) or 0)
        stage_diff = abs(primary_stage - sec_stage)
        if stage_diff >= 2:
            reasons.append("MODEL_DISAGREEMENT_SIGNIFICANT")
            human_review_required = True
        elif stage_diff == 1:
            reasons.append("MODEL_DISAGREEMENT_MINOR")

    # High severity automatically mandates human clinician verification
    if primary_stage >= 2:
        reasons.append("REFERABLE_GRADE_VERIFICATION")
        human_review_required = True

    # Decide status
    if "QUALITY_BORDERLINE" in reasons or "LOW_MODEL_CONFIDENCE" in reasons or "MODEL_DISAGREEMENT_SIGNIFICANT" in reasons:
        status = "UNCERTAIN"
        safety_state = "UNCERTAIN"
        automation_level = "HUMAN_REVIEW_REQUIRED"
        screening_eligibility = "REQUIRES_CONFIRMATION"
        clinical_action_allowed = False
        retake_guidance = (
            "Screening confidence is borderline. Clinician inspection of raw fundus image is recommended."
        )
    else:
        status = "PROCEED"
        safety_state = "VERIFIED"
        automation_level = "AUTOMATED_ASSISTANCE"
        screening_eligibility = "ELIGIBLE"
        clinical_action_allowed = True
        reasons.append("SCREENING_VALID")

    return SafetyDecision(
        status=status,
        overall_quality_score=round(quality_score, 3),
        model_confidence=round(confidence, 2),
        reasons=sorted(set(reasons)),
        human_review_required=human_review_required,
        retake_guidance=retake_guidance,
        safety_state=safety_state,
        automation_level=automation_level,
        clinical_action_allowed=clinical_action_allowed,
        screening_eligibility=screening_eligibility,
        metadata={"primary_stage": primary_stage, "quality_decision": quality_decision},
    )
