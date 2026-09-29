
from pathlib import Path

import pytest

from analytics.gru import (
    INVALID,
    VALID,
    GRU_VERSION,
    GRUArtifact,
    GRUClassifier,
    GRUConfig,
    GRUDataset,
    build_gru_artifact,
    build_gru_dataset,
    build_position_gru_models,
    chronological_gru_split,
    compare_with_baseline,
    get_position_gru_model,
    load_gru_model,
    prepare_gru_dataset_from_sequences,
    reproduce_gru_artifact,
    save_gru_model,
    validate_gru_artifact_lineage,
    validate_gru_config,
    validate_gru_dataset,
    validate_gru_model,
)


def cfg(**overrides):
    values = dict(sequence_length=3, hidden_size=4, learning_rate=0.03, epochs=3,
                  batch_size=4, seed=31, patience=3)
    values.update(overrides)
    return GRUConfig(**values)


def dataset():
    return build_gru_dataset(
        [[0, 1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6, 7],
         [2, 3, 4, 5, 6, 7, 8], [3, 4, 5, 6, 7, 8, 9]],
        "phase31-fixture",
    )


def test_version_and_kind():
    from analytics.gru import MODEL_KIND
    assert GRU_VERSION == "31.0.0"
    assert MODEL_KIND == "gru"


def test_default_config():
    c = GRUConfig()
    validate_gru_config(c)
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
        validate_gru_config(GRUConfig(**values))


def test_invalid_learning_rate():
    with pytest.raises(ValueError):
        validate_gru_config(cfg(learning_rate=0))


def test_invalid_alphabet():
    with pytest.raises(ValueError):
        validate_gru_config(cfg(alphabet_size=9))


def test_invalid_dataset_identity():
    with pytest.raises(ValueError):
        build_gru_dataset([[0, 1, 2, 3]], "")


def test_zero_is_valid():
    ds = build_gru_dataset([[0, 1, 0, 2]], "zero")
    validate_gru_dataset(ds, cfg(sequence_length=2))
    assert 0 in ds.sequences[0]


@pytest.mark.parametrize("bad", [[-1, 1, 2, 3], [10, 1, 2, 3], [True, 1, 2, 3]])
def test_invalid_digit_data(bad):
    with pytest.raises(ValueError):
        build_gru_dataset([bad], "bad")


def test_dataset_contract():
    ds = dataset()
    assert isinstance(ds, GRUDataset)
    assert len(ds.sequences) == 4


def test_prepare_alias():
    ds = prepare_gru_dataset_from_sequences([[0, 1, 2, 3]], "alias")
    assert ds.identity == "alias"


def test_dataset_requires_enough_history():
    ds = build_gru_dataset([[0, 1, 2]], "short")
    with pytest.raises(ValueError):
        validate_gru_dataset(ds, cfg(sequence_length=3))


def test_chronological_split():
    train, test = chronological_gru_split(dataset(), 0.25)
    assert train.sequences == dataset().sequences[:3]
    assert test.sequences == dataset().sequences[3:]


def test_split_rejects_bad_fraction():
    with pytest.raises(ValueError):
        chronological_gru_split(dataset(), 1.0)


def test_model_initialization_is_deterministic():
    a = GRUClassifier(cfg())
    b = GRUClassifier(cfg())
    assert (a.W == b.W).all()
    assert (a.U == b.U).all()
    assert (a.V == b.V).all()


def test_model_starts_unfitted():
    model = GRUClassifier(cfg())
    assert not model.fitted
    assert validate_gru_model(model).status == INVALID


def test_fit_returns_model():
    model = GRUClassifier(cfg()).fit(dataset())
    assert model.fitted


def test_training_history():
    model = GRUClassifier(cfg(epochs=4)).fit(dataset())
    assert model.training_history is not None
    assert 1 <= model.training_history.epochs_completed <= 4
    assert len(model.training_history.losses) == model.training_history.epochs_completed


def test_fit_is_reproducible():
    a = GRUClassifier(cfg()).fit(dataset())
    b = GRUClassifier(cfg()).fit(dataset())
    assert (a.W == b.W).all()
    assert (a.U == b.U).all()
    assert (a.V == b.V).all()
    assert a.training_history == b.training_history


def test_predict_proba_shape_and_normalization():
    model = GRUClassifier(cfg()).fit(dataset())
    probabilities = model.predict_proba([[1, 2, 3], [4, 5, 6]])
    assert len(probabilities) == 2
    assert len(probabilities[0]) == 10
    assert abs(sum(probabilities[0]) - 1.0) < 1e-9


def test_predict_next_top_k():
    model = GRUClassifier(cfg()).fit(dataset())
    prediction = model.predict_next([4, 5, 6], 5)
    assert len(prediction) == 5
    assert len(set(prediction)) == 5
    assert all(0 <= value <= 9 for value in prediction)


def test_predict_top_k_limit():
    model = GRUClassifier(cfg()).fit(dataset())
    assert len(model.predict_next([4, 5, 6], 50)) == 10


def test_predict_rejects_wrong_window():
    model = GRUClassifier(cfg()).fit(dataset())
    with pytest.raises(ValueError):
        model.predict_proba([[1, 2]])


def test_predict_requires_fit():
    model = GRUClassifier(cfg())
    with pytest.raises(ValueError):
        model.predict_next([1, 2, 3])


def test_evaluation_metrics():
    model = GRUClassifier(cfg()).fit(dataset())
    metrics = model.evaluate(dataset())
    assert metrics.observations == 16
    assert metrics.log_loss >= 0
    assert 0 <= metrics.accuracy <= 1


def test_log_likelihood():
    model = GRUClassifier(cfg()).fit(dataset())
    metrics = model.evaluate(dataset())
    assert model.log_likelihood(dataset()) == pytest.approx(-metrics.log_loss * metrics.observations)


def test_baseline_comparison():
    model = GRUClassifier(cfg()).fit(dataset())
    metrics = model.evaluate(dataset())
    comparison = compare_with_baseline(metrics, 2.3)
    assert comparison.baseline_log_loss == 2.3
    assert comparison.difference == pytest.approx(metrics.log_loss - 2.3)


def test_negative_baseline_rejected():
    model = GRUClassifier(cfg()).fit(dataset())
    with pytest.raises(ValueError):
        compare_with_baseline(model.evaluate(dataset()), -1)


def test_model_validation_after_fit():
    model = GRUClassifier(cfg()).fit(dataset())
    result = validate_gru_model(model)
    assert result.status == VALID
    assert result.issues == ()


def test_artifact_identity_is_deterministic():
    model = GRUClassifier(cfg()).fit(dataset())
    first = build_gru_artifact(model, dataset())
    second = build_gru_artifact(model, dataset())
    assert first.artifact_identity == second.artifact_identity


def test_artifact_fields():
    model = GRUClassifier(cfg()).fit(dataset())
    artifact = build_gru_artifact(model, dataset())
    assert isinstance(artifact, GRUArtifact)
    assert artifact.model_kind == "gru"
    assert artifact.model_version == GRU_VERSION
    assert artifact.sequence_length == 3
    assert artifact.hidden_size == 4


def test_artifact_lineage():
    model = GRUClassifier(cfg()).fit(dataset())
    artifact = build_gru_artifact(model, dataset())
    validate_gru_artifact_lineage(artifact, dataset(), model)


def test_artifact_lineage_rejects_dataset():
    model = GRUClassifier(cfg()).fit(dataset())
    artifact = build_gru_artifact(model, dataset())
    other = build_gru_dataset(dataset().sequences, "other")
    with pytest.raises(ValueError):
        validate_gru_artifact_lineage(artifact, other, model)


def test_reproducibility_result():
    model = GRUClassifier(cfg()).fit(dataset())
    artifact = build_gru_artifact(model, dataset())
    result = reproduce_gru_artifact(artifact, artifact)
    assert result.identical
    assert result.first_identity == artifact.artifact_identity


def test_position_models():
    ds = dataset()
    models = build_position_gru_models({"col1": ds, "col2": ds}, cfg(epochs=2))
    assert [name for name, _ in models.models] == ["col1", "col2"]
    assert get_position_gru_model(models, "col1").fitted


def test_position_model_missing():
    models = build_position_gru_models({"col1": dataset()}, cfg(epochs=1))
    with pytest.raises(ValueError):
        get_position_gru_model(models, "col9")


def test_position_models_require_mapping():
    with pytest.raises(ValueError):
        build_position_gru_models({}, cfg())


def test_persistence(tmp_path: Path):
    model = GRUClassifier(cfg()).fit(dataset())
    path = tmp_path / "gru.joblib"
    saved = save_gru_model(model, path)
    loaded = load_gru_model(saved)
    assert loaded.fitted
    assert loaded.predict_next([4, 5, 6], 3) == model.predict_next([4, 5, 6], 3)


def test_persistence_parent_creation(tmp_path: Path):
    model = GRUClassifier(cfg()).fit(dataset())
    path = tmp_path / "nested" / "gru.joblib"
    save_gru_model(model, path)
    assert path.exists()


def test_training_history_early_stopping():
    model = GRUClassifier(cfg(epochs=10, patience=1)).fit(dataset())
    assert model.training_history.epochs_completed <= 10


def test_gradient_values_remain_finite():
    model = GRUClassifier(cfg(epochs=2)).fit(dataset())
    assert validate_gru_model(model).is_valid
