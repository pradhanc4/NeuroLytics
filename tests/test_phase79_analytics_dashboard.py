from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from analytics.analytics_dashboard import (
    ANALYTICS_DASHBOARD_BOUNDARY,
    ANALYTICS_DASHBOARD_VERSION,
    AnalyticsDashboardService,
)
from analytics.production_service import create_production_app
from database.engine import Base
from database.models import HistoricalResult, Market
from tests.test_phase76_production_service_integration import service


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        market = Market(name="Analytics Demo")
        session.add(market)
        session.flush()
        session.add_all([
            HistoricalResult(market_id=market.id, result_date=date(2026, 9, 1), open_result="123", jodi_result="45", close_result="678", col1=1, col2=2, col3=3, col4=5, col5=5, col6=6, col7=7, col8=8),
            HistoricalResult(market_id=market.id, result_date=date(2026, 9, 2), open_result="000", jodi_result="00", close_result="999", col1=0, col2=0, col3=1, col4=2, col5=3, col6=4, col7=5, col8=6),
            HistoricalResult(market_id=market.id, result_date=date(2026, 9, 4), open_result="555", jodi_result="55", close_result="777", col1=5, col2=5, col3=5, col4=5, col5=7, col6=7, col7=7, col8=7),
        ])
        session.commit()
        yield session


def test_01_version(db):
    assert AnalyticsDashboardService(db).summary()["version"] == ANALYTICS_DASHBOARD_VERSION


def test_02_boundary(db):
    assert AnalyticsDashboardService(db).summary()["boundary"] == ANALYTICS_DASHBOARD_BOUNDARY


def test_03_summary_records(db):
    assert AnalyticsDashboardService(db).summary()["record_count"] == 3


def test_04_summary_dates(db):
    result = AnalyticsDashboardService(db).summary()
    assert result["start_date"] == "2026-09-01"
    assert result["end_date"] == "2026-09-04"


def test_05_missing_calendar_days(db):
    result = AnalyticsDashboardService(db).summary()
    assert result["calendar_days"] == 4
    assert result["missing_calendar_days"] == 1
    assert result["coverage_percent"] == 75.0


def test_06_market_metadata(db):
    result = AnalyticsDashboardService(db).summary()
    assert result["available_markets"][0]["name"] == "Analytics Demo"


def test_07_distribution_has_ten_digits(db):
    assert len(AnalyticsDashboardService(db).distribution()["digits"]) == 10


def test_08_distribution_observation_count(db):
    assert AnalyticsDashboardService(db).distribution()["total_digit_observations"] == 24


def test_09_distribution_counts_zero(db):
    digits = AnalyticsDashboardService(db).distribution()["digits"]
    assert digits[0]["count"] == 2


def test_10_entropy_is_finite(db):
    assert AnalyticsDashboardService(db).distribution()["digit_entropy"] >= 0


def test_11_column_count(db):
    assert len(AnalyticsDashboardService(db).column_statistics()["columns"]) == 8


def test_12_column_mean(db):
    columns = AnalyticsDashboardService(db).column_statistics()["columns"]
    assert columns[0]["mean"] == 2.0


def test_13_column_std_nonnegative(db):
    assert all(item["std"] >= 0 for item in AnalyticsDashboardService(db).column_statistics()["columns"])


def test_14_trend_points(db):
    assert AnalyticsDashboardService(db).trends()["point_count"] == 3


def test_15_trend_direction(db):
    assert AnalyticsDashboardService(db).trends()["direction"] == "UP"


def test_16_trend_bounds(db):
    result = AnalyticsDashboardService(db).trends()
    assert result["min_row_mean"] <= result["max_row_mean"]


def test_17_latest_row_mean(db):
    result = AnalyticsDashboardService(db).trends()
    assert result["latest_row_mean"] == 6.0


def test_18_insights_exist(db):
    result = AnalyticsDashboardService(db).insights()
    assert len(result["insights"]) >= 5


def test_19_empty_summary():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        assert AnalyticsDashboardService(session).summary()["record_count"] == 0


def test_20_empty_distribution():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        assert AnalyticsDashboardService(session).distribution()["total_digit_observations"] == 0


def test_21_empty_trend():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        assert AnalyticsDashboardService(session).trends()["direction"] == "FLAT"


def test_22_production_summary_route():
    client = create_production_app(service(security_enabled=False)).test_client()
    assert client.get("/v1/analytics/summary").status_code == 200


def test_23_production_distribution_route():
    client = create_production_app(service(security_enabled=False)).test_client()
    assert client.get("/v1/analytics/distribution").status_code == 200


def test_24_production_columns_and_trends_routes():
    client = create_production_app(service(security_enabled=False)).test_client()
    assert client.get("/v1/analytics/columns").status_code == 200
    assert client.get("/v1/analytics/trends").status_code == 200


def test_25_production_insights_route():
    client = create_production_app(service(security_enabled=False)).test_client()
    assert client.get("/v1/analytics/insights").status_code == 200


def test_26_frontend_contains_analytics_view():
    client = create_production_app(service(security_enabled=False)).test_client()
    data = client.get("/").data
    assert b"Analytics Dashboard" in data
    assert b"analytics-refresh" in data


def test_27_frontend_static_js_contains_analytics_api():
    client = create_production_app(service(security_enabled=False)).test_client()
    data = client.get("/frontend/static/js/app.js").data
    assert b"/v1/analytics/summary" in data
    assert b"/v1/analytics/insights" in data


def test_28_frontend_static_css_contains_insights():
    client = create_production_app(service(security_enabled=False)).test_client()
    data = client.get("/frontend/static/css/app.css").data
    assert b".insight-list" in data


def test_29_analytics_routes_are_read_only():
    client = create_production_app(service(security_enabled=False)).test_client()
    assert client.post("/v1/analytics/summary").status_code == 405


def test_30_market_filter_is_accepted(db):
    market_id = AnalyticsDashboardService(db).markets()[0]["id"]
    assert AnalyticsDashboardService(db).summary(market_id)["record_count"] == 3

