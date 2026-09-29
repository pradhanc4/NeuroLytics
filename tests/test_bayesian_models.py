from datetime import date

import pytest

from analytics.statistical_foundation import StatisticalObservation
from analytics.statistical_baseline_contract import StatisticalBaselineContract
from analytics.statistical_baseline_dataset import build_statistical_baseline_dataset
from analytics.bayesian_models import (
    BAYESIAN_VERSION,
    BayesianLikelihood,
    BayesianPosterior,
    build_bayesian_artifact,
    build_bayesian_conditional_model,
    build_bayesian_position_model,
    build_likelihood,
    build_uniform_prior,
    compare_bayesian_baselines,
    credible_interval,
    posterior_mean,
    posterior_predictive,
    posterior_probabilities,
    reproduce_bayesian_artifact,
    update_bayesian_model,
    update_posterior,
    validate_bayesian_model,
)

def dataset():
    rows = [
        (date(2026, 1, 1), [0,1,2,3,4,5,6,7]),
        (date(2026, 1, 2), [0,1,2,3,4,5,6,8]),
        (date(2026, 1, 3), [1,1,2,3,4,5,6,8]),
    ]
    obs = tuple(
        StatisticalObservation(d, f"col{i+1}", v)
        for d, values in rows
        for i, v in enumerate(values)
    )
    contract = StatisticalBaselineContract(
        market_id=1,
        analysis_version="v1",
        baseline_version="v1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        analysis_columns=tuple(f"col{i}" for i in range(1,9)),
        observation_count=len(obs),
        column_observation_counts=tuple((f"col{i}", 3) for i in range(1,9)),
    )
    return build_statistical_baseline_dataset(contract, obs)

def test_uniform_prior_has_ten_equal_parameters():
    prior = build_uniform_prior()
    assert prior.concentration == (1,) * 10
    assert prior.version == BAYESIAN_VERSION

def test_likelihood_counts_and_total():
    likelihood = build_likelihood((1,2,3,4,5,6,7,8,9,10))
    assert likelihood.total == 55
    assert likelihood.counts[9] == 10

def test_posterior_is_prior_plus_likelihood():
    posterior = update_posterior(
        build_uniform_prior(),
        BayesianLikelihood((2,0,0,0,0,0,0,0,0,0), 2),
    )
    assert posterior.concentration[0] == 3
    assert posterior.total == 12

def test_position_model_is_deterministic_and_zero_is_preserved():
    model = build_bayesian_position_model(dataset())
    assert tuple(x.position for x in model) == tuple(f"col{i}" for i in range(1,9))
    assert model[0].posterior.concentration[0] == 3

def test_position_probabilities_sum_to_one():
    model = build_bayesian_position_model(dataset())
    for item in model:
        assert abs(sum(posterior_probabilities(item.posterior)) - 1.0) < 1e-12

def test_posterior_mean_reads_digit_probability():
    posterior = update_posterior(build_uniform_prior(), build_likelihood((2,0,0,0,0,0,0,0,0,0)))
    assert posterior_mean(posterior, 0) == pytest.approx(3/12)

def test_conditional_model_contains_all_condition_digits():
    result = build_bayesian_conditional_model(dataset(), "col1", "col2")
    assert len(result) == 10
    assert tuple(x.condition_digit for x in result) == tuple(range(10))

def test_conditional_same_position_rejected():
    with pytest.raises(ValueError):
        build_bayesian_conditional_model(dataset(), "col1", "col1")

def test_credible_interval_is_ordered():
    posterior = update_posterior(build_uniform_prior(), build_likelihood((5,0,0,0,0,0,0,0,0,0)))
    interval = credible_interval(posterior, 0)
    assert 0 <= interval.lower < interval.upper <= 1

def test_posterior_predictive_is_normalized():
    posterior = update_posterior(build_uniform_prior(), build_likelihood((1,2,0,0,0,0,0,0,0,0)))
    predictive = posterior_predictive(posterior, sample_size=10)
    assert predictive.sample_size == 10
    assert sum(predictive.probabilities) == pytest.approx(1.0)

def test_bayesian_update_is_equivalent_to_direct_posterior():
    prior = build_uniform_prior()
    counts = (0,1,2,3,0,0,0,0,0,0)
    assert update_bayesian_model(prior, counts) == update_posterior(prior, build_likelihood(counts))

def test_baseline_comparison_detects_change():
    first = build_bayesian_position_model(dataset())
    changed = list(first)
    p = changed[0].posterior
    changed[0] = type(changed[0])(
        changed[0].position,
        BayesianPosterior(tuple(x + (2 if i == 0 else 0) for i, x in enumerate(p.concentration)), p.total + 2),
    )
    comparison = compare_bayesian_baselines(first, tuple(changed))
    assert comparison[0].changed is True

def test_model_validation_passes():
    assert validate_bayesian_model(build_bayesian_position_model(dataset())).is_valid

def test_artifact_is_deterministic():
    model = build_bayesian_position_model(dataset())
    first = build_bayesian_artifact(model, dataset(), "dataset-test")
    second = build_bayesian_artifact(model, dataset(), "dataset-test")
    assert reproduce_bayesian_artifact(first, second).identical is True

def test_artifact_changes_when_dataset_identity_changes():
    model = build_bayesian_position_model(dataset())
    first = build_bayesian_artifact(model, dataset(), "dataset-a")
    second = build_bayesian_artifact(model, dataset(), "dataset-b")
    assert reproduce_bayesian_artifact(first, second).identical is False

def test_invalid_probability_level_rejected():
    posterior = update_posterior(build_uniform_prior(), build_likelihood((1,0,0,0,0,0,0,0,0,0)))
    with pytest.raises(ValueError):
        credible_interval(posterior, 0, level=1.0)


def test_phase_17_version_reference_integration():
    from features.versioning_contract import build_dataset_version_reference
    model = build_bayesian_position_model(dataset())
    reference = build_dataset_version_reference(
        dataset_version="v1",
        identity="dataset-identity",
        algorithm="sha256",
        feature_version="v1",
        feature_identity="feature-identity",
    )
    from analytics.bayesian_models import (
        build_versioned_bayesian_artifact,
        prepare_bayesian_dataset,
    )
    assert prepare_bayesian_dataset(dataset()) == dataset()
    artifact = build_versioned_bayesian_artifact(model, dataset(), reference)
    assert artifact.dataset_identity == "dataset-identity"

def test_phase_17_version_reference_mismatch_rejected():
    from features.versioning_contract import build_dataset_version_reference
    from analytics.bayesian_models import validate_bayesian_dataset_version_reference
    reference = build_dataset_version_reference(
        dataset_version="wrong",
        identity="dataset-identity",
        algorithm="sha256",
        feature_version="v1",
        feature_identity="feature-identity",
    )
    with pytest.raises(ValueError):
        validate_bayesian_dataset_version_reference(dataset(), reference)
