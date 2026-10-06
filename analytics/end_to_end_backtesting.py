from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Callable, Sequence

from analytics.end_to_end_prediction import (
    EndToEndPredictionResult,
    validate_end_to_end_prediction,
)
from analytics.top_k_framework import (
    TopKEvaluationReport,
    build_top_k_evaluation_report,
    top_k_selection,
)
from analytics.actual_vs_ranked import (
    ActualVsRankedReport,
    build_actual_vs_ranked_report,
)
from analytics.performance_over_time import (
    PerformanceOverTimeReport,
    build_performance_over_time_report,
)

END_TO_END_BACKTEST_VERSION = "91.0.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class BacktestFold:
    fold_index: int
    train_start_index: int
    train_end_index: int
    target_index: int
    train_end_date: date
    target_date: date
    fold_identity: str


@dataclass(frozen=True)
class BacktestActual:
    panel: str | None
    jodi: str | None
    digits: tuple[int, ...] = ()


@dataclass(frozen=True)
class EndToEndBacktestObservation:
    fold: BacktestFold
    actual: BacktestActual
    prediction: EndToEndPredictionResult
    panel_hit_at_k: tuple[tuple[int, bool], ...]
    jodi_hit_at_k: tuple[tuple[int, bool], ...]
    panel_actual_rank: int | None
    jodi_actual_rank: int | None
    observation_identity: str


@dataclass(frozen=True)
class EndToEndBacktestReport:
    version: str
    dataset_identity: str
    observations: tuple[EndToEndBacktestObservation, ...]
    panel_top_k_report: TopKEvaluationReport
    jodi_top_k_report: TopKEvaluationReport
    panel_actual_vs_ranked: ActualVsRankedReport
    jodi_actual_vs_ranked: ActualVsRankedReport
    panel_performance_over_time: PerformanceOverTimeReport
    jodi_performance_over_time: PerformanceOverTimeReport
    report_identity: str


@dataclass(frozen=True)
class EndToEndBacktestValidationResult:
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


def _validate_panel(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    if len(value) != 3 or not value.isdigit():
        raise ValueError("actual panel must be a three-digit string.")
    return value


def _validate_jodi(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    if len(value) != 2 or not value.isdigit():
        raise ValueError("actual jodi must be a two-digit string.")
    return value


def build_backtest_folds(
    dates: Sequence[date],
    *,
    initial_train_size: int,
    test_size: int = 1,
    step_size: int = 1,
) -> tuple[BacktestFold, ...]:
    ordered = tuple(dates)
    if len(ordered) <= 1:
        raise ValueError("at least two chronological dates are required.")
    if any(not isinstance(item, date) for item in ordered):
        raise TypeError("dates must contain datetime.date values.")
    if tuple(sorted(ordered)) != ordered:
        raise ValueError("dates must be chronological.")
    if len(set(ordered)) != len(ordered):
        raise ValueError("dates must be unique.")
    for name, value in (
        ("initial_train_size", initial_train_size),
        ("test_size", test_size),
        ("step_size", step_size),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer.")
    if initial_train_size >= len(ordered):
        raise ValueError("initial_train_size must leave test observations.")

    folds = []
    target = initial_train_size
    index = 0
    while target < len(ordered):
        target_end = min(target + test_size, len(ordered))
        for target_index in range(target, target_end):
            train_end_index = target_index - 1
            fold = BacktestFold(
                fold_index=index,
                train_start_index=0,
                train_end_index=train_end_index,
                target_index=target_index,
                train_end_date=ordered[train_end_index],
                target_date=ordered[target_index],
                fold_identity=_identity(
                    "end-to-end-backtest-fold-",
                    (
                        END_TO_END_BACKTEST_VERSION,
                        index,
                        train_end_index,
                        target_index,
                        ordered[train_end_index],
                        ordered[target_index],
                    ),
                ),
            )
            folds.append(fold)
            index += 1
        target += step_size
    return tuple(folds)


def _actual_rank(ranking, actual: str | None) -> int | None:
    if actual is None:
        return None
    for candidate in ranking.candidates:
        value = getattr(candidate, "panel", None)
        if value is None:
            value = getattr(candidate, "jodi", None)
        if value == actual:
            return candidate.rank
    return None


def _hits(ranking, actual: str | None, ks: Sequence[int]):
    rank = _actual_rank(ranking, actual)
    return tuple((k, rank is not None and rank <= k) for k in ks)


def _observation(
    fold: BacktestFold,
    actual: BacktestActual,
    prediction: EndToEndPredictionResult,
    ks: tuple[int, ...],
) -> EndToEndBacktestObservation:
    if fold.target_date != prediction.target_date:
        raise ValueError("prediction target date does not match backtest fold.")
    if fold.train_end_date >= fold.target_date:
        raise ValueError("training boundary must be strictly before target date.")
    validation = validate_end_to_end_prediction(prediction)
    if not validation.is_valid:
        raise ValueError(
            "invalid Phase 90 prediction: " + ",".join(validation.issues)
        )
    panel = _validate_panel(actual.panel)
    jodi = _validate_jodi(actual.jodi)
    panel_ranking = prediction.panel_ranking
    jodi_ranking = prediction.jodi_ranking
    panel_rank = _actual_rank(panel_ranking, panel)
    jodi_rank = _actual_rank(jodi_ranking, jodi)
    return EndToEndBacktestObservation(
        fold,
        BacktestActual(panel, jodi, tuple(actual.digits)),
        prediction,
        _hits(panel_ranking, panel, ks),
        _hits(jodi_ranking, jodi, ks),
        panel_rank,
        jodi_rank,
        _identity(
            "end-to-end-backtest-observation-",
            (
                fold.fold_identity,
                prediction.pipeline_identity,
                panel,
                jodi,
                tuple(actual.digits),
                ks,
            ),
        ),
    )


def run_end_to_end_backtest(
    dates: Sequence[date],
    actuals: Sequence[BacktestActual],
    predictor: Callable[[BacktestFold], EndToEndPredictionResult],
    *,
    dataset_identity: str,
    initial_train_size: int,
    test_size: int = 1,
    step_size: int = 1,
    top_ks: Sequence[int] = (1, 3, 5, 10),
    period_days: int = 7,
) -> EndToEndBacktestReport:
    if not dataset_identity.strip():
        raise ValueError("dataset_identity must be non-empty.")
    if not callable(predictor):
        raise TypeError("predictor must be callable.")
    dates_tuple = tuple(dates)
    actuals_tuple = tuple(actuals)
    if len(dates_tuple) != len(actuals_tuple):
        raise ValueError("dates and actuals must have equal lengths.")
    folds = build_backtest_folds(
        dates_tuple,
        initial_train_size=initial_train_size,
        test_size=test_size,
        step_size=step_size,
    )
    ks = tuple(sorted(set(int(k) for k in top_ks)))
    if not ks or any(k < 1 for k in ks):
        raise ValueError("top_ks must contain positive integers.")

    observations = []
    for fold in folds:
        actual = actuals_tuple[fold.target_index]
        prediction = predictor(fold)
        if not isinstance(prediction, EndToEndPredictionResult):
            raise TypeError("predictor must return EndToEndPredictionResult.")
        observations.append(_observation(fold, actual, prediction, ks))
    if not observations:
        raise ValueError("no backtest observations were produced.")

    panel_rankings = tuple(
        _with_actual(
            item.prediction.panel_ranking,
            item.actual.panel,
            "phase91-panel-" + str(item.fold.fold_index),
            item.fold.target_date,
        )
        for item in observations
    )
    jodi_rankings = tuple(
        _with_actual(
            item.prediction.jodi_ranking,
            item.actual.jodi,
            "phase91-jodi-" + str(item.fold.fold_index),
            item.fold.target_date,
        )
        for item in observations
    )
    panel_top_k = build_top_k_evaluation_report(
        panel_rankings, "phase91-panel-source-" + dataset_identity, ks
    )
    jodi_top_k = build_top_k_evaluation_report(
        jodi_rankings, "phase91-jodi-source-" + dataset_identity, ks
    )
    panel_avr = build_actual_vs_ranked_report(panel_top_k)
    jodi_avr = build_actual_vs_ranked_report(jodi_top_k)
    panel_perf = build_performance_over_time_report(
        panel_avr, period_days=period_days, hit_ks=ks
    )
    jodi_perf = build_performance_over_time_report(
        jodi_avr, period_days=period_days, hit_ks=ks
    )
    identity = _identity(
        "end-to-end-backtest-report-",
        (
            END_TO_END_BACKTEST_VERSION,
            dataset_identity,
            tuple(item.observation_identity for item in observations),
            panel_top_k.report_identity,
            jodi_top_k.report_identity,
            panel_perf.report_identity,
            jodi_perf.report_identity,
        ),
    )
    return EndToEndBacktestReport(
        END_TO_END_BACKTEST_VERSION,
        dataset_identity,
        tuple(observations),
        panel_top_k,
        jodi_top_k,
        panel_avr,
        jodi_avr,
        panel_perf,
        jodi_perf,
        identity,
    )


def _with_actual(ranking, actual, group_id, target_date):
    from dataclasses import replace
    if actual is None:
        if hasattr(ranking, "actual_panel"):
            return replace(
                ranking,
                group_id=group_id,
                target_date=target_date,
                actual_panel=None,
            )
        return replace(
            ranking,
            group_id=group_id,
            target_date=target_date,
            actual_jodi=None,
        )
    if hasattr(ranking, "actual_panel"):
        return replace(
            ranking,
            group_id=group_id,
            target_date=target_date,
            actual_panel=_validate_panel(actual),
        )
    return replace(
        ranking,
        group_id=group_id,
        target_date=target_date,
        actual_jodi=_validate_jodi(actual),
    )


def validate_end_to_end_backtest(
    report: EndToEndBacktestReport,
) -> EndToEndBacktestValidationResult:
    if not isinstance(report, EndToEndBacktestReport):
        return EndToEndBacktestValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues = []
    if report.version != END_TO_END_BACKTEST_VERSION:
        issues.append("INVALID_VERSION")
    if not report.dataset_identity.strip():
        issues.append("MISSING_DATASET_IDENTITY")
    if not report.observations:
        issues.append("NO_OBSERVATIONS")
    target_indices = []
    for item in report.observations:
        fold = item.fold
        if fold.train_end_date >= fold.target_date:
            issues.append("TEMPORAL_LEAKAGE_BOUNDARY")
        if fold.train_end_index >= fold.target_index:
            issues.append("TRAIN_TARGET_INDEX_VIOLATION")
        if fold.target_index in target_indices:
            issues.append("DUPLICATE_TARGET_INDEX")
        target_indices.append(fold.target_index)
        if item.prediction.target_date != fold.target_date:
            issues.append("TARGET_DATE_MISMATCH")
        prediction_validation = validate_end_to_end_prediction(item.prediction)
        if not prediction_validation.is_valid:
            issues.append("INVALID_PREDICTION")
        if not item.observation_identity.startswith("end-to-end-backtest-observation-"):
            issues.append("INVALID_OBSERVATION_IDENTITY")
        if item.panel_actual_rank is not None and item.panel_actual_rank < 1:
            issues.append("INVALID_PANEL_RANK")
        if item.jodi_actual_rank is not None and item.jodi_actual_rank < 1:
            issues.append("INVALID_JODI_RANK")
    if tuple(sorted(target_indices)) != tuple(target_indices):
        issues.append("NON_CHRONOLOGICAL_TARGETS")
    if not report.report_identity.startswith("end-to-end-backtest-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return EndToEndBacktestValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def end_to_end_backtest_summary(
    report: EndToEndBacktestReport,
) -> dict[str, object]:
    validation = validate_end_to_end_backtest(report)
    return {
        "status": validation.status,
        "version": report.version,
        "dataset_identity": report.dataset_identity,
        "observations": len(report.observations),
        "panel": {
            "hit_rates": report.panel_top_k_report.hit_rates,
            "mrr": report.panel_top_k_report.mean_reciprocal_rank,
            "actual_vs_ranked": report.panel_actual_vs_ranked.report_identity,
            "performance_over_time": report.panel_performance_over_time.report_identity,
        },
        "jodi": {
            "hit_rates": report.jodi_top_k_report.hit_rates,
            "mrr": report.jodi_top_k_report.mean_reciprocal_rank,
            "actual_vs_ranked": report.jodi_actual_vs_ranked.report_identity,
            "performance_over_time": report.jodi_performance_over_time.report_identity,
        },
        "report_identity": report.report_identity,
    }


__all__ = [
    "END_TO_END_BACKTEST_VERSION",
    "VALID",
    "INVALID",
    "BacktestFold",
    "BacktestActual",
    "EndToEndBacktestObservation",
    "EndToEndBacktestReport",
    "EndToEndBacktestValidationResult",
    "build_backtest_folds",
    "run_end_to_end_backtest",
    "validate_end_to_end_backtest",
    "end_to_end_backtest_summary",
]
