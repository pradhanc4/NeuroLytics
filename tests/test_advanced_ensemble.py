import pytest

from analytics.advanced_ensemble import (
    SEQUENCE_ADVANCED_ENSEMBLE_VERSION,
    VALID,
    analyze_ensemble_agreement,
    build_advanced_ensemble_report,
    build_consensus,
    build_consensus_weights,
    consensus_summary,
    consensus_top_candidate,
    validate_advanced_ensemble_report,
    validate_consensus,
    validate_consensus_weights,
)
from analytics.sequence_ensemble import build_sequence_ensemble
from tests.test_sequence_ensemble import make_evaluations


def make_ensembles():
    evaluations = make_evaluations()
    return (
        build_sequence_ensemble(evaluations, "equal_weight"),
        build_sequence_ensemble(evaluations, "inverse_log_loss"),
        build_sequence_ensemble(evaluations, "softmax_score"),
    )


def test_version():
    assert SEQUENCE_ADVANCED_ENSEMBLE_VERSION == "38.0.0"


def test_agreement_has_all_ensembles():
    ensembles = make_ensembles()
    result = analyze_ensemble_agreement(ensembles)
    assert len(result.ensemble_identities) == 3
    assert result.mean_pairwise_js_divergence >= 0
    assert result.max_pairwise_js_divergence >= result.mean_pairwise_js_divergence
    assert 0 <= result.mean_pairwise_total_variation <= 1
    assert 0 <= result.agreement_score <= 1
    assert result.identity.startswith("sequence-agreement-")


def test_agreement_is_deterministic():
    ensembles = make_ensembles()
    assert analyze_ensemble_agreement(ensembles) == analyze_ensemble_agreement(ensembles)


def test_agreement_rejects_empty():
    with pytest.raises(ValueError):
        analyze_ensemble_agreement([])


def test_agreement_requires_two():
    with pytest.raises(ValueError):
        analyze_ensemble_agreement(make_ensembles()[:1])


def test_weights_equal():
    result = build_consensus_weights(make_ensembles(), "equal_weight")
    assert result.weights == pytest.approx((1/3, 1/3, 1/3))
    assert validate_consensus_weights(result).status == VALID


def test_weights_inverse_disagreement_normalize():
    result = build_consensus_weights(make_ensembles())
    assert sum(result.weights) == pytest.approx(1.0)
    assert all(value >= 0 for value in result.weights)
    assert result.method == "inverse_disagreement"
    assert validate_consensus_weights(result).status == VALID


def test_weights_are_deterministic():
    ensembles = make_ensembles()
    a = build_consensus_weights(ensembles)
    b = build_consensus_weights(ensembles)
    assert a.weights == b.weights
    assert a.identity == b.identity


def test_weights_reject_unknown_method():
    with pytest.raises(ValueError):
        build_consensus_weights(make_ensembles(), "bad")


def test_consensus_probability_shape():
    result = build_consensus(make_ensembles())
    assert result.observations == len(result.targets)
    assert len(result.probabilities) == result.observations
    assert all(len(row) == 10 for row in result.probabilities)
    assert all(sum(row) == pytest.approx(1.0) for row in result.probabilities)


def test_consensus_top_candidates_are_ranked():
    result = build_consensus(make_ensembles())
    for row, ranking in zip(result.probabilities, result.top_candidates):
        assert ranking == tuple(sorted(range(10), key=lambda digit: (-row[digit], digit)))


def test_consensus_margin_nonnegative():
    result = build_consensus(make_ensembles())
    assert all(value >= 0 for value in result.probability_margin)


def test_consensus_entropy_diagnostics():
    result = build_consensus(make_ensembles())
    assert all(value >= 0 for value in result.entropy)
    assert all(0 <= value <= 1 for value in result.normalized_entropy)
    assert all(value >= 1 for value in result.effective_candidate_count)


def test_consensus_lineage():
    ensembles = make_ensembles()
    result = build_consensus(ensembles)
    assert result.dataset_identity == ensembles[0].dataset_identity
    assert result.ensemble_identities == tuple(item.ensemble_identity for item in ensembles)
    assert result.consensus_identity.startswith("sequence-consensus-")


def test_consensus_validation():
    result = build_consensus(make_ensembles())
    assert validate_consensus(result).status == VALID


def test_report_builds():
    report = build_advanced_ensemble_report(make_ensembles())
    assert report.version == "38.0.0"
    assert report.agreement.identity.startswith("sequence-agreement-")
    assert report.weights.identity.startswith("sequence-consensus-weights-")
    assert report.consensus.consensus_identity.startswith("sequence-consensus-")
    assert report.report_identity.startswith("sequence-advanced-ensemble-report-")


def test_report_validation():
    report = build_advanced_ensemble_report(make_ensembles())
    assert validate_advanced_ensemble_report(report).status == VALID


def test_report_deterministic():
    ensembles = make_ensembles()
    a = build_advanced_ensemble_report(ensembles)
    b = build_advanced_ensemble_report(ensembles)
    assert a.report_identity == b.report_identity


def test_top_candidate_latest_and_explicit():
    result = build_consensus(make_ensembles())
    assert consensus_top_candidate(result) == consensus_top_candidate(result, -1)
    assert consensus_top_candidate(result, 0) == result.top_candidates[0][0]


def test_top_candidate_rejects_invalid_index():
    result = build_consensus(make_ensembles())
    with pytest.raises(IndexError):
        consensus_top_candidate(result, 999)


def test_summary():
    result = build_consensus(make_ensembles())
    summary = consensus_summary(result)
    assert "Consensus candidate" in summary
    assert "agreement score" in summary


def test_invalid_weight_validation():
    result = build_consensus_weights(make_ensembles())
    object.__setattr__(result, "weights", (1.0, 1.0, 1.0))
    assert validate_consensus_weights(result).status != VALID


def test_invalid_consensus_validation():
    result = build_consensus(make_ensembles())
    object.__setattr__(result, "agreement_score", 2.0)
    assert validate_consensus(result).status != VALID


def test_invalid_report_validation():
    report = build_advanced_ensemble_report(make_ensembles())
    object.__setattr__(report, "report_identity", "bad")
    assert validate_advanced_ensemble_report(report).status != VALID
import math

def test_mixed_dataset_rejected():
    ensembles = list(make_ensembles())
    other = build_sequence_ensemble(make_evaluations(), "equal_weight")
    object.__setattr__(other, "dataset_identity", "different")
    ensembles[2] = other
    with pytest.raises(ValueError):
        build_consensus(ensembles)


def test_duplicate_identity_rejected():
    ensembles = list(make_ensembles())
    object.__setattr__(ensembles[1], "ensemble_identity", ensembles[0].ensemble_identity)
    with pytest.raises(ValueError):
        build_consensus(ensembles)


def test_invalid_probability_row_rejected():
    ensembles = list(make_ensembles())
    bad = ensembles[0]
    probabilities = list(bad.probabilities)
    probabilities[0] = tuple([0.2] * 10)
    object.__setattr__(bad, "probabilities", tuple(probabilities))
    with pytest.raises(ValueError):
        analyze_ensemble_agreement(ensembles)


def test_equal_weight_report():
    report = build_advanced_ensemble_report(make_ensembles(), "equal_weight")
    assert report.weights.weights == pytest.approx((1/3, 1/3, 1/3))
    assert validate_advanced_ensemble_report(report).status == VALID


def test_consensus_target_alignment():
    ensembles = make_ensembles()
    result = build_consensus(ensembles)
    assert result.targets == ensembles[0].targets


def test_consensus_observation_alignment():
    ensembles = make_ensembles()
    result = build_consensus(ensembles)
    assert result.observations == ensembles[0].observations


def test_agreement_score_tracks_divergence():
    ensembles = make_ensembles()
    agreement = analyze_ensemble_agreement(ensembles)
    assert agreement.agreement_score == pytest.approx(1.0 - agreement.mean_pairwise_js_divergence)


def test_total_variation_range():
    agreement = analyze_ensemble_agreement(make_ensembles())
    assert 0 <= agreement.mean_pairwise_total_variation <= 1


def test_max_js_not_below_mean():
    agreement = analyze_ensemble_agreement(make_ensembles())
    assert agreement.max_pairwise_js_divergence + 1e-12 >= agreement.mean_pairwise_js_divergence


def test_consensus_identity_stable():
    ensembles = make_ensembles()
    a = build_consensus(ensembles)
    b = build_consensus(ensembles)
    assert a.consensus_identity == b.consensus_identity
    assert a.probabilities == b.probabilities


def test_weight_identity_changes_with_method():
    ensembles = make_ensembles()
    equal = build_consensus_weights(ensembles, "equal_weight")
    inverse = build_consensus_weights(ensembles, "inverse_disagreement")
    assert equal.identity != inverse.identity


def test_report_dataset_identity():
    ensembles = make_ensembles()
    report = build_advanced_ensemble_report(ensembles)
    assert report.dataset_identity == ensembles[0].dataset_identity


def test_report_contains_same_ensemble_ids():
    ensembles = make_ensembles()
    report = build_advanced_ensemble_report(ensembles)
    ids = tuple(item.ensemble_identity for item in ensembles)
    assert report.agreement.ensemble_identities == ids
    assert report.weights.ensemble_identities == ids
    assert report.consensus.ensemble_identities == ids


def test_consensus_weights_are_nonnegative():
    result = build_consensus_weights(make_ensembles())
    assert all(value >= 0 for value in result.weights)


def test_probability_margin_matches_top_two():
    result = build_consensus(make_ensembles())
    for row, margin, ranking in zip(result.probabilities, result.probability_margin, result.top_candidates):
        assert margin == pytest.approx(row[ranking[0]] - row[ranking[1]])


def test_effective_count_matches_entropy():
    result = build_consensus(make_ensembles())
    for entropy, effective in zip(result.entropy, result.effective_candidate_count):
        assert effective == pytest.approx(math.exp(entropy))


def test_report_validation_detects_dataset_mismatch():
    report = build_advanced_ensemble_report(make_ensembles())
    object.__setattr__(report, "dataset_identity", "other")
    assert validate_advanced_ensemble_report(report).status != VALID


def test_consensus_validation_detects_weight_length():
    result = build_consensus(make_ensembles())
    object.__setattr__(result, "weights", (1.0,))
    assert validate_consensus(result).status != VALID
