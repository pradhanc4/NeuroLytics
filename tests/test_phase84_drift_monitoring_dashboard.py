from analytics.calibration_drift import CalibrationDriftReport
from analytics.concept_drift import ConceptDriftReport
from analytics.data_drift import DataDriftReport
from analytics.drift_dashboard import (
    AVAILABLE,
    DRIFT_DASHBOARD_BOUNDARY,
    DRIFT_DASHBOARD_VERSION,
    UNAVAILABLE,
    DriftMonitoringDashboardService,
    drift_dashboard_contract,
)
from analytics.feature_drift import FeatureDriftReport
from analytics.model_drift import ModelDriftReport
from analytics.ranking_drift import RankingDriftReport
from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import service as phase76_service


def data_report():
    return DataDriftReport(
        version="50.0.0",
        feature_version="features-v1",
        source_artifact_count=2,
        source_feature_names=("f1",),
        period_days=7,
        rules=(),
        bin_count=10,
        observations=(),
        drifted_features=(),
        drifted_periods=(),
        drifted=False,
        report_identity="data-drift-report-test",
    )


def model_report():
    return ModelDriftReport(
        version="49.0.0",
        source_type="panel",
        source_report_identity="source-test",
        period_days=7,
        rules=(),
        bin_count=10,
        observations=(),
        drifted_metrics=(),
        drifted_periods=(),
        drifted=False,
        report_identity="model-drift-report-test",
    )


def calibration_report():
    return CalibrationDriftReport(
        version="52.0.0",
        source_type="panel",
        source_report_identity="source-test",
        period_days=7,
        bin_count=10,
        rules=(),
        periods=(),
        observations=(),
        drifted_metrics=(),
        drifted_periods=(),
        drifted=False,
        report_identity="calibration-drift-report-test",
    )


def ranking_report():
    return RankingDriftReport(
        version="53.0.0",
        source_type="panel",
        source_report_identity="source-test",
        period_days=7,
        rank_max=20,
        rules=(),
        periods=(),
        observations=(),
        drifted_metrics=(),
        drifted_periods=(),
        drifted=False,
        report_identity="ranking-drift-report-test",
    )


def feature_report():
    return FeatureDriftReport(
        version="54.0.0",
        feature_version="features-v1",
        source_artifact_count=2,
        source_feature_names=("f1",),
        period_days=7,
        rules=(),
        bin_count=10,
        observations=(),
        drifted_features=(),
        drifted_periods=(),
        drifted=False,
        report_identity="feature-drift-report-test",
    )


def concept_report():
    return ConceptDriftReport(
        version="55.0.0",
        source_type="panel",
        feature_version="features-v1",
        source_feature_artifact_count=2,
        source_outcome_report_identity="outcome-test",
        period_days=7,
        bin_count=5,
        rules=(),
        observations=(),
        drifted_features=(),
        drifted_periods=(),
        drifted=False,
        report_identity="concept-drift-report-test",
    )


def client():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    svc.startup()
    return create_production_app(svc).test_client()


def test_01_version():
    assert DRIFT_DASHBOARD_VERSION == "84.0.0"


def test_02_boundary():
    assert DRIFT_DASHBOARD_BOUNDARY == "DRIFT_MONITORING_DASHBOARD_BOUNDARY"


def test_03_contract_read_only():
    contract = drift_dashboard_contract()
    assert contract["read_only"] is True
    assert contract["sections"] == ("data", "model", "calibration", "ranking", "feature", "concept")
    assert len(contract["routes"]) == 4


def test_04_empty_summary_is_valid():
    result = DriftMonitoringDashboardService().summary()
    assert result["status"] == "VALID"
    assert result["available_sections"] == 0
    assert result["drift_detected"] is False


def test_05_empty_overview():
    result = DriftMonitoringDashboardService().overview()
    assert result["read_only"] is True
    assert result["section_count"] == 6


def test_06_empty_data_section():
    result = DriftMonitoringDashboardService().section("data")
    assert result["summary"]["status"] == UNAVAILABLE
    assert result["validation"]["status"] == UNAVAILABLE
    assert result["observations"]["status"] == UNAVAILABLE


def test_07_empty_model_section():
    assert DriftMonitoringDashboardService().section("model")["summary"]["status"] == UNAVAILABLE


def test_08_empty_calibration_section():
    assert DriftMonitoringDashboardService().section("calibration")["summary"]["status"] == UNAVAILABLE


def test_09_empty_ranking_section():
    assert DriftMonitoringDashboardService().section("ranking")["summary"]["status"] == UNAVAILABLE


def test_10_empty_feature_section():
    assert DriftMonitoringDashboardService().section("feature")["summary"]["status"] == UNAVAILABLE


def test_11_empty_concept_section():
    assert DriftMonitoringDashboardService().section("concept")["summary"]["status"] == UNAVAILABLE


def test_12_invalid_section_name():
    try:
        DriftMonitoringDashboardService().section("unknown")
    except ValueError as exc:
        assert "unknown drift report" in str(exc)
    else:
        raise AssertionError("unknown section must fail")
def test_13_data_attachment_state():
    service = DriftMonitoringDashboardService(data_report=data_report())
    result = service.summary()
    assert result["available_sections"] == 1
    assert result["sections"]["data"]["dashboard_status"] == AVAILABLE


def test_14_model_attachment_state():
    result = DriftMonitoringDashboardService(model_report=model_report()).summary()
    assert result["available_sections"] == 1
    assert result["sections"]["model"]["dashboard_status"] == AVAILABLE


def test_15_calibration_attachment_state():
    result = DriftMonitoringDashboardService(calibration_report=calibration_report()).summary()
    assert result["available_sections"] == 1


def test_16_ranking_attachment_state():
    result = DriftMonitoringDashboardService(ranking_report=ranking_report()).summary()
    assert result["available_sections"] == 1


def test_17_feature_attachment_state():
    result = DriftMonitoringDashboardService(feature_report=feature_report()).summary()
    assert result["available_sections"] == 1


def test_18_concept_attachment_state():
    result = DriftMonitoringDashboardService(concept_report=concept_report()).summary()
    assert result["available_sections"] == 1


def test_19_all_six_attachment_count():
    service = DriftMonitoringDashboardService(
        data_report=data_report(),
        model_report=model_report(),
        calibration_report=calibration_report(),
        ranking_report=ranking_report(),
        feature_report=feature_report(),
        concept_report=concept_report(),
    )
    assert service.summary()["available_sections"] == 6


def test_20_report_identity_is_preserved():
    service = DriftMonitoringDashboardService(data_report=data_report())
    assert service.section("data")["summary"]["report_identity"] == "data-drift-report-test"


def test_21_observation_shape_is_stable():
    service = DriftMonitoringDashboardService(data_report=data_report())
    result = service.observations("data")
    assert result["observation_count"] == 0
    assert result["returned_observations"] == 0
    assert result["observations"] == ()


def test_22_dashboard_composition():
    result = DriftMonitoringDashboardService().dashboard()
    assert set(result) == {"status", "summary", "overview", "sections"}
    assert set(result["sections"]) == {
        "data", "model", "calibration", "ranking", "feature", "concept"
    }


def test_23_dashboard_is_read_only():
    names = set(dir(DriftMonitoringDashboardService))
    assert not any(name in names for name in ("train", "retrain", "promote", "rollback", "delete"))


def test_24_max_observation_limit_is_bounded():
    service = DriftMonitoringDashboardService(data_report=data_report(), max_observations=0)
    assert service.observations("data")["returned_observations"] == 0


def test_25_overview_preserves_version():
    assert DriftMonitoringDashboardService().overview()["version"] == "84.0.0"


def test_26_overview_preserves_boundary():
    assert DriftMonitoringDashboardService().overview()["boundary"] == DRIFT_DASHBOARD_BOUNDARY


def test_27_summary_has_six_sections():
    assert DriftMonitoringDashboardService().summary()["section_count"] == 6


def test_28_drifted_sections_empty_without_reports():
    assert DriftMonitoringDashboardService().summary()["drifted_sections"] == ()


def test_29_no_data_fabrication():
    result = DriftMonitoringDashboardService().dashboard()
    assert result["summary"]["available_sections"] == 0
    assert result["sections"]["data"]["observations"]["status"] == UNAVAILABLE


def test_30_unknown_observation_section():
    try:
        DriftMonitoringDashboardService().observations("unknown")
    except ValueError as exc:
        assert "unknown drift report" in str(exc)
    else:
        raise AssertionError("unknown observation section must fail")
def test_31_production_summary_route():
    response = client().get("/v1/drift/summary")
    assert response.status_code == 200
    assert response.get_json()["available_sections"] == 0


def test_32_production_overview_route():
    response = client().get("/v1/drift/overview")
    assert response.status_code == 200
    assert response.get_json()["section_count"] == 6


def test_33_production_section_route():
    response = client().get("/v1/drift/data")
    assert response.status_code == 200
    assert response.get_json()["summary"]["status"] == UNAVAILABLE


def test_34_production_observations_route():
    response = client().get("/v1/drift/data/observations")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_35_production_invalid_section():
    response = client().get("/v1/drift/unknown")
    assert response.status_code == 400
    assert response.get_json()["status"] == "INVALID"


def test_36_production_get_only():
    c = client()
    for path in (
        "/v1/drift/summary",
        "/v1/drift/overview",
        "/v1/drift/data",
        "/v1/drift/data/observations",
    ):
        assert c.post(path).status_code == 405


def test_37_frontend_summary_route_contract():
    config = client().get("/frontend/config").get_json()
    assert config["routes"]["drift_summary"] == "/v1/drift/summary"


def test_38_frontend_overview_route_contract():
    config = client().get("/frontend/config").get_json()
    assert config["routes"]["drift_overview"] == "/v1/drift/overview"


def test_39_frontend_section_route_contract():
    config = client().get("/frontend/config").get_json()
    assert config["routes"]["drift_section"] == "/v1/drift/<name>"


def test_40_frontend_observation_route_contract():
    config = client().get("/frontend/config").get_json()
    assert config["routes"]["drift_observations"] == "/v1/drift/<name>/observations"


def test_41_frontend_contains_drift_view():
    html = client().get("/").get_data(as_text=True)
    assert 'id="view-drift"' in html
    assert "Drift / Monitoring Dashboard" in html


def test_42_frontend_contains_drift_navigation():
    html = client().get("/").get_data(as_text=True)
    assert 'data-view="drift"' in html


def test_43_frontend_contains_refresh_control():
    html = client().get("/").get_data(as_text=True)
    assert 'id="drift-refresh"' in html
    assert 'id="drift-observations-refresh"' in html


def test_44_frontend_contains_all_drift_panels():
    html = client().get("/").get_data(as_text=True)
    for element in (
        "drift-data", "drift-model", "drift-calibration",
        "drift-ranking", "drift-feature", "drift-concept",
        "drift-overview", "drift-observations",
    ):
        assert f'id="{element}"' in html


def test_45_frontend_contains_drift_api_usage():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "/v1/drift/summary" in js
    assert "/v1/drift/overview" in js
    assert "/v1/drift/" in js
    assert "/observations" in js


def test_46_frontend_switches_to_drift_dashboard():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert 'drift:"Drift / Monitoring Dashboard"' in js
    assert 'if(v==="drift")drift()' in js


def test_47_drift_scope_is_configurable():
    app = create_production_app(
        phase76_service(security_enabled=False, rate_enabled=False),
        drift_scope="custom:drift",
    )
    assert app.test_client().get("/v1/drift/summary").status_code == 200


def test_48_contract_routes_are_stable():
    assert drift_dashboard_contract()["routes"] == (
        "/v1/drift/summary",
        "/v1/drift/overview",
        "/v1/drift/<name>",
        "/v1/drift/<name>/observations",
    )


def test_49_all_report_names_are_stable():
    assert drift_dashboard_contract()["sections"] == (
        "data", "model", "calibration", "ranking", "feature", "concept"
    )


def test_50_report_identity_is_present_when_attached():
    result = DriftMonitoringDashboardService(
        concept_report=concept_report()
    ).section("concept")
    assert result["summary"]["report_identity"] == "concept-drift-report-test"
