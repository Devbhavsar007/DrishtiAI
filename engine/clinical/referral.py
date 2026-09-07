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
    safety_state = str(screening.get("safety_state") or "").upper()
    valid_anatomy = screening.get("valid_anatomy")
    eligibility = str(screening.get("screening_eligibility") or "").upper()

    # Safety Invariant: Failure states must NEVER be treated as normal low-stage screening
    if (
        safety_state in ("REJECTED", "ANATOMY_FAILED", "QUALITY_FAILED", "BLOCKED", "MODEL_FAILURE")
        or valid_anatomy is False
        or eligibility == "INELIGIBLE"
    ):
        fail_codes = ["AUTOMATED_SCREENING_INELIGIBLE"]
        if safety_state == "ANATOMY_FAILED" or valid_anatomy is False:
            fail_codes.append("ANATOMY_FAILED_RETAKE_REQUIRED")
        elif safety_state == "QUALITY_FAILED":
            fail_codes.append("QUALITY_FAILED_RETAKE_REQUIRED")
        elif safety_state == "MODEL_FAILURE":
            fail_codes.append("MODEL_FAILURE_REQUIRES_MANUAL_GRADING")
        else:
            fail_codes.append("SAFETY_REJECTION_RETAKE_REQUIRED")
        return {
            "priority": "RETAKE_OR_SPECIALIST_EVALUATION",
            "reasonCodes": sorted(fail_codes),
            "reason_codes": sorted(fail_codes),
            "humanReviewRequired": True,
            "human_review_required": True,
            "disclaimer": (
                "Automated screening could not be completed safely. "
                "Retake image or refer for in-person comprehensive ophthalmology examination."
            ),
        }

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
