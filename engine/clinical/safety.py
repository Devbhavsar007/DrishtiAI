"""Deterministic Safety and Confidence Decision Engine for DrishtiAI."""

from __future__ import annotations

from typing import Any
from engine.contracts.safety import SafetyDecision
from engine.safety.decision_engine import SafetyDecisionEngine, SafetyEvaluationResult
from engine.safety.image_validator import ImageValidationResult


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
    by delegating directly to the unified authoritative SafetyDecisionEngine.
    Guarantees consistent safety arbitration across all API endpoints and pipelines.
    """
    qa = quality_assessment or {}
    pred = primary_prediction or {}
    sec = secondary_prediction or {}

    q_dec = str(qa.get("decision", "ACCEPT")).upper()
    q_score = _to_float(qa.get("quality_score"), 0.85)

    is_valid_quality = (q_dec != "REJECT" and q_score >= 0.40)
    image_val = ImageValidationResult(
        valid=is_valid_quality,
        error="Image quality rejected" if not is_valid_quality else None,
    )

    engine = SafetyDecisionEngine()
    result: SafetyEvaluationResult = engine.evaluate(
        image_val=image_val,
        primary_detection=pred,
        secondary_detection=sec,
        quality_assessment=qa,
    )

    # Reconcile legacy reason codes for contract parity
    reasons = list(result.reason_codes)
    if "LOW_CONFIDENCE" in reasons:
        reasons.remove("LOW_CONFIDENCE")
        reasons.append("LOW_MODEL_CONFIDENCE")
    if "MODEL_DISAGREEMENT" in reasons:
        reasons.remove("MODEL_DISAGREEMENT")
        reasons.append("MODEL_DISAGREEMENT_SIGNIFICANT")
    if "REFERABLE_DR_DETECTED" in reasons:
        reasons.remove("REFERABLE_DR_DETECTED")
        reasons.append("REFERABLE_GRADE_VERIFICATION")
    if not reasons and result.safety_state == "VERIFIED":
        reasons.append("SCREENING_VALID")

    retake_guidance = result.mitigation_instructions
    if result.status == "UNCERTAIN" and not retake_guidance:
        retake_guidance = "Screening confidence is borderline. Clinician inspection of raw fundus image is recommended."

    primary_stage = int(pred.get("stage", 0) or 0)
    confidence = _to_float(pred.get("confidence"), 0.0)

    return SafetyDecision(
        status=result.status,
        overall_quality_score=round(q_score, 3),
        model_confidence=round(confidence, 2),
        reasons=sorted(set(reasons)),
        human_review_required=result.human_review_required,
        retake_guidance=retake_guidance,
        safety_state=result.safety_state,
        automation_level=result.automation_level,
        clinical_action_allowed=result.clinical_action_allowed,
        screening_eligibility=result.screening_eligibility,
        metadata={"primary_stage": primary_stage, "quality_decision": q_dec, "engine": "SafetyDecisionEngine"},
    )
