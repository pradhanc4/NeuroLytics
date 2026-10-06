from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Sequence

from analytics.model_health import (
    CRITICAL,
    DEGRADED,
    HEALTHY,
    ModelHealthReport,
    validate_model_health_report,
)

MODEL_COMPARISON_VERSION = "58.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEFAULT_METRICS = ("health_score",)
DEFAULT_EPSILON = 1e-12


@dataclass(frozen=True)
class ModelHealthSnapshot:
    period_label: str
    model_identity: str
    health_score: float
    health_status: str
    component_scores: tuple[tuple[str, float], ...]
    source_report_identity: str


@dataclass(frozen=True)
class ModelMetricComparison:
    metric: str
    model_identity: str
    baseline_value: float
    comparison_value: float
    absolute_change: float
    relative_change: float | None


@dataclass(frozen=True)
class ModelComparisonReport:
    version: str
    comparison_id: str
    baseline_period: str
    comparison_period: str
    snapshots: tuple[ModelHealthSnapshot, ...]
    metric_comparisons: tuple[ModelMetricComparison, ...]
    improved_models: tuple[str, ...]
    declined_models: tuple[str, ...]
    unchanged_models: tuple[str, ...]
    common_models: tuple[str, ...]
    baseline_only_models: tuple[str, ...]
    comparison_only_models: tuple[str, ...]
    report_identity: str


@dataclass(frozen=True)
class ModelComparisonValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()


def _snapshot(period_label: str, report: ModelHealthReport) -> ModelHealthSnapshot:
    validation = validate_model_health_report(report)
    if not validation.is_valid:
        raise ValueError("invalid model health report: " + ", ".join(validation.issues))
    return ModelHealthSnapshot(
        period_label,
        report.model_identity,
        report.score.weighted_score,
        report.score.status,
        tuple((item.name, item.score) for item in report.components),
        report.report_identity,
    )


def build_model_health_snapshot(
    period_label: str,
    report: ModelHealthReport,
) -> ModelHealthSnapshot:
    if not isinstance(period_label, str) or not period_label.strip():
        raise ValueError("period_label must not be empty.")
    if not isinstance(report, ModelHealthReport):
        raise TypeError("report must be a ModelHealthReport.")
    return _snapshot(period_label, report)


def _relative_change(baseline: float, comparison: float) -> float | None:
    if abs(baseline) <= DEFAULT_EPSILON:
        return None
    return (comparison - baseline) / abs(baseline)


def _normalize_snapshots(
    baseline_period: str,
    comparison_period: str,
    snapshots: Sequence[ModelHealthSnapshot],
) -> tuple[ModelHealthSnapshot, ...]:
    if not baseline_period.strip() or not comparison_period.strip():
        raise ValueError("period labels must not be empty.")
    if baseline_period == comparison_period:
        raise ValueError("baseline and comparison periods must differ.")
    values = tuple(snapshots)
    if not values:
        raise ValueError("at least one model snapshot is required.")
    if any(item.period_label not in {baseline_period, comparison_period} for item in values):
        raise ValueError("snapshot contains an undeclared period.")
    keys = {(item.period_label, item.model_identity) for item in values}
    if len(keys) != len(values):
        raise ValueError("duplicate model snapshot for a period.")
    models_by_period = {
        period: {item.model_identity for item in values if item.period_label == period}
        for period in (baseline_period, comparison_period)
    }
    if not models_by_period[baseline_period] or not models_by_period[comparison_period]:
        raise ValueError("both comparison periods require at least one snapshot.")
    for item in values:
        if not item.model_identity.strip():
            raise ValueError("snapshot model identity must not be empty.")
        if not math.isfinite(item.health_score) or not 0 <= item.health_score <= 1:
            raise ValueError("snapshot health score must be finite and in [0, 1].")
        if item.health_status not in {HEALTHY, DEGRADED, CRITICAL}:
            raise ValueError("invalid snapshot health status.")
        if not item.source_report_identity.strip():
            raise ValueError("snapshot source report identity must not be empty.")
        if len({name for name, _ in item.component_scores}) != len(item.component_scores):
            raise ValueError("snapshot component names must be unique.")
        for name, score in item.component_scores:
            if not name.strip() or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("invalid component score in snapshot.")
    return values


def build_model_comparison_report(
    comparison_id: str,
    baseline_period: str,
    comparison_period: str,
    snapshots: Sequence[ModelHealthSnapshot],
    *,
    metrics: Sequence[str] | None = None,
) -> ModelComparisonReport:
    if not isinstance(comparison_id, str) or not comparison_id.strip():
        raise ValueError("comparison_id must not be empty.")
    normalized = _normalize_snapshots(baseline_period, comparison_period, snapshots)
    requested_metrics = tuple(metrics) if metrics is not None else DEFAULT_METRICS
    if not requested_metrics:
        raise ValueError("at least one comparison metric is required.")
    if tuple(dict.fromkeys(requested_metrics)) != requested_metrics:
        raise ValueError("comparison metrics must be unique.")
    unsupported = sorted(set(requested_metrics) - {"health_score"})
    if unsupported:
        raise ValueError("unsupported comparison metrics: " + ", ".join(unsupported))

    baseline = {item.model_identity: item for item in normalized if item.period_label == baseline_period}
    comparison = {item.model_identity: item for item in normalized if item.period_label == comparison_period}
    common = tuple(sorted(set(baseline) & set(comparison)))
    baseline_only = tuple(sorted(set(baseline) - set(comparison)))
    comparison_only = tuple(sorted(set(comparison) - set(baseline)))

    comparisons: list[ModelMetricComparison] = []
    for model in common:
        b = baseline[model].health_score
        c = comparison[model].health_score
        comparisons.append(
            ModelMetricComparison(
                "health_score",
                model,
                b,
                c,
                c - b,
                _relative_change(b, c),
            )
        )

    improved = tuple(item.model_identity for item in comparisons if item.absolute_change > DEFAULT_EPSILON)
    declined = tuple(item.model_identity for item in comparisons if item.absolute_change < -DEFAULT_EPSILON)
    unchanged = tuple(item.model_identity for item in comparisons if abs(item.absolute_change) <= DEFAULT_EPSILON)

    payload = {
        "version": MODEL_COMPARISON_VERSION,
        "comparison_id": comparison_id,
        "baseline_period": baseline_period,
        "comparison_period": comparison_period,
        "metrics": requested_metrics,
        "snapshots": [
            (
                item.period_label,
                item.model_identity,
                item.health_score,
                item.health_status,
                item.component_scores,
                item.source_report_identity,
            )
            for item in normalized
        ],
        "comparisons": [
            (
                item.metric,
                item.model_identity,
                item.baseline_value,
                item.comparison_value,
                item.absolute_change,
                item.relative_change,
            )
            for item in comparisons
        ],
    }
    return ModelComparisonReport(
        MODEL_COMPARISON_VERSION,
        comparison_id,
        baseline_period,
        comparison_period,
        normalized,
        tuple(comparisons),
        improved,
        declined,
        unchanged,
        common,
        baseline_only,
        comparison_only,
        _identity("model-comparison-report-", payload),
    )


def model_comparison_summary(report: ModelComparisonReport) -> dict[str, object]:
    validation = validate_model_comparison_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "comparison_id": report.comparison_id,
        "baseline_period": report.baseline_period,
        "comparison_period": report.comparison_period,
        "common_models": report.common_models,
        "baseline_only_models": report.baseline_only_models,
        "comparison_only_models": report.comparison_only_models,
        "improved_models": report.improved_models,
        "declined_models": report.declined_models,
        "unchanged_models": report.unchanged_models,
        "comparisons": len(report.metric_comparisons),
        "report_identity": report.report_identity,
    }


def model_comparison_metrics(
    report: ModelComparisonReport,
    model_identity: str | None = None,
) -> tuple[ModelMetricComparison, ...]:
    if model_identity is None:
        return report.metric_comparisons
    return tuple(item for item in report.metric_comparisons if item.model_identity == model_identity)


def model_comparison_snapshots(
    report: ModelComparisonReport,
    period_label: str | None = None,
) -> tuple[ModelHealthSnapshot, ...]:
    if period_label is None:
        return report.snapshots
    return tuple(item for item in report.snapshots if item.period_label == period_label)


def validate_model_comparison_report(
    report: ModelComparisonReport,
) -> ModelComparisonValidationResult:
    if not isinstance(report, ModelComparisonReport):
        return ModelComparisonValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != MODEL_COMPARISON_VERSION:
        issues.append("INVALID_VERSION")
    if not report.comparison_id.strip():
        issues.append("MISSING_COMPARISON_ID")
    if not report.baseline_period.strip() or not report.comparison_period.strip():
        issues.append("MISSING_PERIOD")
    if report.baseline_period == report.comparison_period:
        issues.append("IDENTICAL_PERIODS")
    if not report.snapshots:
        issues.append("NO_SNAPSHOTS")
    try:
        _normalize_snapshots(report.baseline_period, report.comparison_period, report.snapshots)
    except (TypeError, ValueError):
        issues.append("INVALID_SNAPSHOTS")

    baseline = {item.model_identity: item for item in report.snapshots if item.period_label == report.baseline_period}
    comparison = {item.model_identity: item for item in report.snapshots if item.period_label == report.comparison_period}
    expected_common = tuple(sorted(set(baseline) & set(comparison)))
    expected_baseline_only = tuple(sorted(set(baseline) - set(comparison)))
    expected_comparison_only = tuple(sorted(set(comparison) - set(baseline)))
    if report.common_models != expected_common:
        issues.append("COMMON_MODELS_MISMATCH")
    if report.baseline_only_models != expected_baseline_only:
        issues.append("BASELINE_ONLY_MISMATCH")
    if report.comparison_only_models != expected_comparison_only:
        issues.append("COMPARISON_ONLY_MISMATCH")

    expected_comparisons = {
        (item.metric, item.model_identity): item
        for item in report.metric_comparisons
    }
    if len(expected_comparisons) != len(report.metric_comparisons):
        issues.append("DUPLICATE_METRIC_COMPARISON")
    for item in report.metric_comparisons:
        if item.metric != "health_score":
            issues.append("UNSUPPORTED_METRIC")
        if item.model_identity not in expected_common:
            issues.append("NONCOMMON_MODEL_COMPARISON")
        if not all(math.isfinite(value) for value in (item.baseline_value, item.comparison_value, item.absolute_change)):
            issues.append("NONFINITE_COMPARISON")
        expected_change = item.comparison_value - item.baseline_value
        if not math.isclose(item.absolute_change, expected_change, rel_tol=0.0, abs_tol=DEFAULT_EPSILON):
            issues.append("ABSOLUTE_CHANGE_MISMATCH")
        expected_relative = _relative_change(item.baseline_value, item.comparison_value)
        if item.relative_change is None:
            if expected_relative is not None:
                issues.append("RELATIVE_CHANGE_MISMATCH")
        elif expected_relative is None or not math.isclose(item.relative_change, expected_relative, rel_tol=0.0, abs_tol=DEFAULT_EPSILON):
            issues.append("RELATIVE_CHANGE_MISMATCH")

    expected_improved = tuple(item.model_identity for item in report.metric_comparisons if item.absolute_change > DEFAULT_EPSILON)
    expected_declined = tuple(item.model_identity for item in report.metric_comparisons if item.absolute_change < -DEFAULT_EPSILON)
    expected_unchanged = tuple(item.model_identity for item in report.metric_comparisons if abs(item.absolute_change) <= DEFAULT_EPSILON)
    if report.improved_models != expected_improved:
        issues.append("IMPROVED_MODELS_MISMATCH")
    if report.declined_models != expected_declined:
        issues.append("DECLINED_MODELS_MISMATCH")
    if report.unchanged_models != expected_unchanged:
        issues.append("UNCHANGED_MODELS_MISMATCH")
    if not report.report_identity.startswith("model-comparison-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return ModelComparisonValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "MODEL_COMPARISON_VERSION",
    "VALID",
    "INVALID",
    "DEFAULT_METRICS",
    "ModelHealthSnapshot",
    "ModelMetricComparison",
    "ModelComparisonReport",
    "ModelComparisonValidationResult",
    "build_model_health_snapshot",
    "build_model_comparison_report",
    "model_comparison_summary",
    "model_comparison_metrics",
    "model_comparison_snapshots",
    "validate_model_comparison_report",
]
