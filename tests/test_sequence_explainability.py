from dataclasses import replace

import pytest

from analytics.sequence_ensemble import SequenceEnsembleResult
from analytics.sequence_evaluation import SequenceEvaluationResult
from analytics.sequence_explainability import (
    SEQUENCE_EXPLAINABILITY_VERSION,
    build_explainability_report,
    explain_ensemble_observation,
    explanation_summary,
    validate_explainability_report,
    validate_sequence_explainability,
)


def _ensemble() -> SequenceEnsembleResult:
    return SequenceEnsembleResult(
        "35.0.0", "dataset-1", "inverse_log_loss",
        ("markov", "transformer"), (0.4, 0.6),
        (
            (0.05, 0.10, 0.20, 0.15, 0.12, 0.08, 0.07, 0.06, 0.09, 0.08),
            (0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.90, 0.01, 0.01, 0.02),
        ),
        (2, 6), 2, 0.0, 0.0, 0.0, 0.0, 0.0,
        "sequence-ensemble-test",
    )


def _evaluation(kind: str, version: str, rows) -> SequenceEvaluationResult:
    return SequenceEvaluationResult(
        kind, version, "dataset-1", len(rows),
        1.0, 0.5, 0.5, 0.5, 0.1, 1.0, tuple(rows), (2, 6)
    )


def _evaluations():
    rows = (
        (0.05, 0.10, 0.20, 0.15, 0.12, 0.08, 0.07, 0.06, 0.09, 0.08),
        (0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.90, 0.01, 0.01, 0.02),
    )
    return (
        _evaluation("markov", "28.0.0", rows),
        _evaluation("transformer", "32.0.0", rows),
    )


def test_version_contract():
    assert SEQUENCE_EXPLAINABILITY_VERSION == "37.0.0"


def test_latest_observation_explanation():
    result = explain_ensemble_observation(_ensemble())
    assert result.observation_index == 1
    assert result.selected_candidate == 6
    assert result.selected_rank == 1
    assert result.selected_probability == pytest.approx(0.90)


def test_explicit_observation_explanation():
    result = explain_ensemble_observation(_ensemble(), observation_index=0, top_k=3)
    assert result.observation_index == 0
    assert [x.candidate for x in result.candidate_explanations] == [2, 3, 4]


def test_negative_observation_index():
    result = explain_ensemble_observation(_ensemble(), observation_index=-1)
    assert result.observation_index == 1


def test_top_k_limits_explanations():
    result = explain_ensemble_observation(_ensemble(), top_k=3)
    assert len(result.candidate_explanations) == 3


def test_probability_to_score_is_preserved():
    result = explain_ensemble_observation(_ensemble(), observation_index=1)
    selected = result.candidate_explanations[0]
    assert selected.score == pytest.approx(selected.probability * 100)


def test_rank_percentile_is_deterministic():
    result = explain_ensemble_observation(_ensemble(), observation_index=0)
    assert result.candidate_explanations[0].rank_percentile == pytest.approx(1.0)
    assert result.candidate_explanations[1].rank_percentile == pytest.approx(0.9)


def test_gap_to_next_is_descriptive():
    result = explain_ensemble_observation(_ensemble(), observation_index=0)
    assert result.candidate_explanations[0].gap_to_next == pytest.approx(0.05)


def test_gap_to_previous_for_top_candidate_is_zero():
    result = explain_ensemble_observation(_ensemble(), observation_index=0)
    assert result.candidate_explanations[0].gap_to_previous == pytest.approx(0.0)


def test_cumulative_probability_increases():
    result = explain_ensemble_observation(_ensemble(), observation_index=0)
    values = [x.cumulative_probability_through_rank for x in result.candidate_explanations]
    assert values == sorted(values)


def test_normalized_entropy_is_bounded():
    result = explain_ensemble_observation(_ensemble(), observation_index=0)
    assert 0 <= result.normalized_entropy <= 1


def test_effective_candidate_count_is_positive():
    result = explain_ensemble_observation(_ensemble(), observation_index=0)
    assert result.effective_candidate_count > 0


def test_base_explanation_has_no_model_attribution():
    result = explain_ensemble_observation(_ensemble())
    assert result.attribution_available is False
    assert result.model_attributions == ()


def test_model_attribution_is_available_with_aligned_evaluations():
    result = explain_ensemble_observation(_ensemble(), evaluations=_evaluations())
    assert result.attribution_available is True
    assert len(result.model_attributions) == 2
    assert sum(x.contribution_share for x in result.model_attributions) == pytest.approx(1.0)


def test_model_attribution_preserves_weights():
    result = explain_ensemble_observation(_ensemble(), evaluations=_evaluations())
    assert [x.weight for x in result.model_attributions] == [0.4, 0.6]


def test_model_attribution_preserves_model_identity():
    result = explain_ensemble_observation(_ensemble(), evaluations=_evaluations())
    assert [x.model_kind for x in result.model_attributions] == ["markov", "transformer"]


def test_model_attribution_candidate_probability():
    result = explain_ensemble_observation(_ensemble(), evaluations=_evaluations())
    assert all(x.candidate_probability == pytest.approx(0.90) for x in result.model_attributions)


def test_model_attribution_weighted_contribution():
    result = explain_ensemble_observation(_ensemble(), evaluations=_evaluations())
    values = [x.weighted_contribution for x in result.model_attributions]
    assert values == pytest.approx([0.36, 0.54])


def test_attribution_count_mismatch_rejected():
    with pytest.raises(ValueError):
        explain_ensemble_observation(_ensemble(), evaluations=_evaluations()[:1])


def test_attribution_model_order_mismatch_rejected():
    rows = _evaluations()
    wrong = (
        replace(rows[0], model_kind="transformer"),
        replace(rows[1], model_kind="markov"),
    )
    with pytest.raises(ValueError):
        explain_ensemble_observation(_ensemble(), evaluations=wrong)


def test_attribution_dataset_mismatch_rejected():
    rows = _evaluations()
    with pytest.raises(ValueError):
        explain_ensemble_observation(_ensemble(), evaluations=(replace(rows[0], dataset_identity="other"), rows[1]))


def test_attribution_observation_mismatch_rejected():
    rows = _evaluations()
    with pytest.raises(ValueError):
        explain_ensemble_observation(_ensemble(), evaluations=(replace(rows[0], observations=1), rows[1]))


def test_invalid_explanation_validation():
    result = explain_ensemble_observation(_ensemble())
    broken = replace(result, selected_rank=0)
    validation = validate_sequence_explainability(broken)
    assert not validation.is_valid
    assert "INVALID_SELECTED_RANK" in validation.issues


def test_invalid_ensemble_rejected():
    with pytest.raises(ValueError):
        explain_ensemble_observation(replace(_ensemble(), probabilities=()))


def test_identity_is_deterministic():
    first = explain_ensemble_observation(_ensemble(), observation_index=0)
    second = explain_ensemble_observation(_ensemble(), observation_index=0)
    assert first.explanation_identity == second.explanation_identity


def test_identity_changes_with_observation():
    first = explain_ensemble_observation(_ensemble(), observation_index=0)
    second = explain_ensemble_observation(_ensemble(), observation_index=1)
    assert first.explanation_identity != second.explanation_identity


def test_report_contains_all_observations():
    report = build_explainability_report(_ensemble())
    assert len(report.explanations) == 2


def test_report_top_k():
    report = build_explainability_report(_ensemble(), top_k=2)
    assert all(len(x.candidate_explanations) == 2 for x in report.explanations)


def test_report_validation():
    report = build_explainability_report(_ensemble(), top_k=3)
    validation = validate_explainability_report(report)
    assert validation.is_valid
    assert validation.issues == ()


def test_report_identity_is_deterministic():
    first = build_explainability_report(_ensemble(), top_k=3)
    second = build_explainability_report(_ensemble(), top_k=3)
    assert first.report_identity == second.report_identity


def test_report_dataset_mismatch_detected():
    report = build_explainability_report(_ensemble())
    broken = replace(
        report,
        explanations=(replace(report.explanations[0], dataset_identity="other"),) + report.explanations[1:],
    )
    validation = validate_explainability_report(broken)
    assert not validation.is_valid
    assert "DATASET_IDENTITY_MISMATCH" in validation.issues


def test_report_identity_mismatch_detected():
    report = build_explainability_report(_ensemble())
    validation = validate_explainability_report(replace(report, report_identity="bad"))
    assert not validation.is_valid
    assert "INVALID_REPORT_IDENTITY" in validation.issues


def test_explanation_identity_mismatch_detected():
    result = explain_ensemble_observation(_ensemble())
    validation = validate_sequence_explainability(replace(result, explanation_identity="bad"))
    assert not validation.is_valid
    assert "INVALID_EXPLANATION_IDENTITY" in validation.issues


def test_invalid_top_k_rejected():
    with pytest.raises(ValueError):
        build_explainability_report(_ensemble(), top_k=0)


def test_invalid_observation_rejected():
    with pytest.raises(IndexError):
        explain_ensemble_observation(_ensemble(), observation_index=99)


def test_summary_contains_selected_candidate():
    result = explain_ensemble_observation(_ensemble())
    summary = explanation_summary(result)
    assert "Candidate 6" in summary
    assert "rank 1" in summary


def test_zero_candidate_is_explainable():
    ensemble = replace(
        _ensemble(),
        probabilities=(
            (0.0, 0.5, 0.5, 0, 0, 0, 0, 0, 0, 0),
            (0.0, 0.0, 0.9, 0.1, 0, 0, 0, 0, 0, 0),
        ),
    )
    result = explain_ensemble_observation(ensemble, observation_index=0, top_k=3)
    assert any(x.candidate == 0 and x.probability == 0 for x in result.candidate_explanations)


def test_full_explanation_validation():
    result = explain_ensemble_observation(_ensemble(), evaluations=_evaluations())
    validation = validate_sequence_explainability(result)
    assert validation.is_valid
    assert validation.issues == ()
