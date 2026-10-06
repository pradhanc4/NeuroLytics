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

PREDICTION_DISTRIBUTION_MONITORING_VERSION = "51.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEFAULT_PERIOD_DAYS = 7
DEFAULT_PROBABILITY_BINS = 10
@dataclass(frozen=True)
class PredictionDistributionPeriod:
    period_start: date
    period_end: date
    observation_count: int
    actual_available_observations: int
    missed_observations: int
    rank_distribution: tuple[tuple[int, int], ...]
    rank_bucket_distribution: tuple[tuple[str, int], ...]
    probability_bin_distribution: tuple[tuple[str, int], ...]
    top_probability_mean: float
    cumulative_probability_mean: float
    probability_entropy: float


@dataclass(frozen=True)
class PredictionDistributionMonitoringReport:
    version: str
    source_type: str
    source_report_identity: str
    period_days: int
    probability_bins: int
    periods: tuple[PredictionDistributionPeriod, ...]
    observation_count: int
    actual_available_observations: int
    missed_observations: int
    report_identity: str
@dataclass(frozen=True)
class PredictionDistributionValidationResult:
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


def _period_start(target_date: date, anchor: date, period_days: int) -> date:
    elapsed = (target_date - anchor).days
    return anchor + timedelta(days=(elapsed // period_days) * period_days)


def _rank_bucket(rank: int | None) -> str:
    if rank is None:
        return "UNAVAILABLE"
    if rank == 1:
        return "TOP_1"
    if rank <= 3:
        return "TOP_3"
    if rank <= 5:
        return "TOP_5"
    if rank <= 10:
        return "TOP_10"
    return "OUTSIDE_TOP_10"
def _probability_bin(value: float, bins: int) -> str:
    index = min(bins - 1, int(value * bins))
    lower = index / bins
    upper = (index + 1) / bins
    return f"{lower:.2f}-{upper:.2f}"


def _entropy(counts: Sequence[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts:
        if count:
            probability = count / total
            entropy -= probability * math.log(probability)
    return entropy


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _period(
    observations: Sequence[ActualVsRankedObservation],
    start: date,
    period_days: int,
    probability_bins: int,
) -> PredictionDistributionPeriod:
    ranks = [
        item.actual_rank for item in observations if item.actual_rank is not None
    ]
    rank_counts: dict[int, int] = {}
    bucket_counts: dict[str, int] = {}
    probability_counts: dict[str, int] = {}
    for item in observations:
        if item.actual_rank is not None:
            rank_counts[item.actual_rank] = rank_counts.get(item.actual_rank, 0) + 1
        bucket = _rank_bucket(item.actual_rank)
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        probability_bin = _probability_bin(item.top_probability, probability_bins)
        probability_counts[probability_bin] = probability_counts.get(probability_bin, 0) + 1
    ordered_probability_counts = tuple(
        ( _probability_bin(i / probability_bins + 1e-15, probability_bins), probability_counts.get(
            _probability_bin(i / probability_bins + 1e-15, probability_bins), 0
        )) for i in range(probability_bins)
    )
    return PredictionDistributionPeriod(
        start,
        start + timedelta(days=period_days - 1),
        len(observations),
        len(ranks),
        len(observations) - len(ranks),
        tuple(sorted(rank_counts.items())),
        tuple(sorted(bucket_counts.items())),
        ordered_probability_counts,
        _mean([item.top_probability for item in observations]),
        _mean([item.cumulative_probability_at_max_k for item in observations]),
        _entropy([count for _, count in ordered_probability_counts]),
    )
def build_prediction_distribution_monitoring_report(
    source: ActualVsRankedReport,
    *,
    period_days: int = DEFAULT_PERIOD_DAYS,
    probability_bins: int = DEFAULT_PROBABILITY_BINS,
) -> PredictionDistributionMonitoringReport:
    if not isinstance(source, ActualVsRankedReport):
        raise TypeError("source must be an ActualVsRankedReport.")
    validation = validate_actual_vs_ranked_report(source)
    if not validation.is_valid:
        raise ValueError(
            "invalid Phase 45 source report: " + ", ".join(validation.issues)
        )
    if isinstance(period_days, bool) or not isinstance(period_days, int) or period_days < 1:
        raise ValueError("period_days must be an integer >= 1.")
    if (
        isinstance(probability_bins, bool)
        or not isinstance(probability_bins, int)
        or probability_bins < 2
    ):
        raise ValueError("probability_bins must be an integer >= 2.")
    ordered = tuple(
        sorted(source.observations, key=lambda item: (item.target_date, item.group_id))
    )
    if not ordered:
        raise ValueError("source report contains no observations.")
    anchor = ordered[0].target_date
    grouped: dict[date, list[ActualVsRankedObservation]] = {}
    for item in ordered:
        start = _period_start(item.target_date, anchor, period_days)
        grouped.setdefault(start, []).append(item)
    periods = tuple(
        _period(grouped[start], start, period_days, probability_bins)
        for start in sorted(grouped)
    )
    payload = {
        "version": PREDICTION_DISTRIBUTION_MONITORING_VERSION,
        "source_type": source.source_type,
        "source_report_identity": source.report_identity,
        "period_days": period_days,
        "probability_bins": probability_bins,
        "periods": [
            (
                p.period_start,
                p.period_end,
                p.observation_count,
                p.actual_available_observations,
                p.missed_observations,
                p.rank_distribution,
                p.rank_bucket_distribution,
                p.probability_bin_distribution,
                p.top_probability_mean,
                p.cumulative_probability_mean,
                p.probability_entropy,
            )
            for p in periods
        ],
    }
    return PredictionDistributionMonitoringReport(
        PREDICTION_DISTRIBUTION_MONITORING_VERSION,
        source.source_type,
        source.report_identity,
        period_days,
        probability_bins,
        periods,
        len(ordered),
        sum(item.actual_rank is not None for item in ordered),
        sum(item.actual_rank is None for item in ordered),
        _identity("prediction-distribution-monitoring-report-", payload),
    )


def prediction_distribution_monitoring_summary(
    report: PredictionDistributionMonitoringReport,
) -> dict[str, object]:
    validation = validate_prediction_distribution_monitoring_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "source_report_identity": report.source_report_identity,
        "period_days": report.period_days,
        "probability_bins": report.probability_bins,
        "periods": len(report.periods),
        "observations": report.observation_count,
        "actual_available_observations": report.actual_available_observations,
        "missed_observations": report.missed_observations,
        "report_identity": report.report_identity,
    }


def prediction_distribution_periods(
    report: PredictionDistributionMonitoringReport,
) -> tuple[PredictionDistributionPeriod, ...]:
    return report.periods
def prediction_distribution_period(
    report: PredictionDistributionMonitoringReport,
    period_start: date,
) -> PredictionDistributionPeriod:
    for period in report.periods:
        if period.period_start == period_start:
            return period
    raise KeyError("period not found: " + str(period_start))


def validate_prediction_distribution_monitoring_report(
    report: PredictionDistributionMonitoringReport,
) -> PredictionDistributionValidationResult:
    if not isinstance(report, PredictionDistributionMonitoringReport):
        return PredictionDistributionValidationResult(
            INVALID, ("INVALID_REPORT_TYPE",)
        )
    issues: list[str] = []
    if report.version != PREDICTION_DISTRIBUTION_MONITORING_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.source_report_identity.strip():
        issues.append("MISSING_SOURCE_REPORT_IDENTITY")
    if report.period_days < 1:
        issues.append("INVALID_PERIOD_DAYS")
    if report.probability_bins < 2:
        issues.append("INVALID_PROBABILITY_BINS")
    if not report.periods:
        issues.append("NO_PERIODS")
    starts = [item.period_start for item in report.periods]
    if starts != sorted(starts):
        issues.append("NON_CHRONOLOGICAL_PERIODS")
    if len(starts) != len(set(starts)):
        issues.append("DUPLICATE_PERIOD_STARTS")
    total = actual_total = missed_total = 0
    for period in report.periods:
        if period.period_end != period.period_start + timedelta(days=report.period_days - 1):
            issues.append("INVALID_PERIOD_LENGTH")
        if period.observation_count < 1:
            issues.append("EMPTY_PERIOD")
        if period.actual_available_observations + period.missed_observations != period.observation_count:
            issues.append("PERIOD_COUNT_MISMATCH")
        if len(period.probability_bin_distribution) != report.probability_bins:
            issues.append("PROBABILITY_BIN_COUNT_MISMATCH")
        rank_total = sum(count for _, count in period.rank_distribution)
        bucket_total = sum(count for _, count in period.rank_bucket_distribution)
        probability_total = sum(count for _, count in period.probability_bin_distribution)
        if rank_total != period.actual_available_observations:
            issues.append("RANK_COUNT_MISMATCH")
        if bucket_total != period.observation_count:
            issues.append("RANK_BUCKET_COUNT_MISMATCH")
        if probability_total != period.observation_count:
            issues.append("PROBABILITY_COUNT_MISMATCH")
        if not 0 <= period.missed_observations <= period.observation_count:
            issues.append("INVALID_MISSED_COUNT")
        if not 0 <= period.top_probability_mean <= 1:
            issues.append("INVALID_TOP_PROBABILITY_MEAN")
        if not 0 <= period.cumulative_probability_mean <= 1 + 1e-9:
            issues.append("INVALID_CUMULATIVE_PROBABILITY_MEAN")
        if period.probability_entropy < 0 or not math.isfinite(period.probability_entropy):
            issues.append("INVALID_PROBABILITY_ENTROPY")
        for rank, count in period.rank_distribution:
            if rank < 1 or count < 1:
                issues.append("INVALID_RANK_DISTRIBUTION")
        for label, count in period.probability_bin_distribution:
            if not label or count < 0:
                issues.append("INVALID_PROBABILITY_BIN")
        total += period.observation_count
        actual_total += period.actual_available_observations
        missed_total += period.missed_observations
    if total != report.observation_count:
        issues.append("OBSERVATION_COUNT_MISMATCH")
    if actual_total != report.actual_available_observations:
        issues.append("ACTUAL_COUNT_MISMATCH")
    if missed_total != report.missed_observations:
        issues.append("MISSED_COUNT_MISMATCH")
    if report.actual_available_observations + report.missed_observations != report.observation_count:
        issues.append("GLOBAL_COUNT_MISMATCH")
    if not report.report_identity.startswith("prediction-distribution-monitoring-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return PredictionDistributionValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "PREDICTION_DISTRIBUTION_MONITORING_VERSION",
    "VALID",
    "INVALID",
    "DEFAULT_PERIOD_DAYS",
    "DEFAULT_PROBABILITY_BINS",
    "PredictionDistributionPeriod",
    "PredictionDistributionMonitoringReport",
    "PredictionDistributionValidationResult",
    "build_prediction_distribution_monitoring_report",
    "prediction_distribution_monitoring_summary",
    "prediction_distribution_periods",
    "prediction_distribution_period",
    "validate_prediction_distribution_monitoring_report",
]
