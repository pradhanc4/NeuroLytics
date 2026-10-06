import math
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from analytics.end_to_end_prediction import (
    END_TO_END_PREDICTION_VERSION,
    EndToEndPredictionResult,
    end_to_end_summary,
    run_end_to_end_prediction,
    validate_end_to_end_prediction,
)
from database.services import HistoricalResultService
from tests.test_feature_pipeline import make_config, seed_market
from features.feature_pipeline import build_feature_pipeline


def trained_predictor(seed):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(120, 6))
    y = np.arange(120) % 10
    model = LogisticRegression(
        max_iter=500,
        random_state=seed,
    ).fit(x, y)

    names = tuple(f"f{i}" for i in range(6))

    def predict(features):
        vector = np.asarray([[features.get(name, 0.0) for name in names]], dtype=float)
        return model.predict_proba(vector)[0]

    return predict


def pipeline_result(db):
    service = HistoricalResultService(db)
    market = seed_market(db, service)
    return build_feature_pipeline(
        service=service,
        market=market,
        target_date=__import__("datetime").date(2026, 1, 5),
        config=make_config(),
    )


def predictors():
    return {position: trained_predictor(index + 1) for index, position in enumerate(
        ("col1", "col2", "col3", "col4", "col5", "col6", "col7", "col8")
    )}


def test_phase90_version():
    assert END_TO_END_PREDICTION_VERSION == "90.0.0"


def test_phase90_full_pipeline_returns_result(db):
    result = run_end_to_end_prediction(
        pipeline_result(db),
        predictors(),
        model_identity="phase90-logistic-model",
        model_version="90.test",
        top_k=10,
    )
    assert isinstance(result, EndToEndPredictionResult)
    assert result.feature_count > 0
    assert len(result.position_predictions) == 8
    assert len(result.digit_rankings) == 8


def test_phase90_feature_validation_and_leakage_are_required(db):
    feature_result = pipeline_result(db)
    assert feature_result.is_valid is True
    result = run_end_to_end_prediction(
        feature_result,
        predictors(),
        model_identity="phase90-model",
        model_version="90.test",
    )
    assert validate_end_to_end_prediction(result).is_valid is True


def test_phase90_probability_rows_are_normalized(db):
    result = run_end_to_end_prediction(
        pipeline_result(db),
        predictors(),
        model_identity="phase90-model",
        model_version="90.test",
    )
    for prediction in result.position_predictions:
        assert len(prediction.probabilities) == 10
        assert math.isclose(sum(prediction.probabilities), 1.0, rel_tol=1e-9)


def test_phase90_panel_and_jodi_ranking_are_generated(db):
    result = run_end_to_end_prediction(
        pipeline_result(db),
        predictors(),
        model_identity="phase90-model",
        model_version="90.test",
        top_k=10,
    )
    assert validate_end_to_end_prediction(result).is_valid
    assert len(result.panel_ranking.candidates) == 20
    assert len(result.jodi_ranking.candidates) == 20
    assert len(result.panel_top_k.candidates) == 10
    assert len(result.jodi_top_k.candidates) == 10


def test_phase90_top_k_is_sorted_and_unique(db):
    result = run_end_to_end_prediction(
        pipeline_result(db),
        predictors(),
        model_identity="phase90-model",
        model_version="90.test",
        top_k=5,
    )
    panel = [item.value for item in result.panel_top_k.candidates]
    jodi = [item.value for item in result.jodi_top_k.candidates]
    assert len(panel) == len(set(panel))
    assert len(jodi) == len(set(jodi))
    assert [item.rank for item in result.panel_top_k.candidates] == list(range(1, 6))
    assert [item.rank for item in result.jodi_top_k.candidates] == list(range(1, 6))


def test_phase90_identity_is_reproducible(db):
    feature_result = pipeline_result(db)
    first = run_end_to_end_prediction(
        feature_result, predictors(), model_identity="phase90-model",
        model_version="90.test", top_k=10,
    )
    second = run_end_to_end_prediction(
        feature_result, predictors(), model_identity="phase90-model",
        model_version="90.test", top_k=10,
    )
    assert first.pipeline_identity == second.pipeline_identity
    assert first.panel_top_k.candidates == second.panel_top_k.candidates
    assert first.jodi_top_k.candidates == second.jodi_top_k.candidates


def test_phase90_summary_contains_user_result(db):
    result = run_end_to_end_prediction(
        pipeline_result(db), predictors(),
        model_identity="phase90-model", model_version="90.test",
    )
    summary = end_to_end_summary(result)
    assert summary["status"] == "VALID"
    assert len(summary["predicted_digits"]) == 8
    assert len(summary["panel_top_k"]) == 10
    assert len(summary["jodi_top_k"]) == 10
    assert summary["pipeline_identity"].startswith("end-to-end-pipeline-")


def test_phase90_missing_position_is_rejected(db):
    values = predictors()
    values.pop("col8")
    with pytest.raises(ValueError, match="missing position predictors"):
        run_end_to_end_prediction(
            pipeline_result(db), values,
            model_identity="phase90-model", model_version="90.test",
        )


def test_phase90_invalid_model_metadata_is_rejected(db):
    with pytest.raises(ValueError, match="model identity"):
        run_end_to_end_prediction(
            pipeline_result(db), predictors(),
            model_identity="", model_version="90.test",
        )


def test_phase90_invalid_predictor_output_is_rejected(db):
    values = predictors()
    values["col1"] = lambda features: (0.0,) * 9
    with pytest.raises(ValueError, match="exactly 10"):
        run_end_to_end_prediction(
            pipeline_result(db), values,
            model_identity="phase90-model", model_version="90.test",
        )


def test_phase90_deterministic_model_metadata_is_preserved(db):
    result = run_end_to_end_prediction(
        pipeline_result(db), predictors(),
        model_identity="phase90-logistic-model",
        model_version="90.1",
    )
    assert result.model_identity == "phase90-logistic-model"
    assert result.model_version == "90.1"
    assert result.version == "90.0.0"
