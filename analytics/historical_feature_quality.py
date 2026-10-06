from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from statistics import mean

from analytics.historical_feature_dataset import (
    FEATURE_VERSION,
    HistoricalFeatureDataset,
    validate_historical_feature_dataset,
)

QUALITY_VERSION = "C.4.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class FeatureQualityReport:
    version: str
    feature_version: str
    status: str
    record_count: int
    feature_count: int
    target_count: int
    missing_value_count: int
    non_finite_value_count: int
    duplicate_date_count: int
    chronological_violations: int
    future_history_violations: int
    target_leakage_count: int
    constant_feature_names: tuple[str, ...]
    feature_minimums: tuple[tuple[str, float], ...]
    feature_maximums: tuple[tuple[str, float], ...]
    feature_means: tuple[tuple[str, float], ...]
    temporal_safe: bool
    validation_issues: tuple[str, ...]
    warnings: tuple[str, ...]
    report_identity: str


def _identity(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def evaluate_feature_quality(dataset: HistoricalFeatureDataset) -> FeatureQualityReport:
    validation_status, validation_issues = validate_historical_feature_dataset(dataset)
    missing = non_finite = target_leakage = chronological = future_history = duplicate_dates = 0
    dates: list[date] = []
    values_by_feature: dict[str, list[float]] = {name: [] for name in dataset.feature_names}
    forbidden = {"jodi_1", "jodi_2", "close_1", "close_2", "close_3"}

    for row in dataset.rows:
        current_date = date.fromisoformat(row.result_date)
        if dates and current_date <= dates[-1]:
            chronological += 1
        if current_date in dates:
            duplicate_dates += 1
        dates.append(current_date)
        if row.source_history_end_date is not None and date.fromisoformat(row.source_history_end_date) >= current_date:
            future_history += 1
        target_leakage += len(forbidden.intersection(row.features))
        for name in dataset.feature_names:
            if name not in row.features or row.features[name] is None:
                missing += 1
                continue
            value = row.features[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                missing += 1
                continue
            number = float(value)
            if not math.isfinite(number):
                non_finite += 1
                continue
            values_by_feature[name].append(number)

    constant = tuple(sorted(name for name, values in values_by_feature.items() if values and min(values) == max(values)))
    minimums = tuple(sorted((name, min(values)) for name, values in values_by_feature.items() if values))
    maximums = tuple(sorted((name, max(values)) for name, values in values_by_feature.items() if values))
    means = tuple(sorted((name, round(mean(values), 8)) for name, values in values_by_feature.items() if values))
    warnings = (f"CONSTANT_FEATURES:{len(constant)}",) if constant else ()

    status = VALID if (
        validation_status == VALID and missing == 0 and non_finite == 0
        and duplicate_dates == 0 and chronological == 0
        and future_history == 0 and target_leakage == 0 and dataset.temporal_safe
    ) else INVALID
    payload = {
        "version": QUALITY_VERSION, "feature_version": FEATURE_VERSION, "status": status,
        "record_count": dataset.record_count, "feature_names": dataset.feature_names,
        "target_names": dataset.target_names, "missing": missing, "non_finite": non_finite,
        "duplicate_dates": duplicate_dates, "chronological": chronological,
        "future_history": future_history, "target_leakage": target_leakage,
        "constant": constant, "validation_issues": validation_issues,
    }
    return FeatureQualityReport(
        version=QUALITY_VERSION, feature_version=FEATURE_VERSION, status=status,
        record_count=dataset.record_count, feature_count=len(dataset.feature_names),
        target_count=len(dataset.target_names), missing_value_count=missing,
        non_finite_value_count=non_finite, duplicate_date_count=duplicate_dates,
        chronological_violations=chronological, future_history_violations=future_history,
        target_leakage_count=target_leakage, constant_feature_names=constant,
        feature_minimums=minimums, feature_maximums=maximums, feature_means=means,
        temporal_safe=dataset.temporal_safe, validation_issues=validation_issues,
        warnings=warnings, report_identity=f"historical-feature-quality-{_identity(payload)}",
    )


def validate_feature_quality_report(report: FeatureQualityReport) -> tuple[str, tuple[str, ...]]:
    issues: list[str] = []
    if report.version != QUALITY_VERSION: issues.append("INVALID_VERSION")
    if report.feature_version != FEATURE_VERSION: issues.append("INVALID_FEATURE_VERSION")
    if report.status != VALID: issues.append("QUALITY_STATUS_INVALID")
    if report.missing_value_count: issues.append("MISSING_VALUES")
    if report.non_finite_value_count: issues.append("NON_FINITE_VALUES")
    if report.duplicate_date_count: issues.append("DUPLICATE_DATES")
    if report.chronological_violations: issues.append("CHRONOLOGICAL_VIOLATIONS")
    if report.future_history_violations: issues.append("FUTURE_HISTORY_REFERENCES")
    if report.target_leakage_count: issues.append("TARGET_LEAKAGE")
    if not report.temporal_safe: issues.append("TEMPORAL_SAFETY_FALSE")
    if not report.report_identity.startswith("historical-feature-quality-"): issues.append("INVALID_REPORT_IDENTITY")
    return (VALID if not issues else INVALID, tuple(sorted(set(issues))))


def write_feature_quality_report(report: FeatureQualityReport, path: str | Path = "reports/historical_feature_quality.json") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return destination


__all__ = [
    "QUALITY_VERSION", "VALID", "INVALID", "FeatureQualityReport",
    "evaluate_feature_quality", "validate_feature_quality_report",
    "write_feature_quality_report",
]
