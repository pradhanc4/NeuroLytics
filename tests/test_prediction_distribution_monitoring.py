from datetime import date, timedelta

import pytest

from analytics.actual_vs_ranked import ActualVsRankedObservation, ActualVsRankedReport
from analytics.prediction_distribution_monitoring import (
    DEFAULT_PERIOD_DAYS,
    DEFAULT_PROBABILITY_BINS,
    PREDICTION_DISTRIBUTION_MONITORING_VERSION,
    PredictionDistributionPeriod,
    build_prediction_distribution_monitoring_report,
    prediction_distribution_monitoring_summary,
    prediction_distribution_period,
    prediction_distribution_periods,
    validate_prediction_distribution_monitoring_report,
)


def make_source(
    first=(0.10, 0.20, 0.30, 0.40),
    second=(0.10, 0.20, 0.30, 0.40),
    ranks_first=(1, 2, 3, 4),
    ranks_second=(1, 2, 3, 4),
    source_type="panel",
):
    values = list(first) + list(second)
    ranks = list(ranks_first) + list(ranks_second)
    observations = []
    for index, (probability, rank) in enumerate(zip(values, ranks)):
        if index < len(first):
            target = date(2026, 1, 1) + timedelta(days=index)
        else:
            target = date(2026, 1, 15) + timedelta(days=index - len(first))
        actual_rank = rank
        observations.append(
            ActualVsRankedObservation(
                source_type,
                f"g{index}",
                target,
                "001",
                actual_rank,
                1.0 / actual_rank,
                ((1, actual_rank == 1),),
                ("TOP_1" if actual_rank == 1 else "TOP_3" if actual_rank <= 3 else "TOP_5"),
                probability,
                min(1.0, probability + 0.1),
            )
        )
    count = len(observations)
    return ActualVsRankedReport(
        "45.0.0",
        source_type,
        "source-45-fixture",
        tuple(observations),
        ((rank, ranks.count(rank)) for rank in sorted(set(ranks))),
        (("TOP_1", ranks.count(1)), ("TOP_5", count - ranks.count(1))),
        ((1, ranks.count(1) / count),),
        count,
        0,
        sum(ranks) / count,
        float(sorted(ranks)[count // 2]),
        sum(1.0 / rank for rank in ranks) / count,
        sum(values) / count,
        sum(min(1.0, value + 0.1) for value in values) / count,
        "actual-vs-ranked-report-fixture",
    )
def test_default_report_is_valid_and_deterministic():
    source = make_source()
    first = build_prediction_distribution_monitoring_report(source)
    second = build_prediction_distribution_monitoring_report(source)
    assert first.version == PREDICTION_DISTRIBUTION_MONITORING_VERSION
    assert first.period_days == DEFAULT_PERIOD_DAYS
    assert first.probability_bins == DEFAULT_PROBABILITY_BINS
    assert first.report_identity == second.report_identity
    assert validate_prediction_distribution_monitoring_report(first).is_valid


def test_period_snapshots_are_created():
    report = build_prediction_distribution_monitoring_report(make_source())
    assert len(report.periods) == 2
    assert report.observation_count == 8
    assert report.actual_available_observations == 8
    assert report.missed_observations == 0


def test_rank_distribution_is_preserved():
    report = build_prediction_distribution_monitoring_report(make_source())
    period = report.periods[0]
    assert period.rank_distribution == ((1, 1), (2, 1), (3, 1), (4, 1))
    assert sum(count for _, count in period.rank_distribution) == 4


def test_probability_distribution_has_fixed_bins():
    report = build_prediction_distribution_monitoring_report(make_source())
    period = report.periods[0]
    assert len(period.probability_bin_distribution) == 10
    assert sum(count for _, count in period.probability_bin_distribution) == 4
    assert period.probability_bin_distribution[0][0] == "0.00-0.10"
    assert period.probability_bin_distribution[9][0] == "0.90-1.00"


def test_probability_entropy_is_deterministic():
    report = build_prediction_distribution_monitoring_report(
        make_source(first=(0.1, 0.1, 0.1, 0.1), second=(0.1, 0.1, 0.1, 0.1))
    )
    assert report.periods[0].probability_entropy == 0.0


def test_summary_and_accessors():
    report = build_prediction_distribution_monitoring_report(make_source())
    summary = prediction_distribution_monitoring_summary(report)
    assert summary["status"] == "VALID"
    assert summary["periods"] == 2
    assert prediction_distribution_periods(report) == report.periods
    assert prediction_distribution_period(report, report.periods[0].period_start) == report.periods[0]
def test_period_lookup_rejects_unknown_period():
    report = build_prediction_distribution_monitoring_report(make_source())
    with pytest.raises(KeyError):
        prediction_distribution_period(report, date(2025, 1, 1))


def test_invalid_source_type_is_rejected():
    with pytest.raises(TypeError):
        build_prediction_distribution_monitoring_report(object())


def test_invalid_period_days_are_rejected():
    with pytest.raises(ValueError):
        build_prediction_distribution_monitoring_report(make_source(), period_days=0)


def test_invalid_probability_bins_are_rejected():
    with pytest.raises(ValueError):
        build_prediction_distribution_monitoring_report(make_source(), probability_bins=1)


def test_empty_source_report_is_rejected():
    source = make_source()
    broken = source.__class__(
        source.version, source.source_type, source.source_report_identity, (),
        source.rank_distribution, source.rank_bucket_counts, source.hit_rates,
        0, 0, None, None, 0.0, 0.0, 0.0, source.report_identity,
    )
    with pytest.raises(ValueError):
        build_prediction_distribution_monitoring_report(broken)


def test_invalid_actual_vs_ranked_source_is_rejected():
    source = make_source()
    broken = source.__class__(
        "45.0.0", "invalid", source.source_report_identity, source.observations,
        source.rank_distribution, source.rank_bucket_counts, source.hit_rates,
        source.actual_available_observations, source.missed_observations,
        source.mean_actual_rank, source.median_actual_rank,
        source.mean_reciprocal_rank, source.top_probability_mean,
        source.cumulative_probability_mean, source.report_identity,
    )
    with pytest.raises(ValueError):
        build_prediction_distribution_monitoring_report(broken)
def test_panel_and_jodi_are_supported():
    assert build_prediction_distribution_monitoring_report(
        make_source(source_type="panel")
    ).source_type == "panel"
    assert build_prediction_distribution_monitoring_report(
        make_source(source_type="jodi")
    ).source_type == "jodi"


def test_missed_observations_are_counted_in_distribution():
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
    report = build_prediction_distribution_monitoring_report(broken)
    assert report.periods[0].missed_observations == 1
    assert ("UNAVAILABLE", 1) in report.periods[0].rank_bucket_distribution


def test_zero_probability_is_supported():
    report = build_prediction_distribution_monitoring_report(
        make_source(first=(0.0, 0.0, 0.0, 0.0), second=(0.0, 0.0, 0.0, 0.0))
    )
    assert validate_prediction_distribution_monitoring_report(report).is_valid


def test_probability_one_is_supported():
    report = build_prediction_distribution_monitoring_report(
        make_source(first=(1.0, 1.0, 1.0, 1.0), second=(1.0, 1.0, 1.0, 1.0))
    )
    assert validate_prediction_distribution_monitoring_report(report).is_valid
def test_custom_period_and_bin_configuration():
    report = build_prediction_distribution_monitoring_report(
        make_source(),
        period_days=4,
        probability_bins=5,
    )
    assert len(report.periods) == 3
    assert all(len(p.probability_bin_distribution) == 5 for p in report.periods)


def test_multiple_periods_are_chronological():
    report = build_prediction_distribution_monitoring_report(
        make_source(first=(0.1, 0.2, 0.3, 0.4), second=(0.8, 0.8, 0.8, 0.8)),
        period_days=2,
    )
    starts = [period.period_start for period in report.periods]
    assert starts == sorted(starts)
    assert len(starts) == len(set(starts))


def test_leading_zero_actual_value_is_preserved():
    report = build_prediction_distribution_monitoring_report(make_source())
    assert report.source_report_identity == "actual-vs-ranked-report-fixture"


def test_report_identity_changes_with_configuration():
    source = make_source()
    first = build_prediction_distribution_monitoring_report(source, probability_bins=10)
    second = build_prediction_distribution_monitoring_report(source, probability_bins=5)
    third = build_prediction_distribution_monitoring_report(source, period_days=4)
    assert first.report_identity != second.report_identity
    assert first.report_identity != third.report_identity


def test_validation_rejects_bad_identity():
    report = build_prediction_distribution_monitoring_report(make_source())
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.probability_bins, report.periods,
        report.observation_count, report.actual_available_observations,
        report.missed_observations, "wrong",
    )
    result = validate_prediction_distribution_monitoring_report(broken)
    assert result.status == "INVALID"
    assert "INVALID_REPORT_IDENTITY" in result.issues
def test_validation_rejects_count_mismatch():
    report = build_prediction_distribution_monitoring_report(make_source())
    period = report.periods[0]
    broken_period = PredictionDistributionPeriod(
        period.period_start, period.period_end, period.observation_count,
        period.actual_available_observations + 1, period.missed_observations,
        period.rank_distribution, period.rank_bucket_distribution,
        period.probability_bin_distribution, period.top_probability_mean,
        period.cumulative_probability_mean, period.probability_entropy,
    )
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.probability_bins,
        (broken_period,) + report.periods[1:],
        report.observation_count, report.actual_available_observations,
        report.missed_observations, report.report_identity,
    )
    result = validate_prediction_distribution_monitoring_report(broken)
    assert result.status == "INVALID"
    assert "PERIOD_COUNT_MISMATCH" in result.issues


def test_validation_rejects_invalid_report_type():
    result = validate_prediction_distribution_monitoring_report(object())
    assert result.status == "INVALID"
    assert result.issues == ("INVALID_REPORT_TYPE",)


def test_distribution_monitoring_does_not_classify_drift():
    report = build_prediction_distribution_monitoring_report(
        make_source(first=(0.1, 0.1, 0.1, 0.1), second=(0.9, 0.9, 0.9, 0.9))
    )
    assert not hasattr(report, "drifted")
    assert report.periods[1].top_probability_mean > report.periods[0].top_probability_mean


def test_summary_contains_no_action_fields():
    report = build_prediction_distribution_monitoring_report(make_source())
    summary = prediction_distribution_monitoring_summary(report)
    assert "retrain" not in summary
    assert "promote" not in summary
    assert "rollback" not in summary
