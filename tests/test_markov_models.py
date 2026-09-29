from pathlib import Path

import pytest

from analytics.markov_models import (
    INVALID,
    MARKOV_VERSION,
    MODEL_KIND,
    VALID,
    MarkovChain,
    MarkovConfig,
    build_markov_artifact,
    build_markov_dataset,
    build_position_markov_models,
    compare_with_baseline,
    get_position_markov_model,
    load_markov_model,
    prepare_markov_dataset_from_sequences,
    reproduce_markov_artifact,
    save_markov_model,
    stationary_distribution,
    validate_markov_artifact_lineage,
    validate_markov_config,
    validate_markov_dataset,
    validate_markov_model,
)

def dataset():
    return build_markov_dataset(
        (
            (0, 1, 2, 3, 4, 5, 6),
            (1, 2, 3, 4, 5, 6, 7),
            (2, 3, 4, 5, 6, 7, 8),
            (3, 4, 5, 6, 7, 8, 9),
        ),
        "fixture-v1",
        "col1",
    )

def test_version_and_kind():
    assert MARKOV_VERSION == "28.0.0"
    assert MODEL_KIND == "markov"

def test_default_config_is_valid():
    validate_markov_config(MarkovConfig())

def test_config_rejects_bad_type():
    with pytest.raises(TypeError):
        validate_markov_config("bad")

def test_config_rejects_zero_order():
    with pytest.raises(ValueError):
        validate_markov_config(MarkovConfig(order=0))

def test_config_rejects_negative_smoothing():
    with pytest.raises(ValueError):
        validate_markov_config(MarkovConfig(smoothing=-1))

def test_config_rejects_non_digit_alphabet():
    with pytest.raises(ValueError):
        validate_markov_config(MarkovConfig(alphabet_size=5))

def test_dataset_builds():
    value = dataset()
    assert value.identity == "fixture-v1"
    assert len(value.sequences) == 4

def test_dataset_rejects_empty():
    with pytest.raises(ValueError):
        build_markov_dataset((), "x")

def test_dataset_rejects_bad_identity():
    with pytest.raises(ValueError):
        build_markov_dataset(((1, 2),), "")

def test_dataset_rejects_invalid_digit():
    with pytest.raises(ValueError):
        build_markov_dataset(((1, 2, 10),), "x")

def test_zero_is_valid():
    assert 0 in dataset().sequences[0]

def test_dataset_requires_more_than_order():
    short = build_markov_dataset(((1, 2),), "x")
    with pytest.raises(ValueError):
        validate_markov_dataset(short, MarkovConfig(order=2))

def test_prepare_adapter():
    assert prepare_markov_dataset_from_sequences(((1, 2, 3),), "x").identity == "x"

def test_fit():
    model = MarkovChain().fit(dataset())
    assert model.fitted
    assert model.contexts_

def test_unfitted_validation():
    result = validate_markov_model(MarkovChain())
    assert result.status == INVALID
    assert "MODEL_NOT_FITTED" in result.issues

def test_fitted_validation():
    result = validate_markov_model(MarkovChain().fit(dataset()))
    assert result == type(result)(VALID, ())

def test_transition_counts():
    model = MarkovChain().fit(dataset())
    assert model.transition_counts((0,)) == (0, 1, 0, 0, 0, 0, 0, 0, 0, 0)

def test_transition_probabilities_sum_to_one():
    model = MarkovChain().fit(dataset())
    assert sum(model.transition_probabilities((0,))) == pytest.approx(1.0)

def test_smoothing_gives_unseen_classes_probability():
    model = MarkovChain(MarkovConfig(smoothing=1.0)).fit(dataset())
    assert all(p > 0 for p in model.transition_probabilities((0,)))

def test_zero_smoothing_allows_zero_probability():
    model = MarkovChain(MarkovConfig(smoothing=0.0)).fit(dataset())
    assert model.transition_probabilities((0,))[0] == 0.0

def test_unknown_context_is_uniform_when_smoothed():
    model = MarkovChain().fit(dataset())
    probabilities = model.transition_probabilities((9,))
    assert sum(probabilities) == pytest.approx(1.0)
    assert len(set(probabilities)) == 1

def test_context_width_validation():
    model = MarkovChain().fit(dataset())
    with pytest.raises(ValueError):
        model.transition_probabilities((1, 2))

def test_predict_proba():
    model = MarkovChain().fit(dataset())
    rows = model.predict_proba(((0,), (1,)))
    assert len(rows) == 2
    assert all(sum(row) == pytest.approx(1.0) for row in rows)

def test_predict_next_is_deterministic():
    model = MarkovChain().fit(dataset())
    assert model.predict_next((0,), 3) == (1, 0, 2)

def test_predict_next_rejects_bad_k():
    model = MarkovChain().fit(dataset())
    with pytest.raises(ValueError):
        model.predict_next((0,), 0)

def test_log_likelihood_is_finite():
    model = MarkovChain().fit(dataset())
    assert model.log_likelihood(dataset()) < 0

def test_evaluation():
    model = MarkovChain().fit(dataset())
    metrics = model.evaluate(dataset())
    assert metrics.observations > 0
    assert 0 <= metrics.accuracy <= 1
    assert metrics.log_loss >= 0

def test_position_models():
    models = build_position_markov_models({"col1": dataset(), "col2": dataset()})
    assert len(models.models) == 2
    assert get_position_markov_model(models, "col1").fitted

def test_position_model_missing():
    models = build_position_markov_models({"col1": dataset()})
    with pytest.raises(ValueError):
        get_position_markov_model(models, "col9")

def test_position_models_require_mapping():
    with pytest.raises(ValueError):
        build_position_markov_models({})

def test_baseline_comparison():
    metrics = MarkovChain().fit(dataset()).evaluate(dataset())
    comparison = compare_with_baseline(metrics, 2.0)
    assert comparison.difference == pytest.approx(metrics.log_loss - 2.0)

def test_baseline_rejects_negative():
    metrics = MarkovChain().fit(dataset()).evaluate(dataset())
    with pytest.raises(ValueError):
        compare_with_baseline(metrics, -1)

def test_artifact_is_deterministic():
    model = MarkovChain().fit(dataset())
    first = build_markov_artifact(model, dataset())
    second = build_markov_artifact(model, dataset())
    assert first.artifact_identity == second.artifact_identity

def test_artifact_reproducibility():
    model = MarkovChain().fit(dataset())
    result = reproduce_markov_artifact(
        build_markov_artifact(model, dataset()),
        build_markov_artifact(model, dataset()),
    )
    assert result.identical

def test_artifact_changes_with_dataset_identity():
    model = MarkovChain().fit(dataset())
    first = build_markov_artifact(model, dataset())
    other = build_markov_dataset(dataset().sequences, "different")
    second = build_markov_artifact(model, other)
    assert first.artifact_identity != second.artifact_identity

def test_lineage_validation():
    model = MarkovChain().fit(dataset())
    artifact = build_markov_artifact(model, dataset())
    validate_markov_artifact_lineage(artifact, dataset(), model)

def test_lineage_rejects_identity_mismatch():
    model = MarkovChain().fit(dataset())
    artifact = build_markov_artifact(model, dataset())
    other = build_markov_dataset(dataset().sequences, "other")
    with pytest.raises(ValueError):
        validate_markov_artifact_lineage(artifact, other, model)

def test_persistence(tmp_path: Path):
    model = MarkovChain().fit(dataset())
    path = save_markov_model(model, tmp_path / "markov.joblib")
    loaded = load_markov_model(path)
    assert loaded.predict_next((0,)) == model.predict_next((0,))

def test_persistence_creates_parent(tmp_path: Path):
    model = MarkovChain().fit(dataset())
    path = save_markov_model(model, tmp_path / "nested" / "model.joblib")
    assert path.exists()

def test_load_rejects_wrong_artifact(tmp_path: Path):
    path = tmp_path / "bad.joblib"
    import joblib
    joblib.dump({"bad": True}, path)
    with pytest.raises(ValueError):
        load_markov_model(path)

def test_stationary_distribution():
    model = MarkovChain().fit(dataset())
    values = stationary_distribution(model, (0,), 5)
    assert len(values) == 10
    assert sum(values) == pytest.approx(1.0)

def test_stationary_distribution_rejects_bad_steps():
    model = MarkovChain().fit(dataset())
    with pytest.raises(ValueError):
        stationary_distribution(model, (0,), 0)

def test_order_two_model():
    value = build_markov_dataset(
        (
            (0, 1, 2, 3, 4, 5),
            (1, 2, 3, 4, 5, 6),
            (2, 3, 4, 5, 6, 7),
        ),
        "order2",
    )
    model = MarkovChain(MarkovConfig(order=2)).fit(value)
    assert model.transition_counts((0, 1))[2] == 1

def test_order_two_prediction():
    value = build_markov_dataset(((0, 1, 2, 3, 4, 5),), "x")
    model = MarkovChain(MarkovConfig(order=2)).fit(value)
    assert model.predict_next((0, 1), 1) == (2,)

def test_model_classes_are_digits():
    assert MarkovChain().classes_ == tuple(range(10))

def test_models_are_reproducible():
    first = MarkovChain().fit(dataset())
    second = MarkovChain().fit(dataset())
    assert build_markov_artifact(first, dataset()).artifact_identity == build_markov_artifact(second, dataset()).artifact_identity

def test_model_requires_fit_for_counts():
    with pytest.raises(ValueError):
        MarkovChain().transition_counts((0,))

def test_model_requires_fit_for_prediction():
    with pytest.raises(ValueError):
        MarkovChain().predict_next((0,))

def test_invalid_model_type():
    result = validate_markov_model("bad")
    assert result.status == INVALID

def test_config_order_ten():
    validate_markov_config(MarkovConfig(order=10))

def test_config_rejects_order_eleven():
    with pytest.raises(ValueError):
        validate_markov_config(MarkovConfig(order=11))

def test_dataset_target_name():
    value = build_markov_dataset(((0, 1, 2),), "x", "col8")
    assert value.target_name == "col8"
