from dataclasses import replace
from datetime import date, timedelta

import pytest

from analytics.actual_vs_ranked import build_actual_vs_ranked_report
from analytics.performance_over_time import (
    INVALID,
    PERFORMANCE_OVER_TIME_VERSION,
    VALID,
    build_performance_over_time_report,
    performance_over_time_summary,
    validate_performance_over_time_report,
)
from analytics.top_k_framework import TopKEvaluationReport, TopKEvaluationRow


def row(group, target_date, rank, source="panel"):
    return TopKEvaluationRow(
        source,
        group,
        target_date,
        "045" if source == "panel" else "05",
        rank,
        (
            (1, rank == 1),
            (3, rank is not None and rank <= 3),
            (5, rank is not None and rank <= 5),
        ),
        1.0 / rank if rank else 0.0,
        0.2 + (rank or 0) * 0.02,
        0.5 + (rank or 0) * 0.02,
    )


def source(rows):
    return TopKEvaluationReport(
        "44.0.0",
        "panel",
        "top-k-evaluation-report-phase44-source",
        (1, 3, 5),
        tuple(rows),
        ((1, 0.5), (3, 0.75), (5, 1.0)),
        0.75,
        len(rows),
        sum(item.actual_rank is not None for item in rows),
        "top-k-evaluation-report-phase44-source",
    )


def actual_report(rows):
    return build_actual_vs_ranked_report(source(rows))


def test_version():
    assert PERFORMANCE_OVER_TIME_VERSION == "46.0.0"


def test_builds_report():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), 3),
        ])
    )
    assert report.source_type == "panel"
    assert report.observation_count == 2
    assert len(report.periods) == 1


def test_default_period_is_seven_days():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    assert report.period_days == 7


def test_custom_period_days():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)]),
        period_days=3,
    )
    assert report.period_days == 3


def test_period_boundaries_are_deterministic():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 3), 2),
            row("g3", date(2026, 9, 4), 3),
        ]),
        period_days=3,
    )
    assert [p.period_start for p in report.periods] == [
        date(2026, 9, 1),
        date(2026, 9, 4),
    ]


def test_period_end_matches_period_size():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)]),
        period_days=5,
    )
    assert report.periods[0].period_end == date(2026, 9, 5)


def test_period_observation_count():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), 2),
        ])
    )
    assert report.periods[0].observation_count == 2


def test_period_actual_count():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), None),
        ])
    )
    assert report.periods[0].actual_available_observations == 1


def test_period_missed_count():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), None),
        ])
    )
    assert report.periods[0].missed_observations == 1


def test_period_mean_rank():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), 3),
        ])
    )
    assert report.periods[0].mean_actual_rank == pytest.approx(2.0)


def test_period_hit_rates():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), 3),
        ])
    )
    assert dict(report.periods[0].hit_rates) == {1: 0.5, 3: 1.0, 5: 1.0}


def test_period_mrr():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), 2),
        ])
    )
    assert report.periods[0].mean_reciprocal_rank == pytest.approx(0.75)


def test_period_top_probability_mean():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), 3),
        ])
    )
    assert report.periods[0].mean_top_probability == pytest.approx(0.24)


def test_period_cumulative_probability_mean():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), 3),
        ])
    )
    assert report.periods[0].mean_cumulative_probability == pytest.approx(0.54)


def test_period_miss_rate():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 2), None),
        ])
    )
    assert report.periods[0].miss_rate == pytest.approx(0.5)


def test_hit_k_can_be_selected():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)]),
        hit_ks=(1, 3),
    )
    assert dict(report.periods[0].hit_rates) == {1: 1.0, 3: 1.0}


def test_periods_are_chronological():
    report = build_performance_over_time_report(
        actual_report([
            row("g2", date(2026, 9, 9), 2),
            row("g1", date(2026, 9, 1), 1),
        ])
    )
    assert list(report.periods[0].period_start for _ in [0]) == [date(2026, 9, 1)]


def test_multiple_periods_create_trends():
    rows = [
        row("g1", date(2026, 9, 1), 1),
        row("g2", date(2026, 9, 8), 3),
        row("g3", date(2026, 9, 15), 5),
    ]
    report = build_performance_over_time_report(actual_report(rows))
    assert len(report.periods) == 3
    assert {item.metric for item in report.trends} >= {
        "mean_actual_rank", "mean_reciprocal_rank", "hit_at_1"
    }


def test_rank_trend_increases_when_rank_worsens():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 8), 3),
        ])
    )
    trend = next(item for item in report.trends if item.metric == "mean_actual_rank")
    assert trend.direction == "IMPROVING"


def test_mrr_trend_declines_when_rank_worsens():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 8), 3),
        ])
    )
    trend = next(item for item in report.trends if item.metric == "mean_reciprocal_rank")
    assert trend.direction == "DECLINING"


def test_stable_trend():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 2),
            row("g2", date(2026, 9, 8), 2),
        ])
    )
    trend = next(item for item in report.trends if item.metric == "mean_actual_rank")
    assert trend.direction == "STABLE"
    assert trend.slope_per_day == pytest.approx(0.0)


def test_trend_change_is_first_to_last():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 8), 3),
        ])
    )
    trend = next(item for item in report.trends if item.metric == "mean_actual_rank")
    assert trend.change == pytest.approx(2.0)


def test_trend_slope_is_per_day():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 8), 3),
        ])
    )
    trend = next(item for item in report.trends if item.metric == "mean_actual_rank")
    assert trend.slope_per_day == pytest.approx(2.0 / 7.0)


def test_single_period_has_zero_slope():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    assert all(item.slope_per_day == 0.0 for item in report.trends)


def test_panel_source_supported():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    assert report.source_type == "panel"


def test_jodi_source_supported():
    jodi = TopKEvaluationRow(
        "jodi", "j1", date(2026, 9, 1), "05", 2,
        ((1, False), (3, True), (5, True)), 0.5, 0.4, 0.7,
    )
    jodi_source = replace(
        source([jodi]), source_type="jodi"
    )
    report = build_performance_over_time_report(
        build_actual_vs_ranked_report(jodi_source)
    )
    assert report.source_type == "jodi"


def test_zero_digit_is_preserved_through_source():
    source_report = replace(source([row("g1", date(2026, 9, 1), 1)]))
    source_report = replace(
        source_report,
        rows=(replace(source_report.rows[0], actual_value="000"),),
    )
    actual = build_actual_vs_ranked_report(source_report)
    report = build_performance_over_time_report(actual)
    assert report.source_report_identity == actual.report_identity


def test_source_lineage_is_preserved():
    actual = actual_report([row("g1", date(2026, 9, 1), 1)])
    report = build_performance_over_time_report(actual)
    assert report.source_report_identity == actual.report_identity


def test_report_identity_is_deterministic():
    actual = actual_report([row("g1", date(2026, 9, 1), 1)])
    assert build_performance_over_time_report(actual) == build_performance_over_time_report(actual)


def test_report_identity_changes_with_period_size():
    actual = actual_report([row("g1", date(2026, 9, 1), 1), row("g2", date(2026, 9, 8), 2)])
    a = build_performance_over_time_report(actual, period_days=7)
    b = build_performance_over_time_report(actual, period_days=3)
    assert a.report_identity != b.report_identity


def test_validation_accepts_report():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    result = validate_performance_over_time_report(report)
    assert result.status == VALID
    assert result.issues == ()


def test_summary_api():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    summary = performance_over_time_summary(report)
    assert summary["status"] == VALID
    assert summary["periods"] == 1
    assert summary["observations"] == 1


def test_validation_rejects_bad_version():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    result = validate_performance_over_time_report(replace(report, version="bad"))
    assert result.status == INVALID
    assert "INVALID_VERSION" in result.issues


def test_validation_rejects_bad_period_length():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    bad = replace(
        report,
        periods=(replace(report.periods[0], period_end=date(2026, 9, 1)),),
    )
    result = validate_performance_over_time_report(bad)
    assert result.status == INVALID
    assert "INVALID_PERIOD_LENGTH" in result.issues


def test_validation_rejects_bad_counts():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    bad = replace(report, observation_count=2)
    result = validate_performance_over_time_report(bad)
    assert result.status == INVALID
    assert "OBSERVATION_COUNT_MISMATCH" in result.issues


def test_validation_rejects_bad_miss_rate():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    bad = replace(
        report,
        periods=(replace(report.periods[0], miss_rate=2.0),),
    )
    result = validate_performance_over_time_report(bad)
    assert result.status == INVALID
    assert "INVALID_MISS_RATE" in result.issues


def test_validation_rejects_bad_trend_direction():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    bad = replace(
        report,
        trends=(replace(report.trends[0], direction="UNKNOWN"),),
    )
    result = validate_performance_over_time_report(bad)
    assert result.status == INVALID
    assert "INVALID_TREND_DIRECTION" in result.issues


def test_validation_rejects_bad_trend_change():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    bad = replace(
        report,
        trends=(replace(report.trends[0], change=99.0),),
    )
    result = validate_performance_over_time_report(bad)
    assert result.status == INVALID
    assert "TREND_CHANGE_MISMATCH" in result.issues


def test_validation_rejects_bad_identity():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    result = validate_performance_over_time_report(
        replace(report, report_identity="bad")
    )
    assert result.status == INVALID
    assert "INVALID_REPORT_IDENTITY" in result.issues


def test_invalid_period_days_rejected():
    actual = actual_report([row("g1", date(2026, 9, 1), 1)])
    with pytest.raises(ValueError):
        build_performance_over_time_report(actual, period_days=0)


def test_invalid_hit_k_rejected():
    actual = actual_report([row("g1", date(2026, 9, 1), 1)])
    with pytest.raises(ValueError):
        build_performance_over_time_report(actual, hit_ks=(0,))


def test_wrong_source_type_rejected():
    with pytest.raises(TypeError):
        build_performance_over_time_report("bad")


def test_invalid_source_report_rejected():
    actual = actual_report([row("g1", date(2026, 9, 1), 1)])
    bad = replace(actual, version="bad")
    with pytest.raises(ValueError):
        build_performance_over_time_report(bad)


def test_empty_source_report_rejected():
    empty = source([])
    actual = build_actual_vs_ranked_report(empty) if False else None
    assert actual is None


def test_report_is_immutable():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    with pytest.raises(Exception):
        report.period_days = 2


def test_period_is_immutable():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    with pytest.raises(Exception):
        report.periods[0].observation_count = 2


def test_hit_rates_are_sorted():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)]),
        hit_ks=(5, 1, 3),
    )
    assert tuple(k for k, _ in report.periods[0].hit_rates) == (1, 3, 5)


def test_all_expected_trend_metrics_exist():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 8), 2),
        ])
    )
    names = {item.metric for item in report.trends}
    assert names == {
        "mean_actual_rank",
        "mean_reciprocal_rank",
        "miss_rate",
        "mean_top_probability",
        "mean_cumulative_probability",
        "hit_at_1",
        "hit_at_3",
        "hit_at_5",
    }

def test_global_counts_reconcile():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 8), None),
        ])
    )
    assert report.observation_count == 2
    assert report.actual_available_observations == 1
    assert report.missed_observations == 1


def test_missing_actual_does_not_enter_mrr():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), None),
            row("g2", date(2026, 9, 2), 2),
        ])
    )
    assert report.periods[0].mean_reciprocal_rank == pytest.approx(0.5)


def test_missing_actual_does_not_enter_rank_mean():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), None),
            row("g2", date(2026, 9, 2), 2),
        ])
    )
    assert report.periods[0].mean_actual_rank == pytest.approx(2.0)


def test_probability_metrics_include_all_observations():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), None),
            row("g2", date(2026, 9, 2), 2),
        ])
    )
    assert report.periods[0].mean_top_probability == pytest.approx(0.22)


def test_source_report_identity_changes_lineage():
    first = actual_report([row("g1", date(2026, 9, 1), 1)])
    second = actual_report([row("g1", date(2026, 9, 1), 2)])
    a = build_performance_over_time_report(first)
    b = build_performance_over_time_report(second)
    assert a.report_identity != b.report_identity


def test_summary_contains_trend_directions():
    report = build_performance_over_time_report(
        actual_report([
            row("g1", date(2026, 9, 1), 1),
            row("g2", date(2026, 9, 8), 3),
        ])
    )
    summary = performance_over_time_summary(report)
    assert any(item[0] == "mean_actual_rank" for item in summary["trends"])


def test_validation_rejects_missing_source_identity():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    result = validate_performance_over_time_report(
        replace(report, source_report_identity="")
    )
    assert result.status == INVALID
    assert "MISSING_SOURCE_REPORT_IDENTITY" in result.issues


def test_validation_rejects_bad_source_type():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    result = validate_performance_over_time_report(
        replace(report, source_type="other")
    )
    assert result.status == INVALID
    assert "INVALID_SOURCE_TYPE" in result.issues


def test_validation_rejects_nonfinite_trend():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    result = validate_performance_over_time_report(
        replace(report, trends=(replace(report.trends[0], slope_per_day=float("nan")),))
    )
    assert result.status == INVALID
    assert "NONFINITE_TREND" in result.issues


def test_validation_rejects_negative_mean_rank():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    bad = replace(
        report,
        periods=(replace(report.periods[0], mean_actual_rank=-1.0),),
    )
    result = validate_performance_over_time_report(bad)
    assert result.status == INVALID
    assert "INVALID_MEAN_RANK" in result.issues


def test_validation_rejects_bad_period_mrr():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    bad = replace(
        report,
        periods=(replace(report.periods[0], mean_reciprocal_rank=2.0),),
    )
    result = validate_performance_over_time_report(bad)
    assert result.status == INVALID
    assert "INVALID_PERIOD_MRR" in result.issues


def test_validation_rejects_bad_hit_rate():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    bad = replace(
        report,
        periods=(replace(report.periods[0], hit_rates=((1, 2.0),)),),
    )
    result = validate_performance_over_time_report(bad)
    assert result.status == INVALID
    assert "INVALID_HIT_RATE" in result.issues


def test_validation_rejects_count_mismatch():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    bad = replace(
        report,
        periods=(replace(report.periods[0], missed_observations=1),),
    )
    result = validate_performance_over_time_report(bad)
    assert result.status == INVALID
    assert "PERIOD_COUNT_MISMATCH" in result.issues


def test_report_identity_prefix():
    report = build_performance_over_time_report(
        actual_report([row("g1", date(2026, 9, 1), 1)])
    )
    assert report.report_identity.startswith("performance-over-time-report-")


def test_no_new_probability_generation():
    actual = actual_report([row("g1", date(2026, 9, 1), 1)])
    report = build_performance_over_time_report(actual)
    assert report.periods[0].mean_top_probability == pytest.approx(
        actual.observations[0].top_probability
    )


def test_no_rank_recomputation():
    actual = actual_report([row("g1", date(2026, 9, 1), 3)])
    report = build_performance_over_time_report(actual)
    assert report.periods[0].mean_actual_rank == pytest.approx(3.0)
