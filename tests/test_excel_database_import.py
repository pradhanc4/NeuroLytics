from datetime import date
from pathlib import Path

from analytics.live_activity import live_activity
from database.engine import SessionLocal
from database.models import HistoricalResult, Market, PredictionFeedback
from scripts.import_excel_database import import_excel, read_excel_rows


def test_read_excel_rows_is_chronological_and_normalized():
    rows = read_excel_rows(Path(r"D:\NeuroLytics\data\RawData.xlsx"))
    assert len(rows) == 1990
    assert rows[0].result_date == date(2021, 2, 1)
    assert rows[0].open_result == "448"
    assert rows[0].jodi_result == "63"
    assert rows[0].close_result == "120"
    assert rows[-1].result_date == date(2026, 7, 31)
    assert all(rows[i].result_date < rows[i + 1].result_date for i in range(len(rows) - 1))


def test_database_import_stores_rows_without_ml(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    result = import_excel(
        Path(r"D:\NeuroLytics\data\RawData.xlsx"),
        market_name="TEST_EXCEL_DATABASE_IMPORT",
        checkpoint_path=checkpoint,
        start_row=2,
        limit=3,
    )
    assert result["status"] == "COMPLETED"
    assert result["imported"] == 3
    assert result["ml_executed"] is False
    assert result["predictions_executed"] is False
    assert result["feedback_executed"] is False
    assert result["retraining_executed"] is False

    db = SessionLocal()
    try:
        market = db.query(Market).filter(Market.name == "TEST_EXCEL_DATABASE_IMPORT").one()
        rows = (
            db.query(HistoricalResult)
            .filter(HistoricalResult.market_id == market.id)
            .order_by(HistoricalResult.result_date)
            .all()
        )
        assert len(rows) == 3
        assert [r.jodi_result for r in rows] == ["63", "48", "97"]
        assert [r.close_result for r in rows] == ["120", "134", "377"]
        assert db.query(PredictionFeedback).filter(
            PredictionFeedback.market_id == market.id
        ).count() == 0
        db.query(HistoricalResult).filter(HistoricalResult.market_id == market.id).delete()
        db.delete(market)
        db.commit()
    finally:
        db.close()


def test_database_import_checkpoint_resumes_without_predictions(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    source = Path(r"D:\NeuroLytics\data\RawData.xlsx")
    first = import_excel(
        source,
        market_name="TEST_EXCEL_IMPORT_RESUME",
        checkpoint_path=checkpoint,
        start_row=2,
        limit=2,
    )
    assert first["imported"] == 2

    second = import_excel(
        source,
        market_name="TEST_EXCEL_IMPORT_RESUME",
        checkpoint_path=checkpoint,
        limit=2,
    )
    assert second["imported"] == 2

    db = SessionLocal()
    try:
        market = db.query(Market).filter(Market.name == "TEST_EXCEL_IMPORT_RESUME").one()
        rows = (
            db.query(HistoricalResult)
            .filter(HistoricalResult.market_id == market.id)
            .order_by(HistoricalResult.result_date)
            .all()
        )
        assert len(rows) == 4
        assert [r.result_date.isoformat() for r in rows] == [
            "2021-02-01", "2021-02-02", "2021-02-03", "2021-02-04"
        ]
        db.query(HistoricalResult).filter(HistoricalResult.market_id == market.id).delete()
        db.delete(market)
        db.commit()
    finally:
        db.close()


def test_database_import_dry_run_writes_nothing(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    result = import_excel(
        Path(r"D:\NeuroLytics\data\RawData.xlsx"),
        market_name="TEST_EXCEL_DRY_RUN",
        checkpoint_path=checkpoint,
        start_row=2,
        limit=2,
        dry_run=True,
    )
    assert result["dry_run"] is True
    db = SessionLocal()
    try:
        assert db.query(Market).filter(Market.name == "TEST_EXCEL_DRY_RUN").count() == 0
    finally:
        db.close()


def test_importer_live_activity_uses_database_import_source():
    snapshot = live_activity.snapshot()
    assert snapshot["state"]["source"] in (None, "EXCEL_DATABASE_IMPORT")
