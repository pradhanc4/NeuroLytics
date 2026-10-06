import math

from analytics.model_dashboard import (
    AVAILABLE,
    MODEL_DASHBOARD_BOUNDARY,
    MODEL_DASHBOARD_VERSION,
    UNAVAILABLE,
    ModelDashboardService,
    model_dashboard_contract,
)
from analytics.production_serving import (
    READY,
    ServingCheck,
    ServingPlan,
    ServingPolicy,
)
from analytics.model_health import (
    HEALTHY,
    HealthComponent,
    build_model_health_report,
)


def serving_plan():
    checks = (
        ServingCheck("ACTIVATION_STATUS", "PASS", "activation receipt is ACTIVATED"),
        ServingCheck("MODEL_IDENTITY", "PASS", "activated model identity is present"),
        ServingCheck("MODEL_VERSION", "PASS", "activated model version is present"),
        ServingCheck("ARTIFACT_IDENTITY", "PASS", "activated artifact identity is present"),
    )
    from analytics.production_serving import _hash, PRODUCTION_SERVING_VERSION
    policy = ServingPolicy()
    identity = _hash((
        PRODUCTION_SERVING_VERSION,
        "phase80-serving",
        "phase80-activation",
        "model-phase80",
        "80.1",
        "artifact-phase80",
        policy,
        checks,
        READY,
        READY,
    ))
    return ServingPlan(
        "phase80-serving",
        "phase80-activation",
        "model-phase80",
        "80.1",
        "artifact-phase80",
        policy,
        checks,
        READY,
        READY,
        identity,
    )


def dashboard(**kwargs):
    return ModelDashboardService(serving_plan(), **kwargs)


def test_01_version():
    assert MODEL_DASHBOARD_VERSION == "80.0.0"


def test_02_boundary():
    assert MODEL_DASHBOARD_BOUNDARY == "MODEL_DASHBOARD_BOUNDARY"


def test_03_contract_is_read_only():
    contract = model_dashboard_contract()
    assert contract["read_only"] is True
    assert len(contract["routes"]) == 8


def test_04_identity():
    result = dashboard().identity()
    assert result["model_identity"] == "model-phase80"
    assert result["model_version"] == "80.1"
    assert result["artifact_identity"] == "artifact-phase80"


def test_05_serving_identity():
    result = dashboard().serving()
    assert result["status"] == "VALID"
    assert result["serving_state"] == READY
    assert result["serving_id"] == "phase80-serving"


def test_06_serving_checks():
    result = dashboard().serving()
    assert len(result["checks"]) == 4
    assert result["failed_checks"] == ()


def test_07_health_unavailable_is_explicit():
    result = dashboard().health()
    assert result["status"] == UNAVAILABLE
    assert result["reason"] == "REPORT_NOT_ATTACHED"


def test_08_comparison_unavailable():
    assert dashboard().comparison()["status"] == UNAVAILABLE


def test_09_champion_challenger_unavailable():
    assert dashboard().champion_challenger()["status"] == UNAVAILABLE


def test_10_selection_unavailable():
    assert dashboard().selection()["status"] == UNAVAILABLE


def test_11_lifecycle_unavailable():
    assert dashboard().lifecycle()["status"] == UNAVAILABLE


def test_12_rollout_unavailable():
    assert dashboard().rollout()["status"] == UNAVAILABLE


def test_13_health_report_projection():
    report = build_model_health_report(
        "model-phase80",
        (HealthComponent("performance", 0.90, HEALTHY, 1.0, "perf-57"),),
    )
    result = dashboard(health_report=report).health()
    assert result["status"] == AVAILABLE
    assert math.isclose(result["weighted_score"], 0.90)
    assert result["health_status"] == HEALTHY
    assert result["components"][0]["source_identity"] == "perf-57"


def test_14_health_identity():
    report = build_model_health_report(
        "model-phase80",
        (HealthComponent("performance", 0.90, HEALTHY),),
    )
    assert dashboard(health_report=report).health()["model_identity"] == "model-phase80"


def test_15_summary():
    result = dashboard().summary()
    assert result["status"] == "VALID"
    assert result["read_only"] is True
    assert result["model_identity"] == "model-phase80"


def test_16_summary_sections():
    sections = dashboard().summary()["sections"]
    assert sections["identity"] == AVAILABLE
    assert sections["serving"] == AVAILABLE
    assert sections["health"] == UNAVAILABLE
    assert sections["lifecycle"] == UNAVAILABLE


def test_17_summary_lineage():
    result = dashboard().summary()
    assert result["artifact_identity"] == "artifact-phase80"
    assert result["serving_id"] == "phase80-serving"
    assert len(result["checks"]) == 4
    assert result["failed_checks"] == ()


def test_18_invalid_serving_plan_status():
    plan = serving_plan()
    broken = ServingPlan(
        plan.serving_id, plan.activation_id, plan.model_identity,
        plan.model_version, plan.artifact_identity, plan.policy,
        plan.checks, "BLOCKED", READY, plan.plan_identity,
    )
    result = ModelDashboardService(broken).summary()
    assert result["status"] == "INVALID"


def test_19_no_mutation_api():
    assert not any(name in dir(ModelDashboardService) for name in (
        "promote", "rollback", "activate", "retrain", "delete",
    ))


def test_20_contract_routes_are_read_only_get_style():
    assert all(route.startswith("/v1/model/") for route in model_dashboard_contract()["routes"])


def test_21_health_component_count():
    report = build_model_health_report(
        "model-phase80",
        (
            HealthComponent("performance", 0.90, HEALTHY),
            HealthComponent("stability", 0.85, HEALTHY),
        ),
    )
    assert dashboard(health_report=report).health()["component_count"] == 2


def test_22_health_empty_optional_sections_remain_explicit():
    report = build_model_health_report(
        "model-phase80",
        (HealthComponent("performance", 0.90, HEALTHY),),
    )
    result = dashboard(health_report=report).summary()["sections"]
    assert result["health"] == AVAILABLE
    assert result["comparison"] == UNAVAILABLE


def test_23_identity_source_is_serving():
    assert dashboard().identity()["source"] == "production_serving"


def test_24_dashboard_version_is_independent():
    assert dashboard().summary()["version"] == MODEL_DASHBOARD_VERSION


def test_25_dashboard_contract_boundary():
    assert model_dashboard_contract()["boundary"] == MODEL_DASHBOARD_BOUNDARY

from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import service as phase76_service


def production_client():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    svc.startup()
    return create_production_app(svc).test_client()


def test_26_production_model_summary_route():
    response = production_client().get("/v1/model/summary")
    assert response.status_code == 200
    assert response.get_json()["read_only"] is True


def test_27_production_identity_route():
    response = production_client().get("/v1/model/identity")
    assert response.status_code == 200
    assert response.get_json()["model_identity"]


def test_28_production_health_route():
    response = production_client().get("/v1/model/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_29_production_comparison_route():
    response = production_client().get("/v1/model/comparison")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_30_production_champion_challenger_route():
    response = production_client().get("/v1/model/champion-challenger")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_31_production_selection_route():
    response = production_client().get("/v1/model/selection")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_32_production_lifecycle_route():
    response = production_client().get("/v1/model/lifecycle")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_33_production_rollout_route():
    response = production_client().get("/v1/model/rollout")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_34_model_routes_are_read_only():
    client = production_client()
    for path in (
        "/v1/model/summary",
        "/v1/model/identity",
        "/v1/model/health",
        "/v1/model/comparison",
        "/v1/model/champion-challenger",
        "/v1/model/selection",
        "/v1/model/lifecycle",
        "/v1/model/rollout",
    ):
        assert client.post(path).status_code == 405


def test_35_frontend_contains_model_dashboard():
    html = production_client().get("/").get_data(as_text=True)
    assert "Model Dashboard" in html
    assert "model-refresh" in html


def test_36_frontend_js_contains_model_routes():
    js = production_client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "/v1/model/summary" in js
    assert "/v1/model/lifecycle" in js
    assert "/v1/model/rollout" in js


def test_37_frontend_config_exposes_model_routes():
    payload = production_client().get("/frontend/config").get_json()
    assert payload["routes"]["model_summary"] == "/v1/model/summary"
