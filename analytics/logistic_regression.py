from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)

from features.sequence_dataset import (
    SequenceDataset,
    validate_sequence_dataset,
)
from features.sequence_temporal_split import (
    TemporalSequenceSplit,
    split_sequence_dataset_temporally,
)
from features.versioning_contract import (
    DatasetVersionReference,
    FeatureVersionReference,
    validate_dataset_version_reference,
    validate_feature_version_reference,
)

LOGISTIC_REGRESSION_VERSION = "20.0.0"
MODEL_KIND = "logistic_regression"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class LogisticRegressionConfig:
    penalty: str = "l2"
    C: float = 1.0
    solver: str = "lbfgs"
    max_iter: int = 1000
    class_weight: str | dict[Any, float] | None = None
    random_state: int | None = 0
    fit_intercept: bool = True


@dataclass(frozen=True)
class LogisticRegressionDataset:
    feature_names: tuple[str, ...]
    feature_version: str
    dataset_identity: str
    target_name: str
    dates: tuple[date, ...]
    X: tuple[tuple[float, ...], ...]
    y: tuple[int, ...]


@dataclass(frozen=True)
class LogisticRegressionSplit:
    split_date: date
    train: LogisticRegressionDataset
    validation: LogisticRegressionDataset


@dataclass(frozen=True)
class LogisticRegressionMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    log_loss: float
    confusion_matrix: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class LogisticRegressionArtifact:
    model_kind: str
    model_version: str
    feature_version: str
    dataset_identity: str
    target_name: str
    configuration: tuple[tuple[str, str], ...]
    classes: tuple[int, ...]
    artifact_identity: str


@dataclass(frozen=True)
class LogisticRegressionValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


@dataclass(frozen=True)
class LogisticRegressionBaselineComparison:
    logistic_log_loss: float
    baseline_log_loss: float
    difference: float


@dataclass(frozen=True)
class LogisticRegressionReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str


@dataclass(frozen=True)
class PositionLogisticRegressionModels:
    models: tuple[tuple[str, LogisticRegression], ...]


def validate_logistic_config(config: LogisticRegressionConfig) -> None:
    if not isinstance(config, LogisticRegressionConfig):
        raise TypeError("config must be a LogisticRegressionConfig.")
    if config.penalty not in {"l1", "l2", "elasticnet", "none"}:
        raise ValueError("Unsupported logistic-regression penalty.")
    if config.C <= 0:
        raise ValueError("C must be greater than zero.")
    if config.max_iter <= 0:
        raise ValueError("max_iter must be greater than zero.")
    allowed = {
        "lbfgs": {"l2", "none"},
        "liblinear": {"l1", "l2"},
        "newton-cg": {"l2", "none"},
        "newton-cholesky": {"l2", "none"},
        "sag": {"l2", "none"},
        "saga": {"l1", "l2", "elasticnet", "none"},
    }
    if config.solver not in allowed:
        raise ValueError("Unsupported logistic-regression solver.")
    if config.penalty not in allowed[config.solver]:
        raise ValueError("Penalty is incompatible with solver.")
    if config.penalty == "elasticnet" and config.solver != "saga":
        raise ValueError("elasticnet requires the saga solver.")


def _validate_matrix(X: tuple[tuple[float, ...], ...]) -> int:
    if not isinstance(X, tuple):
        raise TypeError("X must be a tuple of rows.")
    width = None
    for row in X:
        if not isinstance(row, tuple) or not row:
            raise ValueError("Every feature row must be a non-empty tuple.")
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("Feature values must be numeric.")
        width = len(row) if width is None else width
        if len(row) != width:
            raise ValueError("Feature rows must have equal width.")
    return width or 0


def validate_logistic_dataset(dataset: LogisticRegressionDataset) -> None:
    if not isinstance(dataset, LogisticRegressionDataset):
        raise TypeError("dataset must be a LogisticRegressionDataset.")
    if not dataset.feature_version.strip():
        raise ValueError("feature_version must be non-empty.")
    if not dataset.dataset_identity.strip():
        raise ValueError("dataset_identity must be non-empty.")
    if len(dataset.X) != len(dataset.y) or len(dataset.X) != len(dataset.dates):
        raise ValueError("X, y and dates must have equal lengths.")
    if len(set(dataset.feature_names)) != len(dataset.feature_names):
        raise ValueError("feature_names must be unique.")
    width = _validate_matrix(dataset.X)
    if width != len(dataset.feature_names):
        raise ValueError("Feature width must match feature_names.")
    if len(set(dataset.dates)) != len(dataset.dates):
        raise ValueError("Dataset dates must be unique.")
    if tuple(sorted(dataset.dates)) != dataset.dates:
        raise ValueError("Dataset dates must be chronological.")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in dataset.y):
        raise ValueError("Targets must be integer class labels.")
    if len(set(dataset.y)) < 2 and dataset.y:
        raise ValueError("Training data requires at least two classes.")


def build_logistic_dataset(
    feature_names: tuple[str, ...],
    feature_version: str,
    dataset_identity: str,
    target_name: str,
    dates: tuple[date, ...],
    X: tuple[tuple[float, ...], ...],
    y: tuple[int, ...],
) -> LogisticRegressionDataset:
    dataset = LogisticRegressionDataset(
        feature_names=tuple(feature_names),
        feature_version=feature_version,
        dataset_identity=dataset_identity,
        target_name=target_name,
        dates=tuple(dates),
        X=tuple(tuple(float(v) for v in row) for row in X),
        y=tuple(y),
    )
    validate_logistic_dataset(dataset)
    return dataset


def build_logistic_dataset_from_sequence_dataset(
    dataset: SequenceDataset,
    dataset_identity: str,
    target_index: int = 0,
) -> LogisticRegressionDataset:
    validate_sequence_dataset(dataset)
    if not dataset.samples:
        raise ValueError("Sequence dataset cannot be empty.")
    if not isinstance(target_index, int) or target_index < 0:
        raise ValueError("target_index must be a non-negative integer.")
    base_names = dataset.feature_names
    width = len(dataset.samples[0].features[0])
    if base_names:
        feature_names = tuple(
            f"t{t}_{name}"
            for t in range(dataset.sequence_length)
            for name in base_names
        )
    else:
        feature_names = tuple(
            f"t{t}_feature_{i}"
            for t in range(dataset.sequence_length)
            for i in range(width)
        )
    rows: list[tuple[float, ...]] = []
    dates: list[date] = []
    targets: list[int] = []
    for sample in dataset.samples:
        flat = tuple(float(v) for row in sample.features for v in row)
        if len(flat) != len(feature_names):
            raise ValueError("Flattened feature width does not match feature_names.")
        if target_index >= len(sample.target):
            raise ValueError("target_index exceeds sample target width.")
        rows.append(flat)
        dates.append(sample.target_date)
        targets.append(int(sample.target[target_index]))
    return build_logistic_dataset(
        feature_names=feature_names,
        feature_version="sequence-" + "-".join(dataset.feature_names) if dataset.feature_names else "sequence",
        dataset_identity=dataset_identity,
        target_name=dataset.target_positions[target_index],
        dates=tuple(dates),
        X=tuple(rows),
        y=tuple(targets),
    )


def split_logistic_dataset_temporally(
    dataset: LogisticRegressionDataset,
    split_date: date,
) -> LogisticRegressionSplit:
    validate_logistic_dataset(dataset)
    if not isinstance(split_date, date):
        raise TypeError("split_date must be a date.")
    train_idx = [i for i, d in enumerate(dataset.dates) if d <= split_date]
    val_idx = [i for i, d in enumerate(dataset.dates) if d > split_date]
    def subset(indices: list[int]) -> LogisticRegressionDataset:
        return LogisticRegressionDataset(
            feature_names=dataset.feature_names,
            feature_version=dataset.feature_version,
            dataset_identity=dataset.dataset_identity,
            target_name=dataset.target_name,
            dates=tuple(dataset.dates[i] for i in indices),
            X=tuple(dataset.X[i] for i in indices),
            y=tuple(dataset.y[i] for i in indices),
        )
    train = subset(train_idx)
    validation = subset(val_idx)
    if len(set(train.y)) < 2:
        raise ValueError("Temporal training split must contain at least two classes.")
    return LogisticRegressionSplit(split_date, train, validation)


def build_logistic_regression(config: LogisticRegressionConfig) -> LogisticRegression:
    validate_logistic_config(config)
    # sklearn 1.8+ deprecates the explicit ``penalty`` argument.
    # Keep NeuroLytics' legacy penalty configuration/artifact contract, but
    # translate it to the current l1_ratio/C representation at construction.
    kwargs = {
        "C": config.C,
        "solver": config.solver,
        "max_iter": config.max_iter,
        "class_weight": config.class_weight,
        "random_state": config.random_state,
        "fit_intercept": config.fit_intercept,
    }
    if config.penalty == "l1":
        kwargs["l1_ratio"] = 1.0
    elif config.penalty == "elasticnet":
        kwargs["l1_ratio"] = 0.5
    elif config.penalty == "none":
        kwargs["C"] = float("inf")
        kwargs["l1_ratio"] = 0.0
    else:
        # l2 is represented by the current default l1_ratio=0.0.
        kwargs["l1_ratio"] = 0.0
    return LogisticRegression(**kwargs)


def train_logistic_regression(
    dataset: LogisticRegressionDataset,
    config: LogisticRegressionConfig = LogisticRegressionConfig(),
) -> LogisticRegression:
    validate_logistic_dataset(dataset)
    model = build_logistic_regression(config)
    model.fit(dataset.X, dataset.y)
    return model


def predict_classes(
    model: LogisticRegression,
    X: tuple[tuple[float, ...], ...],
) -> tuple[int, ...]:
    _validate_matrix(X)
    return tuple(int(v) for v in model.predict(X))


def predict_probabilities(
    model: LogisticRegression,
    X: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], ...]:
    _validate_matrix(X)
    return tuple(tuple(float(v) for v in row) for row in model.predict_proba(X))


def evaluate_logistic_regression(
    model: LogisticRegression,
    dataset: LogisticRegressionDataset,
) -> LogisticRegressionMetrics:
    validate_logistic_dataset(dataset)
    predictions = predict_classes(model, dataset.X)
    probabilities = predict_probabilities(model, dataset.X)
    return LogisticRegressionMetrics(
        accuracy=float(accuracy_score(dataset.y, predictions)),
        precision=float(precision_score(dataset.y, predictions, average="weighted", zero_division=0)),
        recall=float(recall_score(dataset.y, predictions, average="weighted", zero_division=0)),
        f1=float(f1_score(dataset.y, predictions, average="weighted", zero_division=0)),
        log_loss=float(log_loss(dataset.y, probabilities, labels=model.classes_)),
        confusion_matrix=tuple(tuple(int(v) for v in row) for row in confusion_matrix(dataset.y, predictions, labels=model.classes_)),
    )


def build_position_models(
    datasets: Mapping[str, LogisticRegressionDataset],
    config: LogisticRegressionConfig = LogisticRegressionConfig(),
) -> PositionLogisticRegressionModels:
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    built = []
    for position in sorted(datasets):
        built.append((position, train_logistic_regression(datasets[position], config)))
    return PositionLogisticRegressionModels(tuple(built))


def get_position_model(
    models: PositionLogisticRegressionModels,
    position: str,
) -> LogisticRegression:
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")


def compare_with_baseline(
    metrics: LogisticRegressionMetrics,
    baseline_log_loss: float,
) -> LogisticRegressionBaselineComparison:
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return LogisticRegressionBaselineComparison(
        logistic_log_loss=metrics.log_loss,
        baseline_log_loss=float(baseline_log_loss),
        difference=float(metrics.log_loss - baseline_log_loss),
    )


def _configuration_items(config: LogisticRegressionConfig) -> tuple[tuple[str, str], ...]:
    values = {
        "C": config.C,
        "class_weight": config.class_weight,
        "fit_intercept": config.fit_intercept,
        "max_iter": config.max_iter,
        "penalty": config.penalty,
        "random_state": config.random_state,
        "solver": config.solver,
    }
    return tuple((key, json.dumps(values[key], sort_keys=True)) for key in sorted(values))


def _artifact_payload(
    model: LogisticRegression,
    dataset: LogisticRegressionDataset,
    config: LogisticRegressionConfig,
) -> dict[str, Any]:
    return {
        "classes": [int(v) for v in model.classes_],
        "configuration": list(_configuration_items(config)),
        "dataset_identity": dataset.dataset_identity,
        "feature_version": dataset.feature_version,
        "model_kind": MODEL_KIND,
        "model_version": LOGISTIC_REGRESSION_VERSION,
        "target_name": dataset.target_name,
    }


def build_logistic_artifact(
    model: LogisticRegression,
    dataset: LogisticRegressionDataset,
    config: LogisticRegressionConfig,
) -> LogisticRegressionArtifact:
    validate_logistic_dataset(dataset)
    validate_logistic_config(config)
    payload = _artifact_payload(model, dataset, config)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    identity = "logistic-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return LogisticRegressionArtifact(
        model_kind=MODEL_KIND,
        model_version=LOGISTIC_REGRESSION_VERSION,
        feature_version=dataset.feature_version,
        dataset_identity=dataset.dataset_identity,
        target_name=dataset.target_name,
        configuration=_configuration_items(config),
        classes=tuple(int(v) for v in model.classes_),
        artifact_identity=identity,
    )


def validate_logistic_model(
    model: LogisticRegression,
    dataset: LogisticRegressionDataset,
) -> LogisticRegressionValidationResult:
    issues: list[str] = []
    if not isinstance(model, LogisticRegression):
        issues.append("INVALID_MODEL_TYPE")
        return LogisticRegressionValidationResult(INVALID, tuple(issues))
    if not hasattr(model, "classes_"):
        issues.append("MODEL_NOT_FITTED")
    if len(model.classes_) < 2 if hasattr(model, "classes_") else True:
        issues.append("INSUFFICIENT_MODEL_CLASSES")
    try:
        if model.n_features_in_ != len(dataset.feature_names):
            issues.append("FEATURE_WIDTH_MISMATCH")
    except AttributeError:
        issues.append("MISSING_FEATURE_WIDTH")
    return LogisticRegressionValidationResult(
        VALID if not issues else INVALID,
        tuple(issues),
    )


def validate_logistic_version_references(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
    dataset: LogisticRegressionDataset,
) -> None:
    validate_feature_version_reference(feature_reference)
    validate_dataset_version_reference(dataset_reference)
    validate_logistic_dataset(dataset)
    if feature_reference.feature_version != dataset.feature_version:
        raise ValueError("Feature version reference does not match model dataset.")
    if dataset_reference.identity != dataset.dataset_identity:
        raise ValueError("Dataset version reference does not match model dataset.")


def save_logistic_model(model: LogisticRegression, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_logistic_model(path: str | Path) -> LogisticRegression:
    model = joblib.load(Path(path))
    if not isinstance(model, LogisticRegression):
        raise TypeError("Persisted artifact is not a LogisticRegression model.")
    return model


def reproduce_logistic_artifact(
    first: LogisticRegressionArtifact,
    second: LogisticRegressionArtifact,
) -> LogisticRegressionReproducibilityResult:
    return LogisticRegressionReproducibilityResult(
        identical=first == second,
        first_identity=first.artifact_identity,
        second_identity=second.artifact_identity,
    )


def validate_logistic_pipeline(
    dataset: LogisticRegressionDataset,
    config: LogisticRegressionConfig,
    model: LogisticRegression,
) -> LogisticRegressionValidationResult:
    issues: list[str] = []
    try:
        validate_logistic_dataset(dataset)
        validate_logistic_config(config)
    except (TypeError, ValueError) as exc:
        issues.append(str(exc))
    model_result = validate_logistic_model(model, dataset)
    issues.extend(model_result.issues)
    return LogisticRegressionValidationResult(
        VALID if not issues else INVALID,
        tuple(issues),
    )


def build_temporal_split_from_sequence_dataset(
    sequence_dataset: SequenceDataset,
    dataset_identity: str,
    split_date: date,
    target_index: int = 0,
) -> LogisticRegressionSplit:
    dataset = build_logistic_dataset_from_sequence_dataset(
        sequence_dataset, dataset_identity, target_index
    )
    return split_logistic_dataset_temporally(dataset, split_date)


def get_model_classes(model: LogisticRegression) -> tuple[int, ...]:
    if not hasattr(model, "classes_"):
        raise ValueError("Model has not been fitted.")
    return tuple(int(v) for v in model.classes_)


__all__ = [
    "LOGISTIC_REGRESSION_VERSION",
    "MODEL_KIND",
    "VALID",
    "INVALID",
    "LogisticRegressionConfig",
    "LogisticRegressionDataset",
    "LogisticRegressionSplit",
    "LogisticRegressionMetrics",
    "LogisticRegressionArtifact",
    "LogisticRegressionValidationResult",
    "LogisticRegressionBaselineComparison",
    "LogisticRegressionReproducibilityResult",
    "PositionLogisticRegressionModels",
    "validate_logistic_config",
    "validate_logistic_dataset",
    "build_logistic_dataset",
    "build_logistic_dataset_from_sequence_dataset",
    "split_logistic_dataset_temporally",
    "build_logistic_regression",
    "train_logistic_regression",
    "predict_classes",
    "predict_probabilities",
    "evaluate_logistic_regression",
    "build_position_models",
    "get_position_model",
    "compare_with_baseline",
    "build_logistic_artifact",
    "validate_logistic_model",
    "validate_logistic_version_references",
    "save_logistic_model",
    "load_logistic_model",
    "reproduce_logistic_artifact",
    "validate_logistic_pipeline",
    "build_temporal_split_from_sequence_dataset",
    "get_model_classes",
]
