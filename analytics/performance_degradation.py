from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Sequence

from analytics.performance_monitoring import (
    PerformanceMonitoringReport,
    validate_performance_monitoring_report,
)

PERFORMANCE_DEGRADATION_VERSION = "48.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEGRADED = "DEGRADED"
NOT_DEGRADED = "NOT_DEGRADED"
HIGHER_IS_WORSE = frozenset({"mean_actual_rank", "miss_rate"})

@dataclass(frozen=True)
class DegradationRule:
    metric: str
    absolute_threshold: float
    relative_threshold: float | None = None
    consecutive_periods: int = 1

@dataclass(frozen=True)
class PerformanceDegradationObservation:
    metric: str
    baseline_value: float
    latest_value: float
    absolute_change: float
    relative_change: float | None
    threshold: float
    direction: str
    degraded: bool
    evidence_periods: int

@dataclass(frozen=True)
class PerformanceDegradationReport:
    version: str
    source_type: str
    source_report_identity: str
    monitoring_report_identity: str
    rules: tuple[DegradationRule, ...]
    observations: tuple[PerformanceDegradationObservation, ...]
    degraded_metrics: tuple[str, ...]
    degraded: bool
    report_identity: str

@dataclass(frozen=True)
class PerformanceDegradationValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

DEFAULT_RULES = (
    DegradationRule("mean_actual_rank", 1.0, None, 1),
    DegradationRule("mean_reciprocal_rank", 0.05, None, 1),
    DegradationRule("miss_rate", 0.05, None, 1),
    DegradationRule("mean_top_probability", 0.05, None, 1),
    DegradationRule("mean_cumulative_probability", 0.05, None, 1),
)

def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()

def _relative_change(baseline: float, latest: float) -> float | None:
    if baseline == 0:
        return None
    return (latest - baseline) / abs(baseline)

def _metric_values(report: PerformanceMonitoringReport, metric: str) -> list[float]:
    return [item.value for item in report.snapshots if item.metric == metric]

def _normalize_rules(
    rules: Sequence[DegradationRule] | None,
    report: PerformanceMonitoringReport,
) -> tuple[DegradationRule, ...]:
    values = tuple(rules) if rules is not None else DEFAULT_RULES
    if not values:
        raise ValueError("at least one degradation rule is required.")
    if len({rule.metric for rule in values}) != len(values):
        raise ValueError("degradation rule metrics must be unique.")
    available = set(report.monitored_metrics)
    for rule in values:
        if rule.metric not in available:
            raise ValueError("rule metric is not monitored: " + rule.metric)
        if not math.isfinite(rule.absolute_threshold) or rule.absolute_threshold <= 0:
            raise ValueError("absolute_threshold must be finite and positive.")
        if rule.relative_threshold is not None and (
            not math.isfinite(rule.relative_threshold) or rule.relative_threshold <= 0
        ):
            raise ValueError("relative_threshold must be finite and positive.")
        if isinstance(rule.consecutive_periods, bool) or rule.consecutive_periods < 1:
            raise ValueError("consecutive_periods must be >= 1.")
    return values

def _adverse(value_change: float, metric: str) -> bool:
    if metric in HIGHER_IS_WORSE:
        return value_change > 0
    return value_change < 0

def _threshold_breached(
    absolute_change: float,
    relative_change: float | None,
    rule: DegradationRule,
) -> bool:
    absolute_breach = abs(absolute_change) >= rule.absolute_threshold
    relative_breach = (
        rule.relative_threshold is not None
        and relative_change is not None
        and abs(relative_change) >= rule.relative_threshold
    )
    return absolute_breach or relative_breach

def build_performance_degradation_report(
    source: PerformanceMonitoringReport,
    *,
    rules: Sequence[DegradationRule] | None = None,
) -> PerformanceDegradationReport:
    if not isinstance(source, PerformanceMonitoringReport):
        raise TypeError("source must be a PerformanceMonitoringReport.")
    validation = validate_performance_monitoring_report(source)
    if not validation.is_valid:
        raise ValueError("invalid Phase 47 source report: " + ", ".join(validation.issues))
    normalized_rules = _normalize_rules(rules, source)
    if source.period_count < 2:
        raise ValueError("at least two monitoring periods are required for degradation detection.")
    observations: list[PerformanceDegradationObservation] = []
    for rule in normalized_rules:
        values = _metric_values(source, rule.metric)
        baseline = values[0]
        latest = values[-1]
        change = latest - baseline
        relative = _relative_change(baseline, latest)
        evidence = 0
        for index in range(len(values) - 1, 0, -1):
            step = values[index] - values[index - 1]
            if _adverse(step, rule.metric):
                evidence += 1
            else:
                break
        adverse = _adverse(change, rule.metric)
        threshold_breached = _threshold_breached(change, relative, rule)
        degraded = adverse and threshold_breached and evidence >= rule.consecutive_periods
        observations.append(PerformanceDegradationObservation(
            rule.metric, baseline, latest, change, relative,
            rule.absolute_threshold, "WORSE_HIGHER" if rule.metric in HIGHER_IS_WORSE else "WORSE_LOWER",
            degraded, evidence,
        ))
    degraded_metrics = tuple(item.metric for item in observations if item.degraded)
    payload = {
        "version": PERFORMANCE_DEGRADATION_VERSION,
        "source_type": source.source_type,
        "source_report_identity": source.source_report_identity,
        "monitoring_report_identity": source.report_identity,
        "rules": [
            (r.metric, r.absolute_threshold, r.relative_threshold, r.consecutive_periods)
            for r in normalized_rules
        ],
        "observations": [
            (o.metric, o.baseline_value, o.latest_value, o.absolute_change, o.relative_change, o.degraded, o.evidence_periods)
            for o in observations
        ],
    }
    return PerformanceDegradationReport(
        PERFORMANCE_DEGRADATION_VERSION,
        source.source_type,
        source.source_report_identity,
        source.report_identity,
        normalized_rules,
        tuple(observations),
        degraded_metrics,
        bool(degraded_metrics),
        _identity("performance-degradation-report-", payload),
    )

def performance_degradation_summary(report: PerformanceDegradationReport) -> dict[str, object]:
    validation = validate_performance_degradation_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "source_report_identity": report.source_report_identity,
        "monitoring_report_identity": report.monitoring_report_identity,
        "degraded": report.degraded,
        "degraded_metrics": report.degraded_metrics,
        "observations": tuple((item.metric, item.degraded, item.absolute_change) for item in report.observations),
        "report_identity": report.report_identity,
    }

def validate_performance_degradation_report(report: PerformanceDegradationReport) -> PerformanceDegradationValidationResult:
    if not isinstance(report, PerformanceDegradationReport):
        return PerformanceDegradationValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != PERFORMANCE_DEGRADATION_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.source_report_identity.strip():
        issues.append("MISSING_SOURCE_REPORT_IDENTITY")
    if not report.monitoring_report_identity.strip():
        issues.append("MISSING_MONITORING_REPORT_IDENTITY")
    if not report.rules:
        issues.append("NO_RULES")
    if len({rule.metric for rule in report.rules}) != len(report.rules):
        issues.append("DUPLICATE_RULE_METRICS")
    if len(report.observations) != len(report.rules):
        issues.append("OBSERVATION_RULE_COUNT_MISMATCH")
    if report.degraded_metrics != tuple(item.metric for item in report.observations if item.degraded):
        issues.append("DEGRADED_METRICS_MISMATCH")
    if report.degraded != bool(report.degraded_metrics):
        issues.append("DEGRADED_FLAG_MISMATCH")
    for rule in report.rules:
        if rule.absolute_threshold <= 0 or not math.isfinite(rule.absolute_threshold):
            issues.append("INVALID_ABSOLUTE_THRESHOLD")
        if rule.relative_threshold is not None and (rule.relative_threshold <= 0 or not math.isfinite(rule.relative_threshold)):
            issues.append("INVALID_RELATIVE_THRESHOLD")
        if rule.consecutive_periods < 1:
            issues.append("INVALID_CONSECUTIVE_PERIODS")
    for item in report.observations:
        if item.metric not in {rule.metric for rule in report.rules}:
            issues.append("UNDECLARED_OBSERVATION_METRIC")
        if not all(math.isfinite(value) for value in (item.baseline_value, item.latest_value, item.absolute_change)):
            issues.append("NONFINITE_OBSERVATION")
        if item.relative_change is not None and not math.isfinite(item.relative_change):
            issues.append("NONFINITE_RELATIVE_CHANGE")
        if item.evidence_periods < 0:
            issues.append("INVALID_EVIDENCE_PERIODS")
        expected_direction = "WORSE_HIGHER" if item.metric in HIGHER_IS_WORSE else "WORSE_LOWER"
        if item.direction != expected_direction:
            issues.append("INVALID_DIRECTION")
    if not report.report_identity.startswith("performance-degradation-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return PerformanceDegradationValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))

__all__ = [
    "PERFORMANCE_DEGRADATION_VERSION", "VALID", "INVALID", "DEGRADED", "NOT_DEGRADED",
    "HIGHER_IS_WORSE", "DEFAULT_RULES", "DegradationRule", "PerformanceDegradationObservation",
    "PerformanceDegradationReport", "PerformanceDegradationValidationResult",
    "build_performance_degradation_report", "performance_degradation_summary",
    "validate_performance_degradation_report",
]
