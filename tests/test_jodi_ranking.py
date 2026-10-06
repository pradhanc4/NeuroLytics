from datetime import date

import pytest

from analytics.jodi_ranking import (
    INVALID,
    VALID,
    JODI_RANKING_VERSION,
    JodiCandidateInput,
    JodiRankingObservation,
    build_jodi_ranking_report,
    jodi_ranking_summary,
    jodi_values,
    rank_jodis,
    rank_jodis_from_predictions,
    top_jodi,
    validate_jodi_ranking,
    validate_jodi_ranking_report,
)
from analytics.learning_to_rank_model import LearningToRankPrediction


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


def probs(first=0.7, second=0.2, third=0.1):
    return (first, second, third, 0, 0, 0, 0, 0, 0, 0)


def candidates():
    return (
        JodiCandidateInput("00", "jf0", "pf0"),
        JodiCandidateInput("12", "jf1", "pf1"),
        JodiCandidateInput("99", "jf9", "pf9"),
        JodiCandidateInput("05", "jf5", "pf5"),
    )


def make_ranking(top_k=4):
    return rank_jodis(
        prediction("p1", probs()),
        prediction("p2", probs()),
        candidates(),
        "g1",
        date(2026, 9, 29),
        top_k=top_k,
    )


def test_version():
    assert JODI_RANKING_VERSION == "43.1.0"


def test_leading_zero_jodi_preserved():
    result = make_ranking()
    assert "05" in jodi_values(result)


def test_double_zero_is_valid():
    result = make_ranking()
    assert "00" in jodi_values(result)


def test_invalid_jodi_length_rejected():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", probs()), prediction("p2", probs()), (JodiCandidateInput("0"),), "g1", date(2026, 9, 29))


def test_invalid_jodi_text_rejected():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", probs()), prediction("p2", probs()), (JodiCandidateInput("a1"),), "g1", date(2026, 9, 29))


def test_empty_candidates_rejected():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", probs()), prediction("p2", probs()), (), "g1", date(2026, 9, 29))


def test_duplicate_jodis_rejected():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", probs()), prediction("p2", probs()), (JodiCandidateInput("12"), JodiCandidateInput("12")), "g1", date(2026, 9, 29))


def test_probability_product_is_used():
    result = make_ranking()
    assert result.top_probability > 0


def test_candidate_universe_is_normalized():
    result = make_ranking()
    assert sum(item.probability for item in result.candidates) <= 1.0


def test_score_is_probability_times_100():
    result = make_ranking()
    assert result.candidates[0].score == pytest.approx(result.candidates[0].probability * 100)


def test_ranks_are_contiguous():
    result = make_ranking()
    assert [item.rank for item in result.candidates] == [1, 2, 3, 4]


def test_top_jodi_is_rank_one():
    assert top_jodi(make_ranking()).rank == 1


def test_ties_break_by_jodi_value():
    equal = tuple([0.1] * 10)
    result = rank_jodis(
        prediction("p1", equal),
        prediction("p2", equal),
        (JodiCandidateInput("99"), JodiCandidateInput("00"), JodiCandidateInput("11")),
        "g1",
        date(2026, 9, 29),
        top_k=3,
    )
    assert jodi_values(result) == ("00", "11", "99")


def test_top_k_limits_output():
    assert len(make_ranking(top_k=2).candidates) == 2


def test_top_k_above_count_is_safe():
    assert len(make_ranking(top_k=100).candidates) == 4


def test_zero_top_k_rejected():
    with pytest.raises(ValueError):
        make_ranking(top_k=0)


def test_non_integer_top_k_rejected():
    with pytest.raises(TypeError):
        make_ranking(top_k=1.5)


def test_group_id_required():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", probs()), prediction("p2", probs()), candidates(), "", date(2026, 9, 29))


def test_target_position_preserved():
    result = rank_jodis(prediction("p1", probs()), prediction("p2", probs()), candidates(), "g1", date(2026, 9, 29), target_position="open_jodi")
    assert result.target_position == "open_jodi"


def test_actual_jodi_preserved():
    result = rank_jodis(prediction("p1", probs()), prediction("p2", probs()), candidates(), "g1", date(2026, 9, 29), actual_jodi="12")
    assert result.actual_jodi == "12"


def test_invalid_actual_jodi_rejected():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", probs()), prediction("p2", probs()), candidates(), "g1", date(2026, 9, 29), actual_jodi="1")


def test_family_metadata_preserved():
    result = make_ranking()
    item = next(item for item in result.candidates if item.jodi == "00")
    assert item.jodi_family_id == "jf0"
    assert item.panel_family_id == "pf0"


def test_prediction_adapter_requires_two_predictions():
    with pytest.raises(ValueError):
        rank_jodis_from_predictions((prediction("p1", probs()),), candidates(), "g1", date(2026, 9, 29))


def test_prediction_adapter_works():
    result = rank_jodis_from_predictions((prediction("p1", probs()), prediction("p2", probs())), candidates(), "g1", date(2026, 9, 29))
    assert result.group_id == "g1"


def test_probability_cardinality_rejected():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", (1.0,) * 9), prediction("p2", probs()), candidates(), "g1", date(2026, 9, 29))


def test_probability_sum_rejected():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", (0.5,) * 10), prediction("p2", probs()), candidates(), "g1", date(2026, 9, 29))


def test_negative_probability_rejected():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", (-0.1, 1.1, 0, 0, 0, 0, 0, 0, 0, 0)), prediction("p2", probs()), candidates(), "g1", date(2026, 9, 29))


def test_nan_probability_rejected():
    with pytest.raises(ValueError):
        rank_jodis(prediction("p1", (float("nan"), 0, 0, 0, 0, 0, 0, 0, 0, 0)), prediction("p2", probs()), candidates(), "g1", date(2026, 9, 29))


def test_ranking_identity_is_deterministic():
    assert make_ranking().ranking_identity == make_ranking().ranking_identity


def test_ranking_identity_prefix():
    assert make_ranking().ranking_identity.startswith("jodi-ranking-")


def test_probability_margin_non_negative():
    assert make_ranking().probability_margin >= 0


def test_validation_accepts_valid_ranking():
    assert validate_jodi_ranking(make_ranking()).status == VALID


def test_validation_rejects_invalid_object():
    assert validate_jodi_ranking(object()).status == INVALID


def test_validation_rejects_bad_rank():
    result = make_ranking()
    first = result.candidates[0]
    bad_candidate = type(first)(first.jodi, first.probability, first.score, 2, first.jodi_family_id, first.panel_family_id)
    bad = JodiRankingObservation(result.group_id, result.target_date, result.target_position, (bad_candidate,) + result.candidates[1:], result.actual_jodi, result.top_probability, result.probability_margin, result.ranking_identity)
    assert validate_jodi_ranking(bad).status == INVALID


def test_report_builds():
    report = build_jodi_ranking_report((make_ranking(),), ("m1", "m2"), 4)
    assert report.version == JODI_RANKING_VERSION


def test_report_requires_two_models():
    with pytest.raises(ValueError):
        build_jodi_ranking_report((make_ranking(),), ("m1",), 4)


def test_report_requires_unique_groups():
    result = make_ranking()
    with pytest.raises(ValueError):
        build_jodi_ranking_report((result, result), ("m1", "m2"), 4)


def test_report_validation_accepts_valid_report():
    report = build_jodi_ranking_report((make_ranking(),), ("m1", "m2"), 4)
    assert validate_jodi_ranking_report(report).is_valid


def test_report_validation_rejects_invalid_object():
    assert validate_jodi_ranking_report(object()).status == INVALID


def test_report_identity_is_deterministic():
    first = build_jodi_ranking_report((make_ranking(),), ("m1", "m2"), 4)
    second = build_jodi_ranking_report((make_ranking(),), ("m1", "m2"), 4)
    assert first.report_identity == second.report_identity


def test_report_identity_prefix():
    assert build_jodi_ranking_report((make_ranking(),), ("m1", "m2")).report_identity.startswith("jodi-ranking-report-")


def test_summary_is_structured():
    report = build_jodi_ranking_report((make_ranking(),), ("m1", "m2"), 4)
    summary = jodi_ranking_summary(report)
    assert summary["status"] == VALID
    assert summary["observations"] == 1


def test_actual_none_is_supported():
    assert make_ranking().actual_jodi is None


def test_target_date_must_be_date():
    with pytest.raises(TypeError):
        rank_jodis(prediction("p1", probs()), prediction("p2", probs()), candidates(), "g1", "2026-09-29")


def test_candidate_strings_are_preserved():
    assert all(isinstance(value, str) for value in jodi_values(make_ranking()))


def test_report_model_identities_are_preserved():
    report = build_jodi_ranking_report((make_ranking(),), ("model-a", "model-b"))
    assert report.source_model_identities == ("model-a", "model-b")


def test_top_probability_matches_first_candidate():
    result = make_ranking()
    assert result.top_probability == result.candidates[0].probability
