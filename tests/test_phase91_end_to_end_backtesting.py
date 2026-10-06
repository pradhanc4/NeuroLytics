import dataclasses
from datetime import date, timedelta

import pytest

from analytics.end_to_end_backtesting import (
    END_TO_END_BACKTEST_VERSION,
    BacktestActual,
    build_backtest_folds,
    end_to_end_backtest_summary,
    run_end_to_end_backtest,
    validate_end_to_end_backtest,
)
from analytics.end_to_end_prediction import run_end_to_end_prediction
from database.services import HistoricalResultService
from features.feature_pipeline import build_feature_pipeline
from tests.test_phase90_full_data_to_prediction_pipeline import (
    pipeline_result,
    predictors,
)


def make_prediction(db, target_date=date(2026, 1, 5)):
    service = HistoricalResultService(db)
    feature = pipeline_result(db)
    result = run_end_to_end_prediction(
        feature,
        predictors(),
        model_identity="phase91-test-model",
        model_version="91.test",
        top_k=10,
    )
    return dataclasses.replace(result, target_date=target_date)


def dates():
    return tuple(date(2026, 1, 1) + timedelta(days=i) for i in range(7))


def actuals_from_prediction(prediction):
    panel = prediction.panel_ranking.candidates[0].panel
    jodi = prediction.jodi_ranking.candidates[0].jodi
    return BacktestActual(panel=panel, jodi=jodi, digits=(0, 1, 2))


def run_report(db, base=None):
    base = base or make_prediction(db)

    def predictor(fold):
        return dataclasses.replace(
            base,
            target_date=fold.target_date,
        )

    actuals = [actuals_from_prediction(base) for _ in dates()]
    return run_end_to_end_backtest(
        dates(),
        actuals,
        predictor,
        dataset_identity="phase91-test-dataset",
        initial_train_size=3,
        top_ks=(1, 3, 5, 10),
        period_days=2,
    )


def test_phase91_version():
    assert END_TO_END_BACKTEST_VERSION == "91.0.0"


def test_phase91_builds_expanding_temporal_folds():
    folds = build_backtest_folds(
        dates(),
        initial_train_size=3,
        test_size=1,
        step_size=1,
    )
    assert len(folds) == 4
    assert all(f.train_end_date < f.target_date for f in folds)
    assert all(f.train_end_index < f.target_index for f in folds)
    assert [f.target_index for f in folds] == [3, 4, 5, 6]


def test_phase91_rejects_non_chronological_dates():
    values = dates()
    with pytest.raises(ValueError, match="chronological"):
        build_backtest_folds(
            tuple(reversed(values)),
            initial_train_size=3,
        )


def test_phase91_runs_complete_pipeline(db):
    report = run_report(db)
    validation = validate_end_to_end_backtest(report)
    assert validation.is_valid
    assert len(report.observations) == 4
    assert report.panel_top_k_report.evaluated_observations == 4
    assert report.jodi_top_k_report.evaluated_observations == 4


def test_phase91_panel_and_jodi_hits_are_computed(db):
    report = run_report(db)
    assert dict(report.panel_top_k_report.hit_rates)[1] == 1.0
    assert dict(report.jodi_top_k_report.hit_rates)[1] == 1.0
    assert report.panel_top_k_report.mean_reciprocal_rank == 1.0
    assert report.jodi_top_k_report.mean_reciprocal_rank == 1.0


def test_phase91_actual_vs_ranked_reports_are_composed(db):
    report = run_report(db)
    assert report.panel_actual_vs_ranked.actual_available_observations == 4
    assert report.jodi_actual_vs_ranked.actual_available_observations == 4
    assert report.panel_actual_vs_ranked.mean_actual_rank == 1.0
    assert report.jodi_actual_vs_ranked.mean_actual_rank == 1.0


def test_phase91_performance_over_time_is_composed(db):
    report = run_report(db)
    assert len(report.panel_performance_over_time.periods) == 2
    assert len(report.jodi_performance_over_time.periods) == 2
    assert report.panel_performance_over_time.observation_count == 4


def test_phase91_summary_contains_backtest_outputs(db):
    summary = end_to_end_backtest_summary(run_report(db))
    assert summary["status"] == "VALID"
    assert summary["observations"] == 4
    assert "panel" in summary
    assert "jodi" in summary
    assert len(summary["panel"]["hit_rates"]) == 4
    assert len(summary["jodi"]["hit_rates"]) == 4


def test_phase91_identity_is_reproducible(db):
    base = make_prediction(db)
    first = run_report(db, base)
    second = run_report(db, base)
    assert first.report_identity == second.report_identity
    assert first.panel_top_k_report.report_identity == second.panel_top_k_report.report_identity
    assert first.jodi_top_k_report.report_identity == second.jodi_top_k_report.report_identity


def test_phase91_prediction_must_match_fold_target_date(db):
    base = make_prediction(db)
    actuals = [actuals_from_prediction(base) for _ in dates()]

    def bad_predictor(fold):
        return base

    with pytest.raises(ValueError, match="target date"):
        run_end_to_end_backtest(
            dates(),
            actuals,
            bad_predictor,
            dataset_identity="phase91-test-dataset",
            initial_train_size=3,
        )


def test_phase91_predictor_output_type_is_required(db):
    actuals = [BacktestActual(panel="000", jodi="00") for _ in dates()]

    def bad_predictor(fold):
        return object()

    with pytest.raises(TypeError, match="EndToEndPredictionResult"):
        run_end_to_end_backtest(
            dates(),
            actuals,
            bad_predictor,
            dataset_identity="phase91-test-dataset",
            initial_train_size=3,
        )


def test_phase91_temporal_boundary_cannot_be_equal():
    values = dates()
    folds = build_backtest_folds(values, initial_train_size=3)
    broken = dataclasses.replace(
        folds[0],
        train_end_date=folds[0].target_date,
    )
    assert broken.train_end_date >= broken.target_date


def test_phase91_actual_values_are_validated(db):
    base = make_prediction(db)
    actuals = [BacktestActual(panel="XX1", jodi="00") for _ in dates()]

    def predictor(fold):
        return dataclasses.replace(base, target_date=fold.target_date)

    with pytest.raises(ValueError, match="actual panel"):
        run_end_to_end_backtest(
            dates(),
            actuals,
            predictor,
            dataset_identity="phase91-test-dataset",
            initial_train_size=3,
        )


def test_phase91_missing_actual_is_a_miss_not_a_fake_hit(db):
    base = make_prediction(db)
    actuals = [
        BacktestActual(panel=None, jodi=None)
        for _ in dates()
    ]

    def predictor(fold):
        return dataclasses.replace(base, target_date=fold.target_date)

    report = run_end_to_end_backtest(
        dates(),
        actuals,
        predictor,
        dataset_identity="phase91-test-dataset",
        initial_train_size=3,
        top_ks=(1, 3),
    )
    assert report.panel_top_k_report.actual_available_observations == 0
    assert report.jodi_top_k_report.actual_available_observations == 0
    assert report.panel_top_k_report.mean_reciprocal_rank == 0.0
    assert report.jodi_top_k_report.mean_reciprocal_rank == 0.0
