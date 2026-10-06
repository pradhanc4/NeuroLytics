from datetime import date
from pathlib import Path

from analytics.production_service import create_production_app
from database.engine import SessionLocal
from database.models import SequentialPredictionStage
from tests.test_phase76_production_service_integration import service

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "frontend/static/js/app.js"
HTML = ROOT / "frontend/templates/index.html"


def client():
    return create_production_app(service(security_enabled=False, rate_enabled=False)).test_client()


def test_stage1_endpoint_saves_open_and_jodi_first():
    market = "PHASE92_SEQUENCE"
    response = client().post("/v1/historical/stage1", json={
        "date": "2098-01-01",
        "market_name": market,
        "open": "123",
        "jodi_first": "4",
    })
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["stage"]["open"] == "123"
    assert payload["stage"]["jodi_first"] == "4"

    db = SessionLocal()
    try:
        row = db.query(SequentialPredictionStage).filter(
            SequentialPredictionStage.result_date == date(2098, 1, 1)
        ).one()
        db.delete(row)
        db.commit()
    finally:
        db.close()


def test_stage2_requires_stage1():
    response = client().post("/v1/historical/stage2", json={
        "date": "2098-01-02",
        "market_name": "PHASE92_SEQUENCE_MISSING",
        "jodi_second": "5",
        "close": "678",
    })
    assert response.status_code == 400


def test_sequential_status_endpoint_exists():
    response = client().get("/v1/model/sequential/status")
    assert response.status_code == 200
    assert "status" in response.get_json()


def test_sequential_retrain_reports_insufficient_data_without_faking_training():
    response = client().post("/v1/model/sequential/retrain", json={})
    assert response.status_code in {200, 400}
    assert response.get_json()["status"] in {"COMPLETED", "INSUFFICIENT_DATA"}


def test_sequential_prediction_endpoint_requires_trained_model_or_returns_validation_error():
    response = client().post("/v1/model/sequential/predict", json={
        "open": "123",
        "jodi_first": "4",
    })
    assert response.status_code in {200, 400}


def test_feedback_endpoint_records_correctness_signal():
    response = client().post("/v1/model/feedback", json={
        "stage": "STAGE_2",
        "predicted_value": "45 678",
        "actual_value": "45 678",
        "is_correct": True,
        "date": "2098-01-01",
        "notes": "test",
    })
    assert response.status_code == 200
    assert response.get_json()["status"] == "VALID"


def test_frontend_contains_two_stage_data_entry_controls():
    html = client().get("/").get_data(as_text=True)
    for value in [
        "Stage 1",
        "Open + Jodi 1st digit",
        "Stage 2",
        "Jodi 2nd digit",
        "Save Stage 1 & Predict Stage 2",
        "Save Stage 2 & Complete Record",
        "Prediction Incorrect",
    ]:
        assert value in html


def test_frontend_contains_sequential_prediction_and_feedback_api():
    js = JS.read_text(encoding="utf-8")
    for value in [
        "/v1/historical/stage1",
        "/v1/historical/stage2",
        "/v1/model/sequential/predict",
        "/v1/model/sequential/retrain",
        "/v1/model/feedback",
        "saveStage1",
        "saveStage2",
        "sendPredictionFeedback",
    ]:
        assert value in js
