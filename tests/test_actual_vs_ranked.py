from dataclasses import replace
from datetime import date

import pytest

from analytics.actual_vs_ranked import (
    ACTUAL_VS_RANKED_VERSION,
    INVALID,
    VALID,
    ActualVsRankedObservation,
    actual_vs_ranked_summary,
    build_actual_vs_ranked_report,
    validate_actual_vs_ranked_report,
)
from analytics.top_k_framework import (
    TopKEvaluationReport,
    TopKEvaluationRow,
)


def row(group, rank, actual="045", source="panel"):
    return TopKEvaluationRow(
        source,
        group,
        date(2026, 9, 1),
        actual,
        rank,
        ((1, rank == 1), (3, rank is not None and rank <= 3), (5, rank is not None and rank <= 5)),
        1.0 / rank if rank else 0.0,
        0.4,
        0.7,
    )


def source(rows):
    return TopKEvaluationReport(
        "44.0.0",
        "panel",
        "top-k-evaluation-report-source",
        (1, 3, 5),
        tuple(rows),
        ((1, 0.5), (3, 1.0), (5, 1.0)),
        0.75,
        len(rows),
        sum(item.actual_rank is not None for item in rows),
        "top-k-evaluation-report-source",
    )


def test_version():
    assert ACTUAL_VS_RANKED_VERSION == "45.0.0"


def test_builds_report():
    report = build_actual_vs_ranked_report(
        source([row("g1", 1), row("g2", 2)])
    )
    assert report.source_type == "panel"
    assert len(report.observations) == 2


def test_observation_preserves_actual_rank():
    report = build_actual_vs_ranked_report(source([row("g1", 3)]))
    assert report.observations[0].actual_rank == 3


def test_observation_preserves_hit_at_k():
    report = build_actual_vs_ranked_report(source([row("g1", 3)]))
    assert dict(report.observations[0].hit_at_k) == {1: False, 3: True, 5: True}


def test_rank_bucket_top_one():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    assert report.observations[0].rank_bucket == "TOP_1"


def test_rank_bucket_top_three():
    report = build_actual_vs_ranked_report(source([row("g1", 3)]))
    assert report.observations[0].rank_bucket == "TOP_3"


def test_rank_bucket_top_five():
    report = build_actual_vs_ranked_report(source([row("g1", 5)]))
    assert report.observations[0].rank_bucket == "TOP_5"


def test_rank_bucket_top_ten():
    report = build_actual_vs_ranked_report(source([row("g1", 10)]))
    assert report.observations[0].rank_bucket == "TOP_10"


def test_rank_bucket_outside_top_ten():
    report = build_actual_vs_ranked_report(source([row("g1", 11)]))
    assert report.observations[0].rank_bucket == "OUTSIDE_TOP_10"


def test_missing_actual_bucket():
    report = build_actual_vs_ranked_report(source([row("g1", None, None)]))
    assert report.observations[0].rank_bucket == "UNAVAILABLE"


def test_rank_distribution():
    report = build_actual_vs_ranked_report(
        source([row("g1", 1), row("g2", 2), row("g3", 2)])
    )
    assert report.rank_distribution == ((1, 1), (2, 2))


def test_bucket_counts():
    report = build_actual_vs_ranked_report(
        source([row("g1", 1), row("g2", 3), row("g3", 7)])
    )
    assert dict(report.rank_bucket_counts) == {"TOP_1": 1, "TOP_3": 1, "TOP_10": 1}


def test_mean_rank():
    report = build_actual_vs_ranked_report(
        source([row("g1", 1), row("g2", 3)])
    )
    assert report.mean_actual_rank == pytest.approx(2.0)


def test_median_rank_even():
    report = build_actual_vs_ranked_report(
        source([row("g1", 1), row("g2", 3)])
    )
    assert report.median_actual_rank == pytest.approx(2.0)


def test_median_rank_odd():
    report = build_actual_vs_ranked_report(
        source([row("g1", 1), row("g2", 3), row("g3", 5)])
    )
    assert report.median_actual_rank == pytest.approx(3.0)


def test_mrr():
    report = build_actual_vs_ranked_report(
        source([row("g1", 1), row("g2", 2)])
    )
    assert report.mean_reciprocal_rank == pytest.approx(.75)


def test_missing_actual_counts():
    report = build_actual_vs_ranked_report(
        source([row("g1", 1), row("g2", None, None)])
    )
    assert report.actual_available_observations == 1
    assert report.missed_observations == 1


def test_hit_rates_are_carried_from_phase_44():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    assert report.hit_rates == ((1, .5), (3, 1.0), (5, 1.0))


def test_probability_means():
    report = build_actual_vs_ranked_report(source([row("g1", 1), row("g2", 2)]))
    assert report.top_probability_mean == pytest.approx(.4)
    assert report.cumulative_probability_mean == pytest.approx(.7)


def test_source_identity_is_preserved():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    assert report.source_report_identity == "top-k-evaluation-report-source"


def test_report_identity_is_deterministic():
    first = build_actual_vs_ranked_report(source([row("g1", 1), row("g2", 2)]))
    second = build_actual_vs_ranked_report(source([row("g1", 1), row("g2", 2)]))
    assert first == second
    assert first.report_identity == second.report_identity


def test_report_identity_changes_with_input():
    first = build_actual_vs_ranked_report(source([row("g1", 1)]))
    second = build_actual_vs_ranked_report(source([row("g1", 2)]))
    assert first.report_identity != second.report_identity


def test_validation():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    result = validate_actual_vs_ranked_report(report)
    assert result.status == VALID
    assert result.issues == ()


def test_summary():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    summary = actual_vs_ranked_summary(report)
    assert summary["status"] == VALID
    assert summary["observations"] == 1
def test_validation_rejects_bad_version():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    result = validate_actual_vs_ranked_report(replace(report, version="bad"))
    assert result.status == INVALID
    assert "INVALID_VERSION" in result.issues


def test_validation_rejects_duplicate_groups():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    duplicate = replace(
        report,
        observations=(
            report.observations[0],
            report.observations[0],
        ),
    )
    result = validate_actual_vs_ranked_report(duplicate)
    assert result.status == INVALID
    assert "DUPLICATE_GROUP_IDS" in result.issues


def test_validation_rejects_bad_rank_bucket():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    bad = replace(
        report,
        observations=(replace(report.observations[0], rank_bucket="TOP_3"),),
    )
    result = validate_actual_vs_ranked_report(bad)
    assert result.status == INVALID
    assert "INVALID_RANK_BUCKET" in result.issues


def test_validation_rejects_bad_mrr():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    result = validate_actual_vs_ranked_report(
        replace(report, mean_reciprocal_rank=2.0)
    )
    assert result.status == INVALID
    assert "INVALID_MRR" in result.issues


def test_validation_rejects_bad_identity():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    result = validate_actual_vs_ranked_report(
        replace(report, report_identity="bad")
    )
    assert result.status == INVALID
    assert "INVALID_REPORT_IDENTITY" in result.issues


def test_empty_source_rejected():
    empty = source([])
    with pytest.raises(ValueError):
        build_actual_vs_ranked_report(empty)


def test_wrong_source_type_rejected():
    with pytest.raises(TypeError):
        build_actual_vs_ranked_report("bad")


def test_zero_digit_actual_is_preserved():
    source_report = source([row("g1", 1, "000")])
    report = build_actual_vs_ranked_report(source_report)
    assert report.observations[0].actual_value == "000"


def test_leading_zero_actual_is_preserved():
    source_report = source([row("g1", 1, "005")])
    report = build_actual_vs_ranked_report(source_report)
    assert report.observations[0].actual_value == "005"


def test_jodi_source_is_supported():
    jodi_row = replace(row("g1", 2, "05", "jodi"), source_type="jodi")
    jodi_source = replace(source([jodi_row]), source_type="jodi")
    report = build_actual_vs_ranked_report(jodi_source)
    assert report.source_type == "jodi"
    assert report.observations[0].actual_value == "05"


def test_report_is_immutable():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    with pytest.raises(Exception):
        report.source_type = "jodi"


def test_observation_is_immutable():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    with pytest.raises(Exception):
        report.observations[0].group_id = "x"


def test_no_training_state():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    assert not hasattr(report, "weights")
    assert not hasattr(report, "model")


def test_report_has_expected_prefix():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    assert report.report_identity.startswith("actual-vs-ranked-report-")


def test_observation_dates_are_preserved():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    assert report.observations[0].target_date == date(2026, 9, 1)


def test_actual_rank_none_has_zero_rr():
    report = build_actual_vs_ranked_report(source([row("g1", None, None)]))
    assert report.observations[0].reciprocal_rank == 0.0


def test_summary_contains_distribution():
    report = build_actual_vs_ranked_report(source([row("g1", 2)]))
    summary = actual_vs_ranked_summary(report)
    assert summary["rank_distribution"] == ((2, 1),)


def test_summary_contains_bucket_counts():
    report = build_actual_vs_ranked_report(source([row("g1", 2)]))
    assert actual_vs_ranked_summary(report)["rank_bucket_counts"] == (("TOP_3", 1),)


def test_actual_count_matches_observations():
    report = build_actual_vs_ranked_report(
        source([row("g1", 1), row("g2", None, None)])
    )
    assert report.actual_available_observations + report.missed_observations == 2


def test_phase_45_is_analysis_only():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    assert not hasattr(report, "training_history")
    assert not hasattr(report, "feature_schema")


def test_hit_rate_is_not_recomputed():
    source_report = source([row("g1", 1)])
    changed = replace(source_report, hit_rates=((1, .25), (3, .5), (5, .75)))
    report = build_actual_vs_ranked_report(changed)
    assert report.hit_rates == changed.hit_rates


def test_report_identity_includes_source_identity():
    first = build_actual_vs_ranked_report(source([row("g1", 1)]))
    changed = replace(
        source([row("g1", 1)]),
        report_identity="top-k-evaluation-report-other-source",
    )
    second = build_actual_vs_ranked_report(changed)
    assert first.report_identity != second.report_identity


def test_validation_detects_count_mismatch():
    report = build_actual_vs_ranked_report(source([row("g1", 1)]))
    bad = replace(report, actual_available_observations=0)
    result = validate_actual_vs_ranked_report(bad)
    assert result.status == INVALID
    assert "ACTUAL_COUNT_MISMATCH" in result.issues


def test_validation_detects_invalid_bucket_for_missing():
    report = build_actual_vs_ranked_report(source([row("g1", None, None)]))
    bad = replace(
        report,
        observations=(replace(report.observations[0], rank_bucket="TOP_1"),),
    )
    result = validate_actual_vs_ranked_report(bad)
    assert result.status == INVALID
    assert "INVALID_UNAVAILABLE_BUCKET" in result.issues
