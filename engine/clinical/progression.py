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


def _latest_previous_scan(
    current_scan_or_id: str | dict,
    previous_scans: list[dict] | None,
    current_eye: str | None = None
) -> dict | None:
    if not previous_scans:
        return None
    if isinstance(current_scan_or_id, dict):
        current_scan_id = str(current_scan_or_id.get("id", ""))
        if not current_eye:
            current_eye = current_scan_or_id.get("laterality") or current_scan_or_id.get("eye")
    else:
        current_scan_id = str(current_scan_or_id)

    for s in previous_scans:
        if str(s.get("id", "")) == str(current_scan_id):
            continue

        # Invariant: Never compare progression across opposite eyes (OD vs OS)
        prev_eye = s.get("laterality") or s.get("eye")
        if current_eye and prev_eye and str(current_eye).upper() != str(prev_eye).upper():
            continue

        # Invariant: Never consume previous scans that failed safety or anatomical verification
        prev_safety = str(s.get("safety_state") or "").upper()
        if prev_safety in ("REJECTED", "ANATOMY_FAILED", "QUALITY_FAILED", "BLOCKED"):
            continue
        if s.get("valid_anatomy") is False:
            continue

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
    # Guard: Do not calculate progression from unsafe current scan
    curr_safety = str(current_scan.get("safety_state") or "").upper()
    if curr_safety in ("REJECTED", "ANATOMY_FAILED", "QUALITY_FAILED") or current_scan.get("valid_anatomy") is False:
        return {
            "engine": "deterministic_progression_v1",
            "longitudinal_state": "LONGITUDINAL_UNAVAILABLE",
            "progression_availability_message": "Progression prediction unavailable: current scan failed safety or anatomical validation.",
            "is_individualized_prediction": False,
            "observed_data": {
                "current_stage": current_scan.get("stage"),
                "previous_stage": None,
                "stage_delta": None,
                "current_confidence": 0.0,
            },
            "predicted_risk": {
                "risk_category": "UNKNOWN",
                "six_month_risk": 0.0,
                "twelve_month_risk": 0.0,
                "supporting_factors": ["unsafe current study"],
                "uncertainty_flags": ["current scan ineligible for progression calculation"],
                "longitudinal_state": "LONGITUDINAL_UNAVAILABLE",
            },
            "clinical_recommendation": {
                "follow_up_priority": "UNKNOWN",
                "human_review_recommended": True,
                "note": "Progression suppressed due to invalid current study.",
            },
        }

    current_stage = _stage_from_scan(current_scan)
    current_conf = _confidence_from_scan(current_scan)
    current_eye = current_scan.get("laterality") or current_scan.get("eye")

    base_risk_map = {
        0: 0.10,
        1: 0.18,
        2: 0.40,
        3: 0.65,
        4: 0.82,
    }
    six_month = base_risk_map.get(current_stage, 0.10)
    supporting_factors: list[str] = []
    uncertainty_flags: list[str] = []

    prev_scan = _latest_previous_scan(current_scan, previous_scans, current_eye=current_eye)
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
            # Biological plausibility check: Severe grade regressing to Stage 0
            if prev_stage >= 3 and current_stage == 0:
                uncertainty_flags.append("ANOMALOUS_RAPID_REGRESSION_DETECTED: Stage >=3 to Stage 0 requires clinician verification")
        elif current_stage >= 2:
            six_month += 0.05
            supporting_factors.append("persistent referable abnormal screening")

        # Scan interval check if timestamps are present
        try:
            from datetime import datetime
            c_time_str = current_scan.get("created_at")
            p_time_str = prev_scan.get("created_at")
            if c_time_str and p_time_str:
                c_dt = datetime.fromisoformat(c_time_str.replace("Z", "+00:00"))
                p_dt = datetime.fromisoformat(p_time_str.replace("Z", "+00:00"))
                delta = c_dt - p_dt
                days = abs(delta.days if hasattr(delta, "days") else int(delta.total_seconds() / 86400))
                if days < 7:
                    uncertainty_flags.append("ACUTE_REPEAT_SCAN_SUPPRESSED: scan interval < 7 days; acute duplicate capture suspected")
                elif days > 36 * 30:
                    uncertainty_flags.append("EXTENDED_GAP_REDUCED_FIDELITY: long scan interval (> 36 months); historical baseline has reduced predictive fidelity")
        except Exception:
            pass

    if patient_profile:
        raw_hba1c = patient_profile.get("hba1c")
        raw_duration = patient_profile.get("diabetes_duration")
        raw_sugar = patient_profile.get("sugar_level")

        # Explicit missing value handling (missing != 0.0)
        if raw_hba1c is not None:
            try:
                hba1c = float(raw_hba1c)
                if 3.0 <= hba1c <= 20.0:
                    if hba1c >= 9.0:
                        six_month += 0.12
                        supporting_factors.append("poor glycemic control (HbA1c >= 9.0)")
                    elif hba1c >= 8.0:
                        six_month += 0.08
                        supporting_factors.append("suboptimal glycemic control (HbA1c >= 8.0)")
            except (TypeError, ValueError):
                pass

        if raw_duration is not None:
            try:
                duration = float(raw_duration)
                if 0.0 <= duration <= 80.0:
                    if duration >= 10.0:
                        six_month += 0.06
                        supporting_factors.append("long diabetes duration")
            except (TypeError, ValueError):
                pass

        if raw_sugar is not None:
            try:
                sugar = float(raw_sugar)
                if 20.0 <= sugar <= 1000.0:
                    if sugar >= 180.0:
                        six_month += 0.05
                        supporting_factors.append("elevated blood glucose")
            except (TypeError, ValueError):
                pass

    if prev_stage is None:
        longitudinal_state = "LIMITED_LONGITUDINAL_HISTORY"
        uncertainty_flags.append("limited longitudinal history")
        progression_msg = "Progression prediction unavailable: insufficient longitudinal data."
    elif current_scan.get("stage") is None and current_scan.get("detection") is None:
        longitudinal_state = "LONGITUDINAL_UNAVAILABLE"
        progression_msg = "Progression prediction unavailable: current scan data incomplete."
    elif any("scan interval < 7 days" in f for f in uncertainty_flags):
        longitudinal_state = "LIMITED_LONGITUDINAL_HISTORY"
        progression_msg = "Progression analysis suppressed: scan interval < 7 days."
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
