import pytest

from analytics.api_rate_limit import ApiRateLimitPolicy, ApiRateLimiter
from analytics.api_security import ApiCredentialStore, ApiSecurityPolicy
from analytics.performance_monitoring_api import PerformanceMonitoringApiService, create_monitoring_app
from analytics.production_api import (
    InferenceApiService,
    create_secure_inference_app,
)
from analytics.production_serving import build_serving_plan
from tests.test_production_serving import activation_receipt


def make_service():
    receipt = activation_receipt()
    plan = build_serving_plan("phase75-serving", receipt)
    return InferenceApiService(plan, lambda features: round(features["f1"] + features["f2"], 4))


def make_store():
    store = ApiCredentialStore()
    store.issue_key("phase75-client", "client", ("inference:read",), "phase75-secret")
    return store


def make_payload():
    receipt = activation_receipt()
    return {
        "request_id": "phase75-request",
        "model_identity": receipt.model_identity,
        "model_version": receipt.model_version,
        "artifact_identity": receipt.artifact_identity,
        "features": {"f1": 1, "f2": 2},
    }


def make_client(*, rate_policy=None, limiter=None):
    app = create_secure_inference_app(
        make_service(),
        make_store(),
        rate_limit_policy=rate_policy,
        rate_limiter=limiter,
    )
    return app.test_client()


def test_phase75_versioned_success_path():
    response = make_client().post(
        "/v1/inference", json=make_payload(),
        headers={"X-API-Key": "phase75-secret"},
    )
    body = response.get_json()
    assert response.status_code == 200
    assert body["status"] == "API_ACCEPTED"
    assert body["inference_status"] == "INFERENCE_ACCEPTED"
    assert body["prediction"] == 3.0
    assert body["model_identity"]
    assert body["artifact_identity"]
    assert body["deterministic"] is True


def test_phase75_health_ready_and_inference_contract():
    client = make_client()
    assert client.get("/health").status_code == 200
    ready = client.get("/ready", headers={"X-API-Key": "phase75-secret"})
    infer = client.post("/v1/inference", json=make_payload(), headers={"X-API-Key": "phase75-secret"})
    assert ready.status_code == 200
    assert ready.get_json()["status"] == "READY"
    assert infer.status_code == 200


def test_phase75_authentication_precedes_inference():
    response = make_client().post("/v1/inference", json=make_payload())
    assert response.status_code == 401
    assert response.get_json()["error"]["details"]["code"] == "MISSING_CREDENTIAL"


def test_phase75_invalid_credentials_are_rejected_before_validation():
    response = make_client().post(
        "/v1/inference", data="{bad", content_type="application/json",
        headers={"X-API-Key": "wrong"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["details"]["code"] == "INVALID_CREDENTIAL"


def test_phase75_validation_runs_after_authentication():
    response = make_client().post(
        "/v1/inference", data="{bad", content_type="application/json",
        headers={"X-API-Key": "phase75-secret"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_JSON"


def test_phase75_content_type_boundary():
    response = make_client().post(
        "/v1/inference", data="{}",
        headers={"X-API-Key": "phase75-secret"},
    )
    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "CONTENT_TYPE_REQUIRED"


def test_phase75_method_boundary():
    response = make_client().get("/v1/inference", headers={"X-API-Key": "phase75-secret"})
    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_phase75_missing_fields_stop_before_serving():
    response = make_client().post(
        "/v1/inference", json={}, headers={"X-API-Key": "phase75-secret"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "MISSING_FIELDS"


def test_phase75_serving_identity_validation_reaches_phase68():
    payload = make_payload()
    payload["model_identity"] = "wrong-model"
    response = make_client().post(
        "/v1/inference", json=payload, headers={"X-API-Key": "phase75-secret"},
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "INFERENCE_REJECTED"


def test_phase75_rate_limit_is_after_auth_and_before_inference():
    policy = ApiRateLimitPolicy(
        enabled=True, requests_per_window=1, window_seconds=60,
        burst_limit=1, burst_window_seconds=1,
    )
    limiter = ApiRateLimiter(policy, clock=lambda: 100.0)
    client = make_client(rate_policy=policy, limiter=limiter)
    headers = {"X-API-Key": "phase75-secret"}
    first = client.post("/v1/inference", json=make_payload(), headers=headers)
    second = client.post("/v1/inference", json=make_payload(), headers=headers)
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.get_json()["error"]["code"] == "RATE_LIMIT_DENIED"
    assert second.headers["Retry-After"]


def test_phase75_rate_limit_headers_on_success():
    client = make_client()
    response = client.post(
        "/v1/inference", json=make_payload(),
        headers={"X-API-Key": "phase75-secret"},
    )
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "60"
    assert "X-RateLimit-Remaining" in response.headers
    assert response.headers["X-RateLimit-Window"] == "60.0"


def test_phase75_unknown_route_is_structured():
    response = make_client().get("/v1/not-a-route")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_phase75_deterministic_end_to_end_response():
    client = make_client()
    headers = {"X-API-Key": "phase75-secret"}
    first = client.post("/v1/inference", json=make_payload(), headers=headers).get_json()
    second = client.post("/v1/inference", json=make_payload(), headers=headers).get_json()
    assert first["request_hash"] == second["request_hash"]
    assert first["response_identity"] == second["response_identity"]
    assert first["prediction"] == second["prediction"]


def test_phase75_monitoring_health_is_public():
    app = create_monitoring_app(PerformanceMonitoringApiService())
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "HEALTHY"


def test_phase75_monitoring_authentication_integrates_with_monitoring_api():
    store = ApiCredentialStore()
    store.issue_key("monitor", "monitor", ("monitoring:read",), "monitor-secret")
    app = create_monitoring_app(
        PerformanceMonitoringApiService(),
        security_store=store,
        security_policy=ApiSecurityPolicy(enabled=True),
        required_scope="monitoring:read",
    )
    client = app.test_client()
    assert client.get("/v1/monitoring/summary").status_code == 401
    response = client.get("/v1/monitoring/summary", headers={"X-API-Key": "monitor-secret"})
    assert response.status_code == 200
    assert response.get_json()["api_version"] == "72.0.0"


def test_phase75_monitoring_wrong_scope_is_forbidden():
    store = ApiCredentialStore()
    store.issue_key("other", "other", ("inference:read",), "other-secret")
    app = create_monitoring_app(
        PerformanceMonitoringApiService(),
        security_store=store,
        security_policy=ApiSecurityPolicy(enabled=True),
        required_scope="monitoring:read",
    )
    response = app.test_client().get("/v1/monitoring/summary", headers={"X-API-Key": "other-secret"})
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "INSUFFICIENT_SCOPE"


def test_phase75_monitoring_authenticated_method_boundary():
    store = ApiCredentialStore()
    store.issue_key("monitor", "monitor", ("monitoring:read",), "monitor-secret")
    app = create_monitoring_app(
        PerformanceMonitoringApiService(), security_store=store,
        security_policy=ApiSecurityPolicy(enabled=True), required_scope="monitoring:read",
    )
    response = app.test_client().post(
        "/v1/monitoring/summary", headers={"X-API-Key": "monitor-secret"},
    )
    assert response.status_code == 405


def test_phase75_no_raw_api_key_crosses_response_boundary():
    client = make_client()
    response = client.post(
        "/v1/inference", json=make_payload(),
        headers={"X-API-Key": "phase75-secret"},
    )
    assert "phase75-secret" not in response.get_data(as_text=True)


def test_phase75_public_health_does_not_require_inference_credentials():
    response = make_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["service"] == "neurolytics-inference"


def test_phase75_inference_response_preserves_lineage():
    response = make_client().post(
        "/v1/inference", json=make_payload(),
        headers={"X-API-Key": "phase75-secret"},
    )
    body = response.get_json()
    assert body["serving_id"] == "phase75-serving"
    assert body["model_identity"]
    assert body["model_version"]
    assert body["artifact_identity"]
