"""Deterministic referral/triage policy for screening outputs."""

from __future__ import annotations


def decide_referral(
    *,
    screening: dict,
    progression: dict | None = None,
    doctor_review_present: bool = False,
) -> dict:
    """
    Determine triage priority based on deterministic policy rules.

    Policy intentionally separates ML outputs from decision governance.
    """
    stage = int(screening.get("stage") or 0)
    confidence = float(screening.get("confidence") or 0.0)

    reason_codes: list[str] = []
    priority = "ROUTINE"
    human_review_required = False

    if stage >= 4:
        priority = "URGENT"
        reason_codes.append("STAGE_PROLIFERATIVE")
    elif stage >= 3:
        priority = "URGENT"
        reason_codes.append("STAGE_SEVERE")
    elif stage >= 2:
        priority = "EARLY"
        reason_codes.append("STAGE_REFERABLE")
    else:
        reason_codes.append("STAGE_LOW")

    if confidence < 70.0:
        reason_codes.append("LOW_MODEL_CONFIDENCE")
        human_review_required = True

    if progression:
        predicted = progression.get("predicted_risk") or {}
        risk_category = str(predicted.get("risk_category") or "").upper()
        if risk_category == "HIGH":
            if priority != "URGENT":
                priority = "URGENT"
            reason_codes.append("PROGRESSION_HIGH_RISK")
        elif risk_category == "MODERATE" and priority == "ROUTINE":
            priority = "EARLY"
            reason_codes.append("PROGRESSION_MODERATE_RISK")

        if predicted.get("uncertainty_flags"):
            reason_codes.append("PROGRESSION_UNCERTAINTY")
            human_review_required = True

    if not doctor_review_present and priority in {"EARLY", "URGENT"}:
        human_review_required = True
        reason_codes.append("DOCTOR_REVIEW_PENDING")

    codes = sorted(set(reason_codes))
    return {
        "priority": priority,
        "reasonCodes": codes,
        "reason_codes": codes,
        "humanReviewRequired": human_review_required,
        "human_review_required": human_review_required,
        "disclaimer": (
            "Referral priority is a screening-support policy outcome and does not "
            "replace clinical diagnosis."
        ),
    }
