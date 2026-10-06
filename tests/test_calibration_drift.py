from datetime import date, timedelta

import pytest

from analytics.actual_vs_ranked import (
    ActualVsRankedObservation,
    ActualVsRankedReport,
)
from analytics.calibration_drift import (
    CALIBRATION_DRIFT_VERSION,
    DEFAULT_BINS,
    DEFAULT_PERIOD_DAYS,
    CalibrationDriftRule,
    build_calibration_drift_report,
    calibration_drift_observations,
    calibration_drift_periods,
    calibration_drift_summary,
    validate_calibration_drift_report,
)


def make_source(
    probabilities=(0.1, 0.2, 0.8, 0.9),
    outcomes=(False, False, True, True),
    second_probabilities=(0.1, 0.2, 0.8, 0.9),
    second_outcomes=(False, False, True, True),
    source_type="panel",
):
    observations = []
    groups = [
        (date(2026, 1, 1), probabilities, outcomes),
        (date(2026, 1, 15), second_probabilities, second_outcomes),
    ]
    index = 0
    for start, probs, results in groups:
        for offset, (probability, hit) in enumerate(zip(probs, results)):
            target = start + timedelta(days=offset)
            rank = 1 if hit else 2
            observations.append(
                ActualVsRankedObservation(
                    source_type,
                    f"g{index}",
                    target,
                    "001",
                    rank,
                    1.0 / rank,
                    ((1, hit),),
                    "TOP_1" if hit else "TOP_3",
                    probability,
                    min(1.0, probability + 0.1),
                )
            )
            index += 1
    return ActualVsRankedReport(
        "45.0.0",
        source_type,
        "source-45-fixture",
        tuple(observations),
        ((1, sum(outcomes) + sum(second_outcomes)), (2, len(observations) - sum(outcomes) - sum(second_outcomes))),
        (("TOP_1", sum(outcomes) + sum(second_outcomes)), ("TOP_3", len(observations) - sum(outcomes) - sum(second_outcomes))),
        ((1, 0.5),),
        len(observations),
        0,
        1.5,
        1.5,
        0.75,
        sum(probabilities + second_probabilities) / len(observations),
        0.6,
        "actual-vs-ranked-report-fixture",
    )


def test_default_report_is_valid_and_deterministic():
    source = make_source()
    first = build_calibration_drift_report(source)
    second = build_calibration_drift_report(source)
    assert first.version == CALIBRATION_DRIFT_VERSION
    assert first.period_days == DEFAULT_PERIOD_DAYS
    assert first.bin_count == DEFAULT_BINS
    assert first.report_identity == second.report_identity
    assert validate_calibration_drift_report(first).is_valid


def test_two_periods_and_metrics_are_created():
    report = build_calibration_drift_report(make_source())
    assert len(report.periods) == 2
    assert len(report.observations) == 3
    assert report.drifted is False


def test_calibration_period_metrics_are_bounded():
    report = build_calibration_drift_report(make_source())
    for period in report.periods:
        assert 0 <= period.mean_predicted_probability <= 1
        assert 0 <= period.empirical_hit_rate <= 1
        assert -1 <= period.calibration_gap <= 1
        assert 0 <= period.brier_score <= 1
        assert 0 <= period.expected_calibration_error <= 1


def test_calibration_bins_have_fixed_cardinality():
    report = build_calibration_drift_report(make_source())
    assert all(len(period.bins) == DEFAULT_BINS for period in report.periods)
    assert all(
        sum(item.observation_count for item in period.bins)
        == period.calibration_observation_count
        for period in report.periods
    )


def test_perfectly_calibrated_fixture_has_zero_ece():
    report = build_calibration_drift_report(
        make_source(
            probabilities=(0.0, 0.0, 1.0, 1.0),
            outcomes=(False, False, True, True),
            second_probabilities=(0.0, 0.0, 1.0, 1.0),
            second_outcomes=(False, False, True, True),
        )
    )
    assert report.periods[0].expected_calibration_error == 0.0
    assert report.periods[1].expected_calibration_error == 0.0
    assert report.periods[0].brier_score == 0.0


def test_miscalibration_is_detected_when_threshold_is_crossed():
    report = build_calibration_drift_report(
        make_source(
            probabilities=(0.1, 0.1, 0.1, 0.1),
            outcomes=(False, False, True, True),
            second_probabilities=(0.9, 0.9, 0.9, 0.9),
            second_outcomes=(False, False, True, True),
        )
    )
    assert report.drifted
    assert "calibration_gap" in report.drifted_metrics


def test_custom_rule_threshold_controls_drift():
    source = make_source(
        probabilities=(0.1, 0.1, 0.1, 0.1),
        outcomes=(False, False, True, True),
        second_probabilities=(0.2, 0.2, 0.2, 0.2),
        second_outcomes=(False, False, True, True),
    )
    low = build_calibration_drift_report(
        source,
        rules=(CalibrationDriftRule("mean_predicted_probability", 0.05),),
    )
    high = build_calibration_drift_report(
        source,
        rules=(CalibrationDriftRule("mean_predicted_probability", 0.20),),
    )
    assert low.drifted
    assert not high.drifted


def test_all_supported_rule_metrics():
    rules = tuple(
        CalibrationDriftRule(metric, 0.05)
        for metric in (
            "expected_calibration_error",
            "brier_score",
            "calibration_gap",
            "mean_predicted_probability",
            "empirical_hit_rate",
        )
    )
    report = build_calibration_drift_report(make_source(), rules=rules)
    assert len(report.observations) == 5


def test_summary_and_accessors():
    report = build_calibration_drift_report(make_source())
    summary = calibration_drift_summary(report)
    assert summary["status"] == "VALID"
    assert summary["periods"] == 2
    assert calibration_drift_periods(report) == report.periods
    assert calibration_drift_observations(report) == report.observations
    assert len(calibration_drift_observations(report, "brier_score")) == 1


def test_panel_and_jodi_are_supported():
    assert build_calibration_drift_report(make_source(source_type="panel")).source_type == "panel"
    assert build_calibration_drift_report(make_source(source_type="jodi")).source_type == "jodi"


def test_zero_and_one_probabilities_are_supported():
    report = build_calibration_drift_report(
        make_source(
            probabilities=(0.0, 0.0, 1.0, 1.0),
            outcomes=(False, False, True, True),
            second_probabilities=(0.0, 0.0, 1.0, 1.0),
            second_outcomes=(False, False, True, True),
        )
    )
    assert validate_calibration_drift_report(report).is_valid


def test_missed_observations_are_excluded_from_calibration():
    source = make_source()
    item = source.observations[0]
    replaced = item.__class__(
        item.source_type, item.group_id, item.target_date, item.actual_value,
        None, 0.0, item.hit_at_k, "UNAVAILABLE",
        item.top_probability, item.cumulative_probability_at_max_k,
    )
    observations = (replaced,) + source.observations[1:]
    broken = source.__class__(
        source.version, source.source_type, source.source_report_identity,
        observations, source.rank_distribution, source.rank_bucket_counts,
        source.hit_rates, 7, 1, source.mean_actual_rank,
        source.median_actual_rank, source.mean_reciprocal_rank,
        source.top_probability_mean, source.cumulative_probability_mean,
        source.report_identity,
    )
    report = build_calibration_drift_report(broken)
    assert report.periods[0].missed_observations == 1
    assert report.periods[0].calibration_observation_count == 3


def test_custom_periods_are_supported():
    report = build_calibration_drift_report(make_source(), period_days=4)
    assert len(report.periods) == 3


def test_custom_bin_count_is_supported():
    report = build_calibration_drift_report(make_source(), bin_count=5)
    assert all(len(period.bins) == 5 for period in report.periods)


def test_invalid_source_type_is_rejected():
    with pytest.raises(TypeError):
        build_calibration_drift_report(object())


def test_invalid_period_days_are_rejected():
    with pytest.raises(ValueError):
        build_calibration_drift_report(make_source(), period_days=0)


def test_invalid_bin_count_is_rejected():
    with pytest.raises(ValueError):
        build_calibration_drift_report(make_source(), bin_count=1)


def test_duplicate_rules_are_rejected():
    with pytest.raises(ValueError):
        build_calibration_drift_report(
            make_source(),
            rules=(
                CalibrationDriftRule("brier_score", 0.05),
                CalibrationDriftRule("brier_score", 0.10),
            ),
        )


def test_unknown_rule_is_rejected():
    with pytest.raises(ValueError):
        build_calibration_drift_report(
            make_source(),
            rules=(CalibrationDriftRule("unknown", 0.05),),
        )


def test_invalid_threshold_is_rejected():
    with pytest.raises(ValueError):
        build_calibration_drift_report(
            make_source(),
            rules=(CalibrationDriftRule("brier_score", 0.0),),
        )


def test_single_period_is_rejected():
    source = make_source()
    observations = tuple(
        item for item in source.observations if item.target_date < date(2026, 1, 8)
    )
    broken = source.__class__(
        source.version, source.source_type, source.source_report_identity,
        observations, source.rank_distribution, source.rank_bucket_counts,
        source.hit_rates, len(observations), 0, source.mean_actual_rank,
        source.median_actual_rank, source.mean_reciprocal_rank,
        source.top_probability_mean, source.cumulative_probability_mean,
        source.report_identity,
    )
    with pytest.raises(ValueError):
        build_calibration_drift_report(broken)


def test_validation_rejects_bad_identity():
    report = build_calibration_drift_report(make_source())
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.bin_count, report.rules, report.periods,
        report.observations, report.drifted_metrics, report.drifted_periods,
        report.drifted, "wrong",
    )
    result = validate_calibration_drift_report(broken)
    assert result.status == "INVALID"
    assert "INVALID_REPORT_IDENTITY" in result.issues


def test_validation_rejects_flag_mismatch():
    report = build_calibration_drift_report(make_source())
    observation = report.observations[0]
    broken_observation = observation.__class__(
        observation.metric, observation.baseline_period_start,
        observation.comparison_period_start, observation.baseline_value,
        observation.comparison_value, observation.absolute_change,
        observation.threshold, not observation.drifted,
    )
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.bin_count, report.rules, report.periods,
        (broken_observation,) + report.observations[1:],
        report.drifted_metrics, report.drifted_periods, report.drifted,
        report.report_identity,
    )
    result = validate_calibration_drift_report(broken)
    assert result.status == "INVALID"
    assert "DRIFT_FLAG_MISMATCH" in result.issues


def test_validation_rejects_period_count_mismatch():
    report = build_calibration_drift_report(make_source())
    period = report.periods[0]
    broken_period = period.__class__(
        period.period_start, period.period_end, period.observation_count,
        period.actual_available_observations + 1, period.missed_observations,
        period.calibration_observation_count, period.mean_predicted_probability,
        period.empirical_hit_rate, period.calibration_gap, period.brier_score,
        period.expected_calibration_error, period.bins,
    )
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.bin_count, report.rules,
        (broken_period,) + report.periods[1:], report.observations,
        report.drifted_metrics, report.drifted_periods, report.drifted,
        report.report_identity,
    )
    result = validate_calibration_drift_report(broken)
    assert result.status == "INVALID"
    assert "PERIOD_COUNT_MISMATCH" in result.issues


def test_determinism_changes_with_threshold():
    source = make_source()
    first = build_calibration_drift_report(
        source,
        rules=(CalibrationDriftRule("brier_score", 0.05),),
    )
    second = build_calibration_drift_report(
        source,
        rules=(CalibrationDriftRule("brier_score", 0.10),),
    )
    assert first.report_identity != second.report_identity


def test_report_contains_no_retraining_or_promotion_fields():
    report = build_calibration_drift_report(make_source())
    summary = calibration_drift_summary(report)
    assert "retrain" not in summary
    assert "promote" not in summary
    assert "rollback" not in summary


def test_calibration_drift_uses_top_one_outcome():
    report = build_calibration_drift_report(
        make_source(
            probabilities=(0.9, 0.9, 0.9, 0.9),
            outcomes=(True, False, False, False),
            second_probabilities=(0.9, 0.9, 0.9, 0.9),
            second_outcomes=(True, False, False, False),
        )
    )
    assert report.periods[0].empirical_hit_rate == 0.25
    assert report.periods[0].mean_predicted_probability == 0.9
    assert report.periods[0].calibration_gap == 0.65


def test_brier_score_matches_manual_calculation():
    report = build_calibration_drift_report(
        make_source(
            probabilities=(0.0, 1.0, 0.0, 1.0),
            outcomes=(False, False, True, True),
            second_probabilities=(0.0, 1.0, 0.0, 1.0),
            second_outcomes=(False, False, True, True),
        )
    )
    assert report.periods[0].brier_score == 0.5


def test_ece_matches_single_populated_bin_gap():
    report = build_calibration_drift_report(
        make_source(
            probabilities=(0.2, 0.2, 0.2, 0.2),
            outcomes=(False, False, True, True),
            second_probabilities=(0.2, 0.2, 0.2, 0.2),
            second_outcomes=(False, False, True, True),
        )
    )
    assert report.periods[0].expected_calibration_error == 0.3


def test_no_empty_periods_are_fabricated():
    report = build_calibration_drift_report(make_source())
    assert len(report.periods) == 2
    assert report.periods[0].period_start == date(2026, 1, 1)
    assert report.periods[1].period_start == date(2026, 1, 15)


def test_drifted_periods_preserve_metric_and_date():
    report = build_calibration_drift_report(
        make_source(
            probabilities=(0.1, 0.1, 0.1, 0.1),
            outcomes=(False, False, True, True),
            second_probabilities=(0.9, 0.9, 0.9, 0.9),
            second_outcomes=(False, False, True, True),
        )
    )
    assert all(metric for metric, _ in report.drifted_periods)
    assert all(period == date(2026, 1, 15) for _, period in report.drifted_periods)


def test_validation_rejects_invalid_report_type():
    result = validate_calibration_drift_report(object())
    assert result.status == "INVALID"
    assert result.issues == ("INVALID_REPORT_TYPE",)
