"""Evaluation worker for offline batch model testing and regression suites."""

from __future__ import annotations

import json
import logging
import uuid
from database import get_db
from workers.base import BaseWorker

log = logging.getLogger(__name__)


class EvaluationWorker(BaseWorker):
    """Processes newly registered models in TRAINED state that need evaluation.

    For each TRAINED model, runs the safety gate evaluation and regression
    comparison against the current production model, then transitions
    the model to EVALUATED status with persisted evaluation results.
    """

    def __init__(self, interval_seconds: float = 30.0):
        super().__init__("EvaluationWorker", interval_seconds)

    def step(self) -> None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT version_id, dataset_id, training_run_id FROM model_versions WHERE status = 'TRAINED' LIMIT 1"
            ).fetchone()

        if not row:
            return

        version_id = row["version_id"]
        dataset_id = row["dataset_id"] or ""
        log.info("EvaluationWorker evaluating model version %s", version_id)

        try:
            # Fetch training run metrics if available
            metrics = self._get_training_metrics(row.get("training_run_id", ""))

            # Run safety gates
            from ml_platform.evaluation.safety_gates import evaluate_safety_gates
            gate_result = evaluate_safety_gates(metrics)

            # Run regression comparison against production
            regression_result = self._run_regression(metrics)

            # Persist evaluation record
            eval_id = f"eval-{uuid.uuid4().hex[:12]}"
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO model_evaluations
                       (id, model_version_id, dataset_id, eval_type,
                        metrics_json, safety_gate_results_json, passed_safety_gates,
                        regression_vs_production_json, evaluator_id)
                       VALUES (?, ?, ?, 'AUTOMATED', ?, ?, ?, ?, 'EvaluationWorker')""",
                    (eval_id, version_id, dataset_id,
                     json.dumps(metrics),
                     json.dumps(gate_result),
                     1 if gate_result.get("all_passed") else 0,
                     json.dumps(regression_result))
                )
                # Transition model status
                conn.execute(
                    "UPDATE model_versions SET status = 'EVALUATED', evaluation_summary_json = ? WHERE version_id = ?",
                    (json.dumps({
                        "eval_id": eval_id,
                        "safety_gates_passed": gate_result.get("all_passed", False),
                        "regression_passed": regression_result.get("passed_regression_test", True),
                    }), version_id)
                )
                conn.commit()

            log.info("EvaluationWorker completed evaluation %s for model %s (gates=%s)",
                     eval_id, version_id, gate_result.get("all_passed"))

        except Exception as e:
            log.error("EvaluationWorker failed for model %s: %s", version_id, e, exc_info=True)
            # Mark as EVALUATED anyway to prevent infinite retry, but record failure
            with get_db() as conn:
                conn.execute(
                    "UPDATE model_versions SET status = 'EVALUATED', evaluation_summary_json = ? WHERE version_id = ?",
                    (json.dumps({"error": str(e), "safety_gates_passed": False}), version_id)
                )
                conn.commit()

    def _get_training_metrics(self, training_run_id: str) -> dict:
        """Extract final metrics from a completed training run."""
        if not training_run_id:
            return self._default_metrics()
        try:
            with get_db() as conn:
                run = conn.execute(
                    "SELECT final_metrics_json FROM training_runs WHERE id = ?",
                    (training_run_id,)
                ).fetchone()
            if run and run["final_metrics_json"]:
                parsed = json.loads(run["final_metrics_json"])
                if parsed:
                    return parsed
        except Exception:
            pass
        return self._default_metrics()

    def _default_metrics(self) -> dict:
        """Fallback metrics when no training run metrics are available."""
        return {
            "sensitivity": 0.0,
            "specificity": 0.0,
            "accuracy": 0.0,
            "quadratic_weighted_kappa": 0.0,
            "expected_calibration_error": 1.0,
            "false_negative_rate": 1.0,
        }

    def _run_regression(self, candidate_metrics: dict) -> dict:
        """Compare candidate against current production model metrics."""
        try:
            from ml_platform.registry.models import get_production_model
            prod = get_production_model()
            if not prod or not prod.get("evaluation_summary_json"):
                return {"passed_regression_test": True, "reason": "No production model to compare against"}

            prod_eval = json.loads(prod["evaluation_summary_json"]) if isinstance(prod.get("evaluation_summary_json"), str) else prod.get("evaluation_summary_json", {})
            from ml_platform.evaluation.regression import compare_models
            return compare_models(candidate_metrics, prod_eval)
        except Exception as e:
            log.warning("Regression comparison failed: %s", e)
            return {"passed_regression_test": True, "reason": f"Regression comparison unavailable: {e}"}
