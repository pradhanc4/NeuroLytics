from datetime import date

from analytics.data_integrity_audit import (
    DATA_INTEGRITY_AUDIT_VERSION,
    INVALID,
    VALID,
    data_integrity_summary,
    run_data_integrity_audit,
    validate_data_integrity_audit,
    write_data_integrity_report,
)
from database.models import HistoricalResult, Market, PredictionFeedback, SequentialPredictionStage


def market(db):
    item = db.query(Market).filter(Market.name == "Integrity Market").first()
    if item is None:
        item = Market(name="Integrity Market")
        db.add(item)
        db.flush()
    return item


def result(db, day=1, open_value="123", jodi="45", close="678"):
    item = market(db)
    db.add(HistoricalResult(
        market_id=item.id,
        result_date=date(2026, 2, day),
        open_result=open_value,
        jodi_result=jodi,
        close_result=close,
        col1=int(open_value[0]),
        col2=int(open_value[1]),
        col3=int(open_value[2]),
        col4=int(jodi[0]),
        col5=int(jodi[1]),
        col6=int(close[0]),
        col7=int(close[1]),
        col8=int(close[2]),
    ))
    db.commit()
    return item


def test_phase93_version():
    assert DATA_INTEGRITY_AUDIT_VERSION == "93.0.0"


def test_phase93_valid_clean_database(db):
    result(db)
    report = run_data_integrity_audit(db)
    status, issues = validate_data_integrity_audit(report)
    assert status == VALID, [(item.code, item.severity, item.message) for item in report.issues]
    assert issues == ()
    assert report.is_valid


def test_phase93_row_counts(db):
    result(db)
    report = run_data_integrity_audit(db)
    summary = data_integrity_summary(report)
    assert summary["row_counts"]["markets"] == 1
    assert summary["row_counts"]["historical_results"] == 1
    assert summary["invalid_issue_count"] == 0


def test_phase93_detects_derived_column_mismatch(db):
    item = result(db)
    row = db.query(HistoricalResult).filter(HistoricalResult.market_id == item.id).one()
    row.col8 = 9
    db.commit()
    report = run_data_integrity_audit(db)
    assert report.status == INVALID
    assert any(issue.code == "DERIVED_COLUMNS_MISMATCH" for issue in report.issues)


def test_phase93_detects_invalid_result_shape(db):
    item = result(db)
    row = db.query(HistoricalResult).filter(HistoricalResult.market_id == item.id).one()
    row.open_result = "12"
    db.commit()
    report = run_data_integrity_audit(db)
    assert any(issue.code == "INVALID_OPEN" for issue in report.issues)


def test_phase93_detects_stage_result_mismatch(db):
    item = result(db, open_value="123", jodi="45")
    db.add(SequentialPredictionStage(
        market_id=item.id,
        result_date=date(2026, 2, 1),
        open_result="999",
        jodi_first_digit="9",
        status="COMPLETED",
    ))
    db.commit()
    report = run_data_integrity_audit(db)
    codes = {issue.code for issue in report.issues}
    assert "STAGE_OPEN_MISMATCH" in codes
    assert "STAGE_JODI_FIRST_MISMATCH" in codes


def test_phase93_detects_completed_stage_without_result(db):
    item = market(db)
    db.add(SequentialPredictionStage(
        market_id=item.id,
        result_date=date(2026, 2, 2),
        open_result="123",
        jodi_first_digit="4",
        status="COMPLETED",
    ))
    db.commit()
    report = run_data_integrity_audit(db)
    assert any(issue.code == "COMPLETED_STAGE_WITHOUT_RESULT" for issue in report.issues)


def test_phase93_detects_invalid_feedback_stage(db):
    db.add(PredictionFeedback(
        stage="BROKEN",
        predicted_value="45",
        actual_value="45",
        is_correct=True,
    ))
    db.commit()
    report = run_data_integrity_audit(db)
    assert any(issue.code == "INVALID_FEEDBACK_STAGE" for issue in report.issues)


def test_phase93_report_can_be_written(db, tmp_path):
    result(db)
    report = run_data_integrity_audit(db)
    path = write_data_integrity_report(report, tmp_path / "integrity.json")
    assert path.exists()
    assert "data-integrity-audit-" in path.read_text(encoding="utf-8")


def test_phase93_summary_has_market_context(db):
    result(db, day=1)
    result(db, day=3)
    report = run_data_integrity_audit(db)
    summary = data_integrity_summary(report)
    assert len(summary["market_summaries"]) == 1
    assert summary["market_summaries"][0]["historical_rows"] == 2
    assert summary["market_summaries"][0]["missing_calendar_intervals"]


def test_phase93_validation_rejects_wrong_version(db):
    result(db)
    report = run_data_integrity_audit(db)
    broken = report.__class__(
        version="wrong",
        status=report.status,
        checked_tables=report.checked_tables,
        row_counts=report.row_counts,
        issues=report.issues,
        market_summaries=report.market_summaries,
        report_identity=report.report_identity,
    )
    status, issues = validate_data_integrity_audit(broken)
    assert status == INVALID
    assert "INVALID:INVALID_VERSION" in issues
