from analytics.model_health import (
    CRITICAL,
    DEGRADED,
    HEALTHY,
    HealthComponent,
    build_model_health_report,
)
from analytics.model_health_dashboard import (
    AVAILABLE,
    MODEL_HEALTH_DASHBOARD_BOUNDARY,
    MODEL_HEALTH_DASHBOARD_VERSION,
    UNAVAILABLE,
    ModelHealthDashboardService,
    model_health_dashboard_contract,
)
from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import service as phase76_service


def report():
    return build_model_health_report(
        "model-phase85",
        (
            HealthComponent("performance", 0.90, HEALTHY, 2.0, "perf-47"),
            HealthComponent("drift", 0.70, DEGRADED, 1.0, "drift-49"),
            HealthComponent("concept", 0.95, HEALTHY, 1.0, "concept-55"),
        ),
    )


def service():
    return ModelHealthDashboardService(report())


def client():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    svc.startup()
    return create_production_app(svc).test_client()


def test_01_version():
    assert MODEL_HEALTH_DASHBOARD_VERSION == "85.0.0"


def test_02_boundary():
    assert MODEL_HEALTH_DASHBOARD_BOUNDARY == "MODEL_HEALTH_DASHBOARD_BOUNDARY"


def test_03_contract_read_only():
    c = model_health_dashboard_contract()
    assert c["read_only"] is True
    assert len(c["routes"]) == 6


def test_04_empty_summary():
    result = ModelHealthDashboardService().summary()
    assert result["status"] == "VALID"
    assert result["read_only"] is True
    assert result["health_report"]["status"] == UNAVAILABLE


def test_05_empty_scorecard():
    assert ModelHealthDashboardService().scorecard()["status"] == UNAVAILABLE


def test_06_empty_components():
    assert ModelHealthDashboardService().components()["status"] == UNAVAILABLE


def test_07_empty_thresholds():
    assert ModelHealthDashboardService().thresholds()["status"] == UNAVAILABLE


def test_08_empty_lineage():
    assert ModelHealthDashboardService().lineage()["status"] == UNAVAILABLE


def test_09_empty_validation():
    assert ModelHealthDashboardService().validation()["status"] == UNAVAILABLE


def test_10_attached_summary():
    s = service().summary()
    assert s["status"] == "VALID"
    assert s["model_identity"] == "model-phase85"
    assert s["health_status"] == HEALTHY
    assert s["component_count"] == 3


def test_11_scorecard():
    s = service().scorecard()
    assert s["status"] == "VALID"
    assert s["health_status"] == HEALTHY
    assert s["weighted_score"] == 0.8625


def test_12_scorecard_thresholds():
    s = service().scorecard()
    assert s["healthy_min"] == 0.80
    assert s["degraded_min"] == 0.50


def test_13_components_count():
    assert service().components()["component_count"] == 3


def test_14_components_preserve_names():
    assert tuple(x["name"] for x in service().components()["components"]) == (
        "performance", "drift", "concept"
    )


def test_15_components_preserve_scores():
    values = service().components()["components"]
    assert values[0]["score"] == 0.90
    assert values[1]["score"] == 0.70


def test_16_components_preserve_status():
    values = service().components()["components"]
    assert values[0]["status"] == HEALTHY
    assert values[1]["status"] == DEGRADED


def test_17_components_preserve_weights():
    values = service().components()["components"]
    assert values[0]["weight"] == 2.0
    assert values[1]["weight"] == 1.0


def test_18_components_preserve_source_identity():
    values = service().components()["components"]
    assert values[0]["source_identity"] == "perf-47"
    assert values[1]["source_identity"] == "drift-49"


def test_19_threshold_bands():
    bands = service().thresholds()["bands"]
    assert bands[0]["status"] == HEALTHY
    assert bands[1]["status"] == DEGRADED
    assert bands[2]["status"] == CRITICAL


def test_20_threshold_values():
    bands = service().thresholds()["bands"]
    assert bands[0]["minimum"] == 0.80
    assert bands[1]["minimum"] == 0.50
    assert bands[2]["minimum"] == 0.0


def test_21_lineage_model_identity():
    assert service().lineage()["model_identity"] == "model-phase85"


def test_22_lineage_report_identity():
    assert service().lineage()["report_identity"] == report().report_identity


def test_23_lineage_source_count():
    assert service().lineage()["source_count"] == 3


def test_24_lineage_sources():
    sources = service().lineage()["source_identities"]
    assert sources[0]["source_identity"] == "perf-47"
    assert sources[1]["source_identity"] == "drift-49"
    assert sources[2]["source_identity"] == "concept-55"


def test_25_validation_valid():
    result = service().validation()
    assert result["status"] == "VALID"
    assert result["is_valid"] is True
    assert result["issues"] == ()


def test_26_dashboard_composition():
    result = service().dashboard()
    assert set(result) == {
        "status", "summary", "scorecard", "components",
        "thresholds", "lineage", "validation"
    }


def test_27_dashboard_read_only():
    names = set(dir(ModelHealthDashboardService))
    assert not any(x in names for x in ("retrain", "promote", "rollback", "delete", "activate"))


def test_28_summary_report_status():
    assert service().summary()["report_identity"] == report().report_identity


def test_29_critical_component_count():
    value = build_model_health_report(
        "m",
        (HealthComponent("critical", 0.20, CRITICAL),),
    )
    result = ModelHealthDashboardService(value).summary()
    assert result["critical_component_count"] == 1


def test_30_degraded_component_count():
    result = service().summary()
    assert result["degraded_component_count"] == 1


def test_31_critical_components():
    value = build_model_health_report(
        "m",
        (HealthComponent("critical", 0.20, CRITICAL),),
    )
    assert ModelHealthDashboardService(value).scorecard()["critical_components"] == ("critical",)


def test_32_degraded_components():
    assert service().scorecard()["degraded_components"] == ("drift",)


def test_33_source_version():
    assert service().summary()["source_version"] == "57.0.0"


def test_34_dashboard_version():
    assert service().summary()["version"] == "85.0.0"


def test_35_dashboard_boundary():
    assert service().summary()["boundary"] == MODEL_HEALTH_DASHBOARD_BOUNDARY


def test_36_production_summary_route():
    response = client().get("/v1/model-health/summary")
    assert response.status_code == 200
    assert response.get_json()["health_report"]["status"] == UNAVAILABLE


def test_37_production_scorecard_route():
    response = client().get("/v1/model-health/scorecard")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_38_production_components_route():
    response = client().get("/v1/model-health/components")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_39_production_thresholds_route():
    response = client().get("/v1/model-health/thresholds")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_40_production_lineage_route():
    response = client().get("/v1/model-health/lineage")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_41_production_validation_route():
    response = client().get("/v1/model-health/validation")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_42_production_get_only():
    c = client()
    for path in (
        "/v1/model-health/summary",
        "/v1/model-health/scorecard",
        "/v1/model-health/components",
        "/v1/model-health/thresholds",
        "/v1/model-health/lineage",
        "/v1/model-health/validation",
    ):
        assert c.post(path).status_code == 405


def test_43_frontend_summary_route_contract():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["model_health_summary"] == "/v1/model-health/summary"


def test_44_frontend_scorecard_route_contract():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["model_health_scorecard"] == "/v1/model-health/scorecard"


def test_45_frontend_components_route_contract():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["model_health_components"] == "/v1/model-health/components"


def test_46_frontend_thresholds_route_contract():
    routes = client().get("/frontend/config").get_json()["routes"]
    assert routes["model_health_thresholds"] == "/v1/model-health/thresholds"


def test_47_frontend_contains_navigation():
    html = client().get("/").get_data(as_text=True)
    assert 'data-view="model-health"' in html
    assert "Model Health Dashboard" in html


def test_48_frontend_contains_health_panels():
    html = client().get("/").get_data(as_text=True)
    for element in (
        "view-model-health",
        "mh-status",
        "mh-score",
        "mh-components-count",
        "mh-report-status",
        "mh-scorecard",
        "mh-thresholds",
        "mh-component-rows",
        "mh-lineage",
        "mh-validation",
    ):
        assert f'id="{element}"' in html


def test_49_frontend_contains_api_usage():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    for route in (
        "/v1/model-health/summary",
        "/v1/model-health/scorecard",
        "/v1/model-health/components",
        "/v1/model-health/thresholds",
        "/v1/model-health/lineage",
        "/v1/model-health/validation",
    ):
        assert route in js


def test_50_frontend_refresh_contract():
    html = client().get("/").get_data(as_text=True)
    assert 'id="model-health-refresh"' in html
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "modelHealth" in js


def test_51_configurable_scope():
    app = create_production_app(
        phase76_service(security_enabled=False, rate_enabled=False),
        model_health_scope="custom:model-health",
    )
    assert app.test_client().get("/v1/model-health/summary").status_code == 200


def test_52_contract_route_count():
    assert len(model_health_dashboard_contract()["routes"]) == 6


def test_53_contract_section_identity():
    assert model_health_dashboard_contract()["boundary"] == MODEL_HEALTH_DASHBOARD_BOUNDARY


def test_54_no_fabricated_health_score():
    result = ModelHealthDashboardService().summary()
    assert "weighted_score" not in result
    assert result["health_report"]["status"] == UNAVAILABLE


def test_55_dashboard_summary_is_stable():
    first = service().summary()
    second = service().summary()
    assert first == second
