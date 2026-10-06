from dataclasses import replace

import pytest

from analytics.candidate_scoring import (
    SEQUENCE_CANDIDATE_VERSION,
    build_candidate_ranking_report,
    candidate_values,
    rank_candidate_probabilities,
    rank_ensemble_candidates,
    top_candidate,
    validate_candidate_ranking_report,
    validate_sequence_candidate_ranking,
)
from analytics.sequence_ensemble import SequenceEnsembleResult


def _ensemble() -> SequenceEnsembleResult:
    probabilities = (
        (0.05, 0.10, 0.20, 0.15, 0.12, 0.08, 0.07, 0.06, 0.09, 0.08),
        (0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.90, 0.01, 0.01, 0.02),
    )
    return SequenceEnsembleResult(
        "35.0.0",
        "dataset-1",
        "inverse_log_loss",
        ("markov", "transformer"),
        (0.4, 0.6),
        probabilities,
        (2, 6),
        2,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        "sequence-ensemble-test",
    )


def test_version_contract():
    assert SEQUENCE_CANDIDATE_VERSION == "36.0.0"


def test_probability_ranking_is_descending():
    ranking = rank_candidate_probabilities(
        (0.1, 0.3, 0.2, 0.1, 0.05, 0.05, 0.04, 0.03, 0.07, 0.06),
        "dataset-1",
        "ensemble-1",
        0,
    )
    assert candidate_values(ranking)[:3] == (1, 2, 0)
    assert [item.rank for item in ranking.candidates] == list(range(1, 11))
    assert ranking.candidates[0].score == pytest.approx(30.0)


def test_ties_use_lower_digit_deterministically():
    ranking = rank_candidate_probabilities(
        (0.2, 0.2, 0.1, 0.1, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05),
        "dataset-1",
        "ensemble-1",
        0,
    )
    assert candidate_values(ranking)[:4] == (0, 1, 2, 3)


def test_top_k_limits_visible_candidates():
    ranking = rank_candidate_probabilities(
        (0.1,) * 10,
        "dataset-1",
        "ensemble-1",
        0,
        top_k=3,
    )
    assert len(ranking.candidates) == 3
    assert candidate_values(ranking) == (0, 1, 2)


def test_zero_probability_remains_valid_candidate():
    ranking = rank_candidate_probabilities(
        (0.0, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0, 0.0, 0.0, 0.0),
        "dataset-1",
        "ensemble-1",
        0,
    )
    assert any(item.candidate == 0 and item.probability == 0.0 for item in ranking.candidates)


def test_probability_margin_is_top_two_gap():
    ranking = rank_candidate_probabilities(
        (0.1, 0.4, 0.3, 0.2, 0, 0, 0, 0, 0, 0),
        "dataset-1",
        "ensemble-1",
        0,
        top_k=3,
    )
    assert ranking.probability_margin == pytest.approx(0.1)


def test_single_candidate_margin_is_top_probability():
    ranking = rank_candidate_probabilities(
        (1.0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        "dataset-1",
        "ensemble-1",
        0,
        top_k=1,
    )
    assert ranking.probability_margin == pytest.approx(1.0)
def test_entropy_is_non_negative():
    ranking = rank_candidate_probabilities(
        (0.1,) * 10,
        "dataset-1",
        "ensemble-1",
        0,
    )
    assert ranking.entropy > 0


def test_rank_ensemble_candidates_defaults_to_last_observation():
    ranking = rank_ensemble_candidates(_ensemble())
    assert ranking.observation_index == 1
    assert top_candidate(ranking).candidate == 6
    assert top_candidate(ranking).probability == pytest.approx(0.90)


def test_rank_ensemble_candidates_supports_explicit_index():
    ranking = rank_ensemble_candidates(_ensemble(), observation_index=0, top_k=2)
    assert ranking.observation_index == 0
    assert candidate_values(ranking) == (2, 3)


def test_rank_ensemble_candidates_supports_negative_index():
    ranking = rank_ensemble_candidates(_ensemble(), observation_index=-1)
    assert ranking.observation_index == 1


def test_rank_ensemble_candidates_rejects_invalid_index():
    with pytest.raises(IndexError):
        rank_ensemble_candidates(_ensemble(), observation_index=99)


def test_rank_ensemble_candidates_rejects_invalid_ensemble():
    invalid = replace(_ensemble(), probabilities=())
    with pytest.raises(ValueError):
        rank_ensemble_candidates(invalid)


def test_invalid_probability_shape_rejected():
    with pytest.raises(ValueError):
        rank_candidate_probabilities(
            (0.5, 0.5),
            "dataset-1",
            "ensemble-1",
            0,
        )


def test_invalid_probability_sum_rejected():
    with pytest.raises(ValueError):
        rank_candidate_probabilities(
            (0.2,) * 10,
            "dataset-1",
            "ensemble-1",
            0,
        )


def test_invalid_probability_value_rejected():
    with pytest.raises(ValueError):
        rank_candidate_probabilities(
            (1.1, -0.1, 0, 0, 0, 0, 0, 0, 0, 0),
            "dataset-1",
            "ensemble-1",
            0,
        )


def test_invalid_top_k_rejected():
    with pytest.raises(ValueError):
        rank_candidate_probabilities(
            (0.1,) * 10,
            "dataset-1",
            "ensemble-1",
            0,
            top_k=0,
        )


def test_negative_observation_rejected():
    with pytest.raises(ValueError):
        rank_candidate_probabilities(
            (0.1,) * 10,
            "dataset-1",
            "ensemble-1",
            -2,
        )


def test_ranking_validation_is_valid():
    ranking = rank_ensemble_candidates(_ensemble())
    result = validate_sequence_candidate_ranking(ranking)
    assert result.is_valid
    assert result.issues == ()
def test_ranking_validation_detects_bad_rank():
    ranking = rank_ensemble_candidates(_ensemble())
    broken = replace(
        ranking,
        candidates=(replace(ranking.candidates[0], rank=9),) + ranking.candidates[1:],
    )
    result = validate_sequence_candidate_ranking(broken)
    assert not result.is_valid
    assert "INVALID_RANKS" in result.issues


def test_ranking_validation_detects_bad_score():
    ranking = rank_ensemble_candidates(_ensemble())
    broken = replace(
        ranking,
        candidates=(replace(ranking.candidates[0], score=101.0),) + ranking.candidates[1:],
    )
    result = validate_sequence_candidate_ranking(broken)
    assert not result.is_valid
    assert "INVALID_SCORE" in result.issues


def test_ranking_identity_is_deterministic():
    first = rank_ensemble_candidates(_ensemble(), observation_index=0)
    second = rank_ensemble_candidates(_ensemble(), observation_index=0)
    assert first.ranking_identity == second.ranking_identity


def test_different_observation_has_different_identity():
    first = rank_ensemble_candidates(_ensemble(), observation_index=0)
    second = rank_ensemble_candidates(_ensemble(), observation_index=1)
    assert first.ranking_identity != second.ranking_identity


def test_candidate_scores_are_probability_scaled():
    ranking = rank_ensemble_candidates(_ensemble(), observation_index=1)
    for item in ranking.candidates:
        assert item.score == pytest.approx(item.probability * 100.0)


def test_report_contains_all_observations():
    report = build_candidate_ranking_report(_ensemble())
    assert len(report.rankings) == 2
    assert report.top_k == 10
    assert report.rankings[0].observation_index == 0
    assert report.rankings[1].observation_index == 1


def test_report_top_k():
    report = build_candidate_ranking_report(_ensemble(), top_k=3)
    assert all(len(item.candidates) == 3 for item in report.rankings)


def test_report_validation_is_valid():
    report = build_candidate_ranking_report(_ensemble(), top_k=3)
    result = validate_candidate_ranking_report(report)
    assert result.is_valid
    assert result.issues == ()


def test_report_validation_detects_dataset_mismatch():
    report = build_candidate_ranking_report(_ensemble())
    broken = replace(
        report,
        rankings=(replace(report.rankings[0], dataset_identity="other"),) + report.rankings[1:],
    )
    result = validate_candidate_ranking_report(broken)
    assert not result.is_valid
    assert "DATASET_IDENTITY_MISMATCH" in result.issues


def test_report_identity_is_deterministic():
    first = build_candidate_ranking_report(_ensemble(), top_k=5)
    second = build_candidate_ranking_report(_ensemble(), top_k=5)
    assert first.report_identity == second.report_identity


def test_top_candidate_returns_first_rank():
    ranking = rank_ensemble_candidates(_ensemble(), observation_index=0)
    candidate = top_candidate(ranking)
    assert candidate.rank == 1
    assert candidate.candidate == 2


def test_top_candidate_rejects_empty_ranking():
    ranking = rank_ensemble_candidates(_ensemble(), observation_index=0)
    broken = replace(ranking, candidates=())
    with pytest.raises(ValueError):
        top_candidate(broken)
