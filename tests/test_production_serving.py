from datetime import date, timedelta
import pytest

from features.feature_artifact import FeatureArtifact
from features.feature_versioning import FeatureVersionIdentity
from analytics.retraining_decision import RetrainingEvidence, build_retraining_decision_report
from analytics.retraining_dataset import build_retraining_dataset_report
from analytics.automated_retraining import build_automated_retraining_report
from analytics.post_retraining_validation import build_post_retraining_validation_report
from analytics.model_version_lifecycle import build_model_version, CANDIDATE
from analytics.model_rollout import build_model_rollout_plan, authorize_model_rollout
from analytics.production_activation import (
    build_production_activation_plan, execute_production_activation,
)
from analytics.production_serving import *

def activation_receipt():
    identity = FeatureVersionIdentity("68-test", "x", "sha256", "x")
    artifacts = tuple(
        FeatureArtifact(
            date(2026, 1, 1) + timedelta(days=i), "68-test",
            ("f1", "f2"), {"f1": float(i), "f2": float(i % 3)},
            (), identity, "VALID", "CLEAN",
        ) for i in range(12)
    )
    decision = build_retraining_decision_report(
        "d68", "model68", "2026-09-30",
        (RetrainingEvidence(
            "performance_degradation", "miss_rate", .1, .3, .1,
            True, 1, "p", "p", "",
        ),),
    )
    d = build_retraining_dataset_report(
        "ds68", decision, artifacts,
        {a.target_date: i % 2 for i, a in enumerate(artifacts)}, "data68",
    )
    v = build_post_retraining_validation_report(
        "v68", build_automated_retraining_report("r68", d), d,
    )
    m = build_model_version(
        v.model_identity, "64.0.0", CANDIDATE, "selection-68",
        v.artifact_identity,
    )
    rollout = build_model_rollout_plan(
        "roll68", m, v, source_selection_identity="selection-68",
        authorization_id="auth68",
    )
    authorized = authorize_model_rollout(rollout, "auth68")
    activation = build_production_activation_plan("activation68", authorized, m)
    result = execute_production_activation(activation, m)
    assert result.is_valid
    return result.receipt

def plan():
    return build_serving_plan("serving68", activation_receipt())

def request():
    r = activation_receipt()
    return build_inference_request(
        "request68", r.model_identity, r.model_version,
        r.artifact_identity, {"f1": 1, "f2": 2},
    )

def predictor(features):
    return round(features["f1"] + features["f2"], 4)
def test_01_version():
    assert PRODUCTION_SERVING_VERSION == "68.0.0"

def test_02_policy_valid():
    validate_serving_policy(ServingPolicy())

def test_03_plan_ready():
    assert plan().status == READY

def test_04_plan_state():
    assert plan().serving_state == READY

def test_05_plan_valid():
    assert validate_serving_plan(plan()).is_valid

def test_06_checks():
    assert len(serving_checks(plan())) >= 6

def test_07_failed_checks():
    assert serving_failed_checks(plan()) == ()

def test_08_summary():
    assert serving_summary(plan())["status"] == VALID

def test_09_request_valid():
    r = request()
    assert r.request_id == "request68"
    assert r.features == (("f1", 1.0), ("f2", 2.0))

def test_10_request_hash():
    assert request().request_hash.startswith("production-serving-")

def test_11_serve():
    result = serve_inference(plan(), request(), predictor)
    assert result.is_valid
    assert result.response.prediction == 3.0

def test_12_response_valid():
    result = serve_inference(plan(), request(), predictor)
    assert validate_inference_response(result.response).is_valid

def test_13_response_identity():
    result = serve_inference(plan(), request(), predictor)
    assert inference_response_identity(result.response) == result.response.response_identity

def test_14_predict_helper():
    assert predict_with_mapping(plan(), request(), predictor) == 3.0

def test_15_deterministic_response():
    a = serve_inference(plan(), request(), predictor).response
    b = serve_inference(plan(), request(), predictor).response
    assert a.response_identity == b.response_identity

def test_16_policy_type():
    with pytest.raises(TypeError):
        validate_serving_policy(object())

def test_17_policy_boolean():
    with pytest.raises(ValueError):
        validate_serving_policy(ServingPolicy(require_feature_mapping="x"))

def test_18_feature_type():
    with pytest.raises(TypeError):
        validate_feature_mapping(object())

def test_19_feature_empty():
    with pytest.raises(ValueError):
        validate_feature_mapping({})

def test_20_feature_name():
    with pytest.raises(ValueError):
        validate_feature_mapping({"": 1})
def test_21_feature_bool_rejected():
    with pytest.raises(ValueError):
        validate_feature_mapping({"f1": True})

def test_22_feature_text_rejected():
    with pytest.raises(ValueError):
        validate_feature_mapping({"f1": "1"})

def test_23_nan_rejected():
    with pytest.raises(ValueError):
        validate_feature_mapping({"f1": float("nan")})

def test_24_inf_rejected():
    with pytest.raises(ValueError):
        validate_feature_mapping({"f1": float("inf")})

def test_25_empty_request_id():
    r = activation_receipt()
    with pytest.raises(ValueError):
        build_inference_request("", r.model_identity, r.model_version, r.artifact_identity, {"f1": 1})

def test_26_empty_model_identity():
    r = activation_receipt()
    with pytest.raises(ValueError):
        build_inference_request("x", "", r.model_version, r.artifact_identity, {"f1": 1})

def test_27_empty_features():
    r = activation_receipt()
    with pytest.raises(ValueError):
        build_inference_request("x", r.model_identity, r.model_version, r.artifact_identity, {})

def test_28_receipt_type():
    with pytest.raises(TypeError):
        build_serving_plan("x", object())

def test_29_empty_serving_id():
    with pytest.raises(ValueError):
        build_serving_plan("", activation_receipt())

def test_30_invalid_plan_type():
    assert not validate_serving_plan(object()).is_valid

def test_31_invalid_request_type():
    result = serve_inference(plan(), object(), predictor)
    assert result.status == INVALID

def test_32_invalid_predictor():
    result = serve_inference(plan(), request(), object())
    assert result.status == INVALID

def test_33_model_identity_mismatch():
    r = activation_receipt()
    bad = build_inference_request("x", "other", r.model_version, r.artifact_identity, {"f1": 1})
    assert serve_inference(plan(), bad, predictor).status == INVALID

def test_34_version_mismatch():
    r = activation_receipt()
    bad = build_inference_request("x", r.model_identity, "other", r.artifact_identity, {"f1": 1})
    assert serve_inference(plan(), bad, predictor).status == INVALID

def test_35_artifact_mismatch():
    r = activation_receipt()
    bad = build_inference_request("x", r.model_identity, r.model_version, "other", {"f1": 1})
    assert serve_inference(plan(), bad, predictor).status == INVALID
def test_36_request_hash_mismatch():
    r = request()
    bad = type(r)(
        r.request_id, r.model_identity, r.model_version, r.artifact_identity,
        r.features, "bad",
    )
    assert serve_inference(plan(), bad, predictor).status == INVALID

def test_37_predictor_error():
    def bad(_):
        raise RuntimeError("boom")
    result = serve_inference(plan(), request(), bad)
    assert result.status == INVALID
    assert result.issues[0].startswith("PREDICTOR_ERROR:")

def test_38_response_status():
    response = serve_inference(plan(), request(), predictor).response
    assert response.status == INFERENCE_ACCEPTED

def test_39_response_deterministic():
    response = serve_inference(plan(), request(), predictor).response
    assert response.deterministic is True

def test_40_response_request_id():
    response = serve_inference(plan(), request(), predictor).response
    assert response.request_id == "request68"

def test_41_response_serving_id():
    response = serve_inference(plan(), request(), predictor).response
    assert response.serving_id == "serving68"

def test_42_response_model_identity():
    r = activation_receipt()
    response = serve_inference(plan(), request(), predictor).response
    assert response.model_identity == r.model_identity

def test_43_response_version():
    response = serve_inference(plan(), request(), predictor).response
    assert response.model_version == activation_receipt().model_version

def test_44_response_artifact():
    response = serve_inference(plan(), request(), predictor).response
    assert response.artifact_identity == activation_receipt().artifact_identity

def test_45_response_prediction():
    assert serve_inference(plan(), request(), predictor).response.prediction == 3.0

def test_46_response_hash():
    response = serve_inference(plan(), request(), predictor).response
    assert response.request_hash == request().request_hash

def test_47_response_identity_prefix():
    response = serve_inference(plan(), request(), predictor).response
    assert response.response_identity.startswith("production-serving-")

def test_48_response_accessor_invalid():
    with pytest.raises(ValueError):
        inference_response_identity(object())

def test_49_predict_helper_invalid():
    with pytest.raises(ValueError):
        predict_with_mapping(plan(), request(), lambda _: (_ for _ in ()).throw(RuntimeError()))

def test_50_plan_identity_prefix():
    assert plan().plan_identity.startswith("production-serving-")
def test_51_activation_bound():
    assert plan().activation_id == "activation68"

def test_52_model_bound():
    assert plan().model_identity == activation_receipt().model_identity

def test_53_version_bound():
    assert plan().model_version == activation_receipt().model_version

def test_54_artifact_bound():
    assert plan().artifact_identity == activation_receipt().artifact_identity

def test_55_policy_defaults():
    assert plan().policy == ServingPolicy()

def test_56_check_pass():
    assert all(c.status == "PASS" for c in serving_checks(plan()))

def test_57_summary_version():
    assert serving_summary(plan())["version"] == "68.0.0"

def test_58_summary_serving():
    assert serving_summary(plan())["serving_id"] == "serving68"

def test_59_summary_activation():
    assert serving_summary(plan())["activation_id"] == "activation68"

def test_60_summary_failures():
    assert serving_summary(plan())["failed_checks"] == ()

def test_61_response_validation():
    response = serve_inference(plan(), request(), predictor).response
    assert validate_inference_response(response).status == VALID

def test_62_response_accessor_repeatable():
    response = serve_inference(plan(), request(), predictor).response
    assert inference_response_identity(response) == inference_response_identity(response)

def test_63_feature_sorting():
    assert validate_feature_mapping({"z": 1, "a": 2}) == (("a", 2.0), ("z", 1.0))

def test_64_int_normalization():
    assert validate_feature_mapping({"f": 2}) == (("f", 2.0),)

def test_65_float_preservation():
    assert validate_feature_mapping({"f": 2.5}) == (("f", 2.5),)

def test_66_request_features_tuple():
    assert isinstance(request().features, tuple)

def test_67_plan_checks_tuple():
    assert isinstance(plan().checks, tuple)

def test_68_plan_policy():
    assert isinstance(plan().policy, ServingPolicy)

def test_69_result_empty_issues():
    assert serve_inference(plan(), request(), predictor).issues == ()

def test_70_result_has_response():
    assert serve_inference(plan(), request(), predictor).response is not None

def test_70_plan_identity_detects_tampering():
    p = plan()
    bad = type(p)(p.serving_id,p.activation_id,p.model_identity,p.model_version,p.artifact_identity,p.policy,p.checks,p.status,p.serving_state,"tampered")
    assert not validate_serving_plan(bad).is_valid

def test_71_response_identity_detects_tampering():
    response = serve_inference(plan(), request(), predictor).response
    tampered = type(response)(
        response.request_id,
        response.serving_id,
        response.model_identity,
        response.model_version,
        "tampered-artifact",
        response.prediction,
        response.request_hash,
        response.response_identity,
        response.status,
        response.deterministic,
    )
    result = validate_inference_response(tampered)
    assert result.status == INVALID
    assert "INVALID_RESPONSE_IDENTITY" in result.issues
