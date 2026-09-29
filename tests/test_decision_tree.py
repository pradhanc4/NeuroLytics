from datetime import date
from pathlib import Path

import pytest
from sklearn.tree import DecisionTreeClassifier

from analytics.decision_tree import (
    DECISION_TREE_VERSION, INVALID, VALID,
    DecisionTreeArtifact, DecisionTreeConfig, DecisionTreeDataset,
    build_decision_tree, build_decision_tree_artifact,
    build_decision_tree_dataset, build_position_models,
    compare_with_baseline, evaluate_decision_tree,
    get_model_classes, get_position_model, load_decision_tree_model,
    predict_classes, predict_probabilities, reproduce_decision_tree_artifact,
    save_decision_tree_model, split_decision_tree_dataset_temporally,
    train_decision_tree, validate_decision_tree_config,
    validate_decision_tree_model, validate_decision_tree_pipeline,
)


def dataset():
    return build_decision_tree_dataset(
        ("f1", "f2"), "v1", "ds1", "col1",
        tuple(date(2026, 1, d) for d in range(1, 9)),
        ((0., 0.), (0., 1.), (1., 0.), (1., 1.),
         (2., 0.), (2., 1.), (3., 0.), (3., 1.)),
        (0, 1, 0, 1, 2, 2, 2, 0),
    )


def test_config_defaults():
    config = DecisionTreeConfig()
    validate_decision_tree_config(config)
    assert config.criterion == "gini"
    assert config.random_state == 0


@pytest.mark.parametrize("criterion", ["gini", "entropy", "log_loss"])
def test_supported_criteria(criterion):
    validate_decision_tree_config(DecisionTreeConfig(criterion=criterion))


def test_invalid_config():
    with pytest.raises(ValueError):
        validate_decision_tree_config(DecisionTreeConfig(criterion="bad"))
    with pytest.raises(ValueError):
        validate_decision_tree_config(DecisionTreeConfig(max_depth=0))
    with pytest.raises(ValueError):
        validate_decision_tree_config(DecisionTreeConfig(min_samples_split=1))
    with pytest.raises(ValueError):
        validate_decision_tree_config(DecisionTreeConfig(max_features=0))


def test_dataset_validation_and_zero_preservation():
    ds = dataset()
    assert ds.X[0] == (0.0, 0.0)
    assert ds.y[0] == 0


def test_duplicate_dates_rejected():
    with pytest.raises(ValueError):
        build_decision_tree_dataset(
            ("f1",), "v", "d", "y",
            (date(2026,1,1), date(2026,1,1)),
            ((0.,), (1.,)), (0,1),
        )


def test_temporal_split():
    split = split_decision_tree_dataset_temporally(dataset(), date(2026,1,5))
    assert len(split.train.y) == 5
    assert len(split.validation.y) == 3
    assert max(split.train.dates) <= split.split_date
    assert min(split.validation.dates) > split.split_date


def test_training_and_model_type():
    model = train_decision_tree(dataset())
    assert isinstance(model, DecisionTreeClassifier)
    assert len(model.classes_) >= 2


def test_predictions_and_probabilities():
    model = train_decision_tree(dataset())
    predictions = predict_classes(model, dataset().X)
    probabilities = predict_probabilities(model, dataset().X)
    assert len(predictions) == len(dataset().y)
    assert len(probabilities) == len(dataset().y)
    assert all(abs(sum(row)-1.0) < 1e-9 for row in probabilities)


def test_evaluation():
    ds = dataset()
    metrics = evaluate_decision_tree(train_decision_tree(ds), ds)
    assert 0 <= metrics.accuracy <= 1
    assert metrics.log_loss >= 0
    assert len(metrics.confusion_matrix) >= 2


def test_position_models():
    ds = dataset()
    models = build_position_models({"col1": ds, "col2": ds})
    assert len(models.models) == 2
    assert get_position_model(models, "col1").classes_.size >= 2
    with pytest.raises(ValueError):
        get_position_model(models, "missing")


def test_baseline_comparison():
    metrics = evaluate_decision_tree(train_decision_tree(dataset()), dataset())
    result = compare_with_baseline(metrics, 1.0)
    assert result.difference == pytest.approx(metrics.log_loss - 1.0)
    with pytest.raises(ValueError):
        compare_with_baseline(metrics, -1)


def test_artifact_and_reproducibility():
    ds = dataset()
    config = DecisionTreeConfig(max_depth=3)
    first = build_decision_tree_artifact(train_decision_tree(ds, config), ds, config)
    second = build_decision_tree_artifact(train_decision_tree(ds, config), ds, config)
    assert first.model_version == DECISION_TREE_VERSION
    assert first.artifact_identity.startswith("decision-tree-")
    result = reproduce_decision_tree_artifact(first, second)
    assert result.identical


def test_model_validation():
    ds = dataset()
    model = train_decision_tree(ds)
    result = validate_decision_tree_model(model, ds)
    assert result.status == VALID
    assert validate_decision_tree_pipeline(ds, DecisionTreeConfig(), model).is_valid
    assert validate_decision_tree_model("bad", ds).status == INVALID


def test_class_identity():
    model = train_decision_tree(dataset())
    assert get_model_classes(model) == tuple(int(v) for v in model.classes_)


def test_persistence(tmp_path: Path):
    ds = dataset()
    model = train_decision_tree(ds)
    path = save_decision_tree_model(model, tmp_path / "tree.joblib")
    loaded = load_decision_tree_model(path)
    assert get_model_classes(loaded) == get_model_classes(model)
    assert predict_classes(loaded, ds.X) == predict_classes(model, ds.X)


def test_bad_persistence_type(tmp_path: Path):
    import joblib
    path = tmp_path / "bad.joblib"
    joblib.dump({"not": "a model"}, path)
    with pytest.raises(TypeError):
        load_decision_tree_model(path)


def test_artifact_changes_with_configuration():
    ds = dataset()
    a = build_decision_tree_artifact(
        train_decision_tree(ds, DecisionTreeConfig(max_depth=2)), ds,
        DecisionTreeConfig(max_depth=2)
    )
    b = build_decision_tree_artifact(
        train_decision_tree(ds, DecisionTreeConfig(max_depth=3)), ds,
        DecisionTreeConfig(max_depth=3)
    )
    assert a.artifact_identity != b.artifact_identity


def test_pipeline_rejects_unfitted_model():
    ds = dataset()
    model = build_decision_tree()
    result = validate_decision_tree_pipeline(ds, DecisionTreeConfig(), model)
    assert result.status == INVALID
    assert "MODEL_NOT_FITTED" in result.issues


def test_feature_width_mismatch():
    ds = dataset()
    model = train_decision_tree(ds)
    bad = DecisionTreeDataset(
        ("only_one",), ds.feature_version, ds.dataset_identity,
        ds.target_name, ds.dates, tuple((row[0],) for row in ds.X), ds.y
    )
    result = validate_decision_tree_model(model, bad)
    assert "FEATURE_WIDTH_MISMATCH" in result.issues


def test_random_splitter_is_supported():
    model = train_decision_tree(dataset(), DecisionTreeConfig(splitter="random"))
    assert isinstance(model, DecisionTreeClassifier)


def test_complexity_controls():
    model = train_decision_tree(dataset(), DecisionTreeConfig(max_depth=2, min_samples_leaf=2))
    assert model.max_depth == 2
    assert model.min_samples_leaf == 2


def test_invalid_dataset_target_types():
    with pytest.raises(ValueError):
        build_decision_tree_dataset(
            ("f1",), "v", "d", "y",
            (date(2026,1,1),), ((1.,),), (True,)
        )


def test_empty_position_mapping_rejected():
    with pytest.raises(ValueError):
        build_position_models({})


def test_model_probability_classes_match():
    ds = dataset()
    model = train_decision_tree(ds)
    probabilities = predict_probabilities(model, ds.X)
    assert len(probabilities[0]) == len(model.classes_)
