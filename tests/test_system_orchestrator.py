from datetime import date

from analytics.system_orchestrator import NeuroLyticsSystem


def test_system_reports_single_standalone_pipeline():
    system = NeuroLyticsSystem()
    payload = system.status()
    assert payload["system"] == "NeuroLytics Standalone System"
    assert payload["architecture"] == "LOCAL_SINGLE_APPLICATION"
    assert payload["pipeline"]["frames"] >= 10
    assert payload["pipeline"]["incomplete"] == 0


def test_stage2_is_atomic_and_completes_stage1():
    system = NeuroLyticsSystem()
    marker = date(2099, 12, 27)
    stage = system.save_stage1(marker, "PHASE101_ATOMIC", "123", "4")
    assert stage.payload["stage_id"] > 0

    completed = system.complete_stage2(stage.payload["stage_id"], "5", "678")
    assert completed.payload["jodi"] == "45"
    assert completed.payload["close"] == "678"
    assert completed.payload["stage_status"] == "COMPLETED"

    from database.engine import SessionLocal
    from database.models import HistoricalResult, Market, SequentialPredictionStage

    db = SessionLocal()
    try:
        market = db.query(Market).filter(Market.name == "PHASE101_ATOMIC").one()
        result = db.query(HistoricalResult).filter(
            HistoricalResult.market_id == market.id,
            HistoricalResult.result_date == marker,
        ).one()
        pending = db.query(SequentialPredictionStage).filter(
            SequentialPredictionStage.id == stage.payload["stage_id"]
        ).one()
        assert result.jodi_result == "45"
        assert result.close_result == "678"
        assert pending.status == "COMPLETED"
        db.delete(result)
        db.delete(pending)
        db.delete(market)
        db.commit()
    finally:
        db.close()


def test_database_snapshot_exposes_single_source_counts():
    payload = NeuroLyticsSystem().database_snapshot()
    for key in ("markets", "historical_results", "pending_stage1", "prediction_feedback"):
        assert key in payload


def test_system_routes_are_exposed_by_production_app():
    from analytics.production_service import create_production_app
    from tests.test_phase76_production_service_integration import service

    app = create_production_app(service(security_enabled=False, rate_enabled=False))
    client = app.test_client()
    assert client.get("/v1/system/status").status_code == 200
    assert client.get("/v1/system/pipeline").status_code == 200
    assert client.get("/v1/system/database").status_code == 200
