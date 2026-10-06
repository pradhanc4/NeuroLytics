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

CALIBRATION_DRIFT_VERSION = "52.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEFAULT_PERIOD_DAYS = 7
DEFAULT_BINS = 10
DEFAULT_THRESHOLD = 0.05


@dataclass(frozen=True)
class CalibrationBin:
    label: str
    observation_count: int
    mean_predicted_probability: float
    empirical_hit_rate: float
    absolute_gap: float


@dataclass(frozen=True)
class CalibrationPeriod:
    period_start: date
    period_end: date
    observation_count: int
    actual_available_observations: int
    missed_observations: int
    calibration_observation_count: int
    mean_predicted_probability: float
    empirical_hit_rate: float
    calibration_gap: float
    brier_score: float
    expected_calibration_error: float
    bins: tuple[CalibrationBin, ...]


@dataclass(frozen=True)
class CalibrationDriftRule:
    metric: str
    threshold: float


@dataclass(frozen=True)
class CalibrationDriftObservation:
    metric: str
    baseline_period_start: date
    comparison_period_start: date
    baseline_value: float
    comparison_value: float
    absolute_change: float
    threshold: float
    drifted: bool


@dataclass(frozen=True)
class CalibrationDriftReport:
    version: str
    source_type: str
    source_report_identity: str
    period_days: int
    bin_count: int
    rules: tuple[CalibrationDriftRule, ...]
    periods: tuple[CalibrationPeriod, ...]
    observations: tuple[CalibrationDriftObservation, ...]
    drifted_metrics: tuple[str, ...]
    drifted_periods: tuple[tuple[str, date], ...]
    drifted: bool
    report_identity: str


@dataclass(frozen=True)
class CalibrationDriftValidationResult:
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


def _probability_bin(value: float, bins: int) -> int:
    return min(bins - 1, int(value * bins))


def _bin_label(index: int, bins: int) -> str:
    lower = index / bins
    upper = (index + 1) / bins
    return f"{lower:.2f}-{upper:.2f}"


def _outcome(observation: ActualVsRankedObservation) -> float | None:
    if observation.actual_rank is None:
        return None
    return 1.0 if observation.actual_rank == 1 else 0.0


def _period(
    observations: Sequence[ActualVsRankedObservation],
    start: date,
    period_days: int,
    bin_count: int,
) -> CalibrationPeriod:
    usable = [
        item for item in observations
        if _outcome(item) is not None
    ]
    predictions = [item.top_probability for item in usable]
    outcomes = [float(_outcome(item)) for item in usable]
    mean_predicted = (
        sum(predictions) / len(predictions) if predictions else 0.0
    )
    empirical_rate = (
        sum(outcomes) / len(outcomes) if outcomes else 0.0
    )
    gap = mean_predicted - empirical_rate
    brier = (
        sum((prediction - outcome) ** 2 for prediction, outcome in zip(predictions, outcomes))
        / len(usable)
        if usable else 0.0
    )

    bin_items: list[list[tuple[float, float]]] = [
        [] for _ in range(bin_count)
    ]
    for prediction, outcome in zip(predictions, outcomes):
        bin_items[_probability_bin(prediction, bin_count)].append(
            (prediction, outcome)
        )

    bins: list[CalibrationBin] = []
    ece = 0.0
    total = len(usable)
    for index, items in enumerate(bin_items):
        if not items:
            bins.append(
                CalibrationBin(
                    _bin_label(index, bin_count), 0, 0.0, 0.0, 0.0
                )
            )
            continue
        mean_prediction = sum(item[0] for item in items) / len(items)
        hit_rate = sum(item[1] for item in items) / len(items)
        absolute_gap = abs(mean_prediction - hit_rate)
        ece += (len(items) / total) * absolute_gap
        bins.append(
            CalibrationBin(
                _bin_label(index, bin_count),
                len(items),
                mean_prediction,
                hit_rate,
                absolute_gap,
            )
        )

    return CalibrationPeriod(
        start,
        start + timedelta(days=period_days - 1),
        len(observations),
        len(usable),
        len(observations) - len(usable),
        len(usable),
        mean_predicted,
        empirical_rate,
        gap,
        brier,
        ece,
        tuple(bins),
    )


def _normalize_rules(
    rules: Sequence[CalibrationDriftRule] | None,
) -> tuple[CalibrationDriftRule, ...]:
    normalized = tuple(
        rules
        if rules is not None
        else (
            CalibrationDriftRule("expected_calibration_error", DEFAULT_THRESHOLD),
            CalibrationDriftRule("brier_score", DEFAULT_THRESHOLD),
            CalibrationDriftRule("calibration_gap", DEFAULT_THRESHOLD),
        )
    )
    if not normalized:
        raise ValueError("at least one calibration drift rule is required.")
    seen: set[str] = set()
    allowed = {
        "expected_calibration_error",
        "brier_score",
        "calibration_gap",
        "mean_predicted_probability",
        "empirical_hit_rate",
    }
    for rule in normalized:
        if not isinstance(rule, CalibrationDriftRule):
            raise TypeError("rules must contain CalibrationDriftRule values.")
        if rule.metric in seen:
            raise ValueError("duplicate calibration drift metric: " + rule.metric)
        seen.add(rule.metric)
        if rule.metric not in allowed:
            raise ValueError("unsupported calibration drift metric: " + rule.metric)
        if not math.isfinite(rule.threshold) or rule.threshold <= 0:
            raise ValueError("rule threshold must be finite and > 0.")
    return normalized


def _metric_value(period: CalibrationPeriod, metric: str) -> float:
    if metric == "expected_calibration_error":
        return period.expected_calibration_error
    if metric == "brier_score":
        return period.brier_score
    if metric == "calibration_gap":
        return period.calibration_gap
    if metric == "mean_predicted_probability":
        return period.mean_predicted_probability
    if metric == "empirical_hit_rate":
        return period.empirical_hit_rate
    raise ValueError("unsupported calibration drift metric: " + metric)


def build_calibration_drift_report(
    source: ActualVsRankedReport,
    *,
    period_days: int = DEFAULT_PERIOD_DAYS,
    bin_count: int = DEFAULT_BINS,
    rules: Sequence[CalibrationDriftRule] | None = None,
) -> CalibrationDriftReport:
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
        isinstance(bin_count, bool)
        or not isinstance(bin_count, int)
        or bin_count < 2
    ):
        raise ValueError("bin_count must be an integer >= 2.")

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
        _period(grouped[start], start, period_days, bin_count)
        for start in sorted(grouped)
    )
    if len(periods) < 2:
        raise ValueError(
            "at least two periods are required for calibration drift detection."
        )

    baseline = periods[0]
    observations: list[CalibrationDriftObservation] = []
    for rule in normalized_rules:
        baseline_value = _metric_value(baseline, rule.metric)
        for period in periods[1:]:
            comparison_value = _metric_value(period, rule.metric)
            absolute_change = abs(comparison_value - baseline_value)
            observations.append(
                CalibrationDriftObservation(
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
        "version": CALIBRATION_DRIFT_VERSION,
        "source_type": source.source_type,
        "source_report_identity": source.report_identity,
        "period_days": period_days,
        "bin_count": bin_count,
        "rules": [(rule.metric, rule.threshold) for rule in normalized_rules],
        "periods": [
            (
                period.period_start,
                period.period_end,
                period.observation_count,
                period.actual_available_observations,
                period.missed_observations,
                period.mean_predicted_probability,
                period.empirical_hit_rate,
                period.calibration_gap,
                period.brier_score,
                period.expected_calibration_error,
                tuple(
                    (
                        item.label,
                        item.observation_count,
                        item.mean_predicted_probability,
                        item.empirical_hit_rate,
                        item.absolute_gap,
                    )
                    for item in period.bins
                ),
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

    return CalibrationDriftReport(
        CALIBRATION_DRIFT_VERSION,
        source.source_type,
        source.report_identity,
        period_days,
        bin_count,
        normalized_rules,
        periods,
        tuple(observations),
        drifted_metrics,
        drifted_periods,
        bool(drifted_metrics),
        _identity("calibration-drift-report-", payload),
    )


def calibration_drift_summary(
    report: CalibrationDriftReport,
) -> dict[str, object]:
    validation = validate_calibration_drift_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "source_report_identity": report.source_report_identity,
        "period_days": report.period_days,
        "bin_count": report.bin_count,
        "rules": report.rules,
        "periods": len(report.periods),
        "comparisons": len(report.observations),
        "drifted_metrics": report.drifted_metrics,
        "drifted_periods": report.drifted_periods,
        "drifted": report.drifted,
        "report_identity": report.report_identity,
    }


def calibration_drift_periods(
    report: CalibrationDriftReport,
) -> tuple[CalibrationPeriod, ...]:
    return report.periods


def calibration_drift_observations(
    report: CalibrationDriftReport,
    metric: str | None = None,
) -> tuple[CalibrationDriftObservation, ...]:
    if metric is None:
        return report.observations
    return tuple(item for item in report.observations if item.metric == metric)


def validate_calibration_drift_report(
    report: CalibrationDriftReport,
) -> CalibrationDriftValidationResult:
    if not isinstance(report, CalibrationDriftReport):
        return CalibrationDriftValidationResult(
            INVALID, ("INVALID_REPORT_TYPE",)
        )
    issues: list[str] = []
    if report.version != CALIBRATION_DRIFT_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.source_report_identity.strip():
        issues.append("MISSING_SOURCE_REPORT_IDENTITY")
    if report.period_days < 1:
        issues.append("INVALID_PERIOD_DAYS")
    if report.bin_count < 2:
        issues.append("INVALID_BIN_COUNT")
    if not report.rules:
        issues.append("NO_RULES")
    allowed = {
        "expected_calibration_error",
        "brier_score",
        "calibration_gap",
        "mean_predicted_probability",
        "empirical_hit_rate",
    }
    rule_metrics = {rule.metric for rule in report.rules}
    if len(rule_metrics) != len(report.rules):
        issues.append("DUPLICATE_RULE_METRICS")
    for rule in report.rules:
        if rule.metric not in allowed:
            issues.append("UNKNOWN_RULE_METRIC")
        if not math.isfinite(rule.threshold) or rule.threshold <= 0:
            issues.append("INVALID_THRESHOLD")
    if len(report.periods) < 2:
        issues.append("INSUFFICIENT_PERIODS")
    starts = [period.period_start for period in report.periods]
    if starts != sorted(starts):
        issues.append("NON_CHRONOLOGICAL_PERIODS")
    if len(starts) != len(set(starts)):
        issues.append("DUPLICATE_PERIOD_STARTS")

    expected_bins = report.bin_count
    total = actual_total = missed_total = 0
    for period in report.periods:
        if period.period_end != period.period_start + timedelta(
            days=report.period_days - 1
        ):
            issues.append("INVALID_PERIOD_LENGTH")
        if period.observation_count < 1:
            issues.append("EMPTY_PERIOD")
        if (
            period.actual_available_observations + period.missed_observations
            != period.observation_count
        ):
            issues.append("PERIOD_COUNT_MISMATCH")
        if period.calibration_observation_count != period.actual_available_observations:
            issues.append("CALIBRATION_COUNT_MISMATCH")
        if len(period.bins) != expected_bins:
            issues.append("BIN_COUNT_MISMATCH")
        if not all(
            math.isfinite(value)
            for value in (
                period.mean_predicted_probability,
                period.empirical_hit_rate,
                period.calibration_gap,
                period.brier_score,
                period.expected_calibration_error,
            )
        ):
            issues.append("NONFINITE_PERIOD_METRIC")
        if not 0 <= period.mean_predicted_probability <= 1:
            issues.append("INVALID_MEAN_PREDICTED_PROBABILITY")
        if not 0 <= period.empirical_hit_rate <= 1:
            issues.append("INVALID_EMPIRICAL_HIT_RATE")
        if not -1 <= period.calibration_gap <= 1:
            issues.append("INVALID_CALIBRATION_GAP")
        if not 0 <= period.brier_score <= 1:
            issues.append("INVALID_BRIER_SCORE")
        if not 0 <= period.expected_calibration_error <= 1:
            issues.append("INVALID_ECE")
        bin_total = 0
        for item in period.bins:
            if item.observation_count < 0:
                issues.append("INVALID_BIN_COUNT_VALUE")
            if item.observation_count == 0:
                if item.mean_predicted_probability != 0.0 or item.empirical_hit_rate != 0.0:
                    issues.append("INVALID_EMPTY_BIN_VALUES")
            else:
                if not 0 <= item.mean_predicted_probability <= 1:
                    issues.append("INVALID_BIN_PREDICTION")
                if not 0 <= item.empirical_hit_rate <= 1:
                    issues.append("INVALID_BIN_HIT_RATE")
                if not 0 <= item.absolute_gap <= 1:
                    issues.append("INVALID_BIN_GAP")
                if not math.isclose(
                    item.absolute_gap,
                    abs(
                        item.mean_predicted_probability
                        - item.empirical_hit_rate
                    ),
                    rel_tol=0,
                    abs_tol=1e-12,
                ):
                    issues.append("BIN_GAP_MISMATCH")
            bin_total += item.observation_count
        if bin_total != period.calibration_observation_count:
            issues.append("BIN_OBSERVATION_MISMATCH")
        total += period.observation_count
        actual_total += period.actual_available_observations
        missed_total += period.missed_observations

    if total < 1:
        issues.append("NO_OBSERVATIONS")
    if actual_total + missed_total != total:
        issues.append("GLOBAL_COUNT_MISMATCH")

    expected_observations = len(report.rules) * (len(report.periods) - 1)
    if len(report.observations) != expected_observations:
        issues.append("OBSERVATION_CARDINALITY_MISMATCH")

    seen: set[tuple[str, date]] = set()
    for item in report.observations:
        key = (item.metric, item.comparison_period_start)
        if key in seen:
            issues.append("DUPLICATE_OBSERVATION")
        seen.add(key)
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
        if item.drifted != (item.absolute_change >= item.threshold):
            issues.append("DRIFT_FLAG_MISMATCH")

    expected_metrics = tuple(
        dict.fromkeys(item.metric for item in report.observations if item.drifted)
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
    if not report.report_identity.startswith("calibration-drift-report-"):
        issues.append("INVALID_REPORT_IDENTITY")

    return CalibrationDriftValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "CALIBRATION_DRIFT_VERSION",
    "VALID",
    "INVALID",
    "DEFAULT_PERIOD_DAYS",
    "DEFAULT_BINS",
    "DEFAULT_THRESHOLD",
    "CalibrationBin",
    "CalibrationPeriod",
    "CalibrationDriftRule",
    "CalibrationDriftObservation",
    "CalibrationDriftReport",
    "CalibrationDriftValidationResult",
    "build_calibration_drift_report",
    "calibration_drift_summary",
    "calibration_drift_periods",
    "calibration_drift_observations",
    "validate_calibration_drift_report",
]
