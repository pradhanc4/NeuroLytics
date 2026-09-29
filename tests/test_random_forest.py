from datetime import date
from pathlib import Path

import joblib
import pytest
from sklearn.ensemble import RandomForestClassifier

from analytics.random_forest import (
    RANDOM_FOREST_VERSION, INVALID, VALID, RandomForestConfig,
    RandomForestDataset, build_random_forest, build_random_forest_artifact,
    build_random_forest_dataset, build_position_models, compare_with_baseline,
    evaluate_random_forest, get_feature_importances, get_model_classes,
    get_position_model, load_random_forest_model, predict_classes,
    predict_probabilities, reproduce_random_forest_artifact,
    save_random_forest_model, split_random_forest_dataset_temporally,
    train_random_forest, validate_random_forest_config,
    validate_random_forest_model, validate_random_forest_pipeline,
)


def dataset():
    return build_random_forest_dataset(
        ("f1", "f2"), "v1", "ds1", "col1",
        tuple(date(2026, 1, d) for d in range(1, 11)),
        ((0., 0.), (0., 1.), (1., 0.), (1., 1.), (2., 0.),
         (2., 1.), (3., 0.), (3., 1.), (4., 0.), (4., 1.)),
        (0, 1, 0, 1, 2, 2, 2, 0, 1, 2),
    )


def bootstrap_dataset():
    return build_random_forest_dataset(
        ("f1", "f2"), "v1", "ds-bootstrap", "col1",
        tuple(date(2026, 1, d) for d in range(1, 21)),
        tuple((float(i % 5), float((i // 5) % 2)) for i in range(20)),
        tuple(i % 3 for i in range(20)),
    )


def test_default_config():
    config = RandomForestConfig()
    validate_random_forest_config(config)
    assert config.n_estimators == 100
    assert config.max_features == "sqrt"


@pytest.mark.parametrize("criterion", ["gini", "entropy", "log_loss"])
def test_supported_criteria(criterion):
    validate_random_forest_config(RandomForestConfig(criterion=criterion))


def test_config_validation():
    invalid = [
        RandomForestConfig(n_estimators=0),
        RandomForestConfig(max_depth=0),
        RandomForestConfig(min_samples_split=1),
        RandomForestConfig(min_samples_leaf=0),
        RandomForestConfig(max_features=0),
        RandomForestConfig(max_features=1.5),
        RandomForestConfig(max_features="bad"),
        RandomForestConfig(oob_score=True, bootstrap=False),
        RandomForestConfig(max_samples=0, bootstrap=True),
        RandomForestConfig(max_samples=0.5, bootstrap=False),
    ]
    for config in invalid:
        with pytest.raises(ValueError):
            validate_random_forest_config(config)


def test_dataset_and_zero_preservation():
    ds = dataset()
    assert ds.X[0] == (0.0, 0.0)
    assert ds.y[0] == 0


def test_duplicate_dates_rejected():
    with pytest.raises(ValueError):
        build_random_forest_dataset(
            ("f1",), "v", "d", "y",
            (date(2026,1,1), date(2026,1,1)),
            ((0.,), (1.,)), (0, 1),
        )


def test_temporal_split():
    split = split_random_forest_dataset_temporally(dataset(), date(2026,1,6))
    assert len(split.train.y) == 6
    assert len(split.validation.y) == 4
    assert max(split.train.dates) <= split.split_date
    assert min(split.validation.dates) > split.split_date


def test_training():
    model = train_random_forest(dataset(), RandomForestConfig(n_estimators=25))
    assert isinstance(model, RandomForestClassifier)
    assert len(model.estimators_) == 25
    assert len(model.classes_) >= 2


def test_binary_and_multiclass_probability_prediction():
    ds = dataset()
    model = train_random_forest(ds, RandomForestConfig(n_estimators=20))
    predictions = predict_classes(model, ds.X)
    probabilities = predict_probabilities(model, ds.X)
    assert len(predictions) == len(ds.y)
    assert len(probabilities) == len(ds.y)
    assert len(probabilities[0]) == len(model.classes_)
    assert all(abs(sum(row) - 1.0) < 1e-9 for row in probabilities)


def test_evaluation():
    ds = dataset()
    metrics = evaluate_random_forest(train_random_forest(ds, RandomForestConfig(n_estimators=20)), ds)
    assert 0 <= metrics.accuracy <= 1
    assert 0 <= metrics.precision <= 1
    assert 0 <= metrics.recall <= 1
    assert 0 <= metrics.f1 <= 1
    assert metrics.log_loss >= 0


def test_feature_importances():
    ds = dataset()
    model = train_random_forest(ds, RandomForestConfig(n_estimators=20))
    result = get_feature_importances(model, ds.feature_names)
    assert result.feature_names == ds.feature_names
    assert len(result.importances) == 2
    assert sum(result.importances) == pytest.approx(1.0)


def test_position_models():
    ds = dataset()
    models = build_position_models({"col2": ds, "col1": ds}, RandomForestConfig(n_estimators=10))
    assert tuple(name for name, _ in models.models) == ("col1", "col2")
    assert isinstance(get_position_model(models, "col1"), RandomForestClassifier)
    with pytest.raises(ValueError):
        get_position_model(models, "missing")


def test_empty_position_mapping():
    with pytest.raises(ValueError):
        build_position_models({})


def test_baseline_comparison():
    ds = dataset()
    metrics = evaluate_random_forest(train_random_forest(ds, RandomForestConfig(n_estimators=10)), ds)
    result = compare_with_baseline(metrics, 1.0)
    assert result.difference == pytest.approx(metrics.log_loss - 1.0)
    with pytest.raises(ValueError):
        compare_with_baseline(metrics, -1)


def test_artifact_reproducibility():
    ds = dataset()
    config = RandomForestConfig(n_estimators=15, max_depth=3)
    first = build_random_forest_artifact(train_random_forest(ds, config), ds, config)
    second = build_random_forest_artifact(train_random_forest(ds, config), ds, config)
    assert first.model_version == RANDOM_FOREST_VERSION
    assert first.artifact_identity.startswith("random-forest-")
    assert reproduce_random_forest_artifact(first, second).identical


def test_artifact_changes_with_config():
    ds = dataset()
    a_config = RandomForestConfig(n_estimators=10)
    b_config = RandomForestConfig(n_estimators=20)
    a = build_random_forest_artifact(train_random_forest(ds, a_config), ds, a_config)
    b = build_random_forest_artifact(train_random_forest(ds, b_config), ds, b_config)
    assert a.artifact_identity != b.artifact_identity


def test_model_validation():
    ds = dataset()
    model = train_random_forest(ds, RandomForestConfig(n_estimators=10))
    assert validate_random_forest_model(model, ds).status == VALID
    assert validate_random_forest_pipeline(ds, RandomForestConfig(n_estimators=10), model).is_valid
    assert validate_random_forest_model("bad", ds).status == INVALID


def test_unfitted_pipeline():
    ds = dataset()
    model = build_random_forest(RandomForestConfig(n_estimators=10))
    result = validate_random_forest_pipeline(ds, RandomForestConfig(n_estimators=10), model)
    assert result.status == INVALID
    assert "MODEL_NOT_FITTED" in result.issues


def test_class_identity():
    model = train_random_forest(dataset(), RandomForestConfig(n_estimators=10))
    assert get_model_classes(model) == tuple(int(v) for v in model.classes_)


def test_persistence(tmp_path: Path):
    ds = dataset()
    model = train_random_forest(ds, RandomForestConfig(n_estimators=10))
    path = save_random_forest_model(model, tmp_path / "forest.joblib")
    loaded = load_random_forest_model(path)
    assert get_model_classes(loaded) == get_model_classes(model)
    assert predict_classes(loaded, ds.X) == predict_classes(model, ds.X)


def test_bad_persistence_type(tmp_path: Path):
    path = tmp_path / "bad.joblib"
    joblib.dump({"not": "a model"}, path)
    with pytest.raises(TypeError):
        load_random_forest_model(path)


def test_complexity_controls_and_oob():
    config = RandomForestConfig(n_estimators=15, max_depth=2, min_samples_leaf=2, oob_score=True)
    model = train_random_forest(dataset(), config)
    assert model.max_depth == 2
    assert model.min_samples_leaf == 2
    assert hasattr(model, "oob_score_")


def test_bootstrap_false():
    model = train_random_forest(dataset(), RandomForestConfig(n_estimators=10, bootstrap=False))
    assert model.bootstrap is False


def test_max_samples():
    model = train_random_forest(bootstrap_dataset(), RandomForestConfig(n_estimators=10, max_samples=0.8))
    assert model.max_samples == 0.8


def test_feature_importance_width_validation():
    ds = dataset()
    model = train_random_forest(ds, RandomForestConfig(n_estimators=10))
    with pytest.raises(ValueError):
        get_feature_importances(model, ("only_one",))


def test_invalid_target_type():
    with pytest.raises(ValueError):
        build_random_forest_dataset(
            ("f1",), "v", "d", "y", (date(2026,1,1),), ((1.,),), (True,)
        )


def test_empty_dataset_samples_are_rejected_by_sequence_adapter():
    from unittest.mock import Mock
    sequence = Mock()
    sequence.samples = ()
    with pytest.raises(TypeError):
        from analytics.random_forest import build_random_forest_dataset_from_sequence_dataset
        build_random_forest_dataset_from_sequence_dataset(sequence, "id")


def test_prediction_width_is_validated():
    model = train_random_forest(dataset(), RandomForestConfig(n_estimators=10))
    with pytest.raises(ValueError):
        predict_classes(model, ((1.0,),))


def test_n_jobs_configuration():
    model = train_random_forest(dataset(), RandomForestConfig(n_estimators=10, n_jobs=1))
    assert model.n_jobs == 1


def test_deterministic_training_predictions():
    ds = dataset()
    config = RandomForestConfig(n_estimators=20, random_state=7)
    a = train_random_forest(ds, config)
    b = train_random_forest(ds, config)
    assert predict_classes(a, ds.X) == predict_classes(b, ds.X)
