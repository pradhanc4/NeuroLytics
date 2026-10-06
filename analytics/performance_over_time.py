from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from analytics.actual_vs_ranked import (
    ActualVsRankedObservation,
    ActualVsRankedReport,
    validate_actual_vs_ranked_report,
)

PERFORMANCE_OVER_TIME_VERSION = "46.0.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class PerformancePeriod:
    period_start: date
    period_end: date
    observation_count: int
    actual_available_observations: int
    missed_observations: int
    mean_actual_rank: float | None
    hit_rates: tuple[tuple[int, float], ...]
    mean_reciprocal_rank: float
    mean_top_probability: float
    mean_cumulative_probability: float
    miss_rate: float


@dataclass(frozen=True)
class PerformanceTrend:
    metric: str
    slope_per_day: float
    direction: str
    first_value: float
    last_value: float
    change: float


@dataclass(frozen=True)
class PerformanceOverTimeReport:
    version: str
    source_type: str
    source_report_identity: str
    period_days: int
    periods: tuple[PerformancePeriod, ...]
    trends: tuple[PerformanceTrend, ...]
    observation_count: int
    actual_available_observations: int
    missed_observations: int
    report_identity: str


@dataclass(frozen=True)
class PerformanceOverTimeValidationResult:
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


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _slope(points: Sequence[tuple[date, float]]) -> float:
    if len(points) < 2:
        return 0.0
    origin = points[0][0]
    xs = [(item[0] - origin).days for item in points]
    ys = [item[1] for item in points]
    x_mean = _mean(xs)
    y_mean = _mean(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator


def _direction(slope: float, tolerance: float = 1e-12) -> str:
    if slope > tolerance:
        return "IMPROVING"
    if slope < -tolerance:
        return "DECLINING"
    return "STABLE"


def _period_start(target_date: date, anchor: date, period_days: int) -> date:
    elapsed = (target_date - anchor).days
    return anchor + timedelta(days=(elapsed // period_days) * period_days)


def _period(
    observations: Sequence[ActualVsRankedObservation],
    start: date,
    end: date,
    hit_ks: tuple[int, ...],
) -> PerformancePeriod:
    actual = [item for item in observations if item.actual_rank is not None]
    ranks = [item.actual_rank for item in actual if item.actual_rank is not None]
    hits = {
        k: _mean([1.0 if dict(item.hit_at_k).get(k, False) else 0.0 for item in actual])
        if actual else 0.0
        for k in hit_ks
    }
    return PerformancePeriod(
        start,
        end,
        len(observations),
        len(actual),
        len(observations) - len(actual),
        (sum(ranks) / len(ranks)) if ranks else None,
        tuple(sorted(hits.items())),
        _mean([item.reciprocal_rank for item in actual]),
        _mean([item.top_probability for item in observations]),
        _mean([item.cumulative_probability_at_max_k for item in observations]),
        ((len(observations) - len(actual)) / len(observations))
        if observations else 0.0,
    )
def _trend(
    periods: Sequence[PerformancePeriod],
    metric: str,
    values: Sequence[float],
) -> PerformanceTrend:
    points = [(period.period_start, value) for period, value in zip(periods, values)]
    slope = _slope(points)
    return PerformanceTrend(
        metric,
        slope,
        _direction(slope),
        values[0],
        values[-1],
        values[-1] - values[0],
    )


def build_performance_over_time_report(
    source: ActualVsRankedReport,
    *,
    period_days: int = 7,
    hit_ks: Sequence[int] | None = None,
) -> PerformanceOverTimeReport:
    if not isinstance(source, ActualVsRankedReport):
        raise TypeError("source must be an ActualVsRankedReport.")
    validation = validate_actual_vs_ranked_report(source)
    if not validation.is_valid:
        raise ValueError(
            "invalid Phase 45 source report: "
            + ", ".join(validation.issues)
        )
    if period_days < 1:
        raise ValueError("period_days must be >= 1.")
    normalized_ks = tuple(sorted(set(hit_ks if hit_ks is not None else (
        k for k, _ in source.hit_rates
    ))))
    if not normalized_ks or any(k < 1 for k in normalized_ks):
        raise ValueError("hit_ks must contain positive integers.")

    ordered = tuple(sorted(source.observations, key=lambda item: (
        item.target_date,
        item.group_id,
    )))
    anchor = ordered[0].target_date
    grouped: dict[date, list[ActualVsRankedObservation]] = {}
    for observation in ordered:
        start = _period_start(observation.target_date, anchor, period_days)
        grouped.setdefault(start, []).append(observation)

    periods = tuple(
        _period(
            grouped[start],
            start,
            start + timedelta(days=period_days - 1),
            normalized_ks,
        )
        for start in sorted(grouped)
    )
    trends: list[PerformanceTrend] = []
    if periods:
        metric_values = {
            "mean_actual_rank": [
                p.mean_actual_rank if p.mean_actual_rank is not None else 0.0
                for p in periods
            ],
            "mean_reciprocal_rank": [p.mean_reciprocal_rank for p in periods],
            "miss_rate": [p.miss_rate for p in periods],
            "mean_top_probability": [p.mean_top_probability for p in periods],
            "mean_cumulative_probability": [
                p.mean_cumulative_probability for p in periods
            ],
        }
        for k in normalized_ks:
            metric_values[f"hit_at_{k}"] = [
                dict(p.hit_rates).get(k, 0.0) for p in periods
            ]
        for metric, values in metric_values.items():
            trends.append(_trend(periods, metric, values))

    payload = {
        "version": PERFORMANCE_OVER_TIME_VERSION,
        "source_type": source.source_type,
        "source_report_identity": source.report_identity,
        "period_days": period_days,
        "hit_ks": normalized_ks,
        "periods": [
            (
                p.period_start,
                p.period_end,
                p.observation_count,
                p.actual_available_observations,
                p.missed_observations,
                p.mean_actual_rank,
                p.hit_rates,
                p.mean_reciprocal_rank,
                p.mean_top_probability,
                p.mean_cumulative_probability,
            )
            for p in periods
        ],
        "trends": [
            (t.metric, t.slope_per_day, t.direction, t.first_value, t.last_value)
            for t in trends
        ],
    }
    return PerformanceOverTimeReport(
        PERFORMANCE_OVER_TIME_VERSION,
        source.source_type,
        source.report_identity,
        period_days,
        periods,
        tuple(trends),
        len(ordered),
        sum(item.actual_rank is not None for item in ordered),
        sum(item.actual_rank is None for item in ordered),
        _identity("performance-over-time-report-", payload),
    )


def performance_over_time_summary(
    report: PerformanceOverTimeReport,
) -> dict[str, object]:
    validation = validate_performance_over_time_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "source_report_identity": report.source_report_identity,
        "period_days": report.period_days,
        "periods": len(report.periods),
        "observations": report.observation_count,
        "actual_available_observations": report.actual_available_observations,
        "missed_observations": report.missed_observations,
        "trends": tuple(
            (item.metric, item.direction, item.slope_per_day)
            for item in report.trends
        ),
        "report_identity": report.report_identity,
    }


def validate_performance_over_time_report(
    report: PerformanceOverTimeReport,
) -> PerformanceOverTimeValidationResult:
    if not isinstance(report, PerformanceOverTimeReport):
        return PerformanceOverTimeValidationResult(
            INVALID, ("INVALID_REPORT_TYPE",)
        )
    issues: list[str] = []
    if report.version != PERFORMANCE_OVER_TIME_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.source_report_identity.strip():
        issues.append("MISSING_SOURCE_REPORT_IDENTITY")
    if report.period_days < 1:
        issues.append("INVALID_PERIOD_DAYS")
    if not report.periods:
        issues.append("NO_PERIODS")
    starts = [item.period_start for item in report.periods]
    if starts != sorted(starts):
        issues.append("NON_CHRONOLOGICAL_PERIODS")
    if len(starts) != len(set(starts)):
        issues.append("DUPLICATE_PERIOD_STARTS")
    total = 0
    actual_total = 0
    missed_total = 0
    for item in report.periods:
        if item.period_end < item.period_start:
            issues.append("INVALID_PERIOD_RANGE")
        if item.period_end != item.period_start + timedelta(days=report.period_days - 1):
            issues.append("INVALID_PERIOD_LENGTH")
        if item.observation_count < 1:
            issues.append("EMPTY_PERIOD")
        if item.actual_available_observations < 0 or item.missed_observations < 0:
            issues.append("INVALID_PERIOD_COUNTS")
        if item.actual_available_observations + item.missed_observations != item.observation_count:
            issues.append("PERIOD_COUNT_MISMATCH")
        if not 0 <= item.miss_rate <= 1:
            issues.append("INVALID_MISS_RATE")
        if item.mean_actual_rank is not None and item.mean_actual_rank < 1:
            issues.append("INVALID_MEAN_RANK")
        if not 0 <= item.mean_reciprocal_rank <= 1:
            issues.append("INVALID_PERIOD_MRR")
        if not 0 <= item.mean_top_probability <= 1:
            issues.append("INVALID_PERIOD_TOP_PROBABILITY")
        if not 0 <= item.mean_cumulative_probability <= 1 + 1e-9:
            issues.append("INVALID_PERIOD_CUMULATIVE_PROBABILITY")
        for k, rate in item.hit_rates:
            if k < 1 or not 0 <= rate <= 1:
                issues.append("INVALID_HIT_RATE")
        total += item.observation_count
        actual_total += item.actual_available_observations
        missed_total += item.missed_observations
    if total != report.observation_count:
        issues.append("OBSERVATION_COUNT_MISMATCH")
    if actual_total != report.actual_available_observations:
        issues.append("ACTUAL_COUNT_MISMATCH")
    if missed_total != report.missed_observations:
        issues.append("MISSED_COUNT_MISMATCH")
    if report.actual_available_observations + report.missed_observations != report.observation_count:
        issues.append("GLOBAL_COUNT_MISMATCH")
    if not report.trends:
        issues.append("NO_TRENDS")
    for trend in report.trends:
        if not trend.metric.strip():
            issues.append("MISSING_TREND_METRIC")
        if trend.direction not in {"IMPROVING", "DECLINING", "STABLE"}:
            issues.append("INVALID_TREND_DIRECTION")
        if not all(math.isfinite(value) for value in (
            trend.slope_per_day, trend.first_value, trend.last_value, trend.change
        )):
            issues.append("NONFINITE_TREND")
        if not math.isclose(
            trend.change, trend.last_value - trend.first_value, rel_tol=0, abs_tol=1e-12
        ):
            issues.append("TREND_CHANGE_MISMATCH")
    if not report.report_identity.startswith("performance-over-time-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return PerformanceOverTimeValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "PERFORMANCE_OVER_TIME_VERSION",
    "VALID",
    "INVALID",
    "PerformancePeriod",
    "PerformanceTrend",
    "PerformanceOverTimeReport",
    "PerformanceOverTimeValidationResult",
    "build_performance_over_time_report",
    "performance_over_time_summary",
    "validate_performance_over_time_report",
]
