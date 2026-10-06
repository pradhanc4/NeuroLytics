from pathlib import Path

from analytics.production_service import create_production_app
from database.engine import SessionLocal
from database.models import HistoricalResult, Market
from tests.test_phase76_production_service_integration import service

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "frontend/static/js/app.js"
CSS = ROOT / "frontend/static/css/app.css"


def client():
    return create_production_app(
        service(security_enabled=False, rate_enabled=False)
    ).test_client()


def test_data_entry_database_endpoint_is_available():
    response = client().get("/v1/historical/records?limit=1000")
    assert response.status_code == 200
    assert response.get_json()["status"] == "VALID"


def test_data_entry_saves_and_normalizes_historical_result():
    market_name = "PHASE92_UI_TEST"
    from datetime import date
    result_date = date(2099, 12, 31)
    response = client().post(
        "/v1/historical/records",
        json={
            "date": result_date.isoformat(),
            "market_name": market_name,
            "data": "123 45 678",
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["status"] == "VALID"
    assert payload["record"]["columns"] == [1, 2, 3, 4, 5, 6, 7, 8]

    db = SessionLocal()
    try:
        market = db.query(Market).filter(Market.name == market_name).one()
        row = db.query(HistoricalResult).filter(
            HistoricalResult.market_id == market.id,
            HistoricalResult.result_date == result_date,
        ).one()
        db.delete(row)
        db.delete(market)
        db.commit()
    finally:
        db.close()


def test_frontend_contains_database_verification_table():
    html = client().get("/").get_data(as_text=True)
    for value in [
        "Complete database records",
        "data-entry-database-table",
        "data-entry-db-refresh",
    ]:
        assert value in html


def test_stage2_completes_the_selected_stage1_record():
    from datetime import date
    from database.models import SequentialPredictionStage

    market_name = "PHASE_STAGE2_FLOW_TEST"
    result_date = date(2099, 11, 30)
    client_instance = client()
    stage1 = client_instance.post(
        "/v1/historical/stage1",
        json={"date": result_date.isoformat(), "market_name": market_name, "open": "123", "jodi_first": "4"},
    )
    assert stage1.status_code == 201
    stage_id = stage1.get_json()["stage"]["id"]

    stage2 = client_instance.post(
        "/v1/historical/stage2",
        json={"stage_id": stage_id, "date": "2099-01-01", "market_name": "wrong-market", "jodi_second": "5", "close": "678"},
    )
    assert stage2.status_code == 201
    assert stage2.get_json()["record"]["date"] == result_date.isoformat()

    db = SessionLocal()
    try:
        market = db.query(Market).filter(Market.name == market_name).one()
        row = db.query(HistoricalResult).filter(
            HistoricalResult.market_id == market.id,
            HistoricalResult.result_date == result_date,
        ).one()
        stage = db.query(SequentialPredictionStage).filter(SequentialPredictionStage.id == stage_id).one()
        assert row.jodi_result == "45"
        assert row.close_result == "678"
        assert stage.status == "COMPLETED"
        db.delete(row)
        db.delete(stage)
        db.delete(market)
        db.commit()
    finally:
        db.close()


def test_frontend_contains_retraining_controls():
    html = client().get("/").get_data(as_text=True)
    js = JS.read_text(encoding="utf-8")
    for value in [
        "Retrain & Validate",
        "retrain-status",
        "retrain-accuracy",
        "/v1/model/retrain",
        "/v1/model/retrain/status",
    ]:
        assert value in html or value in js


def test_retraining_status_endpoint_is_available():
    response = client().get("/v1/model/retrain/status")
    assert response.status_code == 200
    assert "status" in response.get_json()


def test_data_entry_refreshes_database_after_save():
    js = JS.read_text(encoding="utf-8")
    assert "await loadDatabaseRecords();" in js


def test_prediction_and_database_layout_remain_responsive():
    css = CSS.read_text(encoding="utf-8")
    assert ".data-entry-database .table-wrap{max-height:560px" in css
    assert "#view-prediction .card-grid{grid-template-columns:1fr}" in css
    assert "@media(max-width:800px)" in css
