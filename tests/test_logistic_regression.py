from datetime import date

import pytest

from analytics.logistic_regression import (
    INVALID,
    VALID,
    LogisticRegressionConfig,
    LogisticRegressionDataset,
    build_logistic_artifact,
    build_logistic_dataset,
    build_logistic_regression,
    build_position_models,
    compare_with_baseline,
    evaluate_logistic_regression,
    get_model_classes,
    predict_classes,
    predict_probabilities,
    reproduce_logistic_artifact,
    save_logistic_model,
    load_logistic_model,
    split_logistic_dataset_temporally,
    train_logistic_regression,
    validate_logistic_config,
    validate_logistic_dataset,
    validate_logistic_model,
    validate_logistic_pipeline,
)


def dataset():
    rows = tuple(
        (float(i), float(i % 3), float((i * 2) % 5))
        for i in range(12)
    )
    labels = tuple(i % 2 for i in range(12))
    dates = tuple(date(2026, 1, i + 1) for i in range(12))
    return build_logistic_dataset(
        feature_names=("f1", "f2", "f3"),
        feature_version="feature-v1",
        dataset_identity="dataset-v1",
        target_name="col1",
        dates=dates,
        X=rows,
        y=labels,
    )


def config():
    return LogisticRegressionConfig(
        penalty="l2",
        C=1.0,
        solver="lbfgs",
        max_iter=500,
        random_state=0,
    )


def test_config_is_valid():
    validate_logistic_config(config())


def test_invalid_penalty_is_rejected():
    with pytest.raises(ValueError):
        validate_logistic_config(
            LogisticRegressionConfig(penalty="bad")
        )


def test_invalid_solver_penalty_pair_is_rejected():
    with pytest.raises(ValueError):
        validate_logistic_config(
            LogisticRegressionConfig(
                penalty="l1",
                solver="lbfgs",
            )
        )


def test_dataset_is_deterministic():
    first = dataset()
    second = dataset()
    assert first == second


def test_dataset_validation_rejects_unsorted_dates():
    value = dataset()
    invalid = LogisticRegressionDataset(
        feature_names=value.feature_names,
        feature_version=value.feature_version,
        dataset_identity=value.dataset_identity,
        target_name=value.target_name,
        dates=tuple(reversed(value.dates)),
        X=tuple(reversed(value.X)),
        y=tuple(reversed(value.y)),
    )
    with pytest.raises(ValueError):
        validate_logistic_dataset(invalid)


def test_training_produces_fitted_model():
    model = train_logistic_regression(dataset(), config())
    assert hasattr(model, "classes_")
    assert len(model.classes_) == 2


def test_prediction_classes_are_deterministic():
    model = train_logistic_regression(dataset(), config())
    first = predict_classes(model, dataset().X)
    second = predict_classes(model, dataset().X)
    assert first == second


def test_prediction_probabilities_sum_to_one():
    model = train_logistic_regression(dataset(), config())
    probabilities = predict_probabilities(model, dataset().X)
    assert all(abs(sum(row) - 1.0) < 1e-9 for row in probabilities)


def test_evaluation_metrics_are_available():
    model = train_logistic_regression(dataset(), config())
    metrics = evaluate_logistic_regression(model, dataset())
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.precision <= 1.0
    assert 0.0 <= metrics.recall <= 1.0
    assert 0.0 <= metrics.f1 <= 1.0
    assert metrics.log_loss >= 0.0
    assert len(metrics.confusion_matrix) == 2


def test_temporal_split_is_chronological():
    split = split_logistic_dataset_temporally(
        dataset(),
        date(2026, 1, 7),
    )
    assert split.train.dates[-1] == date(2026, 1, 7)
    assert split.validation.dates[0] == date(2026, 1, 8)


def test_temporal_split_has_no_overlap():
    split = split_logistic_dataset_temporally(
        dataset(),
        date(2026, 1, 7),
    )
    assert set(split.train.dates).isdisjoint(set(split.validation.dates))


def test_temporal_split_requires_two_training_classes():
    with pytest.raises(ValueError):
        split_logistic_dataset_temporally(
            dataset(),
            date(2026, 1, 1),
        )


def test_model_validation_is_valid():
    value = dataset()
    model = train_logistic_regression(value, config())
    result = validate_logistic_model(model, value)
    assert result.status == VALID
    assert result.is_valid


def test_pipeline_validation_is_valid():
    value = dataset()
    model = train_logistic_regression(value, config())
    result = validate_logistic_pipeline(value, config(), model)
    assert result.status == VALID


def test_model_classes_are_stable():
    model = train_logistic_regression(dataset(), config())
    assert get_model_classes(model) == (0, 1)


def test_baseline_comparison_is_deterministic():
    metrics = evaluate_logistic_regression(
        train_logistic_regression(dataset(), config()),
        dataset(),
    )
    result = compare_with_baseline(metrics, 0.7)
    assert result.difference == pytest.approx(
        result.logistic_log_loss - 0.7
    )


def test_artifact_is_deterministic():
    value = dataset()
    model = train_logistic_regression(value, config())
    first = build_logistic_artifact(model, value, config())
    second = build_logistic_artifact(model, value, config())
    assert first == second
    assert first.artifact_identity.startswith("logistic-")


def test_artifact_reproducibility_result():
    value = dataset()
    model = train_logistic_regression(value, config())
    artifact = build_logistic_artifact(model, value, config())
    result = reproduce_logistic_artifact(artifact, artifact)
    assert result.identical


def test_persistence_round_trip(tmp_path):
    value = dataset()
    model = train_logistic_regression(value, config())
    path = save_logistic_model(
        model,
        tmp_path / "logistic.joblib",
    )
    loaded = load_logistic_model(path)
    assert get_model_classes(loaded) == get_model_classes(model)
    assert predict_classes(loaded, value.X) == predict_classes(
        model,
        value.X,
    )


def test_l1_configuration_trains():
    value = dataset()
    model = train_logistic_regression(
        value,
        LogisticRegressionConfig(
            penalty="l1",
            solver="liblinear",
            max_iter=500,
        ),
    )
    assert len(model.classes_) == 2


def test_multiclass_training_and_probabilities():
    rows = tuple(
        (float(i), float((i * 3) % 7))
        for i in range(15)
    )
    labels = tuple(i % 3 for i in range(15))
    dates = tuple(date(2026, 2, i + 1) for i in range(15))
    value = build_logistic_dataset(
        feature_names=("x", "y"),
        feature_version="v",
        dataset_identity="d",
        target_name="digit",
        dates=dates,
        X=rows,
        y=labels,
    )
    model = train_logistic_regression(value, config())
    assert get_model_classes(model) == (0, 1, 2)
    assert len(predict_probabilities(model, value.X)[0]) == 3


def test_zero_is_a_valid_class():
    rows = tuple((float(i),) for i in range(10))
    labels = (0, 1, 0, 1, 0, 1, 0, 1, 0, 1)
    dates = tuple(date(2026, 3, i + 1) for i in range(10))
    value = build_logistic_dataset(
        ("x",), "v", "d", "digit", dates, rows, labels
    )
    model = train_logistic_regression(value, config())
    assert 0 in get_model_classes(model)


def test_invalid_pipeline_reports_invalid():
    value = dataset()
    result = validate_logistic_pipeline(
        value,
        config(),
        "not-a-model",
    )
    assert result.status == INVALID
    assert result.issues


def test_dataset_identity_is_required():
    with pytest.raises(ValueError):
        build_logistic_dataset(
            ("x",), "v", "", "target",
            (date(2026, 1, 1), date(2026, 1, 2)),
            ((1.0,), (2.0,)),
            (0, 1),
        )


def test_feature_width_mismatch_is_rejected():
    with pytest.raises(ValueError):
        build_logistic_dataset(
            ("x",), "v", "d", "target",
            (date(2026, 1, 1), date(2026, 1, 2)),
            ((1.0, 2.0), (2.0, 3.0)),
            (0, 1),
        )



def test_position_models_are_built_in_deterministic_order():
    value = dataset()
    models = build_position_models(
        {"col2": value, "col1": value},
        config(),
    )
    assert [name for name, _ in models.models] == ["col1", "col2"]


def test_position_models_have_fitted_classes():
    value = dataset()
    models = build_position_models({"col1": value}, config())
    assert models.models[0][1].classes_.tolist() == [0, 1]


def test_artifact_identity_changes_with_configuration():
    value = dataset()
    first_model = train_logistic_regression(value, config())
    second_config = LogisticRegressionConfig(C=0.5, max_iter=500)
    second_model = train_logistic_regression(value, second_config)
    first = build_logistic_artifact(first_model, value, config())
    second = build_logistic_artifact(second_model, value, second_config)
    assert first.artifact_identity != second.artifact_identity


def test_reproducibility_detects_different_artifacts():
    value = dataset()
    first = build_logistic_artifact(
        train_logistic_regression(value, config()), value, config()
    )
    other_config = LogisticRegressionConfig(C=0.25, max_iter=500)
    second = build_logistic_artifact(
        train_logistic_regression(value, other_config), value, other_config
    )
    result = reproduce_logistic_artifact(first, second)
    assert not result.identical


def test_elasticnet_requires_saga():
    with pytest.raises(ValueError):
        validate_logistic_config(
            LogisticRegressionConfig(
                penalty="elasticnet",
                solver="lbfgs",
            )
        )


def test_none_penalty_configuration_is_accepted():
    validate_logistic_config(
        LogisticRegressionConfig(
            penalty="none",
            solver="lbfgs",
        )
    )
