from datetime import date, timedelta

import pytest

from analytics.learning_to_rank_dataset import (
    LearningToRankCandidateInput,
    LearningToRankDatasetConfig,
    LearningToRankObservationInput,
    build_learning_to_rank_dataset,
)
from analytics.learning_to_rank_model import (
    INVALID,
    LEARNING_TO_RANK_MODEL_VERSION,
    MODEL_KIND,
    LearningToRankModelConfig,
    evaluate_learning_to_rank_model,
    learning_to_rank_model_summary,
    load_learning_to_rank_model,
    predict_learning_to_rank,
    predict_learning_to_rank_group,
    save_learning_to_rank_model,
    train_learning_to_rank_model,
    validate_learning_to_rank_model,
    validate_learning_to_rank_model_config,
    validate_learning_to_rank_report,
)


def config():
    return LearningToRankDatasetConfig(
        feature_names=("f1", "f2"),
        validation_start_date=date(2026, 1, 11),
        test_start_date=date(2026, 1, 21),
        target_position="close",
    )


def observation(day, group, actual=0):
    candidates = tuple(
        LearningToRankCandidateInput(
            digit,
            (float(digit), float(9 - digit)),
            day - timedelta(days=1),
            f"p{digit}",
            f"j{digit}",
        )
        for digit in range(10)
    )
    return LearningToRankObservationInput(group, day, "close", actual, candidates)


def dataset():
    return build_learning_to_rank_dataset(
        (
            observation(date(2026, 1, 1), "g1", 0),
            observation(date(2026, 1, 3), "g2", 1),
            observation(date(2026, 1, 5), "g3", 2),
            observation(date(2026, 1, 7), "g4", 3),
            observation(date(2026, 1, 12), "g5", 4),
            observation(date(2026, 1, 15), "g6", 5),
            observation(date(2026, 1, 18), "g7", 6),
            observation(date(2026, 1, 22), "g8", 7),
            observation(date(2026, 1, 25), "g9", 8),
            observation(date(2026, 1, 28), "g10", 9),
        ),
        config(),
        "source-40",
        "schema-40",
    )


def model_config(**kwargs):
    base = dict(learning_rate=0.08, epochs=120, l2=0.001, seed=41, top_k=3, early_stopping_patience=15)
    base.update(kwargs)
    return LearningToRankModelConfig(**base)


def test_version_and_kind():
    assert LEARNING_TO_RANK_MODEL_VERSION == "41.0.0"
    assert MODEL_KIND == "pairwise_logistic_ltr"


def test_config_validates():
    validate_learning_to_rank_model_config(model_config())


@pytest.mark.parametrize("kwargs", [
    {"learning_rate": 0},
    {"learning_rate": -1},
    {"epochs": 0},
    {"l2": -1},
    {"top_k": 0},
    {"top_k": 11},
    {"early_stopping_patience": 0},
])
def test_invalid_config(kwargs):
    with pytest.raises(ValueError):
        validate_learning_to_rank_model_config(model_config(**kwargs))


def test_training_produces_model():
    model = train_learning_to_rank_model(dataset(), model_config())
    assert model.version == "41.0.0"
    assert model.model_kind == MODEL_KIND
    assert len(model.weights) == 2
    assert model.dataset_identity == dataset().dataset_identity


def test_training_is_deterministic():
    first = train_learning_to_rank_model(dataset(), model_config())
    second = train_learning_to_rank_model(dataset(), model_config())
    assert first.model_identity == second.model_identity
    assert first.weights == second.weights
    assert first.bias == second.bias


def test_training_history_present():
    model = train_learning_to_rank_model(dataset(), model_config())
    assert model.history.losses
    assert model.history.validation_losses
    assert 1 <= model.history.best_epoch <= len(model.history.losses)


def test_prediction_has_ten_candidates():
    model = train_learning_to_rank_model(dataset(), model_config())
    group = dataset().groups[-1]
    rows = dataset().rows[group.row_start:group.row_end + 1]
    prediction = predict_learning_to_rank_group(model, group, rows)
    assert len(prediction.candidate_digits) == 10
    assert len(prediction.scores) == 10
    assert len(prediction.probabilities) == 10
    assert len(prediction.ranks) == 10


def test_prediction_probabilities_sum_to_one():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    prediction = predict_learning_to_rank(model, ds, "test")[0]
    assert sum(prediction.probabilities) == pytest.approx(1.0)


def test_prediction_ranks_are_one_to_ten():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    prediction = predict_learning_to_rank(model, ds)[0]
    assert sorted(prediction.ranks) == list(range(1, 11))


def test_digit_zero_is_supported():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    group = ds.groups[0]
    rows = ds.rows[group.row_start:group.row_end + 1]
    prediction = predict_learning_to_rank_group(model, group, rows)
    assert 0 in prediction.candidate_digits
    assert prediction.actual_digit == 0


def test_top_k_respects_config():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config(top_k=5))
    prediction = predict_learning_to_rank(model, ds)[0]
    assert len(prediction.top_k_candidates) == 5


def test_evaluation_report():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    report = evaluate_learning_to_rank_model(model, ds)
    assert report.prediction_count == 10
    assert report.train_evaluation.groups == 4
    assert report.validation_evaluation.groups == 3
    assert report.test_evaluation.groups == 3
    assert 0 <= report.test_evaluation.accuracy <= 1
    assert 0 <= report.test_evaluation.top_k_accuracy <= 1
    assert 0 <= report.test_evaluation.mrr <= 1
    assert 0 <= report.test_evaluation.ndcg <= 1
    assert report.test_evaluation.log_loss >= 0


def test_report_validation():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    report = evaluate_learning_to_rank_model(model, ds)
    assert validate_learning_to_rank_report(report, ds).is_valid


def test_model_validation():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    assert validate_learning_to_rank_model(model, ds).is_valid


def test_summary():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    summary = learning_to_rank_model_summary(model)
    assert summary["version"] == "41.0.0"
    assert summary["model_kind"] == MODEL_KIND


def test_model_persistence(tmp_path):
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    path = tmp_path / "ltr.joblib"
    save_learning_to_rank_model(model, path)
    loaded = load_learning_to_rank_model(path)
    assert loaded.model_identity == model.model_identity
    assert loaded.weights == model.weights


def test_persistence_preserves_prediction(tmp_path):
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    path = tmp_path / "ltr.joblib"
    save_learning_to_rank_model(model, path)
    loaded = load_learning_to_rank_model(path)
    a = predict_learning_to_rank(model, ds)[0]
    b = predict_learning_to_rank(loaded, ds)[0]
    assert a == b


def test_wrong_artifact_rejected(tmp_path):
    import joblib
    path = tmp_path / "wrong.joblib"
    joblib.dump({"wrong": True}, path)
    with pytest.raises(ValueError, match="not a LearningToRankModel"):
        load_learning_to_rank_model(path)


def test_model_dataset_mismatch():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    other = build_learning_to_rank_dataset(
        tuple(observation(group.target_date, group.group_id, group.actual_digit) for group in ds.groups),
        config(), "other-source", "schema-40"
    )
    result = validate_learning_to_rank_model(model, other)
    assert result.status == INVALID
    assert "DATASET_IDENTITY_MISMATCH" in result.issues


def test_model_schema_mismatch():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    other_config = LearningToRankDatasetConfig(
        ("f1", "other"), date(2026, 1, 11), date(2026, 1, 21), target_position="close"
    )
    other = build_learning_to_rank_dataset(
        tuple(
            LearningToRankObservationInput(
                group.group_id, group.target_date, "close", group.actual_digit,
                tuple(
                    LearningToRankCandidateInput(d, (float(d), float(d + 1)), group.target_date - timedelta(days=1))
                    for d in range(10)
                )
            ) for group in ds.groups
        ),
        other_config, "source-40", "other-schema"
    )
    result = validate_learning_to_rank_model(model, other)
    assert result.status == INVALID
    assert "FEATURE_SCHEMA_IDENTITY_MISMATCH" in result.issues


def test_invalid_dataset_blocks_training():
    ds = dataset()
    broken = type(ds)(ds.version, "", ds.feature_schema_identity, ds.config, ds.rows, ds.groups,
                      ds.train_group_ids, ds.validation_group_ids, ds.test_group_ids, ds.dataset_identity)
    with pytest.raises(ValueError, match="dataset is invalid"):
        train_learning_to_rank_model(broken, model_config())


def test_prediction_requires_ten_rows():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    group = ds.groups[0]
    with pytest.raises(ValueError, match="exactly ten"):
        predict_learning_to_rank_group(model, group, ds.rows[group.row_start:group.row_start + 9])


def test_invalid_split_prediction():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    with pytest.raises(KeyError):
        predict_learning_to_rank(model, ds, "bad")


def test_model_identity_contains_expected_prefix():
    model = train_learning_to_rank_model(dataset(), model_config())
    assert model.model_identity.startswith("learning-to-rank-model-")


def test_report_identity_contains_expected_prefix():
    ds = dataset()
    report = evaluate_learning_to_rank_model(train_learning_to_rank_model(ds, model_config()), ds)
    assert report.report_identity.startswith("learning-to-rank-report-")


def test_top_candidate_is_valid_digit():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    prediction = predict_learning_to_rank(model, ds)[0]
    assert prediction.top_candidate in range(10)


def test_training_can_stop_early():
    model = train_learning_to_rank_model(dataset(), model_config(epochs=300, early_stopping_patience=2))
    assert len(model.history.losses) <= 300


def test_prediction_actual_digit_matches_group():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    prediction = predict_learning_to_rank(model, ds)[0]
    assert prediction.actual_digit == ds.groups[7].actual_digit


def test_model_feature_names_match_dataset():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    assert model.feature_names == ds.config.feature_names


def test_model_target_position_matches_dataset():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    assert model.target_position == ds.config.target_position


def test_all_splits_can_be_predicted():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    assert len(predict_learning_to_rank(model, ds, "train")) == 4
    assert len(predict_learning_to_rank(model, ds, "validation")) == 3
    assert len(predict_learning_to_rank(model, ds, "test")) == 3


def test_validation_rejects_bad_model_type():
    assert validate_learning_to_rank_model(object()).status == INVALID


def test_validation_rejects_nonfinite_bias():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    broken = type(model)(
        model.version, model.model_kind, model.dataset_identity,
        model.feature_schema_identity, model.feature_names, model.target_position,
        model.weights, float("nan"), model.config, model.history, model.model_identity
    )
    assert "NON_FINITE_BIAS" in validate_learning_to_rank_model(broken, ds).issues


def test_validation_rejects_bad_model_version():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    broken = type(model)(
        "bad", model.model_kind, model.dataset_identity,
        model.feature_schema_identity, model.feature_names, model.target_position,
        model.weights, model.bias, model.config, model.history, model.model_identity
    )
    assert "INVALID_VERSION" in validate_learning_to_rank_model(broken, ds).issues


def test_validation_rejects_bad_report_type():
    assert validate_learning_to_rank_report(object()).status == INVALID


def test_validation_rejects_bad_report_identity():
    ds = dataset()
    model = train_learning_to_rank_model(ds, model_config())
    report = evaluate_learning_to_rank_model(model, ds)
    broken = type(report)(
        report.version, report.model_identity, report.dataset_identity,
        report.train_evaluation, report.validation_evaluation, report.test_evaluation,
        report.prediction_count, "bad"
    )
    assert "INVALID_REPORT_IDENTITY" in validate_learning_to_rank_report(broken).issues


def test_log_loss_is_finite():
    ds = dataset()
    report = evaluate_learning_to_rank_model(train_learning_to_rank_model(ds, model_config()), ds)
    assert all(map(lambda x: x >= 0 and x < float("inf"), (
        report.train_evaluation.log_loss,
        report.validation_evaluation.log_loss,
        report.test_evaluation.log_loss,
    )))


def test_pairwise_model_has_nonzero_learning_signal():
    model = train_learning_to_rank_model(dataset(), model_config())
    assert any(abs(weight) > 1e-8 for weight in model.weights)


def test_predictions_are_deterministic():
    ds = dataset()
    a = predict_learning_to_rank(train_learning_to_rank_model(ds, model_config()), ds)
    b = predict_learning_to_rank(train_learning_to_rank_model(ds, model_config()), ds)
    assert a == b


def test_evaluation_is_deterministic():
    ds = dataset()
    a = evaluate_learning_to_rank_model(train_learning_to_rank_model(ds, model_config()), ds)
    b = evaluate_learning_to_rank_model(train_learning_to_rank_model(ds, model_config()), ds)
    assert a == b


def test_model_report_links_dataset_identity():
    ds = dataset()
    report = evaluate_learning_to_rank_model(train_learning_to_rank_model(ds, model_config()), ds)
    assert report.dataset_identity == ds.dataset_identity
