from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from database.engine import Base
from database.models import (
    HistoricalResult,
    Market,
    PredictionFeedback,
    SequentialPredictionStage,
)

DATA_INTEGRITY_AUDIT_VERSION = "93.0.0"
VALID = "VALID"
INVALID = "INVALID"
WARNING = "WARNING"


@dataclass(frozen=True)
class IntegrityIssue:
    code: str
    severity: str
    table: str
    record_id: int | None
    message: str


@dataclass(frozen=True)
class DataIntegrityAuditReport:
    version: str
    status: str
    checked_tables: tuple[str, ...]
    row_counts: tuple[tuple[str, int], ...]
    issues: tuple[IntegrityIssue, ...]
    market_summaries: tuple[dict[str, Any], ...]
    report_identity: str

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _stable_identity(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _issue(code: str, severity: str, table: str, record_id: int | None, message: str) -> IntegrityIssue:
    return IntegrityIssue(code, severity, table, record_id, message)


def _valid_digit_string(value: Any, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and value.isdigit()


def _check_historical_results(db: Session) -> list[IntegrityIssue]:
    issues: list[IntegrityIssue] = []
    rows = db.scalars(select(HistoricalResult).order_by(HistoricalResult.id)).all()
    for row in rows:
        if not _valid_digit_string(row.open_result, 3):
            issues.append(_issue("INVALID_OPEN", INVALID, "historical_results", row.id, "Open must contain exactly 3 digits."))
        if not _valid_digit_string(row.jodi_result, 2):
            issues.append(_issue("INVALID_JODI", INVALID, "historical_results", row.id, "Jodi must contain exactly 2 digits."))
        if not _valid_digit_string(row.close_result, 3):
            issues.append(_issue("INVALID_CLOSE", INVALID, "historical_results", row.id, "Close must contain exactly 3 digits."))
        if row.result_date is None:
            issues.append(_issue("NULL_RESULT_DATE", INVALID, "historical_results", row.id, "Result date is required."))
        if row.market_id is None:
            issues.append(_issue("NULL_MARKET_ID", INVALID, "historical_results", row.id, "Market reference is required."))

        digits = (row.open_result or "") + (row.jodi_result or "") + (row.close_result or "")
        columns = [row.col1, row.col2, row.col3, row.col4, row.col5, row.col6, row.col7, row.col8]
        if len(digits) == 8:
            expected = [int(digit) for digit in digits]
            if columns != expected:
                issues.append(_issue(
                    "DERIVED_COLUMNS_MISMATCH",
                    INVALID,
                    "historical_results",
                    row.id,
                    f"col1-col8 do not match Open+Jodi+Close digits; expected {expected}, found {columns}.",
                ))
        if any(value is None or not isinstance(value, int) or value < 0 or value > 9 for value in columns):
            issues.append(_issue("INVALID_DERIVED_DIGIT", INVALID, "historical_results", row.id, "Every derived column must be an integer digit from 0 to 9."))

    duplicate_groups = db.execute(
        select(
            HistoricalResult.market_id,
            HistoricalResult.result_date,
            func.count(HistoricalResult.id),
        )
        .group_by(HistoricalResult.market_id, HistoricalResult.result_date)
        .having(func.count(HistoricalResult.id) > 1)
    ).all()
    for market_id, result_date, count in duplicate_groups:
        issues.append(_issue(
            "DUPLICATE_MARKET_DATE",
            INVALID,
            "historical_results",
            None,
            f"Market {market_id} has {count} records for {result_date}.",
        ))
    return issues


def _check_markets(db: Session) -> list[IntegrityIssue]:
    issues: list[IntegrityIssue] = []
    markets = db.scalars(select(Market).order_by(Market.id)).all()
    names: dict[str, int] = {}
    for market in markets:
        if not market.name or not market.name.strip():
            issues.append(_issue("EMPTY_MARKET_NAME", INVALID, "markets", market.id, "Market name cannot be empty."))
        key = market.name.strip().casefold() if market.name else ""
        if key in names:
            issues.append(_issue("DUPLICATE_MARKET_NAME_CASE_INSENSITIVE", INVALID, "markets", market.id, f"Market name duplicates market {names[key]} ignoring case."))
        else:
            names[key] = market.id
    return issues


def _check_foreign_keys(db: Session) -> list[IntegrityIssue]:
    issues: list[IntegrityIssue] = []
    markets = set(db.scalars(select(Market.id)).all())
    for row in db.scalars(select(HistoricalResult)).all():
        if row.market_id not in markets:
            issues.append(_issue("ORPHAN_HISTORICAL_RESULT", INVALID, "historical_results", row.id, "Historical result references a missing market."))
    for row in db.scalars(select(SequentialPredictionStage)).all():
        if row.market_id not in markets:
            issues.append(_issue("ORPHAN_SEQUENTIAL_STAGE", INVALID, "sequential_prediction_stages", row.id, "Sequential stage references a missing market."))
    for row in db.scalars(select(PredictionFeedback)).all():
        if row.market_id is not None and row.market_id not in markets:
            issues.append(_issue("ORPHAN_FEEDBACK", INVALID, "prediction_feedback", row.id, "Prediction feedback references a missing market."))
    return issues


def _check_sequential_stages(db: Session) -> list[IntegrityIssue]:
    issues: list[IntegrityIssue] = []
    stages = db.scalars(select(SequentialPredictionStage).order_by(SequentialPredictionStage.id)).all()
    for row in stages:
        if not _valid_digit_string(row.open_result, 3):
            issues.append(_issue("INVALID_STAGE_OPEN", INVALID, "sequential_prediction_stages", row.id, "Stage Open must contain exactly 3 digits."))
        if not _valid_digit_string(row.jodi_first_digit, 1):
            issues.append(_issue("INVALID_JODI_FIRST", INVALID, "sequential_prediction_stages", row.id, "Jodi first digit must contain exactly 1 digit."))
        if row.status not in {"STAGE_1", "COMPLETED"}:
            issues.append(_issue("INVALID_STAGE_STATUS", INVALID, "sequential_prediction_stages", row.id, f"Unknown stage status: {row.status}."))
        complete = db.scalar(
            select(HistoricalResult.id).where(
                HistoricalResult.market_id == row.market_id,
                HistoricalResult.result_date == row.result_date,
            )
        )
        if row.status == "COMPLETED" and complete is None:
            issues.append(_issue("COMPLETED_STAGE_WITHOUT_RESULT", INVALID, "sequential_prediction_stages", row.id, "Completed stage has no matching historical result."))
        if complete is not None:
            result = db.get(HistoricalResult, complete)
            if result is not None:
                if row.open_result != result.open_result:
                    issues.append(_issue("STAGE_OPEN_MISMATCH", INVALID, "sequential_prediction_stages", row.id, "Stage Open does not match the completed historical Open."))
                if row.jodi_first_digit != result.jodi_result[0]:
                    issues.append(_issue("STAGE_JODI_FIRST_MISMATCH", INVALID, "sequential_prediction_stages", row.id, "Stage Jodi-first does not match the completed historical Jodi first digit."))
        if row.status == "STAGE_1" and complete is not None:
            issues.append(_issue("OPEN_STAGE_WITH_COMPLETED_RESULT", WARNING, "sequential_prediction_stages", row.id, "Stage 1 remains open even though a complete historical result exists."))
    return issues


def _check_prediction_feedback(db: Session) -> list[IntegrityIssue]:
    issues: list[IntegrityIssue] = []
    rows = db.scalars(select(PredictionFeedback).order_by(PredictionFeedback.id)).all()
    for row in rows:
        if row.stage not in {"STAGE_1", "STAGE_2", "JODI_FIRST", "JODI_SECOND"}:
            issues.append(_issue("INVALID_FEEDBACK_STAGE", INVALID, "prediction_feedback", row.id, f"Unknown feedback stage: {row.stage}."))
        if not row.predicted_value:
            issues.append(_issue("EMPTY_PREDICTION_FEEDBACK", INVALID, "prediction_feedback", row.id, "Predicted value is required."))
        if row.is_correct and row.actual_value is None:
            issues.append(_issue("CORRECT_FEEDBACK_WITHOUT_ACTUAL", WARNING, "prediction_feedback", row.id, "Correct feedback has no actual value recorded."))
        if row.actual_value is not None and not row.actual_value.strip():
            issues.append(_issue("EMPTY_ACTUAL_FEEDBACK", INVALID, "prediction_feedback", row.id, "Actual feedback value cannot be blank."))
    return issues


def _check_database_constraints(db: Session) -> list[IntegrityIssue]:
    issues: list[IntegrityIssue] = []
    bind = db.get_bind()
    inspector = None
    try:
        from sqlalchemy import inspect
        inspector = inspect(bind)
        expected = set(Base.metadata.tables)
        live = set(inspector.get_table_names())
        for table in sorted(expected - live):
            issues.append(_issue("MISSING_TABLE", INVALID, "database", None, f"Expected table is missing: {table}."))
    except Exception as exc:
        issues.append(_issue("SCHEMA_INSPECTION_FAILED", INVALID, "database", None, str(exc)))
    return issues


def _market_summaries(db: Session) -> tuple[dict[str, Any], ...]:
    markets = db.scalars(select(Market).order_by(Market.id)).all()
    result: list[dict[str, Any]] = []
    for market in markets:
        rows = db.scalars(
            select(HistoricalResult)
            .where(HistoricalResult.market_id == market.id)
            .order_by(HistoricalResult.result_date, HistoricalResult.id)
        ).all()
        dates = [row.result_date for row in rows if row.result_date is not None]
        gaps: list[str] = []
        for previous, current in zip(dates, dates[1:]):
            delta = (current - previous).days
            if delta > 1:
                gaps.append(f"{previous.isoformat()}..{current.isoformat()}:{delta - 1} missing days")
        result.append({
            "market_id": market.id,
            "market": market.name,
            "historical_rows": len(rows),
            "first_date": dates[0].isoformat() if dates else None,
            "last_date": dates[-1].isoformat() if dates else None,
            "missing_calendar_intervals": gaps,
        })
    return tuple(result)


def run_data_integrity_audit(db: Session) -> DataIntegrityAuditReport:
    issues = []
    issues.extend(_check_database_constraints(db))
    issues.extend(_check_markets(db))
    issues.extend(_check_foreign_keys(db))
    issues.extend(_check_historical_results(db))
    issues.extend(_check_sequential_stages(db))
    issues.extend(_check_prediction_feedback(db))

    tables = (
        "markets",
        "historical_results",
        "sequential_prediction_stages",
        "prediction_feedback",
    )
    counts = []
    for table_name, model in (
        ("markets", Market),
        ("historical_results", HistoricalResult),
        ("sequential_prediction_stages", SequentialPredictionStage),
        ("prediction_feedback", PredictionFeedback),
    ):
        counts.append((table_name, int(db.scalar(select(func.count()).select_from(model)) or 0)))

    status = VALID if not any(issue.severity == INVALID for issue in issues) else INVALID
    report_identity = _stable_identity({
        "version": DATA_INTEGRITY_AUDIT_VERSION,
        "status": status,
        "tables": tables,
        "counts": counts,
        "issues": [
            {
                "code": issue.code,
                "severity": issue.severity,
                "table": issue.table,
                "record_id": issue.record_id,
                "message": issue.message,
            }
            for issue in issues
        ],
        "markets": _market_summaries(db),
    })

    return DataIntegrityAuditReport(
        version=DATA_INTEGRITY_AUDIT_VERSION,
        status=status,
        checked_tables=tables,
        row_counts=tuple(counts),
        issues=tuple(issues),
        market_summaries=_market_summaries(db),
        report_identity=f"data-integrity-audit-{report_identity}",
    )


def validate_data_integrity_audit(report: DataIntegrityAuditReport) -> tuple[str, tuple[str, ...]]:
    issues = [
        f"{issue.severity}:{issue.code}"
        for issue in report.issues
        if issue.severity == INVALID
    ]
    if report.version != DATA_INTEGRITY_AUDIT_VERSION:
        issues.append("INVALID:INVALID_VERSION")
    if not report.report_identity.startswith("data-integrity-audit-"):
        issues.append("INVALID:INVALID_REPORT_IDENTITY")
    return (INVALID if issues else VALID, tuple(sorted(set(issues))))


def data_integrity_summary(report: DataIntegrityAuditReport) -> dict[str, Any]:
    status, validation_issues = validate_data_integrity_audit(report)
    return {
        "status": status,
        "version": report.version,
        "checked_tables": list(report.checked_tables),
        "row_counts": dict(report.row_counts),
        "issue_count": len(report.issues),
        "invalid_issue_count": sum(item.severity == INVALID for item in report.issues),
        "warning_count": sum(item.severity == WARNING for item in report.issues),
        "issues": [
            {
                "code": item.code,
                "severity": item.severity,
                "table": item.table,
                "record_id": item.record_id,
                "message": item.message,
            }
            for item in report.issues
        ],
        "market_summaries": list(report.market_summaries),
        "report_identity": report.report_identity,
        "validation_issues": list(validation_issues),
    }


def write_data_integrity_report(report: DataIntegrityAuditReport, path=None):
    from pathlib import Path
    destination = Path(path or "reports/data_integrity_audit.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(data_integrity_summary(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination


__all__ = [
    "DATA_INTEGRITY_AUDIT_VERSION",
    "VALID",
    "INVALID",
    "WARNING",
    "IntegrityIssue",
    "DataIntegrityAuditReport",
    "run_data_integrity_audit",
    "validate_data_integrity_audit",
    "data_integrity_summary",
    "write_data_integrity_report",
]
