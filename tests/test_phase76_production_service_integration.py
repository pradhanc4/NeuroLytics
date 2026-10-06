import pytest

from analytics.api_rate_limit import ApiRateLimitPolicy, ApiRateLimiter
from analytics.api_security import ApiCredentialStore, ApiSecurityPolicy
from analytics.performance_monitoring_api import PerformanceMonitoringApiService
from analytics.production_api import InferenceApiService
from analytics.production_service import (
    INVALID,
    PRODUCTION_SERVICE_BOUNDARY,
    PRODUCTION_SERVICE_VERSION,
    SERVICE_CREATED,
    SERVICE_FAILED,
    SERVICE_RUNNING,
    SERVICE_STOPPED,
    VALID,
    NeuroLyticsProductionService,
    ProductionServicePolicy,
    create_production_app,
    production_service_summary,
)
from analytics.production_serving import build_serving_plan
from tests.test_production_serving import activation_receipt


def inference_service():
    receipt = activation_receipt()
    plan = build_serving_plan("phase76-serving", receipt)
    return InferenceApiService(
        plan,
        lambda features: round(features["f1"] + features["f2"], 4),
    )


def monitoring_service():
    return PerformanceMonitoringApiService()


def security_store():
    store = ApiCredentialStore()
    store.issue_key(
        "phase76-client",
        "service-client",
        ("inference:read", "monitoring:read"),
        "phase76-secret",
    )
    return store


def service(
    *,
    security_enabled=True,
    rate_enabled=True,
    monitoring=None,
    policy=None,
    rate_policy=None,
    limiter=None,
):
    limits = rate_policy or ApiRateLimitPolicy(enabled=rate_enabled)
    return NeuroLyticsProductionService(
        inference_service(),
        monitoring or monitoring_service(),
        security_store=security_store(),
        security_policy=ApiSecurityPolicy(enabled=security_enabled),
        rate_limit_policy=limits,
        rate_limiter=limiter,
        policy=policy or ProductionServicePolicy(),
    )


def payload():
    receipt = activation_receipt()
    return {
        "request_id": "phase76-request",
        "model_identity": receipt.model_identity,
        "model_version": receipt.model_version,
        "artifact_identity": receipt.artifact_identity,
        "features": {"f1": 1, "f2": 2},
    }


def test_01_version():
    assert PRODUCTION_SERVICE_VERSION == "76.0.0"


def test_02_boundary():
    assert PRODUCTION_SERVICE_BOUNDARY == "PRODUCTION_SERVICE_INTEGRATION_BOUNDARY"


def test_03_initial_state():
    assert service().state == SERVICE_CREATED


def test_04_policy_defaults():
    assert service().policy == ProductionServicePolicy()


def test_05_dependencies_cover_existing_boundaries():
    names = {item.name for item in service().dependencies()}
    assert names == {
        "production_serving",
        "inference_api",
        "monitoring_api",
        "security",
        "rate_limiter",
    }


def test_06_startup_transitions_to_running():
    result = service().startup()
    assert result.status == VALID
    assert result.http_status == 200
    assert result.payload["service_state"] == SERVICE_RUNNING


def test_07_startup_is_idempotent():
    svc = service()
    first = svc.startup()
    second = svc.startup()
    assert first.payload["service_state"] == SERVICE_RUNNING
    assert second.payload["service_state"] == SERVICE_RUNNING


def test_08_readiness_requires_startup():
    result = service().readiness()
    assert result.status == INVALID
    assert result.http_status == 503
    assert result.payload["error"]["code"] == "PRODUCTION_SERVICE_NOT_RUNNING"


def test_09_readiness_after_startup():
    svc = service()
    svc.startup()
    result = svc.readiness()
    assert result.is_valid
    assert result.payload["readiness"] == "READY"


def test_10_inference_requires_running_service():
    result = service().infer(payload())
    assert result.http_status == 503
    assert result.payload["error"]["code"] == "PRODUCTION_SERVICE_NOT_RUNNING"


def test_11_inference_delegates_to_phase69():
    svc = service()
    svc.startup()
    result = svc.infer(payload())
    assert result.is_valid
    assert result.payload["prediction"] == 3.0
    assert result.payload["serving_id"] == "phase76-serving"


def test_12_inference_preserves_lineage():
    svc = service()
    svc.startup()
    result = svc.infer(payload())
    assert result.payload["model_identity"]
    assert result.payload["model_version"]
    assert result.payload["artifact_identity"]
    assert result.payload["request_hash"].startswith("production-serving-")


def test_13_invalid_inference_reaches_existing_validation():
    svc = service()
    svc.startup()
    bad = payload()
    bad.pop("features")
    result = svc.infer(bad)
    assert result.status == INVALID
    assert result.http_status == 400


def test_14_monitoring_requires_running_service():
    result = service().monitoring("missing")
    assert result.http_status == 503


def test_15_monitoring_delegates_to_phase72():
    svc = service()
    svc.startup()
    result = svc.monitoring("missing")
    assert result.status == INVALID
    assert result.http_status == 404
    assert result.payload["error"]["code"] == "MONITORING_REPORT_NOT_FOUND"


def test_16_health_contains_dependencies():
    health = service().health()
    assert health["boundary"] == PRODUCTION_SERVICE_BOUNDARY
    assert len(health["dependencies"]) == 5


def test_17_health_exposes_no_raw_credentials():
    health = service().health()
    assert "phase76-secret" not in str(health)
    assert "raw_key" not in str(health).lower()


def test_18_summary_contract():
    svc = service()
    summary = production_service_summary(svc)
    assert summary["service_version"] == "76.0.0"
    assert summary["boundary"] == PRODUCTION_SERVICE_BOUNDARY
    assert summary["routes"] == (
        "/health",
        "/ready",
        "/v1/inference",
        "/v1/monitoring/summary",
        "/v1/monitoring/<name>",
    )


def test_19_shutdown():
    svc = service()
    svc.startup()
    result = svc.shutdown()
    assert result.is_valid
    assert svc.state == SERVICE_STOPPED


def test_20_shutdown_is_idempotent():
    svc = service()
    svc.startup()
    svc.shutdown()
    second = svc.shutdown()
    assert second.is_valid
    assert svc.state == SERVICE_STOPPED


def test_21_bad_inference_dependency_fails_startup():
    receipt = activation_receipt()
    plan = build_serving_plan("phase76-serving", receipt)
    from dataclasses import replace
    broken = replace(plan, status="BLOCKED", serving_state="BLOCKED")
    broken_service = InferenceApiService(broken, lambda features: 1)
    svc = NeuroLyticsProductionService(
        broken_service,
        monitoring_service(),
        security_store=security_store(),
        security_policy=ApiSecurityPolicy(enabled=False),
        rate_limit_policy=ApiRateLimitPolicy(enabled=False),
    )
    result = svc.startup()
    assert result.status == INVALID
    assert result.http_status == 503
    assert svc.state == SERVICE_FAILED


def test_22_monitoring_policy_can_be_required():
    policy = ProductionServicePolicy(require_monitoring_healthy=True)
    svc = service(policy=policy)
    assert svc.startup().is_valid


def test_23_security_policy_is_shared():
    svc = service()
    assert svc.security_store is not None
    assert svc.security_policy.enabled is True


def test_24_rate_limiter_is_shared():
    policy = ApiRateLimitPolicy(
        enabled=True,
        requests_per_window=5,
        window_seconds=60,
        burst_limit=5,
        burst_window_seconds=1,
    )
    limiter = ApiRateLimiter(policy, clock=lambda: 100.0)
    svc = service(rate_policy=policy, limiter=limiter)
    assert svc.rate_limiter is limiter


def test_25_rate_limiter_policy_mismatch_rejected():
    policy = ApiRateLimitPolicy(enabled=True)
    limiter = ApiRateLimiter(ApiRateLimitPolicy(enabled=False))
    with pytest.raises(ValueError):
        NeuroLyticsProductionService(
            inference_service(),
            monitoring_service(),
            rate_limit_policy=policy,
            rate_limiter=limiter,
        )


def test_26_invalid_service_type_rejected():
    with pytest.raises(TypeError):
        NeuroLyticsProductionService(object(), monitoring_service())


def test_27_invalid_monitoring_type_rejected():
    with pytest.raises(TypeError):
        NeuroLyticsProductionService(inference_service(), object())


def test_28_invalid_policy_rejected():
    with pytest.raises(ValueError):
        NeuroLyticsProductionService(
            inference_service(),
            monitoring_service(),
            policy=ProductionServicePolicy(require_inference_ready="yes"),
        )


def test_29_app_health_is_public():
    svc = service()
    client = create_production_app(svc).test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["service_state"] == SERVICE_CREATED


def test_30_app_requires_startup_for_readiness():
    svc = service()
    client = create_production_app(svc).test_client()
    response = client.get("/ready", headers={"X-API-Key": "phase76-secret"})
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "PRODUCTION_SERVICE_NOT_RUNNING"


def test_31_app_startup_and_inference_end_to_end():
    svc = service()
    assert svc.startup().is_valid
    client = create_production_app(svc).test_client()
    response = client.post(
        "/v1/inference",
        json=payload(),
        headers={"X-API-Key": "phase76-secret"},
    )
    assert response.status_code == 200
    assert response.get_json()["prediction"] == 3.0


def test_32_app_authentication_boundary():
    svc = service()
    svc.startup()
    response = create_production_app(svc).test_client().post(
        "/v1/inference",
        json=payload(),
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "MISSING_CREDENTIAL"


def test_33_app_monitoring_scope_boundary():
    svc = service()
    svc.startup()
    response = create_production_app(svc).test_client().get(
        "/v1/monitoring/summary",
        headers={"X-API-Key": "phase76-secret"},
    )
    assert response.status_code == 200
    assert response.get_json()["api_version"] == "72.0.0"


def test_34_app_invalid_scope_is_forbidden():
    svc = service()
    svc.startup()
    svc.security_store.issue_key(
        "phase76-inference-only",
        "client",
        ("inference:read",),
        "inference-only-secret",
    )
    response = create_production_app(svc).test_client().get(
        "/v1/monitoring/summary",
        headers={"X-API-Key": "inference-only-secret"},
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "INSUFFICIENT_SCOPE"


def test_35_app_invalid_json_boundary():
    svc = service()
    svc.startup()
    response = create_production_app(svc).test_client().post(
        "/v1/inference",
        data="{bad",
        content_type="application/json",
        headers={"X-API-Key": "phase76-secret"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_JSON"


def test_36_app_content_type_boundary():
    svc = service()
    svc.startup()
    response = create_production_app(svc).test_client().post(
        "/v1/inference",
        data="{}",
        headers={"X-API-Key": "phase76-secret"},
    )
    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "CONTENT_TYPE_REQUIRED"


def test_37_app_rate_limit_is_shared():
    policy = ApiRateLimitPolicy(
        enabled=True,
        requests_per_window=1,
        window_seconds=60,
        burst_limit=1,
        burst_window_seconds=1,
    )
    limiter = ApiRateLimiter(policy, clock=lambda: 100.0)
    svc = service(rate_policy=policy, limiter=limiter)
    svc.startup()
    client = create_production_app(svc).test_client()
    headers = {"X-API-Key": "phase76-secret"}
    first = client.get("/v1/monitoring/summary", headers=headers)
    second = client.post("/v1/inference", json=payload(), headers=headers)
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.get_json()["error"]["code"] == "RATE_LIMIT_DENIED"


def test_38_method_boundary():
    svc = service()
    svc.startup()
    response = create_production_app(svc).test_client().get("/v1/inference")
    assert response.status_code == 405


def test_39_unknown_route_boundary():
    svc = service()
    response = create_production_app(svc).test_client().get("/not-found")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_40_restart_after_shutdown():
    svc = service()
    assert svc.startup().is_valid
    assert svc.shutdown().is_valid
    assert svc.startup().is_valid
    assert svc.state == SERVICE_RUNNING


def test_41_deterministic_inference_identity():
    svc = service()
    svc.startup()
    a = svc.infer(payload()).payload
    b = svc.infer(payload()).payload
    assert a["request_hash"] == b["request_hash"]
    assert a["response_identity"] == b["response_identity"]


def test_42_service_does_not_mutate_payload():
    svc = service()
    svc.startup()
    original = payload()
    copied = dict(original)
    copied["features"] = dict(original["features"])
    svc.infer(copied)
    assert original == payload()


def test_43_security_can_be_disabled_for_local_mode():
    svc = service(security_enabled=False)
    svc.startup()
    response = create_production_app(svc).test_client().post(
        "/v1/inference",
        json=payload(),
        headers={"X-API-Key": "phase76-secret"},
    )
    assert response.status_code == 200


def test_44_rate_limit_can_be_disabled_for_local_mode():
    svc = service(rate_enabled=False)
    svc.startup()
    response = create_production_app(svc).test_client().post(
        "/v1/inference",
        json=payload(),
        headers={"X-API-Key": "phase76-secret"},
    )
    assert response.status_code == 200
