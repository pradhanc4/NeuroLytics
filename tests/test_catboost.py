from datetime import date
from pathlib import Path

import joblib
import pytest
from catboost import CatBoostClassifier

from analytics.catboost import *


def dataset():
    return build_catboost_dataset(
        ("f1", "f2"), "v1", "ds1", "col1",
        tuple(date(2026, 1, d) for d in range(1, 11)),
        ((0., 0.), (0., 1.), (1., 0.), (1., 1.), (2., 0.), (2., 1.),
         (3., 0.), (3., 1.), (4., 0.), (4., 1.)),
        (0, 1, 0, 1, 2, 2, 2, 0, 1, 2),
    )


def bootstrap_dataset():
    return build_catboost_dataset(
        ("f1", "f2"), "v1", "ds-bootstrap", "col1",
        tuple(date(2026, 1, d) for d in range(1, 21)),
        tuple((float(i % 5), float((i // 5) % 2)) for i in range(20)),
        tuple(i % 3 for i in range(20)),
    )


def test_default_config():
    config = CatBoostConfig()
    validate_catboost_config(config)
    assert config.iterations == 100 and config.depth == 6


@pytest.mark.parametrize("loss", ["auto", "Logloss", "MultiClass"])
def test_supported_loss_functions(loss):
    validate_catboost_config(CatBoostConfig(loss_function=loss))


def test_config_validation():
    invalid = [
        CatBoostConfig(iterations=0),
        CatBoostConfig(depth=0),
        CatBoostConfig(depth=17),
        CatBoostConfig(learning_rate=0),
        CatBoostConfig(l2_leaf_reg=-1),
        CatBoostConfig(random_strength=-1),
        CatBoostConfig(bagging_temperature=-1),
        CatBoostConfig(border_count=0),
        CatBoostConfig(loss_function="bad"),
        CatBoostConfig(eval_metric=""),
        CatBoostConfig(early_stopping_rounds=0),
        CatBoostConfig(thread_count=0),
    ]
    for config in invalid:
        with pytest.raises(ValueError):
            validate_catboost_config(config)


def test_dataset_zero_and_split():
    ds = dataset()
    assert ds.X[0] == (0., 0.) and ds.y[0] == 0
    split = split_catboost_dataset_temporally(ds, date(2026, 1, 6))
    assert len(split.train.y) == 6 and len(split.validation.y) == 4


def test_duplicate_dates_rejected():
    ds = dataset()
    with pytest.raises(ValueError):
        build_catboost_dataset(
            ds.feature_names, ds.feature_version, ds.dataset_identity, ds.target_name,
            (date(2026, 1, 1),) * 10, ds.X, ds.y
        )


def test_factory_binary():
    model = build_catboost(CatBoostConfig(iterations=10), loss_function="Logloss")
    assert isinstance(model, CatBoostClassifier)


def test_factory_multiclass():
    model = build_catboost(CatBoostConfig(iterations=10), loss_function="MultiClass")
    assert isinstance(model, CatBoostClassifier)


def test_training_prediction_and_probability():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=20, depth=3))
    preds = predict_classes(model, ds.X)
    probs = predict_probabilities(model, ds.X)
    assert len(preds) == 20 and len(probs) == 20
    assert all(abs(sum(row) - 1) < 1e-9 for row in probs)


def test_multiclass_training():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=20, depth=3))
    assert len(get_model_classes(model)) == 3


def test_evaluation():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=20, depth=3))
    metrics = evaluate_catboost(model, ds)
    assert 0 <= metrics.accuracy <= 1
    assert len(metrics.confusion_matrix) == 3 and metrics.log_loss >= 0


def test_feature_importance():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=10, depth=3))
    importance = get_feature_importances(model, ds.feature_names)
    assert importance.feature_names == ds.feature_names
    assert len(importance.importances) == 2


def test_position_models():
    ds = bootstrap_dataset()
    models = build_position_models(
        {"col1": ds, "col2": ds},
        CatBoostConfig(iterations=10, depth=3),
    )
    assert tuple(name for name, _ in models.models) == ("col1", "col2")
    assert get_position_model(models, "col2") is not None


def test_position_model_missing():
    ds = bootstrap_dataset()
    models = build_position_models({"col1": ds}, CatBoostConfig(iterations=10, depth=3))
    with pytest.raises(ValueError):
        get_position_model(models, "missing")


def test_baseline_comparison():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=10, depth=3))
    result = compare_with_baseline(evaluate_catboost(model, ds), 1.0)
    assert result.difference == pytest.approx(result.catboost_log_loss - 1.0)


def test_artifact_identity_deterministic():
    ds = bootstrap_dataset()
    config = CatBoostConfig(iterations=10, depth=3)
    model = train_catboost(ds, config)
    first = build_catboost_artifact(model, ds, config)
    second = build_catboost_artifact(model, ds, config)
    assert first.artifact_identity == second.artifact_identity
    assert first.model_version == "27.0.0"
    assert first.runtime_version == "1.2.10"
    assert first.model_kind == "catboost"


def test_artifact_changes_with_config():
    ds = bootstrap_dataset()
    first_config = CatBoostConfig(iterations=10, depth=3)
    second_config = CatBoostConfig(iterations=11, depth=3)
    first = build_catboost_artifact(train_catboost(ds, first_config), ds, first_config)
    second = build_catboost_artifact(train_catboost(ds, second_config), ds, second_config)
    assert first.artifact_identity != second.artifact_identity


def test_model_validation():
    ds = bootstrap_dataset()
    config = CatBoostConfig(iterations=10, depth=3)
    model = train_catboost(ds, config)
    result = validate_catboost_model(model, ds)
    assert result.is_valid and result.issues == ()


def test_unfitted_model_validation():
    ds = bootstrap_dataset()
    model = CatBoostClassifier(iterations=10, verbose=False)
    result = validate_catboost_model(model, ds)
    assert not result.is_valid and "MODEL_NOT_FITTED" in result.issues


def test_pipeline_validation():
    ds = bootstrap_dataset()
    config = CatBoostConfig(iterations=10, depth=3)
    model = train_catboost(ds, config)
    assert validate_catboost_pipeline(ds, config, model).is_valid


def test_pipeline_invalid_config():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=10, depth=3))
    result = validate_catboost_pipeline(ds, CatBoostConfig(iterations=0), model)
    assert not result.is_valid


def test_version_references():
    ds = bootstrap_dataset()
    feature_ref = FeatureVersionReference(
        feature_version="v1", identity="feature-1", algorithm="sha256"
    )
    dataset_ref = DatasetVersionReference(
        dataset_version="dsv1", identity="ds-bootstrap", algorithm="sha256",
        feature_version="v1", feature_identity="feature-1"
    )
    validate_catboost_version_references(feature_ref, dataset_ref, ds)


def test_version_reference_mismatch():
    ds = bootstrap_dataset()
    with pytest.raises(ValueError):
        validate_catboost_version_references(
            FeatureVersionReference(feature_version="wrong", identity="feature-1", algorithm="sha256"),
            DatasetVersionReference(
                dataset_version="dsv1", identity="ds-bootstrap", algorithm="sha256",
                feature_version="wrong", feature_identity="feature-1"
            ),
            ds,
        )


def test_persistence(tmp_path):
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=10, depth=3))
    path = save_catboost_model(model, tmp_path / "model.joblib")
    loaded = load_catboost_model(path)
    assert isinstance(loaded, CatBoostClassifier)
    assert predict_classes(model, ds.X) == predict_classes(loaded, ds.X)


def test_load_wrong_artifact(tmp_path):
    path = tmp_path / "wrong.joblib"
    joblib.dump({"not": "model"}, path)
    with pytest.raises(TypeError):
        load_catboost_model(path)


def test_reproducibility():
    ds = bootstrap_dataset()
    config = CatBoostConfig(iterations=10, depth=3, random_state=0)
    first = train_catboost(ds, config)
    second = train_catboost(ds, config)
    result = reproduce_catboost_artifact(
        build_catboost_artifact(first, ds, config),
        build_catboost_artifact(second, ds, config),
    )
    assert result.identical


def test_random_state_changes_artifact():
    ds = bootstrap_dataset()
    first_config = CatBoostConfig(iterations=10, depth=3, random_state=0)
    second_config = CatBoostConfig(iterations=10, depth=3, random_state=7)
    first = build_catboost_artifact(train_catboost(ds, first_config), ds, first_config)
    second = build_catboost_artifact(train_catboost(ds, second_config), ds, second_config)
    assert first.artifact_identity != second.artifact_identity


def test_early_stopping_requires_validation():
    ds = bootstrap_dataset()
    with pytest.raises(ValueError):
        train_catboost(
            ds,
            CatBoostConfig(iterations=20, depth=3, early_stopping_rounds=5),
        )


def test_early_stopping_training():
    ds = bootstrap_dataset()
    split = split_catboost_dataset_temporally(ds, date(2026, 1, 14))
    config = CatBoostConfig(iterations=30, depth=3, early_stopping_rounds=5)
    model = train_catboost(split.train, config, split.validation)
    assert hasattr(model, "get_best_iteration")


def test_validation_class_mismatch():
    ds = bootstrap_dataset()
    bad = build_catboost_dataset(
        ds.feature_names, ds.feature_version, "bad", "col1",
        tuple(date(2026, 2, d) for d in range(1, 6)),
        ds.X[:5], (0, 1, 0, 1, 9)
    )
    with pytest.raises(ValueError):
        train_catboost(ds, CatBoostConfig(iterations=10, depth=3), bad)


def test_temporal_split_empty_validation_allowed():
    ds = bootstrap_dataset()
    split = split_catboost_dataset_temporally(ds, date(2026, 1, 20))
    assert len(split.validation.y) == 0


def test_temporal_split_requires_two_train_classes():
    ds = build_catboost_dataset(
        ("f1",), "v1", "one", "col1",
        (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)),
        ((1.,), (2.,), (3.,)), (0, 0, 1)
    )
    with pytest.raises(ValueError):
        split_catboost_dataset_temporally(ds, date(2026, 1, 1))


def test_empty_mapping_rejected():
    with pytest.raises(ValueError):
        build_position_models({})


def test_baseline_negative_rejected():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=10, depth=3))
    metrics = evaluate_catboost(model, ds)
    with pytest.raises(ValueError):
        compare_with_baseline(metrics, -1)


def test_sequence_adapter_and_temporal_helper():
    assert build_temporal_split_from_sequence_dataset is not None
    assert build_catboost_dataset_from_sequence_dataset is not None


def test_matrix_validation():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=5, depth=3))
    with pytest.raises(ValueError):
        predict_classes(model, ((1,), (1, 2)))


def test_feature_width_mismatch():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=10, depth=3))
    bad = build_catboost_dataset(
        ("f1",), "v1", "bad", "col1", ds.dates,
        tuple((1.,) for _ in ds.dates), ds.y
    )
    result = validate_catboost_model(model, bad)
    assert not result.is_valid and "FEATURE_WIDTH_MISMATCH" in result.issues


def test_dataset_feature_name_duplicate():
    with pytest.raises(ValueError):
        build_catboost_dataset(
            ("f1", "f1"), "v1", "dup", "col1",
            (date(2026, 1, 1), date(2026, 1, 2)),
            ((1., 2.), (2., 3.)), (0, 1)
        )


def test_dataset_chronology():
    with pytest.raises(ValueError):
        build_catboost_dataset(
            ("f1",), "v1", "order", "col1",
            (date(2026, 1, 2), date(2026, 1, 1)),
            ((1.,), (2.,)), (0, 1)
        )


def test_artifact_classes():
    ds = bootstrap_dataset()
    config = CatBoostConfig(iterations=10, depth=3)
    artifact = build_catboost_artifact(train_catboost(ds, config), ds, config)
    assert artifact.classes == (0, 1, 2)
    assert len(artifact.configuration) > 0


def test_model_classes_unfitted():
    with pytest.raises(ValueError):
        get_model_classes(CatBoostClassifier(iterations=5, verbose=False))


def test_invalid_model_type():
    ds = bootstrap_dataset()
    result = validate_catboost_model(object(), ds)
    assert not result.is_valid and result.issues == ("INVALID_MODEL_TYPE",)


def test_save_returns_path(tmp_path):
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=5, depth=3))
    path = save_catboost_model(model, tmp_path / "nested" / "model.joblib")
    assert Path(path).exists()


def test_runtime_version_contract():
    assert CATBOOST_RUNTIME_VERSION == "1.2.10"


def test_probability_integrity():
    ds = bootstrap_dataset()
    model = train_catboost(ds, CatBoostConfig(iterations=15, depth=3))
    probabilities = predict_probabilities(model, ds.X)
    assert all(all(0 <= value <= 1 for value in row) for row in probabilities)
    assert all(sum(row) == pytest.approx(1.0) for row in probabilities)
