import pytest
from tests.test_production_serving import activation_receipt
from analytics.production_serving import build_serving_plan
from analytics.production_api import *

def service():
    receipt = activation_receipt()
    plan = build_serving_plan("serving69", receipt)
    return InferenceApiService(plan, predictor)

def failing_service():
    receipt = activation_receipt()
    plan = build_serving_plan("serving69-fail", receipt)
    def fail(_features):
        raise RuntimeError("boom")
    return InferenceApiService(plan, fail)

def predictor(features):
    return round(features["f1"] + features["f2"], 4)

def payload():
    receipt = activation_receipt()
    return {
        "request_id": "request69",
        "model_identity": receipt.model_identity,
        "model_version": receipt.model_version,
        "artifact_identity": receipt.artifact_identity,
        "features": {"f1": 1, "f2": 2},
    }

def client():
    return create_inference_app(service()).test_client()
def test_01_version(): assert PRODUCTION_API_VERSION == "69.0.0"
def test_02_boundary(): assert API_BOUNDARY == "PRODUCTION_API_BOUNDARY"
def test_03_policy_default(): validate_api_policy(ApiPolicy())
def test_04_policy_type():
    with pytest.raises(TypeError): validate_api_policy(object())
def test_05_policy_bool():
    with pytest.raises(ValueError): validate_api_policy(ApiPolicy(require_json_body="x"))
def test_06_policy_size_zero():
    with pytest.raises(ValueError): validate_api_policy(ApiPolicy(max_json_bytes=0))
def test_07_policy_size_bool():
    with pytest.raises(ValueError): validate_api_policy(ApiPolicy(max_json_bytes=True))
def test_08_service_type():
    with pytest.raises(TypeError): InferenceApiService(object(), predictor)
def test_09_service_plan(): assert service().serving_plan.serving_id == "serving69"
def test_10_service_policy(): assert service().policy == ApiPolicy()
def test_11_health_status(): assert service().health()["status"] == API_HEALTHY
def test_12_health_version(): assert service().health()["api_version"] == PRODUCTION_API_VERSION
def test_13_health_boundary(): assert service().health()["boundary"] == API_BOUNDARY
def test_14_health_service(): assert service().health()["service"] == "neurolytics-inference"
def test_15_readiness_valid(): assert service().readiness().is_valid
def test_16_readiness_http(): assert service().readiness().http_status == 200
def test_17_readiness_ready(): assert service().readiness().payload["status"] == API_READY
def test_18_readiness_serving_id(): assert service().readiness().payload["serving_id"] == "serving69"
def test_19_readiness_model(): assert service().readiness().payload["model_identity"]
def test_20_readiness_version(): assert service().readiness().payload["model_version"]
def test_21_readiness_artifact(): assert service().readiness().payload["artifact_identity"]
def test_22_summary_version(): assert api_summary(service())["api_version"] == "69.0.0"
def test_23_summary_routes(): assert api_summary(service())["routes"] == ("/health","/ready","/v1/inference")
def test_24_summary_ready(): assert api_summary(service())["readiness_status"] == API_ACCEPTED
def test_25_checks_count(): assert len(api_checks(service())) == 3
def test_26_checks_all_pass(): assert api_failed_checks(service()) == ()
def test_27_check_ids(): assert {c.check_id for c in api_checks(service())} == {"SERVING_PLAN","PREDICTOR","API_POLICY"}
def test_28_check_status(): assert all(c.status == "PASS" for c in api_checks(service()))
def test_29_service_infer(): assert service().infer(payload()).is_valid
def test_30_infer_http(): assert service().infer(payload()).http_status == 200
def test_31_infer_status(): assert service().infer(payload()).payload["status"] == API_ACCEPTED
def test_32_infer_prediction(): assert service().infer(payload()).payload["prediction"] == 3.0
def test_33_infer_request_id(): assert service().infer(payload()).payload["request_id"] == "request69"
def test_34_infer_serving_id(): assert service().infer(payload()).payload["serving_id"] == "serving69"
def test_35_infer_model(): assert service().infer(payload()).payload["model_identity"]
def test_36_infer_version(): assert service().infer(payload()).payload["model_version"]
def test_37_infer_artifact(): assert service().infer(payload()).payload["artifact_identity"]
def test_38_infer_request_hash(): assert service().infer(payload()).payload["request_hash"].startswith("production-serving-")
def test_39_infer_response_hash(): assert service().infer(payload()).payload["response_identity"].startswith("production-serving-")
def test_40_infer_deterministic(): assert service().infer(payload()).payload["deterministic"] is True
def test_41_missing_request():
    p=payload(); p.pop("request_id"); assert service().infer(p).http_status == 400
def test_42_missing_features():
    p=payload(); p.pop("features"); assert service().infer(p).http_status == 400
def test_43_non_dict(): assert service().infer([]).http_status == 400
def test_44_empty_features():
    p=payload(); p["features"]={}; assert service().infer(p).http_status == 400
def test_45_bad_feature_text():
    p=payload(); p["features"]={"f1":"x"}; assert service().infer(p).http_status == 400
def test_46_bad_feature_bool():
    p=payload(); p["features"]={"f1":True}; assert service().infer(p).http_status == 400
def test_47_nan_feature():
    p=payload(); p["features"]={"f1":float("nan")}; assert service().infer(p).http_status == 400
def test_48_identity_mismatch():
    p=payload(); p["model_identity"]="wrong"; assert service().infer(p).http_status == 422
def test_49_version_mismatch():
    p=payload(); p["model_version"]="wrong"; assert service().infer(p).http_status == 422
def test_50_artifact_mismatch():
    p=payload(); p["artifact_identity"]="wrong"; assert service().infer(p).http_status == 422
def test_51_health_http(): assert client().get("/health").status_code == 200
def test_52_health_json(): assert client().get("/health").get_json()["status"] == API_HEALTHY
def test_53_ready_http(): assert client().get("/ready").status_code == 200
def test_54_ready_json(): assert client().get("/ready").get_json()["status"] == API_READY
def test_55_inference_http(): assert client().post("/v1/inference",json=payload()).status_code == 200
def test_56_inference_json(): assert client().post("/v1/inference",json=payload()).get_json()["prediction"] == 3.0
def test_57_content_type(): assert client().post("/v1/inference",data="{}").status_code == 415
def test_58_invalid_json(): assert client().post("/v1/inference",data="{bad",content_type="application/json").status_code == 400
def test_59_missing_fields_http(): assert client().post("/v1/inference",json={}).status_code == 400
def test_60_missing_fields_code(): assert client().post("/v1/inference",json={}).get_json()["error"]["code"] == "MISSING_FIELDS"
def test_61_unknown_route(): assert client().get("/unknown").status_code == 404
def test_62_unknown_route_json(): assert client().get("/unknown").get_json()["error"]["code"] == "NOT_FOUND"
def test_63_wrong_method(): assert client().get("/v1/inference").status_code == 405
def test_64_wrong_method_json(): assert client().get("/v1/inference").get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"
def test_65_deterministic_api():
    a=client().post("/v1/inference",json=payload()).get_json()
    b=client().post("/v1/inference",json=payload()).get_json()
    assert a["response_identity"] == b["response_identity"]
def test_66_feature_order():
    p=payload(); p["features"]={"f2":2,"f1":1}; assert service().infer(p).payload["prediction"] == 3.0
def test_67_predictor_error(): assert failing_service().infer(payload()).http_status == 422
def test_68_predictor_error_code(): assert failing_service().infer(payload()).payload["error"]["code"] == "INFERENCE_REJECTED"
def test_69_api_result_property(): assert ApiResult(API_ACCEPTED,200,{}).is_valid
def test_70_api_result_rejection(): assert not ApiResult(API_REJECTED,400,{}).is_valid
