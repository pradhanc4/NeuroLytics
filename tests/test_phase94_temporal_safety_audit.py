from datetime import date
from pathlib import Path

from analytics.temporal_safety_audit import (
    TEMPORAL_SAFETY_AUDIT_VERSION,
    INVALID,
    VALID,
    run_temporal_safety_audit,
    temporal_safety_summary,
    validate_temporal_safety_audit,
    write_temporal_safety_report,
)
from database.models import HistoricalResult, Market


def _market(db, name="Temporal Market"):
    item = db.query(Market).filter(Market.name == name).first()
    if item is None:
        item = Market(name=name)
        db.add(item)
        db.flush()
    return item


def _result(db, market, day, seed="12345678"):
    row = HistoricalResult(
        market_id=market.id,
        result_date=date(2026, 3, day),
        open_result=seed[:3],
        jodi_result=seed[3:5],
        close_result=seed[5:8],
        col1=int(seed[0]),
        col2=int(seed[1]),
        col3=int(seed[2]),
        col4=int(seed[3]),
        col5=int(seed[4]),
        col6=int(seed[5]),
        col7=int(seed[6]),
        col8=int(seed[7]),
    )
    db.add(row)
    db.commit()
    return row


def test_phase94_version():
    assert TEMPORAL_SAFETY_AUDIT_VERSION == "94.0.0"


def test_phase94_empty_database_is_valid(db):
    report = run_temporal_safety_audit(db)
    status, issues = validate_temporal_safety_audit(report)
    assert status == VALID, issues
    assert issues == ()


def test_phase94_feature_boundary_probe_is_clean(db):
    report = run_temporal_safety_audit(db)
    summary = temporal_safety_summary(report)
    assert summary["invalid_issue_count"] == 0
    assert "feature_boundary_runtime_probe" in summary["checks"]


def test_phase94_database_prevents_duplicate_market_dates(db):
    from sqlalchemy.exc import IntegrityError

    market = _market(db)
    _result(db, market, 1, "12345678")
    db.add(HistoricalResult(
        market_id=market.id,
        result_date=date(2026, 3, 1),
        open_result="223",
        jodi_result="45",
        close_result="678",
        col1=2, col2=2, col3=3, col4=4, col5=5, col6=6, col7=7, col8=8,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        assert True
    else:
        raise AssertionError("database accepted a duplicate market/date row")


def test_phase94_multiple_markets_have_separate_temporal_summaries(db):
    first = _market(db, "Temporal A")
    second = _market(db, "Temporal B")
    _result(db, first, 1)
    _result(db, first, 2)
    _result(db, second, 1, "87654321")
    report = run_temporal_safety_audit(db)
    summary = temporal_safety_summary(report)
    assert len(summary["market_summaries"]) == 2


def test_phase94_source_contracts_are_present(db):
    report = run_temporal_safety_audit(db)
    codes = {item.code for item in report.issues}
    assert "POINT_IN_TIME_CONTRACT" not in codes
    assert "BACKTEST_CONTRACT" not in codes
    assert "SEQUENTIAL_CONTRACT" not in codes
    assert "CROSS_MARKET_HISTORY" not in codes


def test_phase94_unsafe_future_operation_scan_is_active(db):
    report = run_temporal_safety_audit(db)
    assert "unsafe_future_operation_scan" in report.checks


def test_phase94_report_identity_is_deterministic_shape(db):
    report = run_temporal_safety_audit(db)
    assert report.report_identity.startswith("temporal-safety-audit-")


def test_phase94_report_can_be_written(db, tmp_path):
    report = run_temporal_safety_audit(db)
    path = write_temporal_safety_report(report, tmp_path / "temporal.json")
    assert Path(path).exists()
    assert "temporal-safety-audit-" in Path(path).read_text(encoding="utf-8")


def test_phase94_summary_contains_issue_counts(db):
    report = run_temporal_safety_audit(db)
    summary = temporal_safety_summary(report)
    assert summary["issue_count"] == 0
    assert summary["invalid_issue_count"] == 0
    assert summary["warning_count"] == 0


def test_phase94_validation_rejects_wrong_version(db):
    report = run_temporal_safety_audit(db)
    broken = report.__class__(
        version="wrong",
        status=report.status,
        checks=report.checks,
        issues=report.issues,
        market_summaries=report.market_summaries,
        report_identity=report.report_identity,
    )
    status, issues = validate_temporal_safety_audit(broken)
    assert status == INVALID
    assert "INVALID:INVALID_VERSION" in issues


def test_phase94_current_project_has_strict_point_in_time_rule(db):
    root = Path(__file__).resolve().parents[1]
    source = (root / "features" / "point_in_time.py").read_text(encoding="utf-8")
    assert "observation.result_date < target_date" in source


def test_phase94_current_project_has_strict_backtest_rule(db):
    root = Path(__file__).resolve().parents[1]
    source = (root / "analytics" / "end_to_end_backtesting.py").read_text(encoding="utf-8")
    assert "fold.train_end_date >= fold.target_date" in source
    assert "fold.train_end_index >= fold.target_index" in source


def test_phase94_sequential_artifact_contract_is_declared(db):
    root = Path(__file__).resolve().parents[1]
    source = (root / "analytics" / "sequential_prediction.py").read_text(encoding="utf-8")
    assert '"strict_temporal_boundary": True' in source
    assert '"market_specific_history": True' in source
