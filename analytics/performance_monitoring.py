from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from analytics.performance_over_time import (
    PerformanceOverTimeReport,
    validate_performance_over_time_report,
)

PERFORMANCE_MONITORING_VERSION = "47.0.0"
VALID = "VALID"
INVALID = "INVALID"

DEFAULT_METRICS = (
    "mean_actual_rank",
    "mean_reciprocal_rank",
    "miss_rate",
    "mean_top_probability",
    "mean_cumulative_probability",
)

@dataclass(frozen=True)
class PerformanceMetricSnapshot:
    period_start: date
    period_end: date
    metric: str
    value: float
    observation_count: int
    actual_available_observations: int

@dataclass(frozen=True)
class PerformanceMonitoringReport:
    version: str
    source_type: str
    source_report_identity: str
    source_period_days: int
    monitored_metrics: tuple[str, ...]
    snapshots: tuple[PerformanceMetricSnapshot, ...]
    period_count: int
    observation_count: int
    actual_available_observations: int
    latest_period_start: date
    latest_period_end: date
    latest_values: tuple[tuple[str, float], ...]
    baseline_values: tuple[tuple[str, float], ...]
    report_identity: str

@dataclass(frozen=True)
class PerformanceMonitoringValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID
def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()

def _metric_value(period, metric: str) -> float:
    if metric == "mean_actual_rank":
        return period.mean_actual_rank if period.mean_actual_rank is not None else 0.0
    if metric == "mean_reciprocal_rank":
        return period.mean_reciprocal_rank
    if metric == "miss_rate":
        return period.miss_rate
    if metric == "mean_top_probability":
        return period.mean_top_probability
    if metric == "mean_cumulative_probability":
        return period.mean_cumulative_probability
    if metric.startswith("hit_at_"):
        k = int(metric.removeprefix("hit_at_"))
        return dict(period.hit_rates).get(k, 0.0)
    raise ValueError(f"unsupported monitoring metric: {metric}")

def _normalize_metrics(metrics: Sequence[str] | None, report) -> tuple[str, ...]:
    values = tuple(metrics) if metrics is not None else DEFAULT_METRICS
    if not values:
        raise ValueError("at least one monitoring metric is required.")
    normalized = tuple(dict.fromkeys(values))
    available = set(DEFAULT_METRICS)
    for period in report.periods:
        available.update(f"hit_at_{k}" for k, _ in period.hit_rates)
    unknown = sorted(set(normalized) - available)
    if unknown:
        raise ValueError("unsupported monitoring metrics: " + ", ".join(unknown))
    return normalized
def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()

def _metric_value(period, metric: str) -> float:
    if metric == "mean_actual_rank":
        return period.mean_actual_rank if period.mean_actual_rank is not None else 0.0
    if metric == "mean_reciprocal_rank":
        return period.mean_reciprocal_rank
    if metric == "miss_rate":
        return period.miss_rate
    if metric == "mean_top_probability":
        return period.mean_top_probability
    if metric == "mean_cumulative_probability":
        return period.mean_cumulative_probability
    if metric.startswith("hit_at_"):
        k = int(metric.removeprefix("hit_at_"))
        return dict(period.hit_rates).get(k, 0.0)
    raise ValueError(f"unsupported monitoring metric: {metric}")

def _normalize_metrics(metrics: Sequence[str] | None, report) -> tuple[str, ...]:
    values = tuple(metrics) if metrics is not None else DEFAULT_METRICS
    if not values:
        raise ValueError("at least one monitoring metric is required.")
    normalized = tuple(dict.fromkeys(values))
    available = set(DEFAULT_METRICS)
    for period in report.periods:
        available.update(f"hit_at_{k}" for k, _ in period.hit_rates)
    unknown = sorted(set(normalized) - available)
    if unknown:
        raise ValueError("unsupported monitoring metrics: " + ", ".join(unknown))
    return normalized
def build_performance_monitoring_report(
    source: PerformanceOverTimeReport,
    *,
    metrics: Sequence[str] | None = None,
) -> PerformanceMonitoringReport:
    if not isinstance(source, PerformanceOverTimeReport):
        raise TypeError("source must be a PerformanceOverTimeReport.")
    validation = validate_performance_over_time_report(source)
    if not validation.is_valid:
        raise ValueError(
            "invalid Phase 46 source report: " + ", ".join(validation.issues)
        )
    monitored = _normalize_metrics(metrics, source)
    snapshots = tuple(
        PerformanceMetricSnapshot(
            period.period_start,
            period.period_end,
            metric,
            _metric_value(period, metric),
            period.observation_count,
            period.actual_available_observations,
        )
        for period in source.periods
        for metric in monitored
    )
    latest = source.periods[-1]
    latest_values = tuple(
        (metric, _metric_value(latest, metric)) for metric in monitored
    )
    baseline = source.periods[0]
    baseline_values = tuple(
        (metric, _metric_value(baseline, metric)) for metric in monitored
    )
    payload = {
        "version": PERFORMANCE_MONITORING_VERSION,
        "source_type": source.source_type,
        "source_report_identity": source.report_identity,
        "source_period_days": source.period_days,
        "monitored_metrics": monitored,
        "snapshots": [
            (
                item.period_start,
                item.period_end,
                item.metric,
                item.value,
                item.observation_count,
                item.actual_available_observations,
            )
            for item in snapshots
        ],
    }
    return PerformanceMonitoringReport(
        PERFORMANCE_MONITORING_VERSION,
        source.source_type,
        source.report_identity,
        source.period_days,
        monitored,
        snapshots,
        len(source.periods),
        source.observation_count,
        source.actual_available_observations,
        latest.period_start,
        latest.period_end,
        latest_values,
        baseline_values,
        _identity("performance-monitoring-report-", payload),
    )

def performance_monitoring_summary(
    report: PerformanceMonitoringReport,
) -> dict[str, object]:
    validation = validate_performance_monitoring_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "source_report_identity": report.source_report_identity,
        "source_period_days": report.source_period_days,
        "monitored_metrics": report.monitored_metrics,
        "periods": report.period_count,
        "observations": report.observation_count,
        "actual_available_observations": report.actual_available_observations,
        "latest_period": (report.latest_period_start, report.latest_period_end),
        "latest_values": report.latest_values,
        "baseline_values": report.baseline_values,
        "report_identity": report.report_identity,
    }

def monitoring_metric_names(
    report: PerformanceMonitoringReport,
) -> tuple[str, ...]:
    return report.monitored_metrics
def monitoring_latest_value(
    report: PerformanceMonitoringReport,
    metric: str,
) -> float:
    values = dict(report.latest_values)
    if metric not in values:
        raise KeyError(metric)
    return values[metric]

def monitoring_baseline_value(
    report: PerformanceMonitoringReport,
    metric: str,
) -> float:
    values = dict(report.baseline_values)
    if metric not in values:
        raise KeyError(metric)
    return values[metric]

def validate_performance_monitoring_report(
    report: PerformanceMonitoringReport,
) -> PerformanceMonitoringValidationResult:
    if not isinstance(report, PerformanceMonitoringReport):
        return PerformanceMonitoringValidationResult(
            INVALID, ("INVALID_REPORT_TYPE",)
        )
    issues: list[str] = []
    if report.version != PERFORMANCE_MONITORING_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.source_report_identity.strip():
        issues.append("MISSING_SOURCE_REPORT_IDENTITY")
    if report.source_period_days < 1:
        issues.append("INVALID_SOURCE_PERIOD_DAYS")
    if not report.monitored_metrics:
        issues.append("NO_MONITORED_METRICS")
    if len(set(report.monitored_metrics)) != len(report.monitored_metrics):
        issues.append("DUPLICATE_MONITORED_METRICS")
    if report.period_count < 1:
        issues.append("INVALID_PERIOD_COUNT")
    expected = report.period_count * len(report.monitored_metrics)
    if len(report.snapshots) != expected:
        issues.append("SNAPSHOT_COUNT_MISMATCH")
    if report.observation_count < 1:
        issues.append("INVALID_OBSERVATION_COUNT")
    if not 0 <= report.actual_available_observations <= report.observation_count:
        issues.append("INVALID_ACTUAL_COUNT")
    seen: set[tuple[date, str]] = set()
    for item in report.snapshots:
        key = (item.period_start, item.metric)
        if key in seen:
            issues.append("DUPLICATE_SNAPSHOT")
        seen.add(key)
        if item.period_end < item.period_start:
            issues.append("INVALID_PERIOD_RANGE")
        if item.period_end != item.period_start + timedelta(
            days=report.source_period_days - 1
        ):
            issues.append("INVALID_PERIOD_LENGTH")
        if item.metric not in report.monitored_metrics:
            issues.append("UNDECLARED_METRIC")
        if item.observation_count < 1:
            issues.append("INVALID_SNAPSHOT_OBSERVATION_COUNT")
        if not 0 <= item.actual_available_observations <= item.observation_count:
            issues.append("INVALID_SNAPSHOT_ACTUAL_COUNT")
        if not math.isfinite(item.value):
            issues.append("NONFINITE_SNAPSHOT_VALUE")
        if item.metric != "mean_actual_rank" and not 0 <= item.value <= 1 + 1e-9:
            issues.append("INVALID_BOUNDED_METRIC_VALUE")
        if item.metric == "mean_actual_rank" and item.value < 0:
            issues.append("INVALID_RANK_VALUE")
    if len(report.latest_values) != len(report.monitored_metrics):
        issues.append("LATEST_VALUE_COUNT_MISMATCH")
    if len(report.baseline_values) != len(report.monitored_metrics):
        issues.append("BASELINE_VALUE_COUNT_MISMATCH")
    snapshot_starts = [item.period_start for item in report.snapshots]
    if snapshot_starts != sorted(snapshot_starts):
        issues.append("NON_CHRONOLOGICAL_SNAPSHOTS")
    snapshot_metrics = {item.metric for item in report.snapshots}
    if snapshot_metrics != set(report.monitored_metrics):
        issues.append("SNAPSHOT_METRIC_SET_MISMATCH")
    latest_by_metric = {
        item.metric: item.value
        for item in report.snapshots
        if item.period_start == report.latest_period_start
    }
    baseline_by_metric = {
        item.metric: item.value
        for item in report.snapshots
        if item.period_start == min(snapshot_starts)
    } if snapshot_starts else {}
    for metric, value in report.latest_values:
        if metric in latest_by_metric and not math.isclose(
            value, latest_by_metric[metric], rel_tol=0, abs_tol=1e-12
        ):
            issues.append("LATEST_VALUE_MISMATCH")
    for metric, value in report.baseline_values:
        if metric in baseline_by_metric and not math.isclose(
            value, baseline_by_metric[metric], rel_tol=0, abs_tol=1e-12
        ):
            issues.append("BASELINE_VALUE_MISMATCH")
    if report.latest_period_start > report.latest_period_end:
        issues.append("INVALID_LATEST_PERIOD")
    if not report.report_identity.startswith("performance-monitoring-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return PerformanceMonitoringValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )

__all__ = [
    "PERFORMANCE_MONITORING_VERSION",
    "VALID",
    "INVALID",
    "DEFAULT_METRICS",
    "PerformanceMetricSnapshot",
    "PerformanceMonitoringReport",
    "PerformanceMonitoringValidationResult",
    "build_performance_monitoring_report",
    "performance_monitoring_summary",
    "monitoring_metric_names",
    "monitoring_latest_value",
    "monitoring_baseline_value",
    "validate_performance_monitoring_report",
]
