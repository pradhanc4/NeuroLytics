from analytics.top_k_dashboard import (
    AVAILABLE,
    UNAVAILABLE,
    TOP_K_DASHBOARD_BOUNDARY,
    TOP_K_DASHBOARD_VERSION,
    TopKDashboardService,
    top_k_dashboard_contract,
)
from analytics.top_k_framework import build_top_k_evaluation_report
from analytics.panel_ranking import PanelCandidateInput, rank_panels, build_panel_ranking_report
from analytics.learning_to_rank_model import LearningToRankPrediction
from analytics.production_service import create_production_app
from tests.test_phase76_production_service_integration import service as phase76_service


def prediction(group_id, probabilities=(0.7, 0.2, 0.1, 0, 0, 0, 0, 0, 0, 0)):
    return LearningToRankPrediction(
        group_id=group_id,
        target_date="2026-09-29",
        candidate_digits=tuple(range(10)),
        scores=probabilities,
        probabilities=probabilities,
        ranks=tuple(range(1, 11)),
        actual_digit=0,
        top_candidate=0,
        top_k_candidates=(0, 1, 2),
    )


def observation(group_id="g1", actual="000"):
    return rank_panels(
        prediction(group_id + "-1"),
        prediction(group_id + "-2"),
        prediction(group_id + "-3"),
        (
            PanelCandidateInput("000", "pf0", "jf0"),
            PanelCandidateInput("123", "pf1", "jf1"),
            PanelCandidateInput("999", "pf9", "jf9"),
            PanelCandidateInput("045", "pf4", "jf4"),
        ),
        group_id,
        __import__("datetime").date(2026, 9, 29),
        actual_panel=actual,
        top_k=4,
    )


def report():
    panel = build_panel_ranking_report(
        (observation(),),
        ("model-p1", "model-p2", "model-p3"),
        4,
    )
    return build_top_k_evaluation_report(panel.observations, panel.report_identity, (1, 2, 4))


def test_01_version():
    assert TOP_K_DASHBOARD_VERSION == "82.0.0"


def test_02_boundary():
    assert TOP_K_DASHBOARD_BOUNDARY == "TOP_K_DASHBOARD_BOUNDARY"


def test_03_contract_read_only():
    c = top_k_dashboard_contract()
    assert c["read_only"] is True
    assert len(c["routes"]) == 6


def test_04_empty_summary():
    result = TopKDashboardService().summary()
    assert result["status"] == "VALID"
    assert result["report_status"] == UNAVAILABLE
    assert result["read_only"] is True


def test_05_empty_metrics():
    assert TopKDashboardService().metrics()["status"] == UNAVAILABLE


def test_06_empty_rows():
    assert TopKDashboardService().rows()["status"] == UNAVAILABLE


def test_07_empty_hit_rate():
    assert TopKDashboardService().hit_rate_series()["status"] == UNAVAILABLE


def test_08_empty_rank_distribution():
    assert TopKDashboardService().rank_distribution()["status"] == UNAVAILABLE


def test_09_empty_coverage():
    assert TopKDashboardService().coverage()["status"] == UNAVAILABLE


def test_10_available_summary():
    result = TopKDashboardService(report=report()).summary()
    assert result["report_status"] == AVAILABLE
    assert result["evaluated_observations"] == 1
def test_11_metrics_ks():
    result = TopKDashboardService(report=report()).metrics()
    assert result["ks"] == (1, 2, 4)


def test_12_metrics_hit_rates():
    result = TopKDashboardService(report=report()).metrics()
    assert len(result["hit_rates"]) == 3
    assert result["hit_rates"][0]["k"] == 1


def test_13_metrics_mrr():
    result = TopKDashboardService(report=report()).metrics()
    assert result["mean_reciprocal_rank"] == 1.0


def test_14_hit_rate_series():
    result = TopKDashboardService(report=report()).hit_rate_series()
    assert [x["k"] for x in result["points"]] == [1, 2, 4]


def test_15_hit_rate_percent():
    result = TopKDashboardService(report=report()).hit_rate_series()
    assert result["points"][0]["hit_percent"] == 100.0


def test_16_rank_distribution():
    result = TopKDashboardService(report=report()).rank_distribution()
    assert result["rank_counts"] == ({"rank": 1, "count": 1},)
    assert result["unranked_observations"] == 0


def test_17_coverage():
    result = TopKDashboardService(report=report()).coverage()
    assert result["actual_available_observations"] == 1
    assert result["actual_coverage"] == 1.0


def test_18_rows_count():
    result = TopKDashboardService(report=report()).rows()
    assert result["row_count"] == 1
    assert result["returned_rows"] == 1


def test_19_row_identity_fields():
    row = TopKDashboardService(report=report()).rows()["rows"][0]
    assert row["group_id"] == "g1"
    assert row["actual_value"] == "000"


def test_20_row_hit_fields():
    row = TopKDashboardService(report=report()).rows()["rows"][0]
    assert row["hit_at_k"] == (
        {"k": 1, "hit": True},
        {"k": 2, "hit": True},
        {"k": 4, "hit": True},
    )


def test_21_dashboard_composition():
    result = TopKDashboardService(report=report()).dashboard()
    assert set(result) == {"status", "summary", "metrics", "hit_rate_series", "rank_distribution", "coverage", "rows"}


def test_22_dashboard_status():
    assert TopKDashboardService(report=report()).dashboard()["status"] == AVAILABLE


def test_23_row_limit_is_bounded():
    service = TopKDashboardService(report=report(), max_detail_rows=0)
    assert service.rows()["returned_rows"] == 1


def test_24_summary_preserves_source_type():
    assert TopKDashboardService(report=report()).summary()["source_type"] == "panel"


def test_25_summary_read_only():
    assert TopKDashboardService(report=report()).summary()["read_only"] is True


def test_26_no_mutation_methods():
    names = set(dir(TopKDashboardService))
    assert "train" not in names
    assert "promote" not in names
    assert "delete" not in names


def test_27_production_summary_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    response = app.test_client().get("/v1/top-k/summary")
    assert response.status_code == 200
    assert response.get_json()["report_status"] == UNAVAILABLE


def test_28_production_metrics_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    response = app.test_client().get("/v1/top-k/metrics")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_29_production_rows_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    response = app.test_client().get("/v1/top-k/rows")
    assert response.status_code == 200
    assert response.get_json()["status"] == UNAVAILABLE


def test_30_production_get_only():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    response = app.test_client().post("/v1/top-k/summary")
    assert response.status_code == 405


def test_31_production_hit_rate_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    assert app.test_client().get("/v1/top-k/hit-rate").status_code == 200


def test_32_production_rank_distribution_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    assert app.test_client().get("/v1/top-k/rank-distribution").status_code == 200


def test_33_production_coverage_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    assert app.test_client().get("/v1/top-k/coverage").status_code == 200


def test_34_frontend_route_contract():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    config = app.test_client().get("/frontend/config").get_json()
    assert config["routes"]["top_k_summary"] == "/v1/top-k/summary"


def test_35_frontend_top_k_metrics_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    config = app.test_client().get("/frontend/config").get_json()
    assert config["routes"]["top_k_metrics"] == "/v1/top-k/metrics"
def test_36_frontend_top_k_rows_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    config = app.test_client().get("/frontend/config").get_json()
    assert config["routes"]["top_k_rows"] == "/v1/top-k/rows"


def test_37_frontend_top_k_hit_rate_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    config = app.test_client().get("/frontend/config").get_json()
    assert config["routes"]["top_k_hit_rate"] == "/v1/top-k/hit-rate"


def test_38_frontend_top_k_rank_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    config = app.test_client().get("/frontend/config").get_json()
    assert config["routes"]["top_k_rank_distribution"] == "/v1/top-k/rank-distribution"


def test_39_frontend_top_k_coverage_route():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    config = app.test_client().get("/frontend/config").get_json()
    assert config["routes"]["top_k_coverage"] == "/v1/top-k/coverage"


def test_40_frontend_contains_top_k_dashboard():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    html = app.test_client().get("/").get_data(as_text=True)
    assert 'id="view-top-k"' in html
    assert 'Top-K Dashboard' in html


def test_41_frontend_contains_navigation():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    html = app.test_client().get("/").get_data(as_text=True)
    assert 'data-view="top-k"' in html


def test_42_frontend_contains_refresh():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    html = app.test_client().get("/").get_data(as_text=True)
    assert 'id="top-k-refresh"' in html


def test_43_frontend_contains_hit_rate_panel():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    html = app.test_client().get("/").get_data(as_text=True)
    assert 'id="top-k-hit-rate"' in html


def test_44_frontend_contains_observation_table():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    html = app.test_client().get("/").get_data(as_text=True)
    assert 'id="top-k-rows"' in html


def test_45_frontend_contains_top_k_api():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    js = app.test_client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "/v1/top-k/summary" in js
    assert "/v1/top-k/metrics" in js
    assert "/v1/top-k/hit-rate" in js


def test_46_frontend_contains_rank_distribution_api():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    js = app.test_client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "/v1/top-k/rank-distribution" in js


def test_47_frontend_contains_coverage_api():
    app = create_production_app(phase76_service(security_enabled=False, rate_enabled=False))
    js = app.test_client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "/v1/top-k/coverage" in js


def test_48_report_identity_is_exposed():
    report_value = report()
    result = TopKDashboardService(report=report_value).metrics()
    assert result["report_identity"] == report_value.report_identity


def test_49_dashboard_does_not_fabricate_data():
    result = TopKDashboardService().dashboard()
    assert result["summary"]["evaluated_observations"] == 0
    assert result["rows"]["status"] == UNAVAILABLE


def test_50_contract_routes_are_stable():
    routes = top_k_dashboard_contract()["routes"]
    assert routes == (
        "/v1/top-k/summary",
        "/v1/top-k/metrics",
        "/v1/top-k/rows",
        "/v1/top-k/hit-rate",
        "/v1/top-k/rank-distribution",
        "/v1/top-k/coverage",
    )
