"""Deterministic progression risk estimation for longitudinal retinal screening."""

from __future__ import annotations

from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _stage_from_scan(scan: dict) -> int:
    """Extract stage from scan payloads used across v1/v2/v3 persistence shapes."""
    if not isinstance(scan, dict):
        return 0
    if "stage" in scan:
        return int(scan.get("stage") or 0)
    detection = scan.get("detection") or {}
    return int(detection.get("stage") or 0)


def _confidence_from_scan(scan: dict) -> float:
    if not isinstance(scan, dict):
        return 0.0
    if "confidence" in scan:
        return _to_float(scan.get("confidence"), 0.0)
    detection = scan.get("detection") or {}
    return _to_float(detection.get("confidence"), 0.0)


def _latest_previous_scan(current_scan_id: str, previous_scans: list[dict] | None) -> dict | None:
    if not previous_scans:
        return None
    for s in previous_scans:
        if str(s.get("id", "")) != str(current_scan_id):
            return s
    return None


def assess_progression_risk(
    *,
    current_scan: dict,
    previous_scans: list[dict] | None = None,
    patient_profile: dict | None = None,
) -> dict:
    """
    Build deterministic progression-risk estimation.

    Notes:
    - This is an evidence-informed rule engine, not a learned longitudinal model.
    - Output intentionally separates observed data, predicted risk, and recommendation.
    """
    current_stage = _stage_from_scan(current_scan)
    current_conf = _confidence_from_scan(current_scan)

    base_risk_map = {
        0: 0.10,
        1: 0.18,
        2: 0.40,
        3: 0.65,
        4: 0.82,
    }
    six_month = base_risk_map.get(current_stage, 0.10)
    supporting_factors: list[str] = []

    prev_scan = _latest_previous_scan(str(current_scan.get("id", "")), previous_scans)
    prev_stage = _stage_from_scan(prev_scan) if prev_scan else None
    stage_delta = None
    if prev_stage is not None:
        stage_delta = current_stage - prev_stage
        if stage_delta > 0:
            six_month += min(0.12 * stage_delta, 0.24)
            supporting_factors.append("worsening retinal grade")
        elif stage_delta < 0:
            six_month -= min(0.08 * abs(stage_delta), 0.16)
            supporting_factors.append("improved retinal grade since previous screening")
        elif current_stage >= 2:
            six_month += 0.05
            supporting_factors.append("persistent referable abnormal screening")

    if patient_profile:
        hba1c = _to_float(patient_profile.get("hba1c"), 0.0)
        duration = _to_float(patient_profile.get("diabetes_duration"), 0.0)
        sugar = _to_float(patient_profile.get("sugar_level"), 0.0)

        if hba1c >= 9.0:
            six_month += 0.12
            supporting_factors.append("poor glycemic control (HbA1c >= 9.0)")
        elif hba1c >= 8.0:
            six_month += 0.08
            supporting_factors.append("suboptimal glycemic control (HbA1c >= 8.0)")

        if duration >= 10.0:
            six_month += 0.06
            supporting_factors.append("long diabetes duration")

        if sugar >= 180.0:
            six_month += 0.05
            supporting_factors.append("elevated blood glucose")

    uncertainty_flags: list[str] = []
    if prev_stage is None:
        longitudinal_state = "LIMITED_LONGITUDINAL_HISTORY"
        uncertainty_flags.append("limited longitudinal history")
        progression_msg = "Progression prediction unavailable: insufficient longitudinal data."
    elif current_scan.get("stage") is None and current_scan.get("detection") is None:
        longitudinal_state = "LONGITUDINAL_UNAVAILABLE"
        progression_msg = "Progression prediction unavailable: current scan data incomplete."
    else:
        longitudinal_state = "LONGITUDINAL_SUPPORTED"
        progression_msg = None

    if current_conf < 70.0:
        uncertainty_flags.append("low model confidence")

    six_month = max(0.02, min(six_month, 0.99))
    twelve_month = max(0.05, min(six_month + 0.10, 0.99))

    if six_month >= 0.60:
        risk_category = "HIGH"
        follow_up_priority = "HIGH"
    elif six_month >= 0.30:
        risk_category = "MODERATE"
        follow_up_priority = "MEDIUM"
    else:
        risk_category = "LOW"
        follow_up_priority = "LOW"

    if not supporting_factors:
        supporting_factors.append("current retinal grade")

    return {
        "engine": "deterministic_progression_v1",
        "longitudinal_state": longitudinal_state,
        "progression_availability_message": progression_msg,
        "is_individualized_prediction": longitudinal_state == "LONGITUDINAL_SUPPORTED",
        "observed_data": {
            "current_stage": current_stage,
            "previous_stage": prev_stage,
            "stage_delta": stage_delta,
            "current_confidence": round(current_conf, 2),
        },
        "predicted_risk": {
            "risk_category": risk_category,
            "six_month_risk": round(six_month, 3),
            "twelve_month_risk": round(twelve_month, 3),
            "supporting_factors": supporting_factors,
            "uncertainty_flags": uncertainty_flags,
            "longitudinal_state": longitudinal_state,
        },
        "clinical_recommendation": {
            "follow_up_priority": follow_up_priority,
            "human_review_recommended": bool(uncertainty_flags),
            "note": (
                "This is a screening-oriented progression estimate. "
                "It does not replace clinician judgment."
            ),
        },
    }
