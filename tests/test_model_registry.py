"""Tests for Model Registry, Compatibility, and Safety Gates."""

import pytest
from ml_platform.registry.models import (
    register_model_version,
    transition_model_status,
    get_model_version,
    list_model_versions,
)
from ml_platform.registry.compatibility import check_runtime_compatibility
from ml_platform.evaluation.safety_gates import evaluate_safety_gates
from ml_platform.evaluation.regression import compare_models


def test_model_registration_and_transition():
    reg = register_model_version(
        architecture="pipeline_v3",
        created_by="ml_tester",
        status="TRAINED",
    )
    v_id = reg["version_id"]
    assert reg["status"] == "TRAINED"

    # Legal transition: TRAINED -> EVALUATED
    trans = transition_model_status(v_id, "EVALUATED", actor_id="ml_tester")
    assert trans["new_status"] == "EVALUATED"

    # Illegal transition: EVALUATED -> PRODUCTION (must be approved first)
    with pytest.raises(ValueError):
        transition_model_status(v_id, "PRODUCTION", actor_id="ml_tester")


def test_runtime_compatibility():
    valid = check_runtime_compatibility("resnet50", input_size=300, num_classes=5)
    assert valid["is_compatible"]
    assert len(valid["issues"]) == 0

    invalid = check_runtime_compatibility("unsupported_model_xyz", num_classes=3)
    assert not invalid["is_compatible"]
    assert len(invalid["issues"]) >= 2


def test_safety_gates_evaluation():
    high_performing_metrics = {
        "sensitivity": 0.92,
        "specificity": 0.88,
        "accuracy": 0.85,
        "quadratic_weighted_kappa": 0.82,
        "expected_calibration_error": 0.08,
        "false_negative_rate": 0.05,
    }
    res = evaluate_safety_gates(high_performing_metrics)
    assert res["all_passed"]
    assert res["promotion_eligible"]
    assert len(res["failed_gates"]) == 0

    poor_metrics = {
        "sensitivity": 0.70,  # Below 0.85
        "specificity": 0.88,
        "accuracy": 0.60,     # Below 0.75
        "quadratic_weighted_kappa": 0.50,
        "expected_calibration_error": 0.25,
        "false_negative_rate": 0.20,
    }
    res_poor = evaluate_safety_gates(poor_metrics)
    assert not res_poor["all_passed"]
    assert not res_poor["promotion_eligible"]
    assert len(res_poor["failed_gates"]) >= 3


def test_model_regression_comparison():
    prod = {"sensitivity": 0.90, "specificity": 0.88, "quadratic_weighted_kappa": 0.80, "false_negative_rate": 0.08}
    cand_better = {"sensitivity": 0.92, "specificity": 0.89, "quadratic_weighted_kappa": 0.82, "false_negative_rate": 0.06}

    comp_good = compare_models(cand_better, prod)
    assert comp_good["passed_regression_test"]
    assert comp_good["recommendation"] == "APPROVE_FOR_STAGING"

    cand_regressed = {"sensitivity": 0.85, "specificity": 0.80, "quadratic_weighted_kappa": 0.70, "false_negative_rate": 0.12}
    comp_bad = compare_models(cand_regressed, prod)
    assert not comp_bad["passed_regression_test"]
    assert comp_bad["recommendation"] == "REJECT_DUE_TO_REGRESSION"
