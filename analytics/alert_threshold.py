from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

ALERT_THRESHOLD_VERSION = "56.0.0"
VALID = "VALID"
INVALID = "INVALID"
ACTIVE = "ACTIVE"
CLEAR = "CLEAR"
SEVERITY_INFO = "INFO"
SEVERITY_WARNING = "WARNING"
SEVERITY_CRITICAL = "CRITICAL"
VALID_SEVERITIES = (SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_CRITICAL)


@dataclass(frozen=True)
class AlertRule:
    alert_id: str
    metric: str
    threshold: float
    severity: str = SEVERITY_WARNING
    operator: str = "gte"
    enabled: bool = True


@dataclass(frozen=True)
class AlertObservation:
    alert_id: str
    metric: str
    observed_value: float
    threshold: float
    operator: str
    severity: str
    active: bool
    evaluated_at: date | None
    source_identity: str


@dataclass(frozen=True)
class AlertThresholdReport:
    version: str
    source_type: str
    source_identity: str
    rules: tuple[AlertRule, ...]
    observations: tuple[AlertObservation, ...]
    active_alerts: tuple[str, ...]
    critical_alerts: tuple[str, ...]
    warning_alerts: tuple[str, ...]
    alert_count: int
    report_identity: str


@dataclass(frozen=True)
class AlertThresholdValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()


def _evaluate(value: float, threshold: float, operator: str) -> bool:
    if operator == "gte":
        return value >= threshold
    if operator == "gt":
        return value > threshold
    if operator == "lte":
        return value <= threshold
    if operator == "lt":
        return value < threshold
    if operator == "eq":
        return math.isclose(value, threshold, rel_tol=0.0, abs_tol=1e-12)
    raise ValueError("unsupported alert operator: " + operator)


def _normalize_rules(rules: Sequence[AlertRule]) -> tuple[AlertRule, ...]:
    values = tuple(rules)
    if not values:
        raise ValueError("at least one alert rule is required.")
    if len({rule.alert_id for rule in values}) != len(values):
        raise ValueError("alert rule IDs must be unique.")
    for rule in values:
        if not rule.alert_id.strip():
            raise ValueError("alert_id must not be empty.")
        if not rule.metric.strip():
            raise ValueError("metric must not be empty.")
        if not math.isfinite(rule.threshold):
            raise ValueError("threshold must be finite.")
        if rule.severity not in VALID_SEVERITIES:
            raise ValueError("invalid alert severity: " + rule.severity)
        if rule.operator not in {"gte", "gt", "lte", "lt", "eq"}:
            raise ValueError("invalid alert operator: " + rule.operator)
        if not isinstance(rule.enabled, bool):
            raise ValueError("enabled must be boolean.")
    return values


def _normalize_values(values: Sequence[tuple[str, float]]) -> tuple[tuple[str, float], ...]:
    result = tuple(values)
    if not result:
        raise ValueError("at least one metric value is required.")
    seen: set[str] = set()
    for metric, value in result:
        if not metric.strip():
            raise ValueError("metric names must not be empty.")
        if metric in seen:
            raise ValueError("metric values must be unique.")
        seen.add(metric)
        if not math.isfinite(value):
            raise ValueError("metric values must be finite.")
    return result


def build_alert_threshold_report(
    source_type: str,
    source_identity: str,
    values: Sequence[tuple[str, float]],
    rules: Sequence[AlertRule],
    *,
    evaluated_at: date | None = None,
) -> AlertThresholdReport:
    if not isinstance(source_type, str) or not source_type.strip():
        raise ValueError("source_type must not be empty.")
    if not isinstance(source_identity, str) or not source_identity.strip():
        raise ValueError("source_identity must not be empty.")
    normalized_rules = _normalize_rules(rules)
    normalized_values = dict(_normalize_values(values))
    observations: list[AlertObservation] = []
    for rule in normalized_rules:
        if not rule.enabled:
            continue
        if rule.metric not in normalized_values:
            raise ValueError("no observed value supplied for rule metric: " + rule.metric)
        value = normalized_values[rule.metric]
        observations.append(
            AlertObservation(
                rule.alert_id,
                rule.metric,
                value,
                rule.threshold,
                rule.operator,
                rule.severity,
                _evaluate(value, rule.threshold, rule.operator),
                evaluated_at,
                source_identity,
            )
        )
    active = tuple(item.alert_id for item in observations if item.active)
    critical = tuple(item.alert_id for item in observations if item.active and item.severity == SEVERITY_CRITICAL)
    warning = tuple(item.alert_id for item in observations if item.active and item.severity == SEVERITY_WARNING)
    payload = {
        "version": ALERT_THRESHOLD_VERSION,
        "source_type": source_type,
        "source_identity": source_identity,
        "rules": [(r.alert_id, r.metric, r.threshold, r.severity, r.operator, r.enabled) for r in normalized_rules],
        "observations": [(o.alert_id, o.metric, o.observed_value, o.threshold, o.operator, o.severity, o.active, o.evaluated_at) for o in observations],
    }
    return AlertThresholdReport(
        ALERT_THRESHOLD_VERSION,
        source_type,
        source_identity,
        normalized_rules,
        tuple(observations),
        active,
        critical,
        warning,
        len(active),
        _identity("alert-threshold-report-", payload),
    )


def alert_threshold_summary(report: AlertThresholdReport) -> dict[str, object]:
    validation = validate_alert_threshold_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "source_identity": report.source_identity,
        "rules": len(report.rules),
        "evaluations": len(report.observations),
        "active_alerts": report.active_alerts,
        "critical_alerts": report.critical_alerts,
        "warning_alerts": report.warning_alerts,
        "alert_count": report.alert_count,
        "report_identity": report.report_identity,
    }


def alert_threshold_observations(
    report: AlertThresholdReport,
    *,
    active_only: bool = False,
) -> tuple[AlertObservation, ...]:
    if active_only:
        return tuple(item for item in report.observations if item.active)
    return report.observations


def validate_alert_threshold_report(
    report: AlertThresholdReport,
) -> AlertThresholdValidationResult:
    if not isinstance(report, AlertThresholdReport):
        return AlertThresholdValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != ALERT_THRESHOLD_VERSION:
        issues.append("INVALID_VERSION")
    if not report.source_type.strip():
        issues.append("MISSING_SOURCE_TYPE")
    if not report.source_identity.strip():
        issues.append("MISSING_SOURCE_IDENTITY")
    try:
        _normalize_rules(report.rules)
    except (TypeError, ValueError):
        issues.append("INVALID_RULES")
    if len(report.observations) > len(report.rules):
        issues.append("OBSERVATION_RULE_COUNT_MISMATCH")
    declared = {rule.alert_id: rule for rule in report.rules}
    seen: set[str] = set()
    for item in report.observations:
        if item.alert_id in seen:
            issues.append("DUPLICATE_ALERT_ID")
        seen.add(item.alert_id)
        if item.alert_id not in declared:
            issues.append("UNDECLARED_ALERT")
        if not math.isfinite(item.observed_value) or not math.isfinite(item.threshold):
            issues.append("NONFINITE_OBSERVATION")
        if item.operator not in {"gte", "gt", "lte", "lt", "eq"}:
            issues.append("INVALID_OPERATOR")
        if item.severity not in VALID_SEVERITIES:
            issues.append("INVALID_SEVERITY")
        if item.source_identity != report.source_identity:
            issues.append("SOURCE_IDENTITY_MISMATCH")
        expected = _evaluate(item.observed_value, item.threshold, item.operator)
        if item.active != expected:
            issues.append("ACTIVE_FLAG_MISMATCH")
        rule = declared.get(item.alert_id)
        if rule is not None:
            if (item.metric, item.threshold, item.operator, item.severity) != (
                rule.metric, rule.threshold, rule.operator, rule.severity
            ):
                issues.append("RULE_OBSERVATION_MISMATCH")
            if rule.enabled and item.alert_id not in seen:
                pass
    expected_active = tuple(item.alert_id for item in report.observations if item.active)
    expected_critical = tuple(item.alert_id for item in report.observations if item.active and item.severity == SEVERITY_CRITICAL)
    expected_warning = tuple(item.alert_id for item in report.observations if item.active and item.severity == SEVERITY_WARNING)
    if report.active_alerts != expected_active:
        issues.append("ACTIVE_ALERTS_MISMATCH")
    if report.critical_alerts != expected_critical:
        issues.append("CRITICAL_ALERTS_MISMATCH")
    if report.warning_alerts != expected_warning:
        issues.append("WARNING_ALERTS_MISMATCH")
    if report.alert_count != len(report.active_alerts):
        issues.append("ALERT_COUNT_MISMATCH")
    if not report.report_identity.startswith("alert-threshold-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return AlertThresholdValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "ALERT_THRESHOLD_VERSION", "VALID", "INVALID", "ACTIVE", "CLEAR",
    "SEVERITY_INFO", "SEVERITY_WARNING", "SEVERITY_CRITICAL",
    "VALID_SEVERITIES", "AlertRule", "AlertObservation",
    "AlertThresholdReport", "AlertThresholdValidationResult",
    "build_alert_threshold_report", "alert_threshold_summary",
    "alert_threshold_observations", "validate_alert_threshold_report",
]
