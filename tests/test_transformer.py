from pathlib import Path

import numpy as np
import pytest

from analytics.transformer import (
    INVALID,
    VALID,
    MODEL_KIND,
    TRANSFORMER_VERSION,
    PositionTransformerModels,
    TransformerArtifact,
    TransformerClassifier,
    TransformerConfig,
    TransformerDataset,
    build_position_transformer_models,
    build_transformer_artifact,
    build_transformer_dataset,
    chronological_transformer_split,
    compare_with_baseline,
    get_position_transformer_model,
    load_transformer_model,
    prepare_transformer_dataset_from_sequences,
    reproduce_transformer_artifact,
    save_transformer_model,
    validate_transformer_artifact_lineage,
    validate_transformer_config,
    validate_transformer_dataset,
    validate_transformer_model,
)


def cfg(**overrides):
    values = dict(
        sequence_length=3,
        d_model=8,
        num_heads=2,
        feed_forward_size=16,
        learning_rate=0.02,
        epochs=3,
        batch_size=4,
        seed=32,
        patience=3,
    )
    values.update(overrides)
    return TransformerConfig(**values)


def dataset():
    return build_transformer_dataset(
        [
            [0, 1, 2, 3, 4, 5, 6],
            [1, 2, 3, 4, 5, 6, 7],
            [2, 3, 4, 5, 6, 7, 8],
            [3, 4, 5, 6, 7, 8, 9],
        ],
        "phase32-fixture",
    )


def test_version_and_kind():
    assert TRANSFORMER_VERSION == "32.0.0"
    assert MODEL_KIND == "transformer"


def test_default_config():
    config = TransformerConfig()
    validate_transformer_config(config)
    assert config.alphabet_size == 10
    assert config.num_heads == 2
    assert config.d_model % config.num_heads == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("sequence_length", 0),
        ("d_model", 0),
        ("num_heads", 0),
        ("feed_forward_size", 0),
        ("epochs", 0),
        ("batch_size", 0),
        ("patience", 0),
    ],
)
def test_invalid_positive_integer_config(field, value):
    values = cfg().__dict__
    values[field] = value
    with pytest.raises(ValueError):
        validate_transformer_config(TransformerConfig(**values))


def test_invalid_head_divisibility():
    with pytest.raises(ValueError):
        validate_transformer_config(cfg(d_model=7, num_heads=2))


def test_invalid_learning_rate():
    with pytest.raises(ValueError):
        validate_transformer_config(cfg(learning_rate=0))


def test_invalid_alphabet():
    with pytest.raises(ValueError):
        validate_transformer_config(cfg(alphabet_size=9))


def test_invalid_identity():
    with pytest.raises(ValueError):
        build_transformer_dataset([[0, 1, 2, 3]], "")


def test_zero_is_valid():
    ds = build_transformer_dataset([[0, 1, 0, 2]], "zero")
    validate_transformer_dataset(ds, cfg(sequence_length=2))
    assert 0 in ds.sequences[0]


@pytest.mark.parametrize(
    "bad",
    [
        [-1, 1, 2, 3],
        [10, 1, 2, 3],
        [True, 1, 2, 3],
    ],
)
def test_invalid_digit_data(bad):
    with pytest.raises(ValueError):
        build_transformer_dataset([bad], "bad")


def test_dataset_contract():
    ds = dataset()
    assert isinstance(ds, TransformerDataset)
    assert len(ds.sequences) == 4


def test_prepare_alias():
    ds = prepare_transformer_dataset_from_sequences([[0, 1, 2, 3]], "alias")
    assert ds.identity == "alias"


def test_dataset_requires_enough_history():
    ds = build_transformer_dataset([[0, 1, 2]], "short")
    with pytest.raises(ValueError):
        validate_transformer_dataset(ds, cfg(sequence_length=3))


def test_chronological_split():
    train, test = chronological_transformer_split(dataset(), 0.25)
    assert train.sequences == dataset().sequences[:3]
    assert test.sequences == dataset().sequences[3:]


def test_split_rejects_bad_fraction():
    with pytest.raises(ValueError):
        chronological_transformer_split(dataset(), 1.0)


def test_model_initialization_is_deterministic():
    first = TransformerClassifier(cfg())
    second = TransformerClassifier(cfg())
    assert np.array_equal(first.embedding, second.embedding)
    assert np.array_equal(first.Wq, second.Wq)
    assert np.array_equal(first.Wk, second.Wk)
    assert np.array_equal(first.Wv, second.Wv)


def test_model_starts_unfitted():
    model = TransformerClassifier(cfg())
    assert not model.fitted
    assert validate_transformer_model(model).status == INVALID


def test_positional_encoding_is_deterministic():
    first = TransformerClassifier(cfg())
    second = TransformerClassifier(cfg())
    assert np.array_equal(first.positional, second.positional)
    assert np.isfinite(first.positional).all()


def test_fit_returns_model():
    model = TransformerClassifier(cfg()).fit(dataset())
    assert model.fitted


def test_training_history():
    model = TransformerClassifier(cfg(epochs=4)).fit(dataset())
    assert model.training_history is not None
    assert 1 <= model.training_history.epochs_completed <= 4
    assert len(model.training_history.losses) == model.training_history.epochs_completed


def test_fit_is_reproducible():
    first = TransformerClassifier(cfg()).fit(dataset())
    second = TransformerClassifier(cfg()).fit(dataset())
    assert np.array_equal(first.embedding, second.embedding)
    assert np.array_equal(first.Wq, second.Wq)
    assert np.array_equal(first.W1, second.W1)
    assert first.training_history == second.training_history


def test_predict_proba_shape_and_normalization():
    model = TransformerClassifier(cfg()).fit(dataset())
    probabilities = model.predict_proba([[1, 2, 3], [4, 5, 6]])
    assert len(probabilities) == 2
    assert len(probabilities[0]) == 10
    assert abs(sum(probabilities[0]) - 1.0) < 1e-9
    assert all(value >= 0 for value in probabilities[0])


def test_predict_next_top_k():
    model = TransformerClassifier(cfg()).fit(dataset())
    prediction = model.predict_next([4, 5, 6], 5)
    assert len(prediction) == 5
    assert len(set(prediction)) == 5
    assert all(0 <= value <= 9 for value in prediction)


def test_predict_top_k_limit():
    model = TransformerClassifier(cfg()).fit(dataset())
    assert len(model.predict_next([4, 5, 6], 50)) == 10


def test_predict_rejects_wrong_window():
    model = TransformerClassifier(cfg()).fit(dataset())
    with pytest.raises(ValueError):
        model.predict_proba([[1, 2]])


def test_predict_requires_fit():
    model = TransformerClassifier(cfg())
    with pytest.raises(ValueError):
        model.predict_next([1, 2, 3])


def test_evaluation_metrics():
    model = TransformerClassifier(cfg()).fit(dataset())
    metrics = model.evaluate(dataset())
    assert metrics.observations == 16
    assert metrics.log_loss >= 0
    assert 0 <= metrics.accuracy <= 1


def test_log_likelihood():
    model = TransformerClassifier(cfg()).fit(dataset())
    metrics = model.evaluate(dataset())
    assert model.log_likelihood(dataset()) == pytest.approx(
        -metrics.log_loss * metrics.observations
    )


def test_baseline_comparison():
    model = TransformerClassifier(cfg()).fit(dataset())
    metrics = model.evaluate(dataset())
    comparison = compare_with_baseline(metrics, 2.3)
    assert comparison.baseline_log_loss == 2.3
    assert comparison.difference == pytest.approx(
        metrics.log_loss - 2.3
    )


def test_negative_baseline_rejected():
    model = TransformerClassifier(cfg()).fit(dataset())
    with pytest.raises(ValueError):
        compare_with_baseline(model.evaluate(dataset()), -1)


def test_model_validation_after_fit():
    model = TransformerClassifier(cfg()).fit(dataset())
    result = validate_transformer_model(model)
    assert result.status == VALID
    assert result.issues == ()


def test_model_parameters_remain_finite():
    model = TransformerClassifier(cfg(epochs=2)).fit(dataset())
    result = validate_transformer_model(model)
    assert result.is_valid


def test_artifact_identity_is_deterministic():
    model = TransformerClassifier(cfg()).fit(dataset())
    first = build_transformer_artifact(model, dataset())
    second = build_transformer_artifact(model, dataset())
    assert first.artifact_identity == second.artifact_identity


def test_artifact_fields():
    model = TransformerClassifier(cfg()).fit(dataset())
    artifact = build_transformer_artifact(model, dataset())
    assert isinstance(artifact, TransformerArtifact)
    assert artifact.model_kind == MODEL_KIND
    assert artifact.model_version == TRANSFORMER_VERSION
    assert artifact.sequence_length == 3
    assert artifact.d_model == 8
    assert artifact.num_heads == 2


def test_artifact_lineage():
    model = TransformerClassifier(cfg()).fit(dataset())
    artifact = build_transformer_artifact(model, dataset())
    validate_transformer_artifact_lineage(artifact, dataset(), model)


def test_artifact_lineage_rejects_dataset():
    model = TransformerClassifier(cfg()).fit(dataset())
    artifact = build_transformer_artifact(model, dataset())
    other = build_transformer_dataset(dataset().sequences, "other")
    with pytest.raises(ValueError):
        validate_transformer_artifact_lineage(artifact, other, model)


def test_artifact_lineage_rejects_config():
    model = TransformerClassifier(cfg()).fit(dataset())
    artifact = build_transformer_artifact(model, dataset())
    other = TransformerClassifier(cfg(d_model=16, num_heads=2))
    with pytest.raises(ValueError):
        validate_transformer_artifact_lineage(artifact, dataset(), other)


def test_reproducibility_result():
    model = TransformerClassifier(cfg()).fit(dataset())
    artifact = build_transformer_artifact(model, dataset())
    result = reproduce_transformer_artifact(artifact, artifact)
    assert result.identical
    assert result.first_identity == artifact.artifact_identity


def test_position_models():
    ds = dataset()
    models = build_position_transformer_models(
        {"col1": ds, "col2": ds},
        cfg(epochs=2),
    )
    assert isinstance(models, PositionTransformerModels)
    assert [name for name, _ in models.models] == ["col1", "col2"]
    assert get_position_transformer_model(models, "col1").fitted


def test_position_model_missing():
    models = build_position_transformer_models(
        {"col1": dataset()},
        cfg(epochs=1),
    )
    with pytest.raises(ValueError):
        get_position_transformer_model(models, "col9")


def test_position_models_require_mapping():
    with pytest.raises(ValueError):
        build_position_transformer_models({}, cfg())


def test_persistence(tmp_path: Path):
    model = TransformerClassifier(cfg()).fit(dataset())
    path = tmp_path / "transformer.joblib"
    saved = save_transformer_model(model, path)
    loaded = load_transformer_model(saved)
    assert loaded.fitted
    assert loaded.predict_next([4, 5, 6], 3) == model.predict_next([4, 5, 6], 3)


def test_persistence_parent_creation(tmp_path: Path):
    model = TransformerClassifier(cfg()).fit(dataset())
    path = tmp_path / "nested" / "transformer.joblib"
    save_transformer_model(model, path)
    assert path.exists()


def test_training_history_early_stopping():
    model = TransformerClassifier(
        cfg(epochs=10, patience=1)
    ).fit(dataset())
    assert model.training_history.epochs_completed <= 10


def test_numpy_integer_windows_are_supported():
    model = TransformerClassifier(cfg()).fit(dataset())
    window = np.asarray([4, 5, 6], dtype=np.int64)
    assert len(model.predict_next(window, 3)) == 3


def test_attention_probability_rows_normalize():
    model = TransformerClassifier(cfg())
    probabilities, cache = model._forward([1, 2, 3])
    weights = cache[5]
    assert np.allclose(weights.sum(axis=-1), 1.0)
    assert np.isfinite(probabilities).all()


def test_transformer_has_multi_head_attention():
    model = TransformerClassifier(cfg())
    assert model.config.num_heads == 2
    assert model.Wq.shape == (8, 8)
    assert model.Wk.shape == (8, 8)
    assert model.Wv.shape == (8, 8)


def test_empty_prediction_windows():
    model = TransformerClassifier(cfg()).fit(dataset())
    assert model.predict_proba([]) == ()


def test_reproducibility_requires_artifacts():
    model = TransformerClassifier(cfg()).fit(dataset())
    artifact = build_transformer_artifact(model, dataset())
    assert reproduce_transformer_artifact(artifact, artifact).identical


def test_artifact_type_validation():
    with pytest.raises(TypeError):
        reproduce_transformer_artifact("bad", "bad")


def test_model_type_validation():
    result = validate_transformer_model(object())
    assert result.status == INVALID
    assert result.issues == ("INVALID_MODEL_TYPE",)


def test_config_type_validation():
    with pytest.raises(TypeError):
        validate_transformer_config(object())


def test_dataset_type_validation():
    with pytest.raises(TypeError):
        validate_transformer_dataset(object(), cfg())


def test_predict_top_k_validation():
    model = TransformerClassifier(cfg()).fit(dataset())
    with pytest.raises(ValueError):
        model.predict_next([1, 2, 3], 0)


def test_artifact_identity_changes_with_training_seed():
    first = TransformerClassifier(cfg(seed=32)).fit(dataset())
    second = TransformerClassifier(cfg(seed=33)).fit(dataset())
    first_artifact = build_transformer_artifact(first, dataset())
    second_artifact = build_transformer_artifact(second, dataset())
    assert first_artifact.artifact_identity != second_artifact.artifact_identity


def test_target_name_is_preserved():
    ds = build_transformer_dataset(
        [[0, 1, 2, 3]],
        "target-name",
        target_name="col1",
    )
    assert ds.target_name == "col1"

