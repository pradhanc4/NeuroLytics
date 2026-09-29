from pathlib import Path

import pytest

from analytics.lstm import (
    INVALID,
    VALID,
    LSTM_VERSION,
    LSTMArtifact,
    LSTMClassifier,
    LSTMConfig,
    LSTMDataset,
    build_lstm_artifact,
    build_lstm_dataset,
    build_position_lstm_models,
    chronological_lstm_split,
    compare_with_baseline,
    get_position_lstm_model,
    load_lstm_model,
    prepare_lstm_dataset_from_sequences,
    reproduce_lstm_artifact,
    save_lstm_model,
    validate_lstm_artifact_lineage,
    validate_lstm_config,
    validate_lstm_dataset,
    validate_lstm_model,
)


def cfg(**overrides):
    values = dict(sequence_length=3, hidden_size=4, learning_rate=0.03, epochs=3,
                  batch_size=4, seed=30, patience=3)
    values.update(overrides)
    return LSTMConfig(**values)


def dataset():
    return build_lstm_dataset(
        [[0, 1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6, 7],
         [2, 3, 4, 5, 6, 7, 8], [3, 4, 5, 6, 7, 8, 9]],
        "phase30-fixture",
    )


def test_version_and_kind():
    from analytics.lstm import MODEL_KIND
    assert LSTM_VERSION == "30.0.0"
    assert MODEL_KIND == "lstm"


def test_default_config():
    c = LSTMConfig()
    validate_lstm_config(c)
    assert c.alphabet_size == 10
    assert c.hidden_size == 16


@pytest.mark.parametrize("field,value", [
    ("sequence_length", 0), ("hidden_size", 0), ("epochs", 0),
    ("batch_size", 0), ("patience", 0),
])
def test_invalid_positive_integer_config(field, value):
    values = cfg().__dict__
    values[field] = value
    with pytest.raises(ValueError):
        validate_lstm_config(LSTMConfig(**values))


def test_invalid_learning_rate():
    with pytest.raises(ValueError):
        validate_lstm_config(cfg(learning_rate=0))


def test_invalid_alphabet():
    with pytest.raises(ValueError):
        validate_lstm_config(cfg(alphabet_size=9))


def test_invalid_dataset_identity():
    with pytest.raises(ValueError):
        build_lstm_dataset([[0, 1, 2, 3]], "")


def test_zero_is_valid():
    ds = build_lstm_dataset([[0, 1, 0, 2]], "zero")
    validate_lstm_dataset(ds, cfg(sequence_length=2))
    assert 0 in ds.sequences[0]


@pytest.mark.parametrize("bad", [[-1, 1, 2, 3], [10, 1, 2, 3], [True, 1, 2, 3]])
def test_invalid_digit_data(bad):
    with pytest.raises(ValueError):
        build_lstm_dataset([bad], "bad")


def test_dataset_contract():
    ds = dataset()
    assert isinstance(ds, LSTMDataset)
    assert len(ds.sequences) == 4


def test_prepare_alias():
    ds = prepare_lstm_dataset_from_sequences([[0, 1, 2, 3]], "alias")
    assert ds.identity == "alias"


def test_dataset_requires_enough_history():
    ds = build_lstm_dataset([[0, 1, 2]], "short")
    with pytest.raises(ValueError):
        validate_lstm_dataset(ds, cfg(sequence_length=3))


def test_chronological_split():
    train, test = chronological_lstm_split(dataset(), 0.25)
    assert train.sequences == dataset().sequences[:3]
    assert test.sequences == dataset().sequences[3:]


def test_split_rejects_bad_fraction():
    with pytest.raises(ValueError):
        chronological_lstm_split(dataset(), 1.0)


def test_model_initialization_is_deterministic():
    a = LSTMClassifier(cfg())
    b = LSTMClassifier(cfg())
    assert (a.W == b.W).all()
    assert (a.U == b.U).all()
    assert (a.V == b.V).all()


def test_model_starts_unfitted():
    model = LSTMClassifier(cfg())
    assert not model.fitted
    assert validate_lstm_model(model).status == INVALID


def test_fit_returns_model():
    model = LSTMClassifier(cfg()).fit(dataset())
    assert model.fitted


def test_training_history():
    model = LSTMClassifier(cfg(epochs=4)).fit(dataset())
    assert model.training_history is not None
    assert 1 <= model.training_history.epochs_completed <= 4
    assert len(model.training_history.losses) == model.training_history.epochs_completed


def test_fit_is_reproducible():
    a = LSTMClassifier(cfg()).fit(dataset())
    b = LSTMClassifier(cfg()).fit(dataset())
    assert (a.W == b.W).all()
    assert (a.U == b.U).all()
    assert (a.V == b.V).all()
    assert a.training_history == b.training_history


def test_predict_proba_shape_and_normalization():
    model = LSTMClassifier(cfg()).fit(dataset())
    probabilities = model.predict_proba([[1, 2, 3], [4, 5, 6]])
    assert len(probabilities) == 2
    assert len(probabilities[0]) == 10
    assert abs(sum(probabilities[0]) - 1.0) < 1e-9


def test_predict_next_top_k():
    model = LSTMClassifier(cfg()).fit(dataset())
    prediction = model.predict_next([4, 5, 6], 5)
    assert len(prediction) == 5
    assert len(set(prediction)) == 5
    assert all(0 <= value <= 9 for value in prediction)


def test_predict_top_k_limit():
    model = LSTMClassifier(cfg()).fit(dataset())
    assert len(model.predict_next([4, 5, 6], 50)) == 10


def test_predict_rejects_wrong_window():
    model = LSTMClassifier(cfg()).fit(dataset())
    with pytest.raises(ValueError):
        model.predict_proba([[1, 2]])


def test_predict_requires_fit():
    model = LSTMClassifier(cfg())
    with pytest.raises(ValueError):
        model.predict_next([1, 2, 3])


def test_evaluation_metrics():
    model = LSTMClassifier(cfg()).fit(dataset())
    metrics = model.evaluate(dataset())
    assert metrics.observations == 16
    assert metrics.log_loss >= 0
    assert 0 <= metrics.accuracy <= 1


def test_log_likelihood():
    model = LSTMClassifier(cfg()).fit(dataset())
    metrics = model.evaluate(dataset())
    assert model.log_likelihood(dataset()) == pytest.approx(-metrics.log_loss * metrics.observations)


def test_baseline_comparison():
    model = LSTMClassifier(cfg()).fit(dataset())
    metrics = model.evaluate(dataset())
    comparison = compare_with_baseline(metrics, 2.3)
    assert comparison.baseline_log_loss == 2.3
    assert comparison.difference == pytest.approx(metrics.log_loss - 2.3)


def test_negative_baseline_rejected():
    model = LSTMClassifier(cfg()).fit(dataset())
    with pytest.raises(ValueError):
        compare_with_baseline(model.evaluate(dataset()), -1)


def test_model_validation_after_fit():
    model = LSTMClassifier(cfg()).fit(dataset())
    result = validate_lstm_model(model)
    assert result.status == VALID
    assert result.issues == ()


def test_artifact_identity_is_deterministic():
    model = LSTMClassifier(cfg()).fit(dataset())
    first = build_lstm_artifact(model, dataset())
    second = build_lstm_artifact(model, dataset())
    assert first.artifact_identity == second.artifact_identity


def test_artifact_fields():
    model = LSTMClassifier(cfg()).fit(dataset())
    artifact = build_lstm_artifact(model, dataset())
    assert isinstance(artifact, LSTMArtifact)
    assert artifact.model_kind == "lstm"
    assert artifact.model_version == LSTM_VERSION
    assert artifact.sequence_length == 3
    assert artifact.hidden_size == 4


def test_artifact_lineage():
    model = LSTMClassifier(cfg()).fit(dataset())
    artifact = build_lstm_artifact(model, dataset())
    validate_lstm_artifact_lineage(artifact, dataset(), model)


def test_artifact_lineage_rejects_dataset():
    model = LSTMClassifier(cfg()).fit(dataset())
    artifact = build_lstm_artifact(model, dataset())
    other = build_lstm_dataset(dataset().sequences, "other")
    with pytest.raises(ValueError):
        validate_lstm_artifact_lineage(artifact, other, model)


def test_reproducibility_result():
    model = LSTMClassifier(cfg()).fit(dataset())
    artifact = build_lstm_artifact(model, dataset())
    result = reproduce_lstm_artifact(artifact, artifact)
    assert result.identical
    assert result.first_identity == artifact.artifact_identity


def test_position_models():
    ds = dataset()
    models = build_position_lstm_models({"col1": ds, "col2": ds}, cfg(epochs=2))
    assert [name for name, _ in models.models] == ["col1", "col2"]
    assert get_position_lstm_model(models, "col1").fitted


def test_position_model_missing():
    models = build_position_lstm_models({"col1": dataset()}, cfg(epochs=1))
    with pytest.raises(ValueError):
        get_position_lstm_model(models, "col9")


def test_position_models_require_mapping():
    with pytest.raises(ValueError):
        build_position_lstm_models({}, cfg())


def test_persistence(tmp_path: Path):
    model = LSTMClassifier(cfg()).fit(dataset())
    path = tmp_path / "lstm.joblib"
    saved = save_lstm_model(model, path)
    loaded = load_lstm_model(saved)
    assert loaded.fitted
    assert loaded.predict_next([4, 5, 6], 3) == model.predict_next([4, 5, 6], 3)


def test_persistence_parent_creation(tmp_path: Path):
    model = LSTMClassifier(cfg()).fit(dataset())
    path = tmp_path / "nested" / "lstm.joblib"
    save_lstm_model(model, path)
    assert path.exists()


def test_training_history_early_stopping():
    model = LSTMClassifier(cfg(epochs=10, patience=1)).fit(dataset())
    assert model.training_history.epochs_completed <= 10


def test_gradient_values_remain_finite():
    model = LSTMClassifier(cfg(epochs=2)).fit(dataset())
    assert validate_lstm_model(model).is_valid
