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

RANKING_DRIFT_VERSION = "53.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEFAULT_PERIOD_DAYS = 7
DEFAULT_THRESHOLD = 0.05
DEFAULT_PSI_BINS = 10
DEFAULT_RANK_MAX = 20

DEFAULT_METRICS = (
    "top_1_rate",
    "top_3_rate",
    "top_5_rate",
    "top_10_rate",
    "mean_actual_rank",
    "mean_reciprocal_rank",
    "rank_distribution_psi",
)


@dataclass(frozen=True)
class RankingDistribution:
    rank_counts: tuple[tuple[int, int], ...]
    rank_probabilities: tuple[tuple[int, float], ...]
    bucket_counts: tuple[tuple[str, int], ...]
    bucket_probabilities: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class RankingPeriod:
    period_start: date
    period_end: date
    observation_count: int
    actual_available_observations: int
    missed_observations: int
    top_1_rate: float
    top_3_rate: float
    top_5_rate: float
    top_10_rate: float
    mean_actual_rank: float | None
    mean_reciprocal_rank: float
    distribution: RankingDistribution


@dataclass(frozen=True)
class RankingDriftRule:
    metric: str
    threshold: float = DEFAULT_THRESHOLD


@dataclass(frozen=True)
class RankingDriftObservation:
    metric: str
    baseline_period_start: date
    comparison_period_start: date
    baseline_value: float
    comparison_value: float
    absolute_change: float
    threshold: float
    drifted: bool


@dataclass(frozen=True)
class RankingDriftReport:
    version: str
    source_type: str
    source_report_identity: str
    period_days: int
    rank_max: int
    rules: tuple[RankingDriftRule, ...]
    periods: tuple[RankingPeriod, ...]
    observations: tuple[RankingDriftObservation, ...]
    drifted_metrics: tuple[str, ...]
    drifted_periods: tuple[tuple[str, date], ...]
    drifted: bool
    report_identity: str


@dataclass(frozen=True)
class RankingDriftValidationResult:
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


def _rate(ranks: Sequence[int], k: int) -> float:
    return (
        sum(rank <= k for rank in ranks) / len(ranks)
        if ranks else 0.0
    )


def _psi(
    baseline_counts: Sequence[int],
    comparison_counts: Sequence[int],
) -> float:
    if len(baseline_counts) != len(comparison_counts):
        raise ValueError("rank distribution cardinality mismatch.")
    if not baseline_counts:
        return 0.0
    baseline_total = sum(baseline_counts)
    comparison_total = sum(comparison_counts)
    if baseline_total < 1 or comparison_total < 1:
        return 0.0
    epsilon = 1e-12
    value = 0.0
    for baseline_count, comparison_count in zip(
        baseline_counts, comparison_counts
    ):
        baseline_probability = max(
            baseline_count / baseline_total, epsilon
        )
        comparison_probability = max(
            comparison_count / comparison_total, epsilon
        )
        value += (
            comparison_probability - baseline_probability
        ) * math.log(comparison_probability / baseline_probability)
    return value


def _distribution(
    ranks: Sequence[int],
    rank_max: int,
) -> RankingDistribution:
    counts = {rank: 0 for rank in range(1, rank_max + 1)}
    for rank in ranks:
        counts[min(rank, rank_max)] += 1
    total = len(ranks)
    probabilities = {
        rank: (count / total if total else 0.0)
        for rank, count in counts.items()
    }

    bucket_names = (
        "TOP_1",
        "TOP_3",
        "TOP_5",
        "TOP_10",
        "OUTSIDE_TOP_10",
    )
    bucket_counts = {name: 0 for name in bucket_names}
    for rank in ranks:
        bucket_counts[_rank_bucket(rank)] += 1
    bucket_probabilities = {
        name: (count / total if total else 0.0)
        for name, count in bucket_counts.items()
    }

    return RankingDistribution(
        tuple(counts.items()),
        tuple(probabilities.items()),
        tuple(bucket_counts.items()),
        tuple(bucket_probabilities.items()),
    )


def _period(
    observations: Sequence[ActualVsRankedObservation],
    start: date,
    period_days: int,
    rank_max: int,
) -> RankingPeriod:
    ranks = tuple(
        item.actual_rank
        for item in observations
        if item.actual_rank is not None
    )
    return RankingPeriod(
        start,
        start + timedelta(days=period_days - 1),
        len(observations),
        len(ranks),
        len(observations) - len(ranks),
        _rate(ranks, 1),
        _rate(ranks, 3),
        _rate(ranks, 5),
        _rate(ranks, 10),
        (sum(ranks) / len(ranks)) if ranks else None,
        (
            sum(1.0 / rank for rank in ranks) / len(ranks)
            if ranks else 0.0
        ),
        _distribution(ranks, rank_max),
    )


def _normalize_rules(
    rules: Sequence[RankingDriftRule] | None,
) -> tuple[RankingDriftRule, ...]:
    values = tuple(
        rules
        if rules is not None
        else tuple(RankingDriftRule(metric) for metric in DEFAULT_METRICS)
    )
    if not values:
        raise ValueError("at least one ranking drift rule is required.")
    allowed = set(DEFAULT_METRICS)
    seen: set[str] = set()
    for rule in values:
        if not isinstance(rule, RankingDriftRule):
            raise TypeError("rules must contain RankingDriftRule values.")
        if rule.metric in seen:
            raise ValueError(
                "ranking drift rule metrics must be unique."
            )
        seen.add(rule.metric)
        if rule.metric not in allowed:
            raise ValueError(
                "unsupported ranking drift metric: " + rule.metric
            )
        if (
            not math.isfinite(rule.threshold)
            or rule.threshold <= 0
        ):
            raise ValueError(
                "ranking drift threshold must be finite and > 0."
            )
    return values


def _metric_value(
    period: RankingPeriod,
    metric: str,
    baseline: RankingPeriod | None = None,
) -> float:
    if metric == "top_1_rate":
        return period.top_1_rate
    if metric == "top_3_rate":
        return period.top_3_rate
    if metric == "top_5_rate":
        return period.top_5_rate
    if metric == "top_10_rate":
        return period.top_10_rate
    if metric == "mean_actual_rank":
        return period.mean_actual_rank if period.mean_actual_rank is not None else 0.0
    if metric == "mean_reciprocal_rank":
        return period.mean_reciprocal_rank
    if metric == "rank_distribution_psi":
        if baseline is None:
            raise ValueError("baseline is required for rank_distribution_psi.")
        baseline_counts = tuple(
            count for _, count in baseline.distribution.rank_counts
        )
        comparison_counts = tuple(
            count for _, count in period.distribution.rank_counts
        )
        return _psi(baseline_counts, comparison_counts)
    raise ValueError("unsupported ranking drift metric: " + metric)


def build_ranking_drift_report(
    source: ActualVsRankedReport,
    *,
    period_days: int = DEFAULT_PERIOD_DAYS,
    rank_max: int = DEFAULT_RANK_MAX,
    rules: Sequence[RankingDriftRule] | None = None,
) -> RankingDriftReport:
    if not isinstance(source, ActualVsRankedReport):
        raise TypeError("source must be an ActualVsRankedReport.")
    validation = validate_actual_vs_ranked_report(source)
    if not validation.is_valid:
        raise ValueError(
            "invalid Phase 45 source report: " + ", ".join(validation.issues)
        )
    if (
        isinstance(period_days, bool)
        or not isinstance(period_days, int)
        or period_days < 1
    ):
        raise ValueError("period_days must be an integer >= 1.")
    if (
        isinstance(rank_max, bool)
        or not isinstance(rank_max, int)
        or rank_max < 1
    ):
        raise ValueError("rank_max must be an integer >= 1.")

    normalized_rules = _normalize_rules(rules)
    ordered = tuple(
        sorted(
            source.observations,
            key=lambda item: (item.target_date, item.group_id),
        )
    )
    if not ordered:
        raise ValueError("source report contains no observations.")

    anchor = ordered[0].target_date
    grouped: dict[date, list[ActualVsRankedObservation]] = {}
    for item in ordered:
        start = _period_start(item.target_date, anchor, period_days)
        grouped.setdefault(start, []).append(item)

    periods = tuple(
        _period(
            grouped[start],
            start,
            period_days,
            rank_max,
        )
        for start in sorted(grouped)
    )
    if len(periods) < 2:
        raise ValueError(
            "at least two periods are required for ranking drift detection."
        )

    baseline = periods[0]
    observations: list[RankingDriftObservation] = []
    for rule in normalized_rules:
        baseline_value = _metric_value(
            baseline, rule.metric, baseline
        )
        for period in periods[1:]:
            comparison_value = _metric_value(
                period, rule.metric, baseline
            )
            absolute_change = abs(comparison_value - baseline_value)
            observations.append(
                RankingDriftObservation(
                    rule.metric,
                    baseline.period_start,
                    period.period_start,
                    baseline_value,
                    comparison_value,
                    absolute_change,
                    rule.threshold,
                    absolute_change >= rule.threshold,
                )
            )

    drifted_metrics = tuple(
        dict.fromkeys(
            item.metric for item in observations if item.drifted
        )
    )
    drifted_periods = tuple(
        (item.metric, item.comparison_period_start)
        for item in observations
        if item.drifted
    )

    payload = {
        "version": RANKING_DRIFT_VERSION,
        "source_type": source.source_type,
        "source_report_identity": source.report_identity,
        "period_days": period_days,
        "rank_max": rank_max,
        "rules": [
            (rule.metric, rule.threshold)
            for rule in normalized_rules
        ],
        "periods": [
            (
                period.period_start,
                period.period_end,
                period.observation_count,
                period.actual_available_observations,
                period.missed_observations,
                period.top_1_rate,
                period.top_3_rate,
                period.top_5_rate,
                period.top_10_rate,
                period.mean_actual_rank,
                period.mean_reciprocal_rank,
                period.distribution,
            )
            for period in periods
        ],
        "observations": [
            (
                item.metric,
                item.baseline_period_start,
                item.comparison_period_start,
                item.baseline_value,
                item.comparison_value,
                item.absolute_change,
                item.threshold,
                item.drifted,
            )
            for item in observations
        ],
    }

    return RankingDriftReport(
        RANKING_DRIFT_VERSION,
        source.source_type,
        source.report_identity,
        period_days,
        rank_max,
        normalized_rules,
        periods,
        tuple(observations),
        drifted_metrics,
        drifted_periods,
        bool(drifted_metrics),
        _identity("ranking-drift-report-", payload),
    )


def ranking_drift_summary(
    report: RankingDriftReport,
) -> dict[str, object]:
    validation = validate_ranking_drift_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "source_report_identity": report.source_report_identity,
        "period_days": report.period_days,
        "rank_max": report.rank_max,
        "rules": report.rules,
        "periods": len(report.periods),
        "comparisons": len(report.observations),
        "drifted_metrics": report.drifted_metrics,
        "drifted_periods": report.drifted_periods,
        "drifted": report.drifted,
        "report_identity": report.report_identity,
    }


def ranking_drift_periods(
    report: RankingDriftReport,
) -> tuple[RankingPeriod, ...]:
    return report.periods


def ranking_drift_observations(
    report: RankingDriftReport,
    metric: str | None = None,
) -> tuple[RankingDriftObservation, ...]:
    if metric is None:
        return report.observations
    return tuple(
        item for item in report.observations if item.metric == metric
    )


def validate_ranking_drift_report(
    report: RankingDriftReport,
) -> RankingDriftValidationResult:
    if not isinstance(report, RankingDriftReport):
        return RankingDriftValidationResult(
            INVALID, ("INVALID_REPORT_TYPE",)
        )

    issues: list[str] = []
    if report.version != RANKING_DRIFT_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.source_report_identity.strip():
        issues.append("MISSING_SOURCE_REPORT_IDENTITY")
    if report.period_days < 1:
        issues.append("INVALID_PERIOD_DAYS")
    if report.rank_max < 1:
        issues.append("INVALID_RANK_MAX")
    if not report.rules:
        issues.append("NO_RULES")

    allowed = set(DEFAULT_METRICS)
    seen_rules: set[str] = set()
    for rule in report.rules:
        if rule.metric not in allowed:
            issues.append("UNKNOWN_RULE_METRIC")
        if rule.metric in seen_rules:
            issues.append("DUPLICATE_RULE_METRICS")
        seen_rules.add(rule.metric)
        if (
            not math.isfinite(rule.threshold)
            or rule.threshold <= 0
        ):
            issues.append("INVALID_THRESHOLD")

    if len(report.periods) < 2:
        issues.append("INSUFFICIENT_PERIODS")

    starts = [period.period_start for period in report.periods]
    if starts != sorted(starts):
        issues.append("NON_CHRONOLOGICAL_PERIODS")
    if len(starts) != len(set(starts)):
        issues.append("DUPLICATE_PERIOD_STARTS")

    total = 0
    actual_total = 0
    missed_total = 0

    for period in report.periods:
        if period.period_end != period.period_start + timedelta(
            days=report.period_days - 1
        ):
            issues.append("INVALID_PERIOD_LENGTH")
        if period.observation_count < 1:
            issues.append("EMPTY_PERIOD")
        if (
            period.actual_available_observations
            + period.missed_observations
            != period.observation_count
        ):
            issues.append("PERIOD_COUNT_MISMATCH")
        if (
            len(period.distribution.rank_counts)
            != report.rank_max
        ):
            issues.append("RANK_COUNT_CARDINALITY_MISMATCH")
        if (
            len(period.distribution.rank_probabilities)
            != report.rank_max
        ):
            issues.append("RANK_PROBABILITY_CARDINALITY_MISMATCH")

        rank_count_total = sum(
            count for _, count in period.distribution.rank_counts
        )
        rank_probability_total = sum(
            value for _, value in period.distribution.rank_probabilities
        )
        if rank_count_total != period.actual_available_observations:
            issues.append("RANK_COUNT_MISMATCH")
        if not math.isclose(
            rank_probability_total,
            1.0 if period.actual_available_observations else 0.0,
            rel_tol=0,
            abs_tol=1e-9,
        ):
            issues.append("RANK_PROBABILITY_SUM_MISMATCH")

        if not all(
            math.isfinite(value)
            for value in (
                period.top_1_rate,
                period.top_3_rate,
                period.top_5_rate,
                period.top_10_rate,
                period.mean_reciprocal_rank,
            )
        ):
            issues.append("NONFINITE_PERIOD_METRIC")
        if not all(
            0 <= value <= 1
            for value in (
                period.top_1_rate,
                period.top_3_rate,
                period.top_5_rate,
                period.top_10_rate,
                period.mean_reciprocal_rank,
            )
        ):
            issues.append("INVALID_RATE_BOUNDS")
        if (
            period.mean_actual_rank is not None
            and (
                not math.isfinite(period.mean_actual_rank)
                or period.mean_actual_rank < 1
            )
        ):
            issues.append("INVALID_MEAN_RANK")

        bucket_total = sum(
            count
            for _, count in period.distribution.bucket_counts
        )
        if bucket_total != period.actual_available_observations:
            issues.append("BUCKET_COUNT_MISMATCH")
        if len(period.distribution.bucket_counts) != 5:
            issues.append("BUCKET_CARDINALITY_MISMATCH")
        if len(period.distribution.bucket_probabilities) != 5:
            issues.append("BUCKET_PROBABILITY_CARDINALITY_MISMATCH")

        total += period.observation_count
        actual_total += period.actual_available_observations
        missed_total += period.missed_observations

    if actual_total + missed_total != total:
        issues.append("GLOBAL_COUNT_MISMATCH")

    expected_observations = len(report.rules) * (len(report.periods) - 1)
    if len(report.observations) != expected_observations:
        issues.append("OBSERVATION_CARDINALITY_MISMATCH")

    rule_metrics = {rule.metric for rule in report.rules}
    seen_observations: set[tuple[str, date]] = set()

    for item in report.observations:
        key = (item.metric, item.comparison_period_start)
        if key in seen_observations:
            issues.append("DUPLICATE_OBSERVATION")
        seen_observations.add(key)
        if item.metric not in rule_metrics:
            issues.append("UNDECLARED_METRIC")
        if item.comparison_period_start <= item.baseline_period_start:
            issues.append("INVALID_COMPARISON_ORDER")
        if not all(
            math.isfinite(value)
            for value in (
                item.baseline_value,
                item.comparison_value,
                item.absolute_change,
                item.threshold,
            )
        ):
            issues.append("NONFINITE_OBSERVATION")
        if item.absolute_change < 0:
            issues.append("NEGATIVE_ABSOLUTE_CHANGE")
        if item.threshold <= 0:
            issues.append("INVALID_OBSERVATION_THRESHOLD")
        if item.drifted != (
            item.absolute_change >= item.threshold
        ):
            issues.append("DRIFT_FLAG_MISMATCH")

    expected_metrics = tuple(
        dict.fromkeys(
            item.metric
            for item in report.observations
            if item.drifted
        )
    )
    expected_periods = tuple(
        (item.metric, item.comparison_period_start)
        for item in report.observations
        if item.drifted
    )

    if report.drifted_metrics != expected_metrics:
        issues.append("DRIFTED_METRIC_MISMATCH")
    if report.drifted_periods != expected_periods:
        issues.append("DRIFTED_PERIOD_MISMATCH")
    if report.drifted != bool(report.drifted_metrics):
        issues.append("OVERALL_DRIFT_MISMATCH")
    if not report.report_identity.startswith(
        "ranking-drift-report-"
    ):
        issues.append("INVALID_REPORT_IDENTITY")

    return RankingDriftValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "RANKING_DRIFT_VERSION",
    "VALID",
    "INVALID",
    "DEFAULT_PERIOD_DAYS",
    "DEFAULT_THRESHOLD",
    "DEFAULT_PSI_BINS",
    "DEFAULT_RANK_MAX",
    "DEFAULT_METRICS",
    "RankingDistribution",
    "RankingPeriod",
    "RankingDriftRule",
    "RankingDriftObservation",
    "RankingDriftReport",
    "RankingDriftValidationResult",
    "build_ranking_drift_report",
    "ranking_drift_summary",
    "ranking_drift_periods",
    "ranking_drift_observations",
    "validate_ranking_drift_report",
]
