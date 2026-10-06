from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np

from analytics.learning_to_rank_dataset import (
    LearningToRankDataset,
    LearningToRankGroup,
    LearningToRankRow,
    SPLIT_TEST,
    SPLIT_TRAIN,
    SPLIT_VALIDATION,
    validate_learning_to_rank_dataset,
)

LEARNING_TO_RANK_MODEL_VERSION = "41.0.0"
MODEL_KIND = "pairwise_logistic_ltr"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class LearningToRankModelConfig:
    learning_rate: float = 0.05
    epochs: int = 300
    l2: float = 0.001
    seed: int = 41
    top_k: int = 3
    early_stopping_patience: int = 40
    min_delta: float = 1e-10


@dataclass(frozen=True)
class LearningToRankTrainingHistory:
    losses: tuple[float, ...]
    validation_losses: tuple[float, ...]
    best_epoch: int
    stopped_early: bool


@dataclass(frozen=True)
class LearningToRankModel:
    version: str
    model_kind: str
    dataset_identity: str
    feature_schema_identity: str
    feature_names: tuple[str, ...]
    target_position: str
    weights: tuple[float, ...]
    bias: float
    config: LearningToRankModelConfig
    history: LearningToRankTrainingHistory
    model_identity: str


@dataclass(frozen=True)
class LearningToRankPrediction:
    group_id: str
    target_date: str
    candidate_digits: tuple[int, ...]
    scores: tuple[float, ...]
    probabilities: tuple[float, ...]
    ranks: tuple[int, ...]
    actual_digit: int
    top_candidate: int
    top_k_candidates: tuple[int, ...]


@dataclass(frozen=True)
class LearningToRankEvaluation:
    split: str
    groups: int
    accuracy: float
    top_k_accuracy: float
    mrr: float
    ndcg: float
    log_loss: float


@dataclass(frozen=True)
class LearningToRankModelReport:
    version: str
    model_identity: str
    dataset_identity: str
    train_evaluation: LearningToRankEvaluation
    validation_evaluation: LearningToRankEvaluation
    test_evaluation: LearningToRankEvaluation
    prediction_count: int
    report_identity: str


@dataclass(frozen=True)
class LearningToRankValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _finite(value: float) -> bool:
    return math.isfinite(float(value))


def _identity(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "learning-to-rank-model-" + hashlib.sha256(encoded).hexdigest()


def validate_learning_to_rank_model_config(config: LearningToRankModelConfig) -> None:
    if not isinstance(config, LearningToRankModelConfig):
        raise TypeError("config must be a LearningToRankModelConfig.")
    if not _finite(config.learning_rate) or config.learning_rate <= 0:
        raise ValueError("learning_rate must be positive and finite.")
    if config.epochs < 1:
        raise ValueError("epochs must be >= 1.")
    if not _finite(config.l2) or config.l2 < 0:
        raise ValueError("l2 must be finite and non-negative.")
    if config.top_k < 1 or config.top_k > 10:
        raise ValueError("top_k must be between 1 and 10.")
    if config.early_stopping_patience < 1:
        raise ValueError("early_stopping_patience must be >= 1.")
    if not _finite(config.min_delta) or config.min_delta < 0:
        raise ValueError("min_delta must be finite and non-negative.")


def _rows_by_group(dataset: LearningToRankDataset, split: str) -> tuple[tuple[LearningToRankRow, ...], ...]:
    group_ids = {
        SPLIT_TRAIN: dataset.train_group_ids,
        SPLIT_VALIDATION: dataset.validation_group_ids,
        SPLIT_TEST: dataset.test_group_ids,
    }[split]
    by_id = {group.group_id: group for group in dataset.groups}
    rows_by_id: dict[str, tuple[LearningToRankRow, ...]] = {}
    for group_id in group_ids:
        group = by_id[group_id]
        rows_by_id[group_id] = dataset.rows[group.row_start:group.row_end + 1]
    return tuple(rows_by_id[group_id] for group_id in group_ids)


def _matrix(group_rows: Sequence[LearningToRankRow]) -> tuple[np.ndarray, int]:
    rows = tuple(group_rows)
    if len(rows) != 10:
        raise ValueError("each ranking group must contain exactly ten rows.")
    x = np.asarray([row.feature_values for row in rows], dtype=float)
    labels = np.asarray([row.relevance_label for row in rows], dtype=int)
    positives = np.flatnonzero(labels == 1)
    if len(positives) != 1:
        raise ValueError("each ranking group must contain exactly one positive label.")
    return x, int(positives[0])


def _standardization(dataset: LearningToRankDataset) -> tuple[np.ndarray, np.ndarray]:
    matrices = []
    for group in _rows_by_group(dataset, SPLIT_TRAIN):
        x, _ = _matrix(group)
        matrices.append(x)
    stacked = np.vstack(matrices)
    mean = stacked.mean(axis=0)
    std = stacked.std(axis=0)
    std = np.where(std < 1e-12, 1.0, std)
    return mean, std


def _pairwise_loss_and_gradient(
    weights: np.ndarray,
    bias: float,
    x: np.ndarray,
    positive_index: int,
    l2: float,
) -> tuple[float, np.ndarray, float]:
    positive = x[positive_index]
    negatives = [index for index in range(len(x)) if index != positive_index]
    grad_w = np.zeros_like(weights)
    grad_b = 0.0
    loss = 0.0
    for negative_index in negatives:
        diff = positive - x[negative_index]
        margin = float(np.dot(weights, diff) + bias - bias)
        sigmoid = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, margin))))
        pair_loss = math.log1p(math.exp(-max(-60.0, min(60.0, margin))))
        loss += pair_loss
        grad_w += -(1.0 - sigmoid) * diff
    loss /= len(negatives)
    grad_w /= len(negatives)
    loss += 0.5 * l2 * float(np.dot(weights, weights))
    grad_w += l2 * weights
    return loss, grad_w, grad_b


def _score_matrix(weights: np.ndarray, bias: float, x: np.ndarray) -> np.ndarray:
    return x @ weights + bias


def _softmax(scores: Sequence[float]) -> np.ndarray:
    values = np.asarray(scores, dtype=float)
    shifted = values - np.max(values)
    exp_values = np.exp(np.clip(shifted, -700, 700))
    total = float(exp_values.sum())
    if total <= 0 or not math.isfinite(total):
        raise ValueError("unable to normalize ranking scores.")
    return exp_values / total


def _rank_from_scores(scores: Sequence[float]) -> tuple[int, ...]:
    order = sorted(range(len(scores)), key=lambda index: (-float(scores[index]), index))
    ranks = [0] * len(scores)
    for rank, index in enumerate(order, start=1):
        ranks[index] = rank
    return tuple(ranks)


def _evaluation(
    model: LearningToRankModel,
    dataset: LearningToRankDataset,
    split: str,
) -> LearningToRankEvaluation:
    groups = _rows_by_group(dataset, split)
    if not groups:
        raise ValueError(f"split has no ranking groups: {split}")
    accuracy = topk = mrr = ndcg = total_log_loss = 0.0
    for group_rows in groups:
        x, actual_index = _matrix(group_rows)
        standardized = (x - np.asarray(model._mean)) / np.asarray(model._std) if hasattr(model, "_mean") else x
        scores = _score_matrix(np.asarray(model.weights), model.bias, standardized)
        probabilities = _softmax(scores)
        ranks = _rank_from_scores(scores)
        accuracy += float(int(np.argmax(scores) == actual_index))
        topk += float(actual_index in sorted(range(10), key=lambda i: (-scores[i], i))[:model.config.top_k])
        mrr += 1.0 / ranks[actual_index]
        ndcg += 1.0 / math.log2(ranks[actual_index] + 1.0)
        total_log_loss += -math.log(max(float(probabilities[actual_index]), 1e-15))
    n = len(groups)
    return LearningToRankEvaluation(
        split=split,
        groups=n,
        accuracy=accuracy / n,
        top_k_accuracy=topk / n,
        mrr=mrr / n,
        ndcg=ndcg / n,
        log_loss=total_log_loss / n,
    )


def _attach_scalers(model: LearningToRankModel, mean: np.ndarray, std: np.ndarray) -> LearningToRankModel:
    object.__setattr__(model, "_mean", tuple(float(v) for v in mean))
    object.__setattr__(model, "_std", tuple(float(v) for v in std))
    return model


def train_learning_to_rank_model(
    dataset: LearningToRankDataset,
    config: LearningToRankModelConfig | None = None,
) -> LearningToRankModel:
    validation = validate_learning_to_rank_dataset(dataset)
    if not validation.is_valid:
        raise ValueError("dataset is invalid: " + ",".join(validation.issues))
    config = config or LearningToRankModelConfig()
    validate_learning_to_rank_model_config(config)
    mean, std = _standardization(dataset)
    rng = np.random.default_rng(config.seed)
    weights = rng.normal(0.0, 0.01, len(dataset.config.feature_names))
    bias = 0.0
    losses: list[float] = []
    validation_losses: list[float] = []
    best_weights = weights.copy()
    best_bias = bias
    best_validation = float("inf")
    best_epoch = 0
    patience = 0
    train_groups = _rows_by_group(dataset, SPLIT_TRAIN)
    validation_groups = _rows_by_group(dataset, SPLIT_VALIDATION)
    for epoch in range(config.epochs):
        order = rng.permutation(len(train_groups))
        epoch_loss = 0.0
        for group_index in order:
            x, positive = _matrix(train_groups[int(group_index)])
            x = (x - mean) / std
            loss, grad_w, grad_b = _pairwise_loss_and_gradient(weights, bias, x, positive, config.l2)
            weights -= config.learning_rate * grad_w
            bias -= config.learning_rate * grad_b
            epoch_loss += loss
        epoch_loss /= len(train_groups)
        losses.append(float(epoch_loss))
        val_loss = 0.0
        for group_rows in validation_groups:
            x, positive = _matrix(group_rows)
            x = (x - mean) / std
            scores = _score_matrix(weights, bias, x)
            probabilities = _softmax(scores)
            val_loss += -math.log(max(float(probabilities[positive]), 1e-15))
        val_loss /= len(validation_groups)
        validation_losses.append(float(val_loss))
        if val_loss < best_validation - config.min_delta:
            best_validation = val_loss
            best_weights = weights.copy()
            best_bias = bias
            best_epoch = epoch + 1
            patience = 0
        else:
            patience += 1
        if patience >= config.early_stopping_patience:
            break
    stopped_early = len(losses) < config.epochs
    history = LearningToRankTrainingHistory(tuple(losses), tuple(validation_losses), best_epoch, stopped_early)
    identity_payload = {
        "version": LEARNING_TO_RANK_MODEL_VERSION,
        "model_kind": MODEL_KIND,
        "dataset_identity": dataset.dataset_identity,
        "feature_schema_identity": dataset.feature_schema_identity,
        "feature_names": dataset.config.feature_names,
        "target_position": dataset.config.target_position,
        "weights": tuple(float(v) for v in best_weights),
        "bias": float(best_bias),
        "config": config,
        "history": history,
        "mean": tuple(float(v) for v in mean),
        "std": tuple(float(v) for v in std),
    }
    model = LearningToRankModel(
        version=LEARNING_TO_RANK_MODEL_VERSION,
        model_kind=MODEL_KIND,
        dataset_identity=dataset.dataset_identity,
        feature_schema_identity=dataset.feature_schema_identity,
        feature_names=dataset.config.feature_names,
        target_position=dataset.config.target_position,
        weights=tuple(float(v) for v in best_weights),
        bias=float(best_bias),
        config=config,
        history=history,
        model_identity=_identity(identity_payload),
    )
    return _attach_scalers(model, mean, std)


def predict_learning_to_rank_group(
    model: LearningToRankModel,
    group: LearningToRankGroup,
    rows: Sequence[LearningToRankRow],
) -> LearningToRankPrediction:
    if len(rows) != 10:
        raise ValueError("prediction requires exactly ten candidate rows.")
    x = np.asarray([row.feature_values for row in rows], dtype=float)
    mean = np.asarray(getattr(model, "_mean", np.zeros(x.shape[1])), dtype=float)
    std = np.asarray(getattr(model, "_std", np.ones(x.shape[1])), dtype=float)
    scores = _score_matrix(np.asarray(model.weights), model.bias, (x - mean) / std)
    probabilities = _softmax(scores)
    ranks = _rank_from_scores(scores)
    order = sorted(range(10), key=lambda i: (-scores[i], i))
    return LearningToRankPrediction(
        group_id=group.group_id,
        target_date=group.target_date.isoformat(),
        candidate_digits=tuple(row.candidate_digit for row in rows),
        scores=tuple(float(v) for v in scores),
        probabilities=tuple(float(v) for v in probabilities),
        ranks=ranks,
        actual_digit=group.actual_digit,
        top_candidate=rows[order[0]].candidate_digit,
        top_k_candidates=tuple(rows[i].candidate_digit for i in order[:model.config.top_k]),
    )


def predict_learning_to_rank(
    model: LearningToRankModel,
    dataset: LearningToRankDataset,
    split: str = SPLIT_TEST,
) -> tuple[LearningToRankPrediction, ...]:
    validation = validate_learning_to_rank_dataset(dataset)
    if not validation.is_valid:
        raise ValueError("dataset is invalid: " + ",".join(validation.issues))
    return tuple(
        predict_learning_to_rank_group(model, dataset.groups[index], group_rows)
        for index, group_rows in zip(
            [dataset.groups.index(next(group for group in dataset.groups if group.group_id == gid)) for gid in
             ({SPLIT_TRAIN: dataset.train_group_ids, SPLIT_VALIDATION: dataset.validation_group_ids, SPLIT_TEST: dataset.test_group_ids}[split])],
            _rows_by_group(dataset, split),
        )
    )


def evaluate_learning_to_rank_model(
    model: LearningToRankModel,
    dataset: LearningToRankDataset,
) -> LearningToRankModelReport:
    validation = validate_learning_to_rank_dataset(dataset)
    if not validation.is_valid:
        raise ValueError("dataset is invalid: " + ",".join(validation.issues))
    evaluations = {split: _evaluation(model, dataset, split) for split in (SPLIT_TRAIN, SPLIT_VALIDATION, SPLIT_TEST)}
    prediction_count = sum(e.groups for e in evaluations.values())
    identity_payload = {
        "version": LEARNING_TO_RANK_MODEL_VERSION,
        "model_identity": model.model_identity,
        "dataset_identity": dataset.dataset_identity,
        "evaluations": evaluations,
        "prediction_count": prediction_count,
    }
    return LearningToRankModelReport(
        version=LEARNING_TO_RANK_MODEL_VERSION,
        model_identity=model.model_identity,
        dataset_identity=dataset.dataset_identity,
        train_evaluation=evaluations[SPLIT_TRAIN],
        validation_evaluation=evaluations[SPLIT_VALIDATION],
        test_evaluation=evaluations[SPLIT_TEST],
        prediction_count=prediction_count,
        report_identity=_identity(identity_payload).replace("learning-to-rank-model-", "learning-to-rank-report-", 1),
    )


def validate_learning_to_rank_model(
    model: LearningToRankModel,
    dataset: LearningToRankDataset | None = None,
) -> LearningToRankValidationResult:
    issues: list[str] = []
    if not isinstance(model, LearningToRankModel):
        return LearningToRankValidationResult(INVALID, ("INVALID_MODEL_TYPE",))
    if model.version != LEARNING_TO_RANK_MODEL_VERSION:
        issues.append("INVALID_VERSION")
    if model.model_kind != MODEL_KIND:
        issues.append("INVALID_MODEL_KIND")
    if not model.weights or len(model.weights) != len(model.feature_names):
        issues.append("INVALID_WEIGHT_DIMENSION")
    if not all(_finite(value) for value in model.weights):
        issues.append("NON_FINITE_WEIGHTS")
    if not _finite(model.bias):
        issues.append("NON_FINITE_BIAS")
    try:
        validate_learning_to_rank_model_config(model.config)
    except (TypeError, ValueError) as exc:
        issues.append("INVALID_CONFIG:" + str(exc))
    if not model.dataset_identity:
        issues.append("MISSING_DATASET_IDENTITY")
    if not model.feature_schema_identity:
        issues.append("MISSING_FEATURE_SCHEMA_IDENTITY")
    if not model.model_identity.startswith("learning-to-rank-model-"):
        issues.append("INVALID_MODEL_IDENTITY")
    if dataset is not None:
        dataset_validation = validate_learning_to_rank_dataset(dataset)
        if not dataset_validation.is_valid:
            issues.extend("DATASET:" + issue for issue in dataset_validation.issues)
        else:
            if model.dataset_identity != dataset.dataset_identity:
                issues.append("DATASET_IDENTITY_MISMATCH")
            if model.feature_schema_identity != dataset.feature_schema_identity:
                issues.append("FEATURE_SCHEMA_IDENTITY_MISMATCH")
            if model.feature_names != dataset.config.feature_names:
                issues.append("FEATURE_SCHEMA_MISMATCH")
            if model.target_position != dataset.config.target_position:
                issues.append("TARGET_POSITION_MISMATCH")
    return LearningToRankValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))


def validate_learning_to_rank_report(
    report: LearningToRankModelReport,
    dataset: LearningToRankDataset | None = None,
) -> LearningToRankValidationResult:
    issues: list[str] = []
    if not isinstance(report, LearningToRankModelReport):
        return LearningToRankValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    if report.version != LEARNING_TO_RANK_MODEL_VERSION:
        issues.append("INVALID_VERSION")
    if report.prediction_count <= 0:
        issues.append("INVALID_PREDICTION_COUNT")
    for evaluation in (report.train_evaluation, report.validation_evaluation, report.test_evaluation):
        if evaluation.groups <= 0:
            issues.append("INVALID_GROUP_COUNT")
        for value in (evaluation.accuracy, evaluation.top_k_accuracy, evaluation.mrr, evaluation.ndcg):
            if not _finite(value) or value < 0 or value > 1:
                issues.append("INVALID_METRIC_RANGE")
        if not _finite(evaluation.log_loss) or evaluation.log_loss < 0:
            issues.append("INVALID_LOG_LOSS")
    if dataset is not None and report.dataset_identity != dataset.dataset_identity:
        issues.append("DATASET_IDENTITY_MISMATCH")
    if not report.report_identity.startswith("learning-to-rank-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return LearningToRankValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))


def save_learning_to_rank_model(model: LearningToRankModel, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_learning_to_rank_model(path: str | Path) -> LearningToRankModel:
    model = joblib.load(Path(path))
    if not isinstance(model, LearningToRankModel):
        raise ValueError("artifact is not a LearningToRankModel.")
    return model


def learning_to_rank_model_summary(model: LearningToRankModel) -> dict[str, object]:
    return {
        "version": model.version,
        "model_kind": model.model_kind,
        "dataset_identity": model.dataset_identity,
        "feature_schema_identity": model.feature_schema_identity,
        "target_position": model.target_position,
        "feature_count": len(model.feature_names),
        "top_k": model.config.top_k,
        "best_epoch": model.history.best_epoch,
        "stopped_early": model.history.stopped_early,
        "model_identity": model.model_identity,
    }


__all__ = [
    "LEARNING_TO_RANK_MODEL_VERSION",
    "MODEL_KIND",
    "VALID",
    "INVALID",
    "LearningToRankModelConfig",
    "LearningToRankTrainingHistory",
    "LearningToRankModel",
    "LearningToRankPrediction",
    "LearningToRankEvaluation",
    "LearningToRankModelReport",
    "LearningToRankValidationResult",
    "validate_learning_to_rank_model_config",
    "train_learning_to_rank_model",
    "predict_learning_to_rank_group",
    "predict_learning_to_rank",
    "evaluate_learning_to_rank_model",
    "validate_learning_to_rank_model",
    "validate_learning_to_rank_report",
    "save_learning_to_rank_model",
    "load_learning_to_rank_model",
    "learning_to_rank_model_summary",
]
