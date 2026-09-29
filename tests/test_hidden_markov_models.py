from pathlib import Path

import pytest

from analytics.hidden_markov_models import (
    HMM_VERSION,
    INVALID,
    MODEL_KIND,
    VALID,
    HMMConfig,
    HiddenMarkovModel,
    build_hmm_artifact,
    build_hmm_dataset,
    build_position_hmm_models,
    compare_hmm_with_baseline,
    get_position_hmm_model,
    load_hmm_model,
    prepare_hmm_dataset_from_sequences,
    reproduce_hmm_artifact,
    save_hmm_model,
    validate_hmm_artifact_lineage,
    validate_hmm_config,
    validate_hmm_dataset,
    validate_hmm_model,
)


def dataset():
    return build_hmm_dataset(
        (
            (0, 1, 2, 3, 4, 5, 6, 7),
            (1, 2, 3, 4, 5, 6, 7, 8),
            (2, 3, 4, 5, 6, 7, 8, 9),
            (3, 4, 5, 6, 7, 8, 9, 0),
        ),
        "hmm-fixture-v1",
        "col1",
    )


def fitted():
    return HiddenMarkovModel(HMMConfig(max_iterations=4)).fit(dataset())


def test_version_and_kind():
    assert HMM_VERSION == "29.0.0"
    assert MODEL_KIND == "hidden_markov"


def test_default_config():
    validate_hmm_config(HMMConfig())


def test_config_type():
    with pytest.raises(TypeError):
        validate_hmm_config("bad")


def test_config_rejects_zero_states():
    with pytest.raises(ValueError):
        validate_hmm_config(HMMConfig(n_states=0))


def test_config_rejects_non_digit_observations():
    with pytest.raises(ValueError):
        validate_hmm_config(HMMConfig(n_observations=5))


def test_config_rejects_negative_smoothing():
    with pytest.raises(ValueError):
        validate_hmm_config(HMMConfig(smoothing=-1))


def test_config_rejects_bad_iterations():
    with pytest.raises(ValueError):
        validate_hmm_config(HMMConfig(max_iterations=0))


def test_config_rejects_negative_tolerance():
    with pytest.raises(ValueError):
        validate_hmm_config(HMMConfig(tolerance=-1))


def test_dataset_builds():
    value = dataset()
    assert value.identity == "hmm-fixture-v1"
    assert len(value.sequences) == 4


def test_dataset_rejects_empty():
    with pytest.raises(ValueError):
        build_hmm_dataset((), "x")


def test_dataset_rejects_bad_identity():
    with pytest.raises(ValueError):
        build_hmm_dataset(((1, 2),), "")


def test_dataset_rejects_bad_target_name():
    with pytest.raises(ValueError):
        build_hmm_dataset(((1, 2),), "x", "")


def test_dataset_rejects_invalid_digit():
    with pytest.raises(ValueError):
        build_hmm_dataset(((1, 10),), "x")


def test_zero_is_valid_observation():
    assert 0 in dataset().sequences[-1]


def test_dataset_validation():
    validate_hmm_dataset(dataset())


def test_dataset_type_validation():
    with pytest.raises(TypeError):
        validate_hmm_dataset("bad")


def test_prepare_adapter():
    assert prepare_hmm_dataset_from_sequences(((0, 1, 2),), "x").identity == "x"


def test_model_initial_state():
    model = HiddenMarkovModel()
    assert not model.fitted
    assert model.classes_ == tuple(range(10))


def test_unfitted_validation():
    result = validate_hmm_model(HiddenMarkovModel())
    assert result.status == INVALID
    assert "MODEL_NOT_FITTED" in result.issues


def test_fit_marks_model_fitted():
    model = fitted()
    assert model.fitted
    assert model.training_result is not None


def test_training_result_has_iterations():
    result = fitted().training_result
    assert result.iterations >= 1
    assert result.log_likelihood <= 0


def test_initial_probabilities_normalize():
    model = fitted()
    assert sum(model.initial_probabilities) == pytest.approx(1.0)


def test_transition_rows_normalize():
    model = fitted()
    assert all(sum(row) == pytest.approx(1.0) for row in model.transition_matrix)


def test_emission_rows_normalize():
    model = fitted()
    assert all(sum(row) == pytest.approx(1.0) for row in model.emission_matrix)


def test_fitted_validation_is_valid():
    result = validate_hmm_model(fitted())
    assert result.status == VALID
    assert result.issues == ()


def test_forward_state_probabilities():
    rows = fitted().predict_state_proba((0, 1, 2, 3))
    assert len(rows) == 4
    assert all(sum(row) == pytest.approx(1.0) for row in rows)


def test_forward_requires_fit():
    with pytest.raises(ValueError):
        HiddenMarkovModel().predict_state_proba((0, 1))


def test_forward_rejects_bad_observation():
    with pytest.raises(ValueError):
        fitted().predict_state_proba((0, 10))


def test_backward_posterior_probabilities():
    rows = fitted().posterior_state_proba((0, 1, 2, 3))
    assert len(rows) == 4
    assert all(sum(row) == pytest.approx(1.0) for row in rows)


def test_posterior_requires_fit():
    with pytest.raises(ValueError):
        HiddenMarkovModel().posterior_state_proba((0, 1))


def test_viterbi_path_length():
    path = fitted().viterbi((0, 1, 2, 3, 4))
    assert len(path) == 5


def test_viterbi_state_range():
    model = fitted()
    path = model.viterbi((0, 1, 2, 3))
    assert all(0 <= state < model.config.n_states for state in path)


def test_viterbi_is_deterministic():
    model = fitted()
    sequence = (0, 1, 2, 3, 4)
    assert model.viterbi(sequence) == model.viterbi(sequence)


def test_next_probability_shape():
    probabilities = fitted().predict_next_proba((0, 1, 2))
    assert len(probabilities) == 10
    assert sum(probabilities) == pytest.approx(1.0)


def test_next_probability_is_nonnegative():
    assert all(p >= 0 for p in fitted().predict_next_proba((0, 1, 2)))


def test_next_prediction_is_deterministic():
    model = fitted()
    assert model.predict_next((0, 1, 2), 3) == model.predict_next((0, 1, 2), 3)


def test_next_prediction_top_k():
    assert len(fitted().predict_next((0, 1, 2), 4)) == 4


def test_next_prediction_rejects_bad_k():
    with pytest.raises(ValueError):
        fitted().predict_next((0, 1, 2), 0)


def test_log_likelihood():
    value = fitted().log_likelihood(dataset())
    assert math_is_finite(value)
    assert value <= 0


def test_evaluate():
    metrics = fitted().evaluate(dataset())
    assert metrics.observations == sum(len(row) - 1 for row in dataset().sequences)
    assert metrics.log_loss >= 0
    assert 0 <= metrics.accuracy <= 1


def test_baseline_comparison():
    metrics = fitted().evaluate(dataset())
    comparison = compare_hmm_with_baseline(metrics, 3.0)
    assert comparison.difference == pytest.approx(metrics.log_loss - 3.0)


def test_baseline_rejects_negative():
    metrics = fitted().evaluate(dataset())
    with pytest.raises(ValueError):
        compare_hmm_with_baseline(metrics, -1)


def test_position_models():
    models = build_position_hmm_models({"col1": dataset(), "col2": dataset()}, HMMConfig(max_iterations=2))
    assert len(models.models) == 2
    assert get_position_hmm_model(models, "col1").fitted


def test_position_model_missing():
    models = build_position_hmm_models({"col1": dataset()}, HMMConfig(max_iterations=2))
    with pytest.raises(ValueError):
        get_position_hmm_model(models, "col9")


def test_position_models_require_mapping():
    with pytest.raises(ValueError):
        build_position_hmm_models({}, HMMConfig(max_iterations=2))


def test_position_models_are_sorted():
    models = build_position_hmm_models({"col8": dataset(), "col1": dataset()}, HMMConfig(max_iterations=1))
    assert tuple(name for name, _ in models.models) == ("col1", "col8")


def test_artifact_is_deterministic():
    model = fitted()
    first = build_hmm_artifact(model, dataset())
    second = build_hmm_artifact(model, dataset())
    assert first.artifact_identity == second.artifact_identity


def test_artifact_reproducibility():
    model = fitted()
    result = reproduce_hmm_artifact(
        build_hmm_artifact(model, dataset()),
        build_hmm_artifact(model, dataset()),
    )
    assert result.identical


def test_artifact_changes_with_dataset_identity():
    model = fitted()
    first = build_hmm_artifact(model, dataset())
    other = build_hmm_dataset(dataset().sequences, "other")
    second = build_hmm_artifact(model, other)
    assert first.artifact_identity != second.artifact_identity


def test_lineage_validation():
    model = fitted()
    artifact = build_hmm_artifact(model, dataset())
    validate_hmm_artifact_lineage(artifact, dataset(), model)


def test_lineage_rejects_identity_mismatch():
    model = fitted()
    artifact = build_hmm_artifact(model, dataset())
    other = build_hmm_dataset(dataset().sequences, "other")
    with pytest.raises(ValueError):
        validate_hmm_artifact_lineage(artifact, other, model)


def test_lineage_rejects_configuration_mismatch():
    model = fitted()
    artifact = build_hmm_artifact(model, dataset())
    other = HiddenMarkovModel(HMMConfig(n_states=9, max_iterations=1)).fit(dataset())
    with pytest.raises(ValueError):
        validate_hmm_artifact_lineage(artifact, dataset(), other)


def test_persistence(tmp_path: Path):
    model = fitted()
    path = save_hmm_model(model, tmp_path / "hmm.joblib")
    loaded = load_hmm_model(path)
    assert loaded.viterbi((0, 1, 2, 3)) == model.viterbi((0, 1, 2, 3))


def test_persistence_creates_parent(tmp_path: Path):
    path = save_hmm_model(fitted(), tmp_path / "nested" / "hmm.joblib")
    assert path.exists()


def test_load_rejects_wrong_artifact(tmp_path: Path):
    import joblib
    path = tmp_path / "bad.joblib"
    joblib.dump({"bad": True}, path)
    with pytest.raises(ValueError):
        load_hmm_model(path)


def test_reproducible_training():
    first = fitted()
    second = fitted()
    assert build_hmm_artifact(first, dataset()).artifact_identity == build_hmm_artifact(second, dataset()).artifact_identity


def test_training_with_zero_smoothing():
    model = HiddenMarkovModel(HMMConfig(smoothing=0.0, max_iterations=2)).fit(dataset())
    assert model.fitted
    assert all(sum(row) == pytest.approx(1.0) for row in model.emission_matrix)


def test_single_observation_sequence_support():
    value = build_hmm_dataset(((0,), (1,), (2,), (3,)), "singletons")
    model = HiddenMarkovModel(HMMConfig(max_iterations=2)).fit(value)
    assert model.fitted


def test_single_sequence_support():
    value = build_hmm_dataset(((0, 1, 2, 3, 4, 5),), "single")
    model = HiddenMarkovModel(HMMConfig(max_iterations=2)).fit(value)
    assert model.fitted


def test_observation_zero_survives_prediction():
    model = fitted()
    assert len(model.predict_next_proba((0,))) == 10


def test_config_seed_is_reproducible():
    first = HiddenMarkovModel(HMMConfig(max_iterations=2, random_seed=77)).fit(dataset())
    second = HiddenMarkovModel(HMMConfig(max_iterations=2, random_seed=77)).fit(dataset())
    assert build_hmm_artifact(first, dataset()).artifact_identity == build_hmm_artifact(second, dataset()).artifact_identity


def test_different_seed_changes_artifact():
    first = HiddenMarkovModel(HMMConfig(max_iterations=2, random_seed=1)).fit(dataset())
    second = HiddenMarkovModel(HMMConfig(max_iterations=2, random_seed=2)).fit(dataset())
    assert build_hmm_artifact(first, dataset()).artifact_identity != build_hmm_artifact(second, dataset()).artifact_identity


def test_predict_state_probabilities_are_deterministic():
    model = fitted()
    assert model.predict_state_proba((0, 1, 2)) == model.predict_state_proba((0, 1, 2))


def test_posterior_probabilities_are_deterministic():
    model = fitted()
    assert model.posterior_state_proba((0, 1, 2)) == model.posterior_state_proba((0, 1, 2))


def test_training_iteration_limit():
    model = HiddenMarkovModel(HMMConfig(max_iterations=1)).fit(dataset())
    assert model.training_result.iterations == 1


def test_training_result_converged_flag_is_boolean():
    assert isinstance(fitted().training_result.converged, bool)


def test_invalid_model_type():
    result = validate_hmm_model("bad")
    assert result.status == INVALID


def test_model_classes_are_digits():
    assert HiddenMarkovModel().classes_ == tuple(range(10))


def test_dataset_target_name():
    assert build_hmm_dataset(((0, 1, 2),), "x", "col8").target_name == "col8"


def test_state_count_changes_matrix_shape():
    model = HiddenMarkovModel(HMMConfig(n_states=4, max_iterations=2)).fit(dataset())
    assert len(model.initial_probabilities) == 4
    assert len(model.transition_matrix) == 4
    assert len(model.emission_matrix) == 4


def test_state_count_is_independent_of_observation_count():
    model = HiddenMarkovModel(HMMConfig(n_states=4, max_iterations=2)).fit(dataset())
    assert all(len(row) == 10 for row in model.emission_matrix)


def math_is_finite(value):
    import math
    return math.isfinite(value)
