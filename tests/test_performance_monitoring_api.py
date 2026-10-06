from dataclasses import replace
from datetime import date

import pytest

from analytics.performance_monitoring import build_performance_monitoring_report
from analytics.actual_vs_ranked import build_actual_vs_ranked_report
from analytics.performance_over_time import build_performance_over_time_report
from analytics.top_k_framework import TopKEvaluationReport, TopKEvaluationRow
from analytics.performance_degradation import build_performance_degradation_report
from analytics.model_health import HealthComponent, build_model_health_report
from analytics.performance_monitoring_api import (
    INVALID,
    MONITORING_AVAILABLE,
    MONITORING_BOUNDARY,
    MONITORING_UNAVAILABLE,
    PERFORMANCE_MONITORING_API_VERSION,
    VALID,
    PerformanceMonitoringApiService,
    create_monitoring_app,
    monitoring_api_summary,
)


def source_report():
    rows = (
        TopKEvaluationRow("panel", "g1", date(2026, 9, 1), "01", 1,
                          ((1, True), (3, True), (5, True)), 1.0, 0.22, 0.52),
        TopKEvaluationRow("panel", "g2", date(2026, 9, 2), "02", 2,
                          ((1, False), (3, True), (5, True)), 0.5, 0.24, 0.54),
    )
    source = TopKEvaluationReport(
        "44.0.0", "panel", "top-k-evaluation-report-phase44-source",
        (1, 3, 5), rows, ((1, 0.5), (3, 1.0), (5, 1.0)),
        0.5, 2, 2, "top-k-evaluation-report-phase44-source",
    )
    return build_actual_vs_ranked_report(source)


def monitoring_report():
    actual = source_report()
    over_time = build_performance_over_time_report(actual)
    return build_performance_monitoring_report(over_time)


def health_report():
    return build_model_health_report(
        "model-72",
        (HealthComponent("performance", 0.9, "HEALTHY"),),
    )


def test_version_constant():
    assert PERFORMANCE_MONITORING_API_VERSION == "72.0.0"


def test_boundary_constant():
    assert MONITORING_BOUNDARY == "PERFORMANCE_MONITORING_API_BOUNDARY"


def test_empty_service_is_unavailable():
    service = PerformanceMonitoringApiService()
    assert service.summary()["status"] == MONITORING_UNAVAILABLE


def test_service_reports_are_sorted():
    service = PerformanceMonitoringApiService({"model_health": health_report(), "performance": monitoring_report()})
    assert service.reports == ("model_health", "performance")


def test_available_report():
    service = PerformanceMonitoringApiService({"performance": monitoring_report()})
    assert service.available("performance") is True


def test_missing_report_is_not_available():
    service = PerformanceMonitoringApiService()
    assert service.available("performance") is False


def test_invalid_report_name_rejected():
    with pytest.raises(ValueError):
        PerformanceMonitoringApiService({"unknown": object()})


def test_wrong_report_type_rejected():
    with pytest.raises(TypeError):
        PerformanceMonitoringApiService({"performance": health_report()})


def test_summary_has_boundary():
    summary = PerformanceMonitoringApiService({"performance": monitoring_report()}).summary()
    assert summary["boundary"] == MONITORING_BOUNDARY


def test_summary_counts_reports():
    service = PerformanceMonitoringApiService({"performance": monitoring_report(), "model_health": health_report()})
    assert service.summary()["report_count"] == 2


def test_get_performance_report():
    result = PerformanceMonitoringApiService({"performance": monitoring_report()}).get("performance")
    assert result.status == VALID
    assert result.http_status == 200
    assert result.payload["report_type"] == "performance"


def test_get_missing_report_returns_404():
    result = PerformanceMonitoringApiService().get("performance")
    assert result.status == INVALID
    assert result.http_status == 404
    assert result.payload["error"]["code"] == "MONITORING_REPORT_NOT_FOUND"


def test_get_model_health_report():
    result = PerformanceMonitoringApiService({"model_health": health_report()}).get("model_health")
    assert result.is_valid
    assert result.payload["health_status"] == "HEALTHY"


def test_get_serializes_dates():
    result = PerformanceMonitoringApiService({"performance": monitoring_report()}).get("performance")
    assert result.is_valid
    assert isinstance(result.payload["latest_period"][0], str)


def test_get_preserves_source_lineage():
    report = monitoring_report()
    result = PerformanceMonitoringApiService({"performance": report}).get("performance")
    assert result.payload["source_report_identity"] == report.source_report_identity


def test_get_preserves_report_identity():
    report = monitoring_report()
    result = PerformanceMonitoringApiService({"performance": report}).get("performance")
    assert result.payload["report_identity"] == report.report_identity


def test_invalid_configured_report_returns_503():
    report = monitoring_report()
    bad = replace(report, version="bad")
    result = PerformanceMonitoringApiService({"performance": bad}).get("performance")
    assert result.status == INVALID
    assert result.http_status == 503
    assert result.payload["error"]["code"] == "MONITORING_REPORT_INVALID"


def test_invalid_report_health_is_degraded():
    report = monitoring_report()
    bad = replace(report, version="bad")
    service = PerformanceMonitoringApiService({"performance": bad})
    health = service.health()
    assert health["status"] == "DEGRADED"
    assert health["invalid_reports"] == ("performance",)


def test_valid_report_health_is_healthy():
    service = PerformanceMonitoringApiService({"performance": monitoring_report()})
    health = service.health()
    assert health["status"] == "HEALTHY"
    assert health["valid_report_count"] == 1


def test_all_reports_returns_valid_payloads():
    service = PerformanceMonitoringApiService({"performance": monitoring_report(), "model_health": health_report()})
    reports = service.all_reports()
    assert set(reports) == {"performance", "model_health"}


def test_all_reports_skips_invalid_reports():
    good = monitoring_report()
    bad = replace(good, version="bad")
    service = PerformanceMonitoringApiService({"performance": bad, "model_health": health_report()})
    assert set(service.all_reports()) == {"model_health"}


def test_monitoring_api_summary_wrapper():
    service = PerformanceMonitoringApiService({"performance": monitoring_report()})
    assert monitoring_api_summary(service) == service.summary()


def test_summary_wrapper_rejects_wrong_type():
    with pytest.raises(TypeError):
        monitoring_api_summary(object())


def test_create_app_rejects_wrong_service():
    with pytest.raises(TypeError):
        create_monitoring_app(object())


def test_health_route():
    client = create_monitoring_app(PerformanceMonitoringApiService()).test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["boundary"] == MONITORING_BOUNDARY


def test_summary_route():
    service = PerformanceMonitoringApiService({"performance": monitoring_report()})
    response = create_monitoring_app(service).test_client().get("/v1/monitoring/summary")
    assert response.status_code == 200
    assert response.get_json()["status"] == MONITORING_AVAILABLE


def test_all_monitoring_route():
    service = PerformanceMonitoringApiService({"performance": monitoring_report()})
    response = create_monitoring_app(service).test_client().get("/v1/monitoring")
    assert response.status_code == 200
    assert "performance" in response.get_json()["reports"]


def test_named_monitoring_route():
    service = PerformanceMonitoringApiService({"model_health": health_report()})
    response = create_monitoring_app(service).test_client().get("/v1/monitoring/model_health")
    assert response.status_code == 200
    assert response.get_json()["report_type"] == "model_health"


def test_missing_named_monitoring_route():
    response = create_monitoring_app(PerformanceMonitoringApiService()).test_client().get("/v1/monitoring/model_health")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "MONITORING_REPORT_NOT_FOUND"


def test_unknown_route_returns_structured_404():
    response = create_monitoring_app(PerformanceMonitoringApiService()).test_client().get("/unknown")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_post_is_not_allowed_on_read_only_report_route():
    response = create_monitoring_app(PerformanceMonitoringApiService()).test_client().post("/v1/monitoring/summary")
    assert response.status_code == 405


def test_no_mutation_of_report():
    report = monitoring_report()
    service = PerformanceMonitoringApiService({"performance": report})
    service.get("performance")
    assert service.get("performance").payload["report_identity"] == report.report_identity


def test_model_health_identity_is_exposed():
    report = health_report()
    payload = PerformanceMonitoringApiService({"model_health": report}).get("model_health").payload
    assert payload["report_identity"] == report.report_identity


def test_multiple_report_types_are_exposed():
    service = PerformanceMonitoringApiService({
        "performance": monitoring_report(),
        "performance_over_time": build_performance_over_time_report(source_report()),
        "model_health": health_report(),
    })
    assert service.reports == ("model_health", "performance", "performance_over_time")


def test_api_version_is_in_payload():
    payload = PerformanceMonitoringApiService({"model_health": health_report()}).get("model_health").payload
    assert payload["api_version"] == PERFORMANCE_MONITORING_API_VERSION


def test_api_boundary_is_in_payload():
    payload = PerformanceMonitoringApiService({"model_health": health_report()}).get("model_health").payload
    assert payload["boundary"] == MONITORING_BOUNDARY


def test_service_does_not_generate_new_model_metrics():
    report = health_report()
    payload = PerformanceMonitoringApiService({"model_health": report}).get("model_health").payload
    assert payload["weighted_score"] == report.score.weighted_score


def test_service_does_not_recompute_performance():
    report = monitoring_report()
    payload = PerformanceMonitoringApiService({"performance": report}).get("performance").payload
    assert payload["latest_values"] == [[name, value] for name, value in report.latest_values]


def test_json_safe_is_used_by_flask():
    report = build_performance_over_time_report(source_report())
    response = create_monitoring_app(PerformanceMonitoringApiService({"performance_over_time": report})).test_client().get("/v1/monitoring/performance_over_time")
    assert response.is_json
    assert response.status_code == 200


def test_empty_all_reports_is_valid_empty_container():
    service = PerformanceMonitoringApiService()
    assert service.all_reports() == {}


def test_health_counts_invalid_and_valid_reports():
    good = health_report()
    bad = replace(good, version="bad")
    service = PerformanceMonitoringApiService({"model_health": bad})
    health = service.health()
    assert health["configured_report_count"] == 1
    assert health["valid_report_count"] == 0


def test_report_registry_is_immutable_from_external_mapping():
    reports = {"model_health": health_report()}
    service = PerformanceMonitoringApiService(reports)
    reports.clear()
    assert service.reports == ("model_health",)


def test_health_route_has_json_content():
    response = create_monitoring_app(PerformanceMonitoringApiService()).test_client().get("/health")
    assert response.is_json


def test_summary_route_reports_unavailable_when_empty():
    response = create_monitoring_app(PerformanceMonitoringApiService()).test_client().get("/v1/monitoring/summary")
    assert response.status_code == 200
    assert response.get_json()["status"] == MONITORING_UNAVAILABLE


def test_performance_report_validation_is_required_before_response():
    report = monitoring_report()
    bad = replace(report, report_identity="bad")
    response = create_monitoring_app(PerformanceMonitoringApiService({"performance": bad})).test_client().get("/v1/monitoring/performance")
    assert response.status_code == 503


def test_health_status_is_independent_of_report_endpoint():
    report = monitoring_report()
    bad = replace(report, report_identity="bad")
    service = PerformanceMonitoringApiService({"performance": bad})
    assert service.health()["status"] == "DEGRADED"
    assert service.get("performance").http_status == 503


def test_report_type_is_explicit():
    payload = PerformanceMonitoringApiService({"performance": monitoring_report()}).get("performance").payload
    assert payload["report_type"] == "performance"


def test_read_only_api_has_no_mutation_method():
    service = PerformanceMonitoringApiService({"performance": monitoring_report()})
    assert not hasattr(service, "update")
    assert not hasattr(service, "delete")
