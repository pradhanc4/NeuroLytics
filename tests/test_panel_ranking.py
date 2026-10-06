from datetime import date

import pytest

from analytics.learning_to_rank_model import LearningToRankPrediction
from analytics.panel_ranking import (
    INVALID,
    VALID,
    PANEL_RANKING_VERSION,
    PanelCandidateInput,
    PanelRankingObservation,
    PanelRankingReport,
    build_panel_ranking_report,
    panel_ranking_summary,
    panel_values,
    rank_panels,
    rank_panels_from_predictions,
    top_panel,
    validate_panel_ranking,
    validate_panel_ranking_report,
)


def prediction(group_id: str, probabilities: tuple[float, ...]):
    return LearningToRankPrediction(
        group_id=group_id,
        target_date="2026-09-29",
        candidate_digits=tuple(range(10)),
        scores=probabilities,
        probabilities=probabilities,
        ranks=tuple(range(1, 11)),
        actual_digit=0,
        top_candidate=0,
        top_k_candidates=(0, 1, 2),
    )


def candidates():
    return (
        PanelCandidateInput("000", "pf0", "jf0"),
        PanelCandidateInput("123", "pf1", "jf1"),
        PanelCandidateInput("999", "pf9", "jf9"),
        PanelCandidateInput("045", "pf4", "jf4"),
    )


def probs(first=0.7, second=0.2, third=0.1):
    return (first, second, third, 0, 0, 0, 0, 0, 0, 0)


def test_version():
    assert PANEL_RANKING_VERSION == "42.0.0"


def test_panel_candidate_accepts_leading_zero():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        (PanelCandidateInput("000"),),
        "g1",
        date(2026, 9, 29),
    )
    assert result.candidates[0].panel == "000"


def test_panel_candidate_rejects_non_three_digit():
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", probs()),
            prediction("p2", probs()),
            prediction("p3", probs()),
            (PanelCandidateInput("00"),),
            "g1",
            date(2026, 9, 29),
        )


def test_panel_candidate_rejects_non_numeric():
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", probs()),
            prediction("p2", probs()),
            prediction("p3", probs()),
            (PanelCandidateInput("0a0"),),
            "g1",
            date(2026, 9, 29),
        )


def test_empty_candidates_rejected():
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", probs()),
            prediction("p2", probs()),
            prediction("p3", probs()),
            (),
            "g1",
            date(2026, 9, 29),
        )
def test_duplicate_panels_rejected():
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", probs()),
            prediction("p2", probs()),
            prediction("p3", probs()),
            (PanelCandidateInput("123"), PanelCandidateInput("123")),
            "g1",
            date(2026, 9, 29),
        )


def test_probability_product_is_normalized():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert sum(item.probability for item in result.candidates) <= 1.0
    assert result.top_probability > 0


def test_panel_000_has_valid_zero_probability_path():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert "000" in panel_values(result)


def test_top_panel_is_rank_one():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert top_panel(result).rank == 1


def test_scores_are_probability_times_100():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert result.candidates[0].score == pytest.approx(
        result.candidates[0].probability * 100
    )


def test_rank_order_is_deterministic():
    first = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    second = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert first.ranking_identity == second.ranking_identity
    assert first.candidates == second.candidates


def test_ties_break_by_panel_value():
    equal = tuple([0.1] * 10)
    result = rank_panels(
        prediction("p1", equal),
        prediction("p2", equal),
        prediction("p3", equal),
        (
            PanelCandidateInput("999"),
            PanelCandidateInput("000"),
            PanelCandidateInput("111"),
        ),
        "g1",
        date(2026, 9, 29),
        top_k=3,
    )
    assert panel_values(result) == ("000", "111", "999")


def test_top_k_caps_visible_candidates():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=2,
    )
    assert len(result.candidates) == 2


def test_top_k_above_candidate_count_is_safe():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=100,
    )
    assert len(result.candidates) == 4
def test_negative_top_k_rejected():
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", probs()),
            prediction("p2", probs()),
            prediction("p3", probs()),
            candidates(),
            "g1",
            date(2026, 9, 29),
            top_k=0,
        )


def test_empty_group_id_rejected():
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", probs()),
            prediction("p2", probs()),
            prediction("p3", probs()),
            candidates(),
            "",
            date(2026, 9, 29),
        )


def test_actual_panel_is_preserved():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        actual_panel="123",
    )
    assert result.actual_panel == "123"


def test_invalid_actual_panel_rejected():
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", probs()),
            prediction("p2", probs()),
            prediction("p3", probs()),
            candidates(),
            "g1",
            date(2026, 9, 29),
            actual_panel="12",
        )


def test_family_metadata_preserved():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
    )
    item = next(item for item in result.candidates if item.panel == "000")
    assert item.panel_family_id == "pf0"
    assert item.jodi_family_id == "jf0"


def test_three_predictions_required():
    with pytest.raises(ValueError):
        rank_panels_from_predictions(
            (
                prediction("p1", probs()),
                prediction("p2", probs()),
            ),
            candidates(),
            "g1",
            date(2026, 9, 29),
        )


def test_prediction_adapter_accepts_three_positions():
    result = rank_panels_from_predictions(
        (
            prediction("p1", probs()),
            prediction("p2", probs()),
            prediction("p3", probs()),
        ),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert len(result.candidates) == 4


def test_validation_accepts_valid_ranking():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    validation = validate_panel_ranking(result)
    assert validation.status == VALID
    assert validation.issues == ()


def test_validation_rejects_bad_rank_sequence():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    bad = PanelRankingObservation(
        result.group_id,
        result.target_date,
        result.target_position,
        tuple(
            item if index else type(item)(
                item.panel, item.probability, item.score, 2,
                item.panel_family_id, item.jodi_family_id
            )
            for index, item in enumerate(result.candidates)
        ),
        result.actual_panel,
        result.top_probability,
        result.probability_margin,
        result.ranking_identity,
    )
    assert validate_panel_ranking(bad).status == INVALID
def test_build_report():
    observation = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    report = build_panel_ranking_report(
        (observation,),
        ("model-1", "model-2", "model-3"),
        top_k=4,
    )
    assert report.version == PANEL_RANKING_VERSION
    assert report.source_model_identities == ("model-1", "model-2", "model-3")


def test_report_validation_accepts_valid_report():
    observation = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    report = build_panel_ranking_report(
        (observation,),
        ("m1", "m2", "m3"),
        top_k=4,
    )
    assert validate_panel_ranking_report(report).is_valid


def test_report_requires_three_source_identities():
    observation = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
    )
    with pytest.raises(ValueError):
        build_panel_ranking_report((observation,), ("m1", "m2"))


def test_report_requires_unique_groups():
    observation = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
    )
    with pytest.raises(ValueError):
        build_panel_ranking_report(
            (observation, observation),
            ("m1", "m2", "m3"),
        )


def test_summary_is_structured():
    observation = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    report = build_panel_ranking_report(
        (observation,),
        ("m1", "m2", "m3"),
        top_k=4,
    )
    summary = panel_ranking_summary(report)
    assert summary["status"] == VALID
    assert summary["observations"] == 1
def test_report_identity_is_deterministic():
    observation = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    first = build_panel_ranking_report((observation,), ("m1", "m2", "m3"), 4)
    second = build_panel_ranking_report((observation,), ("m1", "m2", "m3"), 4)
    assert first.report_identity == second.report_identity


def test_probability_margin_is_non_negative():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert result.probability_margin >= 0


def test_candidate_probability_range():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert all(0 <= item.probability <= 1 for item in result.candidates)


def test_rank_values_are_contiguous():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert [item.rank for item in result.candidates] == [1, 2, 3, 4]


def test_panel_values_are_strings():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=4,
    )
    assert all(isinstance(panel, str) for panel in panel_values(result))


def test_actual_panel_can_be_none():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
    )
    assert result.actual_panel is None


def test_invalid_report_object():
    result = validate_panel_ranking_report(object())
    assert result.status == INVALID


def test_invalid_ranking_object():
    result = validate_panel_ranking(object())
    assert result.status == INVALID
def test_probability_input_rejects_wrong_cardinality():
    bad = (1.0,) * 9
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", bad),
            prediction("p2", probs()),
            prediction("p3", probs()),
            candidates(),
            "g1",
            date(2026, 9, 29),
        )


def test_probability_input_rejects_non_normalized():
    bad = (0.5,) * 10
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", bad),
            prediction("p2", probs()),
            prediction("p3", probs()),
            candidates(),
            "g1",
            date(2026, 9, 29),
        )


def test_probability_input_rejects_negative():
    bad = (-0.1, 1.1, 0, 0, 0, 0, 0, 0, 0, 0)
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", bad),
            prediction("p2", probs()),
            prediction("p3", probs()),
            candidates(),
            "g1",
            date(2026, 9, 29),
        )


def test_probability_input_rejects_nan():
    bad = (float("nan"), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        rank_panels(
            prediction("p1", bad),
            prediction("p2", probs()),
            prediction("p3", probs()),
            candidates(),
            "g1",
            date(2026, 9, 29),
        )


def test_panel_identity_prefix():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
    )
    assert result.ranking_identity.startswith("panel-ranking-")


def test_report_identity_prefix():
    observation = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
    )
    report = build_panel_ranking_report(
        (observation,), ("m1", "m2", "m3")
    )
    assert report.report_identity.startswith("panel-ranking-report-")


def test_target_position_is_preserved():
    result = rank_panels(
        prediction("p1", probs()),
        prediction("p2", probs()),
        prediction("p3", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        target_position="close_panel",
    )
    assert result.target_position == "close_panel"
