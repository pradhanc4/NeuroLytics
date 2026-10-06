from datetime import date, timedelta

import pytest

from analytics.actual_vs_ranked import ActualVsRankedObservation, ActualVsRankedReport
from analytics.ranking_drift import (
    RANKING_DRIFT_VERSION,
    DEFAULT_METRICS,
    DEFAULT_PERIOD_DAYS,
    RankingDriftRule,
    build_ranking_drift_report,
    ranking_drift_observations,
    ranking_drift_periods,
    ranking_drift_summary,
    validate_ranking_drift_report,
)


def make_source(
    first_ranks=(1, 2, 3, 4, 5),
    second_ranks=(1, 2, 3, 4, 5),
    source_type="panel",
):
    observations = []
    index = 0
    for start, ranks in (
        (date(2026, 1, 1), first_ranks),
        (date(2026, 1, 15), second_ranks),
    ):
        for offset, rank in enumerate(ranks):
            target = start + timedelta(days=offset)
            observations.append(
                ActualVsRankedObservation(
                    source_type,
                    f"g{index}",
                    target,
                    "001",
                    rank,
                    1.0 / rank,
                    tuple((k, rank <= k) for k in (1, 3, 5, 10)),
                    "TOP_1" if rank == 1 else
                    "TOP_3" if rank <= 3 else
                    "TOP_5" if rank <= 5 else
                    "TOP_10" if rank <= 10 else
                    "OUTSIDE_TOP_10",
                    0.1,
                    0.5,
                )
            )
            index += 1
    total = len(observations)
    return ActualVsRankedReport(
        "45.0.0",
        source_type,
        "actual-vs-ranked-fixture",
        tuple(observations),
        tuple(),
        tuple(),
        ((1, 0.2), (3, 0.6), (5, 1.0), (10, 1.0)),
        total,
        0,
        3.0,
        3.0,
        0.4,
        0.1,
        0.5,
        "actual-vs-ranked-report-fixture",
    )


def test_default_report_is_valid_and_deterministic():
    source = make_source()
    first = build_ranking_drift_report(source)
    second = build_ranking_drift_report(source)
    assert first.version == RANKING_DRIFT_VERSION
    assert first.period_days == DEFAULT_PERIOD_DAYS
    assert first.report_identity == second.report_identity
    assert validate_ranking_drift_report(first).is_valid


def test_default_metrics_and_periods_are_created():
    report = build_ranking_drift_report(make_source())
    assert tuple(rule.metric for rule in report.rules) == DEFAULT_METRICS
    assert len(report.periods) == 2
    assert len(report.observations) == len(DEFAULT_METRICS)


def test_rank_rates_and_means_are_calculated():
    report = build_ranking_drift_report(make_source())
    period = report.periods[0]
    assert period.top_1_rate == 0.2
    assert period.top_3_rate == 0.6
    assert period.top_5_rate == 1.0
    assert period.top_10_rate == 1.0
    assert period.mean_actual_rank == 3.0


def test_rank_distribution_is_fixed_and_reconciles():
    report = build_ranking_drift_report(make_source(), rank_max=10)
    period = report.periods[0]
    assert len(period.distribution.rank_counts) == 10
    assert sum(count for _, count in period.distribution.rank_counts) == 5
    assert abs(sum(value for _, value in period.distribution.rank_probabilities) - 1.0) < 1e-12


def test_bucket_distribution_is_fixed():
    report = build_ranking_drift_report(make_source())
    buckets = dict(report.periods[0].distribution.bucket_counts)
    assert buckets["TOP_1"] == 1
    assert buckets["TOP_3"] == 2
    assert buckets["TOP_5"] == 2
    assert buckets["TOP_10"] == 0
    assert buckets["OUTSIDE_TOP_10"] == 0


def test_stable_distribution_has_no_drift():
    report = build_ranking_drift_report(make_source())
    assert report.drifted is False
    assert report.drifted_metrics == ()


def test_top_rate_drift_is_detected():
    report = build_ranking_drift_report(
        make_source(
            first_ranks=(1, 1, 1, 1, 1),
            second_ranks=(5, 5, 5, 5, 5),
        ),
        rules=(RankingDriftRule("top_1_rate", 0.05),),
    )
    assert report.drifted
    assert report.drifted_metrics == ("top_1_rate",)


def test_mean_rank_drift_is_detected():
    report = build_ranking_drift_report(
        make_source(
            first_ranks=(1, 1, 1, 1, 1),
            second_ranks=(10, 10, 10, 10, 10),
        ),
        rules=(RankingDriftRule("mean_actual_rank", 1.0),),
    )
    assert report.drifted
    assert report.drifted_metrics == ("mean_actual_rank",)


def test_rank_distribution_psi_is_detected():
    report = build_ranking_drift_report(
        make_source(
            first_ranks=(1, 1, 1, 1, 1),
            second_ranks=(5, 5, 5, 5, 5),
        ),
        rules=(RankingDriftRule("rank_distribution_psi", 0.05),),
    )
    assert report.drifted
    assert report.drifted_metrics == ("rank_distribution_psi",)


def test_custom_threshold_controls_drift():
    source = make_source(
        first_ranks=(1, 1, 1, 1, 1),
        second_ranks=(2, 2, 2, 2, 2),
    )
    low = build_ranking_drift_report(
        source,
        rules=(RankingDriftRule("top_1_rate", 0.05),),
    )
    high = build_ranking_drift_report(
        source,
        rules=(RankingDriftRule("top_1_rate", 1.01),),
    )
    assert low.drifted
    assert not high.drifted


def test_all_supported_metrics_are_accepted():
    rules = tuple(RankingDriftRule(metric, 0.05) for metric in DEFAULT_METRICS)
    report = build_ranking_drift_report(make_source(), rules=rules)
    assert len(report.observations) == len(DEFAULT_METRICS)


def test_summary_and_accessors():
    report = build_ranking_drift_report(make_source())
    summary = ranking_drift_summary(report)
    assert summary["status"] == "VALID"
    assert summary["periods"] == 2
    assert ranking_drift_periods(report) == report.periods
    assert ranking_drift_observations(report) == report.observations
    assert len(ranking_drift_observations(report, "top_1_rate")) == 1


def test_panel_and_jodi_are_supported():
    assert build_ranking_drift_report(make_source(source_type="panel")).source_type == "panel"
    assert build_ranking_drift_report(make_source(source_type="jodi")).source_type == "jodi"


def test_missing_actuals_are_excluded_from_rank_metrics():
    source = make_source()
    item = source.observations[0]
    replacement = ActualVsRankedObservation(
        item.source_type, item.group_id, item.target_date, item.actual_value,
        None, 0.0, item.hit_at_k, "UNAVAILABLE",
        item.top_probability, item.cumulative_probability_at_max_k,
    )
    observations = (replacement,) + source.observations[1:]
    broken = source.__class__(
        source.version, source.source_type, source.source_report_identity,
        observations, source.rank_distribution, source.rank_bucket_counts,
        source.hit_rates, 9, 1, source.mean_actual_rank,
        source.median_actual_rank, source.mean_reciprocal_rank,
        source.top_probability_mean, source.cumulative_probability_mean,
        source.report_identity,
    )
    report = build_ranking_drift_report(broken)
    assert report.periods[0].missed_observations == 1
    assert report.periods[0].actual_available_observations == 4


def test_custom_period_size():
    report = build_ranking_drift_report(make_source(), period_days=4)
    assert len(report.periods) == 4


def test_custom_rank_max():
    report = build_ranking_drift_report(make_source(), rank_max=5)
    assert len(report.periods[0].distribution.rank_counts) == 5


def test_invalid_source_type_is_rejected():
    with pytest.raises(TypeError):
        build_ranking_drift_report(object())


def test_invalid_period_days_are_rejected():
    with pytest.raises(ValueError):
        build_ranking_drift_report(make_source(), period_days=0)


def test_invalid_rank_max_is_rejected():
    with pytest.raises(ValueError):
        build_ranking_drift_report(make_source(), rank_max=0)


def test_empty_rules_are_rejected():
    with pytest.raises(ValueError):
        build_ranking_drift_report(make_source(), rules=())


def test_duplicate_rules_are_rejected():
    with pytest.raises(ValueError):
        build_ranking_drift_report(
            make_source(),
            rules=(
                RankingDriftRule("top_1_rate"),
                RankingDriftRule("top_1_rate"),
            ),
        )


def test_unknown_metric_is_rejected():
    with pytest.raises(ValueError):
        build_ranking_drift_report(
            make_source(),
            rules=(RankingDriftRule("unknown_metric"),),
        )


def test_invalid_threshold_is_rejected():
    with pytest.raises(ValueError):
        build_ranking_drift_report(
            make_source(),
            rules=(RankingDriftRule("top_1_rate", 0),),
        )


def test_single_period_is_rejected():
    source = make_source()
    observations = tuple(
        item for item in source.observations
        if item.target_date < date(2026, 1, 8)
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
        build_ranking_drift_report(broken)


def test_invalid_identity_is_rejected():
    report = build_ranking_drift_report(make_source())
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.rank_max, report.rules, report.periods,
        report.observations, report.drifted_metrics, report.drifted_periods,
        report.drifted, "wrong",
    )
    result = validate_ranking_drift_report(broken)
    assert result.status == "INVALID"
    assert "INVALID_REPORT_IDENTITY" in result.issues


def test_drift_flag_mismatch_is_rejected():
    report = build_ranking_drift_report(make_source())
    item = report.observations[0]
    broken_item = item.__class__(
        item.metric, item.baseline_period_start,
        item.comparison_period_start, item.baseline_value,
        item.comparison_value, item.absolute_change,
        item.threshold, not item.drifted,
    )
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.rank_max, report.rules, report.periods,
        (broken_item,) + report.observations[1:],
        report.drifted_metrics, report.drifted_periods,
        report.drifted, report.report_identity,
    )
    result = validate_ranking_drift_report(broken)
    assert result.status == "INVALID"
    assert "DRIFT_FLAG_MISMATCH" in result.issues


def test_period_count_mismatch_is_rejected():
    report = build_ranking_drift_report(make_source())
    period = report.periods[0]
    broken_period = period.__class__(
        period.period_start, period.period_end, period.observation_count,
        period.actual_available_observations + 1, period.missed_observations,
        period.top_1_rate, period.top_3_rate, period.top_5_rate,
        period.top_10_rate, period.mean_actual_rank,
        period.mean_reciprocal_rank, period.distribution,
    )
    broken = report.__class__(
        report.version, report.source_type, report.source_report_identity,
        report.period_days, report.rank_max, report.rules,
        (broken_period,) + report.periods[1:], report.observations,
        report.drifted_metrics, report.drifted_periods,
        report.drifted, report.report_identity,
    )
    result = validate_ranking_drift_report(broken)
    assert result.status == "INVALID"
    assert "PERIOD_COUNT_MISMATCH" in result.issues


def test_no_retraining_or_promotion_fields_are_exposed():
    report = build_ranking_drift_report(make_source())
    summary = ranking_drift_summary(report)
    assert "retrain" not in summary
    assert "promote" not in summary
    assert "rollback" not in summary


def test_deterministic_identity_changes_with_configuration():
    source = make_source()
    first = build_ranking_drift_report(
        source, rules=(RankingDriftRule("top_1_rate", 0.05),)
    )
    second = build_ranking_drift_report(
        source, rules=(RankingDriftRule("top_1_rate", 0.10),)
    )
    assert first.report_identity != second.report_identity


def test_rank_distribution_preserves_zero_counts():
    report = build_ranking_drift_report(make_source(), rank_max=10)
    counts = dict(report.periods[0].distribution.rank_counts)
    assert counts[6] == 0
    assert counts[10] == 0


def test_outside_top_ten_is_preserved_in_bucket_distribution():
    report = build_ranking_drift_report(
        make_source(first_ranks=(11, 12, 13, 14, 15))
    )
    buckets = dict(report.periods[0].distribution.bucket_counts)
    assert buckets["OUTSIDE_TOP_10"] == 5


def test_rank_max_caps_distribution_without_losing_observation_count():
    report = build_ranking_drift_report(
        make_source(first_ranks=(11, 12, 13, 14, 15)),
        rank_max=5,
    )
    counts = dict(report.periods[0].distribution.rank_counts)
    assert counts[5] == 5
    assert sum(counts.values()) == 5


def test_drifted_periods_preserve_metric_and_date():
    report = build_ranking_drift_report(
        make_source(
            first_ranks=(1, 1, 1, 1, 1),
            second_ranks=(10, 10, 10, 10, 10),
        ),
        rules=(RankingDriftRule("top_1_rate", 0.05),),
    )
    assert report.drifted_periods == (("top_1_rate", date(2026, 1, 15)),)


def test_validation_rejects_invalid_report_type():
    result = validate_ranking_drift_report(object())
    assert result.status == "INVALID"
    assert result.issues == ("INVALID_REPORT_TYPE",)


def test_mean_reciprocal_rank_is_calculated():
    report = build_ranking_drift_report(make_source())
    assert abs(report.periods[0].mean_reciprocal_rank - 0.45666666666666667) < 1e-12


def test_multiple_comparison_periods_are_all_compared_to_baseline():
    source = make_source()
    extra = tuple(
        ActualVsRankedObservation(
            "panel", f"x{i}", date(2026, 2, 1) + timedelta(days=i),
            "001", 10, 0.1, ((1, False), (3, False), (5, False), (10, True)),
            "TOP_10", 0.1, 0.2
        )
        for i in range(5)
    )
    expanded = source.__class__(
        source.version, source.source_type, source.source_report_identity,
        source.observations + extra, source.rank_distribution, source.rank_bucket_counts,
        source.hit_rates, 15, 0, source.mean_actual_rank, source.median_actual_rank,
        source.mean_reciprocal_rank, source.top_probability_mean,
        source.cumulative_probability_mean, source.report_identity,
    )
    report = build_ranking_drift_report(
        expanded, rules=(RankingDriftRule("top_1_rate", 0.05),)
    )
    assert len(report.observations) == len(report.periods) - 1
