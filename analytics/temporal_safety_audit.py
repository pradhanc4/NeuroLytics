from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import HistoricalResult
from features.historical_data_loader import HistoricalFeatureObservation
from features.lag_features import build_lag_features
from features.point_in_time import build_point_in_time_history
from features.rolling_features import build_rolling_features
from features.feature_config import FeatureConfig


TEMPORAL_SAFETY_AUDIT_VERSION = "94.0.0"
VALID = "VALID"
INVALID = "INVALID"
WARNING = "WARNING"

FUTURE_ROW = "FUTURE_ROW"
TARGET_DATE_INCLUDED = "TARGET_DATE_INCLUDED"
DUPLICATE_MARKET_DATE = "DUPLICATE_MARKET_DATE"
TRAIN_TARGET_BOUNDARY = "TRAIN_TARGET_BOUNDARY"
VALIDATION_BOUNDARY = "VALIDATION_BOUNDARY"
CROSS_MARKET_HISTORY = "CROSS_MARKET_HISTORY"
UNSAFE_FEATURE_PATTERN = "UNSAFE_FEATURE_PATTERN"
POINT_IN_TIME_CONTRACT = "POINT_IN_TIME_CONTRACT"
BACKTEST_CONTRACT = "BACKTEST_CONTRACT"
SEQUENTIAL_CONTRACT = "SEQUENTIAL_CONTRACT"


@dataclass(frozen=True)
class TemporalSafetyIssue:
    code: str
    severity: str
    area: str
    message: str
    market_id: int | None = None
    result_date: date | None = None


@dataclass(frozen=True)
class TemporalSafetyAuditReport:
    version: str
    status: str
    checks: tuple[str, ...]
    issues: tuple[TemporalSafetyIssue, ...]
    market_summaries: tuple[dict[str, Any], ...]
    report_identity: str

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _issue(
    code: str,
    severity: str,
    area: str,
    message: str,
    market_id: int | None = None,
    result_date: date | None = None,
) -> TemporalSafetyIssue:
    return TemporalSafetyIssue(code, severity, area, message, market_id, result_date)


def _check_database_temporal_order(db: Session) -> tuple[list[TemporalSafetyIssue], tuple[dict[str, Any], ...]]:
    issues: list[TemporalSafetyIssue] = []
    summaries: list[dict[str, Any]] = []

    market_ids = [
        int(value)
        for value in db.scalars(
            select(HistoricalResult.market_id)
            .where(HistoricalResult.market_id.is_not(None))
            .distinct()
            .order_by(HistoricalResult.market_id)
        ).all()
    ]

    for market_id in market_ids:
        rows = list(
            db.scalars(
                select(HistoricalResult)
                .where(HistoricalResult.market_id == market_id)
                .order_by(HistoricalResult.result_date, HistoricalResult.id)
            ).all()
        )
        dates = [row.result_date for row in rows if row.result_date is not None]
        duplicate_dates = {
            item for item in dates if dates.count(item) > 1
        }
        for duplicate in sorted(duplicate_dates):
            issues.append(
                _issue(
                    DUPLICATE_MARKET_DATE,
                    INVALID,
                    "database",
                    f"Market {market_id} contains duplicate historical result date {duplicate}.",
                    market_id,
                    duplicate,
                )
            )

        gaps = []
        for previous, current in zip(dates, dates[1:]):
            if current <= previous:
                issues.append(
                    _issue(
                        DUPLICATE_MARKET_DATE,
                        INVALID,
                        "database",
                        f"Historical dates are not strictly increasing for market {market_id}.",
                        market_id,
                        current,
                    )
                )
            elif (current - previous).days > 1:
                gaps.append(
                    f"{previous.isoformat()}..{current.isoformat()}:{(current - previous).days - 1}"
                )

        summaries.append(
            {
                "market_id": market_id,
                "rows": len(rows),
                "first_date": dates[0].isoformat() if dates else None,
                "last_date": dates[-1].isoformat() if dates else None,
                "missing_calendar_intervals": gaps,
            }
        )
    return issues, tuple(summaries)


def _source_contracts() -> tuple[list[TemporalSafetyIssue], dict[str, Any]]:
    issues: list[TemporalSafetyIssue] = []
    root = Path(__file__).resolve().parent.parent

    files = {
        "point_in_time": root / "features" / "point_in_time.py",
        "lag_features": root / "features" / "lag_features.py",
        "rolling_features": root / "features" / "rolling_features.py",
        "feature_pipeline": root / "features" / "feature_pipeline.py",
        "backtesting": root / "analytics" / "end_to_end_backtesting.py",
        "sequential": root / "analytics" / "sequential_prediction.py",
    }
    source = {}
    for name, path in files.items():
        if not path.exists():
            issues.append(_issue(
                "SOURCE_FILE_MISSING", INVALID, name,
                f"Required temporal-safety source file is missing: {path.name}.",
            ))
            continue
        source[name] = path.read_text(encoding="utf-8")

    pit = source.get("point_in_time", "")
    if "observation.result_date < target_date" not in pit:
        issues.append(_issue(
            POINT_IN_TIME_CONTRACT, INVALID, "point_in_time",
            "Point-in-time history must exclude the target date and all future dates.",
        ))

    pipeline = source.get("feature_pipeline", "")
    if "build_point_in_time_history" not in pipeline or "detect_point_in_time_history_leakage" not in pipeline:
        issues.append(_issue(
            POINT_IN_TIME_CONTRACT, INVALID, "feature_pipeline",
            "Feature pipeline must construct point-in-time history before feature generation.",
        ))

    lag = source.get("lag_features", "")
    rolling = source.get("rolling_features", "")
    if "get_point_in_time_observations" not in lag:
        issues.append(_issue(
            UNSAFE_FEATURE_PATTERN, INVALID, "lag_features",
            "Lag features do not visibly consume the point-in-time observation boundary.",
        ))
    if "get_point_in_time_observations" not in rolling:
        issues.append(_issue(
            UNSAFE_FEATURE_PATTERN, INVALID, "rolling_features",
            "Rolling features do not visibly consume the point-in-time observation boundary.",
        ))

    unsafe_patterns = (
        (r"shift\(\s*-\d+", "negative pandas shift detected"),
        (r"rolling\([^\n]*center\s*=\s*True", "centered rolling window detected"),
        (r"bfill\s*\(", "backward fill detected"),
    )
    for name, text in source.items():
        for pattern, message in unsafe_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                issues.append(_issue(
                    UNSAFE_FEATURE_PATTERN, INVALID, name,
                    f"Potential future-information operation: {message}.",
                ))

    backtest = source.get("backtesting", "")
    if "fold.train_end_date >= fold.target_date" not in backtest:
        issues.append(_issue(
            BACKTEST_CONTRACT, INVALID, "end_to_end_backtesting",
            "End-to-end backtesting must reject a training boundary at or after the target date.",
        ))
    if "fold.train_end_index >= fold.target_index" not in backtest:
        issues.append(_issue(
            BACKTEST_CONTRACT, INVALID, "end_to_end_backtesting",
            "End-to-end backtesting must reject a training index at or after the target index.",
        ))

    sequential = source.get("sequential", "")
    if '"strict_temporal_boundary": True' not in sequential:
        issues.append(_issue(
            SEQUENTIAL_CONTRACT, INVALID, "sequential_prediction",
            "Sequential model artifacts must declare a strict temporal boundary.",
        ))
    if '"market_specific_history": True' not in sequential:
        issues.append(_issue(
            CROSS_MARKET_HISTORY, INVALID, "sequential_prediction",
            "Sequential feature history must be restricted to the requested market.",
        ))
    if "grouped: dict[int, list[HistoricalResult]]" not in sequential:
        issues.append(_issue(
            CROSS_MARKET_HISTORY, INVALID, "sequential_prediction",
            "Sequential training must group historical rows by market before building history.",
        ))

    return issues, {
        "checked_files": {name: str(path) for name, path in files.items()},
        "unsafe_pattern_scan": True,
    }


def _feature_boundary_probe() -> tuple[list[TemporalSafetyIssue], dict[str, Any]]:
    issues: list[TemporalSafetyIssue] = []
    observations = (
        HistoricalFeatureObservation(1, 1, date(2026, 1, 1), (1, 2, 3, 4, 5, 6, 7, 8)),
        HistoricalFeatureObservation(2, 1, date(2026, 1, 2), (2, 3, 4, 5, 6, 7, 8, 1)),
        HistoricalFeatureObservation(3, 1, date(2026, 1, 3), (9, 9, 9, 9, 9, 9, 9, 9)),
    )
    target = date(2026, 1, 3)
    history = build_point_in_time_history(observations, target)

    if any(item.result_date >= target for item in history.observations):
        issues.append(_issue(
            FUTURE_ROW, INVALID, "feature_boundary_probe",
            "Point-in-time history included a target or future observation.",
            1, target,
        ))

    config = FeatureConfig(
        lag_windows=(1, 2),
        rolling_windows=(2,),
    )
    lag_result = build_lag_features(history, config)
    rolling_result = build_rolling_features(history, config)

    if any(record.value == 9 for record in lag_result.records if record.value is not None):
        issues.append(_issue(
            FUTURE_ROW, INVALID, "lag_features",
            "Lag feature probe consumed the target-date sentinel value.",
            1, target,
        ))
    if any(
        record.mean == 9 or record.minimum == 9 or record.maximum == 9
        for record in rolling_result.records
    ):
        issues.append(_issue(
            FUTURE_ROW, INVALID, "rolling_features",
            "Rolling feature probe consumed the target-date sentinel value.",
            1, target,
        ))

    return issues, {
        "target_date": target.isoformat(),
        "historical_observations": len(history.observations),
        "lag_records": len(lag_result.records),
        "rolling_records": len(rolling_result.records),
    }


def run_temporal_safety_audit(db: Session) -> TemporalSafetyAuditReport:
    issues, market_summaries = _check_database_temporal_order(db)
    source_issues, source_context = _source_contracts()
    probe_issues, probe_context = _feature_boundary_probe()
    issues.extend(source_issues)
    issues.extend(probe_issues)

    checks = (
        "database_market_chronology",
        "duplicate_market_date_detection",
        "point_in_time_source_contract",
        "lag_feature_source_contract",
        "rolling_feature_source_contract",
        "unsafe_future_operation_scan",
        "backtest_boundary_contract",
        "sequential_market_specific_history_contract",
        "feature_boundary_runtime_probe",
    )
    status = INVALID if any(item.severity == INVALID for item in issues) else VALID
    identity = _hash({
        "version": TEMPORAL_SAFETY_AUDIT_VERSION,
        "status": status,
        "checks": checks,
        "issues": [
            {
                "code": item.code,
                "severity": item.severity,
                "area": item.area,
                "message": item.message,
                "market_id": item.market_id,
                "result_date": item.result_date,
            }
            for item in issues
        ],
        "markets": market_summaries,
        "source": source_context,
        "probe": probe_context,
    })
    return TemporalSafetyAuditReport(
        version=TEMPORAL_SAFETY_AUDIT_VERSION,
        status=status,
        checks=checks,
        issues=tuple(issues),
        market_summaries=market_summaries,
        report_identity=f"temporal-safety-audit-{identity}",
    )


def validate_temporal_safety_audit(
    report: TemporalSafetyAuditReport,
) -> tuple[str, tuple[str, ...]]:
    problems = [
        f"{item.severity}:{item.code}"
        for item in report.issues
    ]
    if report.version != TEMPORAL_SAFETY_AUDIT_VERSION:
        problems.append("INVALID:INVALID_VERSION")
    if not report.report_identity.startswith("temporal-safety-audit-"):
        problems.append("INVALID:INVALID_REPORT_IDENTITY")
    return (
        INVALID if problems else VALID,
        tuple(sorted(set(problems))),
    )


def temporal_safety_summary(
    report: TemporalSafetyAuditReport,
) -> dict[str, Any]:
    status, validation_issues = validate_temporal_safety_audit(report)
    return {
        "status": status,
        "version": report.version,
        "checks": list(report.checks),
        "issue_count": len(report.issues),
        "invalid_issue_count": sum(item.severity == INVALID for item in report.issues),
        "warning_count": sum(item.severity == WARNING for item in report.issues),
        "issues": [
            {
                "code": item.code,
                "severity": item.severity,
                "area": item.area,
                "message": item.message,
                "market_id": item.market_id,
                "result_date": item.result_date.isoformat() if item.result_date else None,
            }
            for item in report.issues
        ],
        "market_summaries": list(report.market_summaries),
        "report_identity": report.report_identity,
        "validation_issues": list(validation_issues),
    }


def write_temporal_safety_report(
    report: TemporalSafetyAuditReport,
    path: str | Path | None = None,
) -> Path:
    destination = Path(path or "reports/temporal_safety_audit.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(temporal_safety_summary(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination


__all__ = [
    "TEMPORAL_SAFETY_AUDIT_VERSION",
    "VALID",
    "INVALID",
    "WARNING",
    "TemporalSafetyIssue",
    "TemporalSafetyAuditReport",
    "run_temporal_safety_audit",
    "validate_temporal_safety_audit",
    "temporal_safety_summary",
    "write_temporal_safety_report",
]
