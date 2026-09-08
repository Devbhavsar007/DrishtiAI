"""Clinical discordance drift monitoring.

Monitors real-world doctor-AI agreement rates over time to detect clinical drift
before catastrophic errors occur in deployed models.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from database import get_db
from config_admin import DRIFT_CONFIG

log = logging.getLogger(__name__)


def evaluate_clinical_discordance(
    days: int = 30,
    model_version_id: str | None = None,
    persist_event: bool = True,
) -> dict[str, Any]:
    """
    Query doctor reviews from the past N days and compute concordance with AI grading.
    """
    with get_db() as conn:
        # Fetch scans that have doctor reviews
        rows = conn.execute(
            """SELECT s.id as scan_id, s.stage as ai_stage,
                      dr.decision, dr.original_stage, dr.adjusted_stage, dr.created_at
               FROM doctor_reviews dr
               JOIN scans s ON dr.scan_id = s.id
               WHERE dr.created_at >= datetime('now', ?)
               ORDER BY dr.created_at DESC""",
            (f"-{days} days",),
        ).fetchall()

    total_reviews = len(rows)
    if total_reviews < DRIFT_CONFIG["min_samples_for_drift"]:
        return {
            "status": "INSUFFICIENT_DATA",
            "sample_count": total_reviews,
            "min_required": DRIFT_CONFIG["min_samples_for_drift"],
            "severity": "NONE",
        }

    agreements = sum(
        1 for r in rows
        if (r["adjusted_stage"] is None or r["adjusted_stage"] == r["original_stage"])
        and r["decision"] in ("AGREE", "CONFIRMED", "APPROVED")
    )
    discordant = total_reviews - agreements
    discordance_rate = round(discordant / total_reviews, 4)

    warn_thresh = DRIFT_CONFIG["clinical_discordance_warning"]
    crit_thresh = DRIFT_CONFIG["clinical_discordance_critical"]

    severity = "NONE"
    if discordance_rate >= crit_thresh:
        severity = "CRITICAL"
    elif discordance_rate >= warn_thresh:
        severity = "WARNING"

    result = {
        "status": "EVALUATED",
        "total_reviews": total_reviews,
        "agreements": agreements,
        "discordant": discordant,
        "discordance_rate": discordance_rate,
        "severity": severity,
        "warning_threshold": warn_thresh,
        "critical_threshold": crit_thresh,
        "window_days": days,
    }

    if persist_event and severity in ("WARNING", "CRITICAL"):
        event_id = f"drift-{uuid.uuid4().hex[:12]}"
        mv_fk = model_version_id if model_version_id else None
        with get_db() as conn:
            conn.execute(
                """INSERT INTO drift_events
                   (id, model_version_id, drift_type, severity, metrics_json, details)
                   VALUES (?, ?, 'CLINICAL_DISCORDANCE', ?, ?, ?)""",
                (
                    event_id,
                    mv_fk,
                    severity,
                    json.dumps({
                        "metric_name": "discordance_rate",
                        "metric_value": discordance_rate,
                        "threshold": crit_thresh if severity == "CRITICAL" else warn_thresh,
                    }),
                    json.dumps(result),
                ),
            )
            conn.commit()
        result["drift_event_id"] = event_id
        log.warning("Recorded clinical drift event %s (%s, rate=%.2f)", event_id, severity, discordance_rate)

    return result
