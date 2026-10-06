from dataclasses import replace
from datetime import date

import pytest

from analytics.jodi_ranking import JodiRankedCandidate, JodiRankingObservation
from analytics.panel_ranking import PanelRankedCandidate, PanelRankingObservation
from analytics.top_k_framework import (
    INVALID, TOP_K_FRAMEWORK_VERSION, VALID, TopKEvaluationRow,
    actual_rank, build_top_k_evaluation_report, build_top_k_evaluation_row,
    cumulative_probability, hit_at_k, normalize_top_k_values, reciprocal_rank,
    top_k_selection, top_k_summary, top_k_values,
    validate_top_k_evaluation_report, validate_top_k_selection,
)


def panel_ranking(actual="045"):
    candidates = tuple(
        PanelRankedCandidate(value, probability, probability * 100, index, "pf", "jf")
        for index, (value, probability) in enumerate(
            (("045", .40), ("123", .30), ("005", .20), ("000", .10)), 1
        )
    )
    return PanelRankingObservation(
        "panel-g1", date(2026, 9, 1), "panel", candidates, actual, .40, .10,
        "panel-ranking-test-1",
    )


def jodi_ranking(actual="05"):
    candidates = tuple(
        JodiRankedCandidate(value, probability, probability * 100, index, "jf", "pf")
        for index, (value, probability) in enumerate(
            (("05", .50), ("00", .25), ("12", .15), ("45", .10)), 1
        )
    )
    return JodiRankingObservation(
        "jodi-g1", date(2026, 9, 2), "jodi", candidates, actual, .50, .25,
        "jodi-ranking-test-1",
    )


def test_version():
    assert TOP_K_FRAMEWORK_VERSION == "44.0.0"


def test_normalize_top_k_values():
    assert normalize_top_k_values((5, 1, 3)) == (1, 3, 5)


def test_normalize_top_k_rejects_empty():
    with pytest.raises(ValueError):
        normalize_top_k_values(())


def test_normalize_top_k_rejects_duplicate():
    with pytest.raises(ValueError):
        normalize_top_k_values((1, 1))


def test_normalize_top_k_rejects_zero():
    with pytest.raises(ValueError):
        normalize_top_k_values((0,))


def test_normalize_top_k_rejects_non_integer():
    with pytest.raises(TypeError):
        normalize_top_k_values((1.5,))


def test_panel_selection():
    selection = top_k_selection(panel_ranking(), 2)
    assert selection.source_type == "panel"
    assert tuple(item.value for item in selection.candidates) == ("045", "123")


def test_panel_selection_preserves_leading_zero():
    assert top_k_values(panel_ranking(), 4)[2:] == ("005", "000")


def test_jodi_selection():
    selection = top_k_selection(jodi_ranking(), 2)
    assert selection.source_type == "jodi"
    assert top_k_values(jodi_ranking(), 2) == ("05", "00")


def test_selection_clamps_k_to_available_candidates():
    selection = top_k_selection(panel_ranking(), 99)
    assert selection.requested_k == 99
    assert selection.available_count == 4
    assert len(selection.candidates) == 4


def test_selection_cumulative_probability():
    assert cumulative_probability(panel_ranking(), 2) == pytest.approx(.70)


def test_selection_identity_is_deterministic():
    assert top_k_selection(panel_ranking(), 3) == top_k_selection(panel_ranking(), 3)


def test_selection_identity_changes_with_k():
    assert top_k_selection(panel_ranking(), 2).selection_identity != top_k_selection(panel_ranking(), 3).selection_identity


def test_selection_validation():
    result = validate_top_k_selection(top_k_selection(panel_ranking(), 3))
    assert result.status == VALID
    assert result.issues == ()


def test_selection_validation_rejects_bad_identity():
    bad = replace(top_k_selection(panel_ranking(), 2), selection_identity="bad")
    result = validate_top_k_selection(bad)
    assert result.status == INVALID
    assert "INVALID_SELECTION_IDENTITY" in result.issues


def test_actual_rank_panel():
    assert actual_rank(panel_ranking()) == 1


def test_actual_rank_jodi():
    assert actual_rank(jodi_ranking()) == 1


def test_actual_rank_missing_actual():
    assert actual_rank(replace(panel_ranking(), actual_panel=None)) is None


def test_actual_rank_outside_visible_ranking():
    assert actual_rank(panel_ranking(actual="999")) is None


def test_hit_at_k():
    assert hit_at_k(panel_ranking(), 1)
    assert hit_at_k(panel_ranking(), 3)


def test_hit_at_k_false_when_actual_missing():
    assert not hit_at_k(replace(panel_ranking(), actual_panel=None), 3)


def test_reciprocal_rank():
    assert reciprocal_rank(panel_ranking()) == pytest.approx(1.0)


def test_reciprocal_rank_rank_two():
    assert reciprocal_rank(panel_ranking(actual="123")) == pytest.approx(.5)


def test_build_panel_row():
    row = build_top_k_evaluation_row(panel_ranking(), (1, 3, 5))
    assert row.source_type == "panel"
    assert row.actual_rank == 1
    assert dict(row.hit_at_k) == {1: True, 3: True, 5: True}


def test_build_jodi_row():
    row = build_top_k_evaluation_row(jodi_ranking(), (1, 2, 5))
    assert row.source_type == "jodi"
    assert row.actual_value == "05"


def test_row_without_actual():
    row = build_top_k_evaluation_row(replace(panel_ranking(), actual_panel=None), (1, 3))
    assert row.actual_rank is None
    assert row.reciprocal_rank == 0.0
    assert dict(row.hit_at_k) == {1: False, 3: False}


def test_report_builds_panel():
    report = build_top_k_evaluation_report([panel_ranking()], "panel-source", (1, 2, 3))
    assert report.version == TOP_K_FRAMEWORK_VERSION
    assert report.source_type == "panel"
    assert report.evaluated_observations == 1
    assert report.actual_available_observations == 1


def test_report_builds_jodi():
    report = build_top_k_evaluation_report([jodi_ranking()], "jodi-source", (1, 2))
    assert report.source_type == "jodi"
    assert dict(report.hit_rates)[1] == pytest.approx(1.0)


def test_report_hit_rates():
    report = build_top_k_evaluation_report(
        [panel_ranking(), replace(panel_ranking(actual="123"), group_id="panel-g2")], "source", (1, 2, 3)
    )
    assert dict(report.hit_rates)[1] == pytest.approx(.5)
    assert dict(report.hit_rates)[2] == pytest.approx(1.0)


def test_report_mrr():
    report = build_top_k_evaluation_report(
        [panel_ranking(), replace(panel_ranking(actual="123"), group_id="panel-g2")], "source", (1, 2)
    )
    assert report.mean_reciprocal_rank == pytest.approx(.75)
def test_report_counts_missing_actual():
    report = build_top_k_evaluation_report(
        [panel_ranking(), replace(panel_ranking(), group_id="panel-g2", actual_panel=None)], "source", (1, 2)
    )
    assert report.evaluated_observations == 2
    assert report.actual_available_observations == 1
    assert dict(report.hit_rates)[1] == pytest.approx(1.0)


def test_report_validation():
    report = build_top_k_evaluation_report([panel_ranking()], "source", (1, 2, 3))
    assert validate_top_k_evaluation_report(report).status == VALID


def test_report_validation_rejects_bad_version():
    report = build_top_k_evaluation_report([panel_ranking()], "source", (1, 2))
    result = validate_top_k_evaluation_report(replace(report, version="bad"))
    assert result.status == INVALID
    assert "INVALID_VERSION" in result.issues


def test_report_validation_rejects_bad_mrr():
    report = build_top_k_evaluation_report([panel_ranking()], "source", (1, 2))
    result = validate_top_k_evaluation_report(replace(report, mean_reciprocal_rank=2.0))
    assert result.status == INVALID
    assert "INVALID_MRR" in result.issues


def test_report_validation_rejects_duplicate_ks():
    report = build_top_k_evaluation_report([panel_ranking()], "source", (1, 2))
    result = validate_top_k_evaluation_report(replace(report, ks=(1, 1)))
    assert result.status == INVALID
    assert "DUPLICATE_KS" in result.issues


def test_report_identity_is_deterministic():
    first = build_top_k_evaluation_report([panel_ranking()], "source", (1, 2, 3))
    second = build_top_k_evaluation_report([panel_ranking()], "source", (1, 2, 3))
    assert first == second
    assert first.report_identity == second.report_identity


def test_report_identity_changes_with_source():
    first = build_top_k_evaluation_report([panel_ranking()], "source-a", (1, 2))
    second = build_top_k_evaluation_report([panel_ranking()], "source-b", (1, 2))
    assert first.report_identity != second.report_identity


def test_panel_and_jodi_cannot_be_mixed():
    with pytest.raises(ValueError):
        build_top_k_evaluation_report([panel_ranking(), jodi_ranking()], "mixed", (1, 2))


def test_empty_observation_report_rejected():
    with pytest.raises(ValueError):
        build_top_k_evaluation_report([], "source", (1,))


def test_empty_source_identity_rejected():
    with pytest.raises(ValueError):
        build_top_k_evaluation_report([panel_ranking()], "", (1,))


def test_top_k_summary():
    report = build_top_k_evaluation_report([panel_ranking()], "source", (1, 2, 3))
    summary = top_k_summary(report)
    assert summary["status"] == VALID
    assert summary["source_type"] == "panel"
    assert summary["ks"] == (1, 2, 3)


def test_zero_digit_values_are_preserved():
    ranking = panel_ranking(actual="000")
    assert actual_rank(ranking) == 4
    assert hit_at_k(ranking, 4)
    assert top_k_values(ranking, 4)[-1] == "000"


def test_jodi_leading_zero_is_preserved():
    ranking = jodi_ranking(actual="00")
    assert actual_rank(ranking) == 2
    assert top_k_values(ranking, 2)[1] == "00"


def test_family_metadata_is_preserved():
    candidate = top_k_selection(panel_ranking(), 1).candidates[0]
    assert candidate.panel_family_id == "pf"
    assert candidate.jodi_family_id == "jf"


def test_selection_carries_date_and_position():
    selection = top_k_selection(panel_ranking(), 1)
    assert selection.target_date == date(2026, 9, 1)
    assert selection.target_position == "panel"


def test_hit_at_k_rejects_invalid_k():
    with pytest.raises(ValueError):
        hit_at_k(panel_ranking(), 0)


def test_selection_rejects_empty_ranking():
    ranking = replace(panel_ranking(), candidates=())
    with pytest.raises(ValueError):
        top_k_selection(ranking, 1)


def test_report_uses_sorted_ks():
    report = build_top_k_evaluation_report([panel_ranking()], "source", (5, 1, 3))
    assert report.ks == (1, 3, 5)


def test_report_hit_rates_are_bounded():
    report = build_top_k_evaluation_report(
        [panel_ranking(), replace(panel_ranking(actual="123"), group_id="panel-g2")], "source", (1, 2, 4)
    )
    assert all(0.0 <= value <= 1.0 for _, value in report.hit_rates)


def test_row_validation_detects_inconsistent_hit():
    from analytics.top_k_framework import _validate_row
    row = TopKEvaluationRow(
        "panel", "g", date(2026, 9, 1), "045", 1, ((1, False),),
        1.0, .4, .4,
    )
    result = _validate_row(row)
    assert result.status == INVALID
    assert "INCONSISTENT_HIT_AT_K" in result.issues


def test_selection_dataclass_is_immutable():
    selection = top_k_selection(panel_ranking(), 2)
    with pytest.raises(Exception):
        selection.requested_k = 4


def test_report_is_immutable():
    report = build_top_k_evaluation_report([panel_ranking()], "source", (1, 2))
    with pytest.raises(Exception):
        report.ks = (1,)


def test_probability_sum_for_selected_candidates():
    assert cumulative_probability(panel_ranking(), 4) == pytest.approx(1.0)


def test_actual_rank_uses_rank_field():
    ranking = panel_ranking()
    altered = replace(
        ranking,
        candidates=tuple(replace(item, rank=item.rank + 1) for item in ranking.candidates),
    )
    assert actual_rank(altered) == 2


def test_top_k_values_returns_tuple():
    assert isinstance(top_k_values(panel_ranking(), 2), tuple)


def test_report_source_identity_is_retained():
    report = build_top_k_evaluation_report([panel_ranking()], "panel-report-abc", (1, 3))
    assert report.source_report_identity == "panel-report-abc"


def test_cumulative_probability_is_monotonic():
    ranking = panel_ranking()
    assert cumulative_probability(ranking, 1) <= cumulative_probability(ranking, 2)
    assert cumulative_probability(ranking, 2) <= cumulative_probability(ranking, 4)


def test_phase_44_has_no_training_state():
    selection = top_k_selection(panel_ranking(), 2)
    assert not hasattr(selection, "weights")
    assert not hasattr(selection, "model")


def test_actual_value_is_string():
    assert build_top_k_evaluation_row(panel_ranking(), (1,)).actual_value == "045"


def test_jodi_actual_value_is_string():
    assert build_top_k_evaluation_row(jodi_ranking(), (1,)).actual_value == "05"


def test_report_identity_has_expected_prefix():
    report = build_top_k_evaluation_report([panel_ranking()], "source", (1,))
    assert report.report_identity.startswith("top-k-evaluation-report-")


def test_selection_identity_has_expected_prefix():
    selection = top_k_selection(panel_ranking(), 1)
    assert selection.selection_identity.startswith("top-k-selection-")


def test_framework_is_position_agnostic():
    ranking = replace(panel_ranking(), target_position="custom-position")
    assert top_k_selection(ranking, 2).target_position == "custom-position"
