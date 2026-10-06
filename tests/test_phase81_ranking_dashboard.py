from dataclasses import replace
from datetime import date, timedelta

from analytics.ranking_dashboard import (
    AVAILABLE,
    UNAVAILABLE,
    RANKING_DASHBOARD_BOUNDARY,
    RANKING_DASHBOARD_VERSION,
    RankingDashboardService,
    ranking_dashboard_contract,
)
from analytics.panel_ranking import (
    PanelCandidateInput,
    build_panel_ranking_report,
    rank_panels,
)
from analytics.jodi_ranking import (
    JodiCandidateInput,
    build_jodi_ranking_report,
    rank_jodis,
)
from analytics.top_k_framework import build_top_k_evaluation_report
from analytics.actual_vs_ranked import build_actual_vs_ranked_report
from analytics.performance_over_time import build_performance_over_time_report
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


def panel_observation(group_id="panel-g1", target_date=date(2026, 9, 29), actual="000"):
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
        target_date,
        actual_panel=actual,
        top_k=4,
    )


def jodi_observation(group_id="jodi-g1", target_date=date(2026, 9, 29), actual="00"):
    return rank_jodis(
        prediction(group_id + "-1"),
        prediction(group_id + "-2"),
        (
            JodiCandidateInput("00", "jf0", "pf0"),
            JodiCandidateInput("12", "jf1", "pf1"),
            JodiCandidateInput("99", "jf9", "pf9"),
            JodiCandidateInput("05", "jf5", "pf5"),
        ),
        group_id,
        target_date,
        actual_jodi=actual,
        top_k=4,
    )


def reports():
    panel = build_panel_ranking_report(
        (panel_observation(),),
        ("model-p1", "model-p2", "model-p3"),
        4,
    )
    jodi = build_jodi_ranking_report(
        (jodi_observation(),),
        ("model-j1", "model-j2"),
        4,
    )
    topk = build_top_k_evaluation_report(panel.observations, panel.report_identity, (1, 2, 4))
    actual = build_actual_vs_ranked_report(topk)
    performance = build_performance_over_time_report(actual, period_days=7)
    return panel, jodi, topk, actual, performance


def test_01_version():
    assert RANKING_DASHBOARD_VERSION == "81.0.0"


def test_02_boundary():
    assert RANKING_DASHBOARD_BOUNDARY == "RANKING_DASHBOARD_BOUNDARY"


def test_03_contract_is_read_only():
    contract = ranking_dashboard_contract()
    assert contract["read_only"] is True
    assert len(contract["routes"]) == 6


def test_04_empty_summary_is_truthful():
    result = RankingDashboardService().summary()
    assert result["status"] == "VALID"
    assert result["available_sections"] == 0
    assert result["read_only"] is True


def test_05_empty_panel():
    result = RankingDashboardService().panel()
    assert result["status"] == UNAVAILABLE
    assert result["reason"] == "REPORT_NOT_ATTACHED"


def test_06_empty_jodi():
    assert RankingDashboardService().jodi()["status"] == UNAVAILABLE


def test_07_empty_top_k():
    assert RankingDashboardService().top_k()["status"] == UNAVAILABLE


def test_08_empty_actual_vs_ranked():
    assert RankingDashboardService().actual_vs_ranked()["status"] == UNAVAILABLE


def test_09_empty_performance():
    assert RankingDashboardService().performance()["status"] == UNAVAILABLE


def test_10_panel_projection():
    panel, *_ = reports()
    result = RankingDashboardService(panel_report=panel).panel()
    assert result["status"] == AVAILABLE
    assert result["observations"] == 1
    assert result["top_k"] == 4
    assert len(result["observations_detail"]) == 1


def test_11_panel_top_candidate_projection():
    panel, *_ = reports()
    observation = RankingDashboardService(panel_report=panel).panel()["observations_detail"][0]
    assert observation["top_candidates"][0]["rank"] == 1
    assert observation["top_candidates"][0]["panel"] == "000"


def test_12_jodi_projection():
    _, jodi, *_ = reports()
    result = RankingDashboardService(jodi_report=jodi).jodi()
    assert result["status"] == AVAILABLE
    assert result["observations"] == 1
    assert result["top_k"] == 4


def test_13_jodi_leading_zero_preserved():
    _, jodi, *_ = reports()
    result = RankingDashboardService(jodi_report=jodi).jodi()
    assert result["observations_detail"][0]["top_candidates"][0]["jodi"] == "00"


def test_14_top_k_projection():
    panel, _, topk, _, _ = reports()
    result = RankingDashboardService(top_k_report=topk).top_k()
    assert result["status"] == AVAILABLE
    assert result["ks"] == (1, 2, 4)
    assert result["evaluated_observations"] == 1


def test_15_top_k_hit_rate_projection():
    panel, _, topk, _, _ = reports()
    result = RankingDashboardService(top_k_report=topk).top_k()
    assert dict(result["hit_rates"])[1] == 1.0


def test_16_actual_vs_ranked_projection():
    _, _, _, actual, _ = reports()
    result = RankingDashboardService(actual_vs_ranked_report=actual).actual_vs_ranked()
    assert result["status"] == AVAILABLE
    assert result["actual_available_observations"] == 1
    assert result["missed_observations"] == 0


def test_17_actual_vs_ranked_rank_metrics():
    _, _, _, actual, _ = reports()
    result = RankingDashboardService(actual_vs_ranked_report=actual).actual_vs_ranked()
    assert result["mean_actual_rank"] >= 1
    assert result["mean_reciprocal_rank"] > 0


def test_18_performance_projection():
    *_, performance = reports()
    result = RankingDashboardService(performance_report=performance).performance()
    assert result["status"] == AVAILABLE
    assert result["periods"] == 1
    assert result["observations"] == 1


def test_19_performance_trends_projection():
    *_, performance = reports()
    result = RankingDashboardService(performance_report=performance).performance()
    assert result["trends"]


def test_20_combined_summary():
    panel, jodi, topk, actual, performance = reports()
    result = RankingDashboardService(
        panel_report=panel,
        jodi_report=jodi,
        top_k_report=topk,
        actual_vs_ranked_report=actual,
        performance_report=performance,
    ).summary()
    assert result["available_sections"] == 5
    assert all(value == AVAILABLE for value in result["sections"].values())


def test_21_partial_summary():
    panel, *_ = reports()
    result = RankingDashboardService(panel_report=panel).summary()
    assert result["available_sections"] == 1
    assert result["sections"]["panel"] == AVAILABLE
    assert result["sections"]["jodi"] == UNAVAILABLE


def test_22_read_only_api_surface():
    names = dir(RankingDashboardService)
    assert not any(name in names for name in ("rank", "promote", "retrain", "activate", "rollback", "delete"))


def test_23_panel_report_identity_preserved():
    panel, *_ = reports()
    assert RankingDashboardService(panel_report=panel).panel()["report_identity"] == panel.report_identity


def test_24_jodi_report_identity_preserved():
    _, jodi, *_ = reports()
    assert RankingDashboardService(jodi_report=jodi).jodi()["report_identity"] == jodi.report_identity


def test_25_top_k_report_identity_preserved():
    _, _, topk, _, _ = reports()
    assert RankingDashboardService(top_k_report=topk).top_k()["report_identity"] == topk.report_identity


def test_26_actual_report_identity_preserved():
    _, _, _, actual, _ = reports()
    assert RankingDashboardService(actual_vs_ranked_report=actual).actual_vs_ranked()["report_identity"] == actual.report_identity


def test_27_performance_report_identity_preserved():
    *_, performance = reports()
    assert RankingDashboardService(performance_report=performance).performance()["report_identity"] == performance.report_identity


def production_client():
    svc = phase76_service(security_enabled=False, rate_enabled=False)
    svc.startup()
    return create_production_app(svc).test_client()


def test_28_production_summary_route():
    response = production_client().get("/v1/ranking/summary")
    assert response.status_code == 200
    assert response.get_json()["read_only"] is True


def test_29_production_panel_route():
    response = production_client().get("/v1/ranking/panel")
    assert response.status_code == 200
    assert response.get_json()["status"] == AVAILABLE


def test_30_production_jodi_route():
    response = production_client().get("/v1/ranking/jodi")
    assert response.status_code == 200
    assert response.get_json()["status"] == AVAILABLE


def test_31_production_top_k_route():
    response = production_client().get("/v1/ranking/top-k")
    assert response.status_code == 200
    assert response.get_json()["status"] == AVAILABLE


def test_32_production_actual_route():
    response = production_client().get("/v1/ranking/actual-vs-ranked")
    assert response.status_code == 200
    assert response.get_json()["status"] == AVAILABLE


def test_33_production_performance_route():
    response = production_client().get("/v1/ranking/performance")
    assert response.status_code == 200
    assert response.get_json()["status"] == AVAILABLE


def test_34_ranking_routes_are_get_only():
    client = production_client()
    for path in (
        "/v1/ranking/summary",
        "/v1/ranking/panel",
        "/v1/ranking/jodi",
        "/v1/ranking/top-k",
        "/v1/ranking/actual-vs-ranked",
        "/v1/ranking/performance",
    ):
        assert client.post(path).status_code == 405


def test_35_frontend_contains_ranking_view():
    html = production_client().get("/").get_data(as_text=True)
    assert "Ranking Dashboard" in html
    assert "ranking-refresh" in html


def test_36_frontend_js_contains_ranking_routes():
    js = production_client().get("/frontend/static/js/app.js").get_data(as_text=True)
    assert "/v1/ranking/summary" in js
    assert "/v1/ranking/top-k" in js
    assert "/v1/ranking/performance" in js


def test_37_frontend_config_exposes_ranking_routes():
    config = production_client().get("/frontend/config").get_json()
    assert config["routes"]["ranking_summary"] == "/v1/ranking/summary"


def test_38_frontend_has_ranking_navigation():
    html = production_client().get("/").get_data(as_text=True)
    assert 'data-view="ranking"' in html


def test_39_panel_zero_value_survives_dashboard():
    panel, *_ = reports()
    assert RankingDashboardService(panel_report=panel).panel()["observations_detail"][0]["top_candidates"][0]["panel"] == "000"


def test_40_contract_route_names_are_stable():
    assert ranking_dashboard_contract()["routes"] == (
        "/v1/ranking/summary",
        "/v1/ranking/panel",
        "/v1/ranking/jodi",
        "/v1/ranking/top-k",
        "/v1/ranking/actual-vs-ranked",
        "/v1/ranking/performance",
    )
