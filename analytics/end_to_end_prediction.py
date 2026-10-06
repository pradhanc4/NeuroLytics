from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Callable, Mapping, Sequence

from analytics.candidate_scoring import (
    SequenceCandidateRanking,
    rank_candidate_probabilities,
    validate_sequence_candidate_ranking,
)
from analytics.jodi_ranking import (
    JodiCandidateInput,
    JodiRankingObservation,
    rank_jodis_from_predictions,
    validate_jodi_ranking,
)
from analytics.learning_to_rank_model import LearningToRankPrediction
from analytics.panel_ranking import (
    PanelCandidateInput,
    PanelRankingObservation,
    rank_panels_from_predictions,
    validate_panel_ranking,
)
from analytics.top_k_framework import (
    TopKSelection,
    top_k_selection,
    validate_top_k_selection,
)
from features.feature_pipeline import FeaturePipelineResult, is_pipeline_valid

END_TO_END_PREDICTION_VERSION = "90.0.0"
VALID = "VALID"
INVALID = "INVALID"
POSITIONS = ("col1", "col2", "col3", "col4", "col5", "col6", "col7", "col8")


@dataclass(frozen=True)
class PositionPrediction:
    position: str
    probabilities: tuple[float, ...]
    predicted_digit: int
    model_identity: str
    model_version: str


@dataclass(frozen=True)
class EndToEndPredictionResult:
    version: str
    market_id: int
    target_date: date
    feature_version: str
    feature_identity: str
    feature_count: int
    model_identity: str
    model_version: str
    position_predictions: tuple[PositionPrediction, ...]
    digit_rankings: tuple[SequenceCandidateRanking, ...]
    panel_ranking: PanelRankingObservation
    jodi_ranking: JodiRankingObservation
    panel_top_k: TopKSelection
    jodi_top_k: TopKSelection
    pipeline_identity: str


@dataclass(frozen=True)
class EndToEndValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _identity(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "end-to-end-pipeline-" + hashlib.sha256(encoded).hexdigest()


def _validate_probabilities(values: Sequence[float]) -> tuple[float, ...]:
    row = tuple(float(value) for value in values)
    if len(row) != 10:
        raise ValueError("position prediction must contain exactly 10 probabilities.")
    if any(not math.isfinite(value) or value < 0 for value in row):
        raise ValueError("position probabilities must be finite and non-negative.")
    total = sum(row)
    if total <= 0:
        raise ValueError("position probabilities must contain positive mass.")
    return tuple(value / total for value in row)


def _prediction(
    position: str,
    probabilities: Sequence[float],
    model_identity: str,
    model_version: str,
) -> PositionPrediction:
    if position not in POSITIONS:
        raise ValueError("unsupported prediction position: " + position)
    if not model_identity.strip() or not model_version.strip():
        raise ValueError("model identity and model version are required.")
    normalized = _validate_probabilities(probabilities)
    predicted = max(range(10), key=lambda digit: (normalized[digit], -digit))
    return PositionPrediction(position, normalized, predicted, model_identity, model_version)


def _learning_prediction(
    position: str,
    prediction: PositionPrediction,
) -> LearningToRankPrediction:
    order = sorted(range(10), key=lambda digit: (-prediction.probabilities[digit], digit))
    ranks = [0] * 10
    for index, digit in enumerate(order, start=1):
        ranks[digit] = index
    return LearningToRankPrediction(
        group_id="phase90-" + position,
        target_date="",
        candidate_digits=tuple(range(10)),
        scores=prediction.probabilities,
        probabilities=prediction.probabilities,
        ranks=tuple(ranks),
        actual_digit=prediction.predicted_digit,
        top_candidate=prediction.predicted_digit,
        top_k_candidates=tuple(order[:3]),
    )
def _numeric_feature_vector(result: FeaturePipelineResult) -> Mapping[str, float]:
    if not isinstance(result, FeaturePipelineResult):
        raise TypeError("feature_result must be a FeaturePipelineResult.")
    if not is_pipeline_valid(result):
        raise ValueError("feature pipeline is invalid or contains leakage.")
    values = {}
    for name, value in result.dataset.values.items():
        if isinstance(value, bool):
            values[name] = float(value)
        elif isinstance(value, (int, float)) and math.isfinite(float(value)):
            values[name] = float(value)
    if not values:
        raise ValueError("feature pipeline contains no numeric features.")
    return values


def run_end_to_end_prediction(
    feature_result: FeaturePipelineResult,
    position_predictors: Mapping[str, Callable[[Mapping[str, float]], Sequence[float]]],
    *,
    model_identity: str,
    model_version: str,
    top_k: int = 10,
) -> EndToEndPredictionResult:
    features = _numeric_feature_vector(feature_result)
    missing = [position for position in POSITIONS if position not in position_predictors]
    if missing:
        raise ValueError("missing position predictors: " + ",".join(missing))

    predictions = []
    for position in POSITIONS:
        predictor = position_predictors[position]
        if not callable(predictor):
            raise TypeError("position predictor must be callable.")
        probabilities = predictor(features)
        predictions.append(
            _prediction(position, probabilities, model_identity, model_version)
        )
    position_predictions = tuple(predictions)

    digit_rankings = tuple(
        rank_candidate_probabilities(
            prediction.probabilities,
            dataset_identity=feature_result.version_identity.identity,
            ensemble_identity=model_identity,
            observation_index=index,
            top_k=top_k,
        )
        for index, prediction in enumerate(position_predictions)
    )

    rank_by_position = {
        prediction.position: prediction
        for prediction in position_predictions
    }
    panel_candidates = tuple(
        PanelCandidateInput(
            f"{a}{b}{c}",
        )
        for a in range(10)
        for b in range(10)
        for c in range(10)
    )
    panel_ranking = rank_panels_from_predictions(
        (
            _learning_prediction("col1", rank_by_position["col1"]),
            _learning_prediction("col2", rank_by_position["col2"]),
            _learning_prediction("col3", rank_by_position["col3"]),
        ),
        panel_candidates,
        group_id="phase90-panel",
        target_date=feature_result.target_date,
        target_position="panel",
        top_k=max(top_k, 20),
    )

    jodi_candidates = tuple(
        JodiCandidateInput(f"{a}{b}")
        for a in range(10)
        for b in range(10)
    )
    jodi_ranking = rank_jodis_from_predictions(
        (
            _learning_prediction("col1", rank_by_position["col1"]),
            _learning_prediction("col2", rank_by_position["col2"]),
        ),
        jodi_candidates,
        group_id="phase90-jodi",
        target_date=feature_result.target_date,
        target_position="jodi",
        top_k=max(top_k, 20),
    )

    panel_top_k = top_k_selection(panel_ranking, top_k)
    jodi_top_k = top_k_selection(jodi_ranking, top_k)

    identity = _identity(
        {
            "version": END_TO_END_PREDICTION_VERSION,
            "market_id": feature_result.market_id,
            "target_date": feature_result.target_date,
            "feature_identity": feature_result.version_identity.identity,
            "model_identity": model_identity,
            "model_version": model_version,
            "positions": [
                (item.position, item.probabilities)
                for item in position_predictions
            ],
            "panel": panel_ranking.ranking_identity,
            "jodi": jodi_ranking.ranking_identity,
            "top_k": top_k,
        }
    )
    return EndToEndPredictionResult(
        END_TO_END_PREDICTION_VERSION,
        feature_result.market_id,
        feature_result.target_date,
        feature_result.feature_version,
        feature_result.version_identity.identity,
        feature_result.feature_count,
        model_identity,
        model_version,
        position_predictions,
        digit_rankings,
        panel_ranking,
        jodi_ranking,
        panel_top_k,
        jodi_top_k,
        identity,
    )


def validate_end_to_end_prediction(
    result: EndToEndPredictionResult,
) -> EndToEndValidationResult:
    if not isinstance(result, EndToEndPredictionResult):
        return EndToEndValidationResult(INVALID, ("INVALID_RESULT_TYPE",))
    issues = []
    if result.version != END_TO_END_PREDICTION_VERSION:
        issues.append("INVALID_VERSION")
    if result.market_id <= 0:
        issues.append("INVALID_MARKET_ID")
    if not result.feature_version.strip() or not result.feature_identity.strip():
        issues.append("MISSING_FEATURE_IDENTITY")
    if result.feature_count <= 0:
        issues.append("INVALID_FEATURE_COUNT")
    if not result.model_identity.strip() or not result.model_version.strip():
        issues.append("MISSING_MODEL_IDENTITY")
    if tuple(item.position for item in result.position_predictions) != POSITIONS:
        issues.append("POSITION_PREDICTION_MISMATCH")
    for item in result.position_predictions:
        try:
            _validate_probabilities(item.probabilities)
        except ValueError:
            issues.append("INVALID_POSITION_PROBABILITIES")
    for ranking in result.digit_rankings:
        if not validate_sequence_candidate_ranking(ranking).is_valid:
            issues.append("INVALID_DIGIT_RANKING")
    if not validate_panel_ranking(result.panel_ranking).is_valid:
        issues.append("INVALID_PANEL_RANKING")
    if not validate_jodi_ranking(result.jodi_ranking).is_valid:
        issues.append("INVALID_JODI_RANKING")
    if not validate_top_k_selection(result.panel_top_k).is_valid:
        issues.append("INVALID_PANEL_TOP_K")
    if not validate_top_k_selection(result.jodi_top_k).is_valid:
        issues.append("INVALID_JODI_TOP_K")
    if not result.pipeline_identity.startswith("end-to-end-pipeline-"):
        issues.append("INVALID_PIPELINE_IDENTITY")
    return EndToEndValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def end_to_end_summary(result: EndToEndPredictionResult) -> dict[str, object]:
    validation = validate_end_to_end_prediction(result)
    return {
        "status": validation.status,
        "version": result.version,
        "market_id": result.market_id,
        "target_date": result.target_date.isoformat(),
        "feature_version": result.feature_version,
        "feature_identity": result.feature_identity,
        "feature_count": result.feature_count,
        "model_identity": result.model_identity,
        "model_version": result.model_version,
        "predicted_digits": {
            item.position: item.predicted_digit
            for item in result.position_predictions
        },
        "panel_top_k": [item.value for item in result.panel_top_k.candidates],
        "jodi_top_k": [item.value for item in result.jodi_top_k.candidates],
        "pipeline_identity": result.pipeline_identity,
    }


__all__ = [
    "END_TO_END_PREDICTION_VERSION",
    "VALID",
    "INVALID",
    "PositionPrediction",
    "EndToEndPredictionResult",
    "EndToEndValidationResult",
    "run_end_to_end_prediction",
    "validate_end_to_end_prediction",
    "end_to_end_summary",
]
