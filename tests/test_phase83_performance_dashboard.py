from datetime import date

from analytics.performance_dashboard import (
    AVAILABLE,
    UNAVAILABLE,
    PERFORMANCE_DASHBOARD_BOUNDARY,
    PERFORMANCE_DASHBOARD_VERSION,
    PerformanceOverTimeDashboardService,
    performance_dashboard_contract,
)
from analytics.panel_ranking import PanelCandidateInput, build_panel_ranking_report, rank_panels
from analytics.top_k_framework import build_top_k_evaluation_report
from analytics.actual_vs_ranked import build_actual_vs_ranked_report
from analytics.performance_over_time import build_performance_over_time_report
from analytics.learning_to_rank_model import LearningToRankPrediction
from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import service as phase76_service


def prediction(group_id, target_date="2026-09-29"):
    return LearningToRankPrediction(
        group_id=group_id,
        target_date=target_date,
        candidate_digits=tuple(range(10)),
        scores=(0.7, 0.2, 0.1, 0, 0, 0, 0, 0, 0, 0),
        probabilities=(0.7, 0.2, 0.1, 0, 0, 0, 0, 0, 0, 0),
        ranks=tuple(range(1, 11)),
        actual_digit=0,
        top_candidate=0,
        top_k_candidates=(0, 1, 2),
    )


def panel_observation(group_id="g1", target_date=date(2026, 9, 29)):
    return rank_panels(
        prediction(group_id + "-1", target_date.isoformat()),
        prediction(group_id + "-2", target_date.isoformat()),
        prediction(group_id + "-3", target_date.isoformat()),
        (
            PanelCandidateInput("000", "pf0", "jf0"),
            PanelCandidateInput("123", "pf1", "jf1"),
            PanelCandidateInput("999", "pf9", "jf9"),
            PanelCandidateInput("045", "pf4", "jf4"),
        ),
        group_id,
        target_date,
        actual_panel="000",
        top_k=4,
    )


def report():
    panel = build_panel_ranking_report(
        (
            panel_observation("g1", date(2026, 9, 1)),
            panel_observation("g2", date(2026, 9, 9)),
        ),
        ("model-p1", "model-p2", "model-p3"),
        4,
    )
    topk = build_top_k_evaluation_report(panel.observations, panel.report_identity, (1, 2, 4))
    actual = build_actual_vs_ranked_report(topk)
    return build_performance_over_time_report(actual, period_days=7, hit_ks=(1, 2, 4))


def client():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    svc.startup()
    return create_production_app(svc).test_client()


def test_01_version():
    assert PERFORMANCE_DASHBOARD_VERSION == "83.0.0"


def test_02_boundary():
    assert PERFORMANCE_DASHBOARD_BOUNDARY == "PERFORMANCE_OVER_TIME_DASHBOARD_BOUNDARY"


def test_03_contract_read_only():
    contract = performance_dashboard_contract()
    assert contract["read_only"] is True
    assert len(contract["routes"]) == 5


def test_04_empty_summary():
    result = PerformanceOverTimeDashboardService().summary()
    assert result["status"] == "VALID"
    assert result["report_status"] == UNAVAILABLE
    assert result["read_only"] is True


def test_05_empty_periods():
    assert PerformanceOverTimeDashboardService().periods()["status"] == UNAVAILABLE


def test_06_empty_trends():
    assert PerformanceOverTimeDashboardService().trends()["status"] == UNAVAILABLE


def test_07_empty_hit_rates():
    assert PerformanceOverTimeDashboardService().hit_rates()["status"] == UNAVAILABLE


def test_08_empty_metrics():
    assert PerformanceOverTimeDashboardService().metrics()["status"] == UNAVAILABLE


def test_09_empty_dashboard_shape():
    result = PerformanceOverTimeDashboardService().dashboard()
    assert set(result) == {"status", "summary", "metrics", "periods", "trends", "hit_rates"}


def test_10_available_summary():
    value = report()
    result = PerformanceOverTimeDashboardService(report=value).summary()
    assert result["report_status"] == AVAILABLE
    assert result["periods"] == 2
    assert result["observations"] == 2


def test_11_period_projection():
    result = PerformanceOverTimeDashboardService(report=report()).periods()
    assert result["period_count"] == 2
    assert result["returned_periods"] == 2


def test_12_period_dates():
    row = PerformanceOverTimeDashboardService(report=report()).periods()["periods"][0]
    assert row["period_start"] == "2026-09-01"
    assert row["period_end"] == "2026-09-07"


def test_13_period_counts():
    row = PerformanceOverTimeDashboardService(report=report()).periods()["periods"][0]
    assert row["observation_count"] == 1
    assert row["actual_available_observations"] == 1
    assert row["missed_observations"] == 0


def test_14_period_hit_rates():
    row = PerformanceOverTimeDashboardService(report=report()).periods()["periods"][0]
    assert row["hit_rates"][0]["k"] == 1
    assert row["hit_rates"][0]["hit_percent"] == 100.0


def test_15_period_probability_metrics():
    row = PerformanceOverTimeDashboardService(report=report()).periods()["periods"][0]
    assert row["mean_top_probability"] >= 0
    assert row["mean_cumulative_probability"] >= 0


def test_16_period_mrr():
    row = PerformanceOverTimeDashboardService(report=report()).periods()["periods"][0]
    assert row["mean_reciprocal_rank"] == 1.0


def test_17_period_miss_rate():
    row = PerformanceOverTimeDashboardService(report=report()).periods()["periods"][0]
    assert row["miss_rate"] == 0.0
    assert row["miss_percent"] == 0.0


def test_18_trend_projection():
    result = PerformanceOverTimeDashboardService(report=report()).trends()
    assert result["status"] == AVAILABLE
    assert result["trends"]


def test_19_trend_fields():
    item = PerformanceOverTimeDashboardService(report=report()).trends()["trends"][0]
    assert {"metric", "slope_per_day", "direction", "first_value", "last_value", "change"} <= set(item)


def test_20_hit_rate_series():
    result = PerformanceOverTimeDashboardService(report=report()).hit_rates()
    assert result["points"]
    assert result["points"][0]["k"] == 1


def test_21_hit_rate_series_dates():
    point = PerformanceOverTimeDashboardService(report=report()).hit_rates()["points"][0]
    assert point["period_start"] == "2026-09-01"


def test_22_metrics_counts():
    result = PerformanceOverTimeDashboardService(report=report()).metrics()
    assert result["observation_count"] == 2
    assert result["actual_available_observations"] == 2
    assert result["missed_observations"] == 0


def test_23_metrics_coverage():
    result = PerformanceOverTimeDashboardService(report=report()).metrics()
    assert result["actual_coverage"] == 1.0
    assert result["miss_rate"] == 0.0


def test_24_dashboard_composition():
    result = PerformanceOverTimeDashboardService(report=report()).dashboard()
    assert result["status"] == AVAILABLE
    assert result["summary"]["report_status"] == AVAILABLE
    assert result["periods"]["period_count"] == 2


def test_25_report_identity_summary():
    value = report()
    assert PerformanceOverTimeDashboardService(report=value).summary()["report_identity"] == value.report_identity


def test_26_report_identity_periods():
    value = report()
    assert PerformanceOverTimeDashboardService(report=value).periods()["report_identity"] == value.report_identity


def test_27_report_identity_trends():
    value = report()
    assert PerformanceOverTimeDashboardService(report=value).trends()["report_identity"] == value.report_identity


def test_28_report_identity_hit_rates():
    value = report()
    assert PerformanceOverTimeDashboardService(report=value).hit_rates()["report_identity"] == value.report_identity


def test_29_report_identity_metrics():
    value = report()
    assert PerformanceOverTimeDashboardService(report=value).metrics()["report_identity"] == value.report_identity


def test_30_period_limit():
    result = PerformanceOverTimeDashboardService(report=report(), max_periods=1).periods()
    assert result["returned_periods"] == 1
    assert result["period_count"] == 2


def test_31_read_only_surface():
    names = set(dir(PerformanceOverTimeDashboardService))
    assert not any(name in names for name in ("train", "retrain", "promote", "rollback", "delete"))


def test_32_source_type_preserved():
    value = report()
    assert PerformanceOverTimeDashboardService(report=value).summary()["source_type"] == "panel"


def test_33_period_days_preserved():
    value = report()
    assert PerformanceOverTimeDashboardService(report=value).summary()["period_days"] == 7


def test_34_trend_direction_is_valid():
    allowed = {"IMPROVING", "DECLINING", "STABLE"}
    for item in PerformanceOverTimeDashboardService(report=report()).trends()["trends"]:
        assert item["direction"] in allowed


def test_35_production_summary_route():
    response = client().get("/v1/performance/summary")
    assert response.status_code == 200
    assert response.get_json()["report_status"] == UNAVAILABLE


def test_36_production_periods_route():
    response = client().get("/v1/performance/periods")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_37_production_trends_route():
    response = client().get("/v1/performance/trends")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_38_production_hit_rates_route():
    response = client().get("/v1/performance/hit-rates")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_39_production_metrics_route():
    response = client().get("/v1/performance/metrics")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_40_production_routes_get_only():
    c = client()
    for path in (
        "/v1/performance/summary",
        "/v1/performance/periods",
        "/v1/performance/trends",
        "/v1/performance/hit-rates",
        "/v1/performance/metrics",
    ):
        assert c.post(path).status_code == 405


def test_41_frontend_summary_route():
    config = client().get("/frontend/config").get_json()
    assert config["routes"]["performance_summary"] == "/v1/performance/summary"


def test_42_frontend_periods_route():
    config = client().get("/frontend/config").get_json()
    assert config["routes"]["performance_periods"] == "/v1/performance/periods"


def test_43_frontend_trends_route():
    config = client().get("/frontend/config").get_json()
    assert config["routes"]["performance_trends"] == "/v1/performance/trends"


def test_44_frontend_hit_rates_route():
    config = client().get("/frontend/config").get_json()
    assert config["routes"]["performance_hit_rates"] == "/v1/performance/hit-rates"


def test_45_frontend_metrics_route():
    config = client().get("/frontend/config").get_json()
    assert config["routes"]["performance_metrics"] == "/v1/performance/metrics"


def test_46_frontend_view():
    html = client().get("/").get_data(as_text=True)
    assert 'id="view-performance"' in html
    assert "Performance-over-Time Dashboard" in html


def test_47_frontend_navigation():
    html = client().get("/").get_data(as_text=True)
    assert 'data-view="performance"' in html


def test_48_frontend_refresh():
    html = client().get("/").get_data(as_text=True)
    assert 'id="performance-refresh"' in html


def test_49_frontend_api_wiring():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "/v1/performance/summary" in js
    assert "/v1/performance/periods" in js
    assert "/v1/performance/trends" in js
    assert "/v1/performance/hit-rates" in js


def test_50_frontend_metrics_wiring():
    js = client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "/v1/performance/metrics" in js


def test_51_frontend_period_panel():
    html = client().get("/").get_data(as_text=True)
    assert 'id="performance-periods"' in html


def test_52_frontend_trend_panel():
    html = client().get("/").get_data(as_text=True)
    assert 'id="performance-trends"' in html


def test_53_frontend_hit_rate_panel():
    html = client().get("/").get_data(as_text=True)
    assert 'id="performance-hit-rates"' in html


def test_54_no_fabricated_dashboard_data():
    result = PerformanceOverTimeDashboardService().dashboard()
    assert result["summary"]["observations"] == 0
    assert result["periods"]["status"] == UNAVAILABLE
