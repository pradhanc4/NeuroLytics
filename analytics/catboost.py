from __future__ import annotations

import hashlib
import json
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss, precision_score, recall_score

from features.sequence_dataset import SequenceDataset, validate_sequence_dataset
from features.versioning_contract import (
    DatasetVersionReference,
    FeatureVersionReference,
    validate_dataset_version_reference,
    validate_feature_version_reference,
)

CATBOOST_VERSION = "27.0.0"
CATBOOST_RUNTIME_VERSION = "1.2.10"
MODEL_KIND = "catboost"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class CatBoostConfig:
    iterations: int = 100
    depth: int = 6
    learning_rate: float = 0.1
    l2_leaf_reg: float = 3.0
    random_strength: float = 1.0
    bagging_temperature: float = 1.0
    border_count: int = 254
    loss_function: str = "auto"
    eval_metric: str = "Logloss"
    early_stopping_rounds: int | None = None
    random_state: int | None = 0
    thread_count: int = 1
    verbose: bool = False
    allow_writing_files: bool = False


@dataclass(frozen=True)
class CatBoostDataset:
    feature_names: tuple[str, ...]
    feature_version: str
    dataset_identity: str
    target_name: str
    dates: tuple[date, ...]
    X: tuple[tuple[float, ...], ...]
    y: tuple[int, ...]


@dataclass(frozen=True)
class CatBoostSplit:
    split_date: date
    train: CatBoostDataset
    validation: CatBoostDataset


@dataclass(frozen=True)
class CatBoostMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    log_loss: float
    confusion_matrix: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class CatBoostFeatureImportance:
    feature_names: tuple[str, ...]
    importances: tuple[float, ...]


@dataclass(frozen=True)
class CatBoostArtifact:
    model_kind: str
    model_version: str
    runtime_version: str
    feature_version: str
    dataset_identity: str
    target_name: str
    configuration: tuple[tuple[str, str], ...]
    classes: tuple[int, ...]
    artifact_identity: str


@dataclass(frozen=True)
class CatBoostValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


@dataclass(frozen=True)
class CatBoostBaselineComparison:
    catboost_log_loss: float
    baseline_log_loss: float
    difference: float


@dataclass(frozen=True)
class CatBoostReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str


@dataclass(frozen=True)
class PositionCatBoostModels:
    models: tuple[tuple[str, CatBoostClassifier], ...]


def validate_catboost_config(config: CatBoostConfig) -> None:
    if not isinstance(config, CatBoostConfig):
        raise TypeError("config must be a CatBoostConfig.")
    if not isinstance(config.iterations, int) or config.iterations <= 0:
        raise ValueError("iterations must be a positive integer.")
    if not isinstance(config.depth, int) or not 1 <= config.depth <= 16:
        raise ValueError("depth must be between 1 and 16.")
    if config.learning_rate <= 0:
        raise ValueError("learning_rate must be positive.")
    if config.l2_leaf_reg < 0 or config.random_strength < 0 or config.bagging_temperature < 0:
        raise ValueError("CatBoost regularization/randomness parameters cannot be negative.")
    if not isinstance(config.border_count, int) or not 1 <= config.border_count <= 65535:
        raise ValueError("border_count must be between 1 and 65535.")
    if config.loss_function not in {"auto", "Logloss", "MultiClass"}:
        raise ValueError("Unsupported CatBoost loss_function.")
    if not isinstance(config.eval_metric, str) or not config.eval_metric.strip():
        raise ValueError("eval_metric must be a non-empty string.")
    if config.early_stopping_rounds is not None and (
        not isinstance(config.early_stopping_rounds, int) or config.early_stopping_rounds <= 0
    ):
        raise ValueError("early_stopping_rounds must be None or a positive integer.")
    if not isinstance(config.thread_count, int) or config.thread_count == 0:
        raise ValueError("thread_count must be a non-zero integer.")
    if not isinstance(config.verbose, bool) or not isinstance(config.allow_writing_files, bool):
        raise ValueError("verbose and allow_writing_files must be booleans.")


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
            if not np.isfinite(float(value)):
                raise ValueError("Feature values must be finite.")
        width = len(row) if width is None else width
        if len(row) != width:
            raise ValueError("Feature rows must have equal width.")
    return width or 0


def validate_catboost_dataset(dataset: CatBoostDataset) -> None:
    if not isinstance(dataset, CatBoostDataset):
        raise TypeError("dataset must be a CatBoostDataset.")
    if not dataset.feature_version.strip() or not dataset.dataset_identity.strip():
        raise ValueError("feature_version and dataset_identity must be non-empty.")
    if len(dataset.X) != len(dataset.y) or len(dataset.X) != len(dataset.dates):
        raise ValueError("X, y and dates must have equal lengths.")
    if len(set(dataset.feature_names)) != len(dataset.feature_names):
        raise ValueError("feature_names must be unique.")
    if _validate_matrix(dataset.X) != len(dataset.feature_names):
        raise ValueError("Feature width must match feature_names.")
    if len(set(dataset.dates)) != len(dataset.dates):
        raise ValueError("Dataset dates must be unique.")
    if tuple(sorted(dataset.dates)) != dataset.dates:
        raise ValueError("Dataset dates must be chronological.")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in dataset.y):
        raise ValueError("Targets must be integer class labels.")
    if len(dataset.y) and len(set(dataset.y)) < 2:
        raise ValueError("Training data requires at least two classes.")


def build_catboost_dataset(
    feature_names, feature_version, dataset_identity, target_name, dates, X, y
) -> CatBoostDataset:
    dataset = CatBoostDataset(
        tuple(feature_names),
        feature_version,
        dataset_identity,
        target_name,
        tuple(dates),
        tuple(tuple(float(v) for v in row) for row in X),
        tuple(y),
    )
    validate_catboost_dataset(dataset)
    return dataset


def build_catboost_dataset_from_sequence_dataset(
    dataset: SequenceDataset, dataset_identity: str, target_index: int = 0
) -> CatBoostDataset:
    validate_sequence_dataset(dataset)
    if not dataset.samples:
        raise ValueError("Sequence dataset cannot be empty.")
    if not isinstance(target_index, int) or target_index < 0:
        raise ValueError("target_index must be a non-negative integer.")
    names = (
        tuple(
            f"t{t}_{name}"
            for t in range(dataset.sequence_length)
            for name in dataset.feature_names
        )
        if dataset.feature_names
        else tuple(
            f"t{t}_feature_{i}"
            for t in range(dataset.sequence_length)
            for i in range(len(dataset.samples[0].features[0]))
        )
    )
    rows, dates, targets = [], [], []
    for sample in dataset.samples:
        flat = tuple(float(v) for row in sample.features for v in row)
        if len(flat) != len(names):
            raise ValueError("Flattened feature width does not match feature_names.")
        if target_index >= len(sample.target):
            raise ValueError("target_index exceeds sample target width.")
        rows.append(flat)
        dates.append(sample.target_date)
        targets.append(int(sample.target[target_index]))
    return build_catboost_dataset(
        names,
        "sequence-" + "-".join(dataset.feature_names) if dataset.feature_names else "sequence",
        dataset_identity,
        dataset.target_positions[target_index],
        tuple(dates),
        tuple(rows),
        tuple(targets),
    )


def split_catboost_dataset_temporally(dataset: CatBoostDataset, split_date: date) -> CatBoostSplit:
    validate_catboost_dataset(dataset)
    if not isinstance(split_date, date):
        raise TypeError("split_date must be a date.")
    train_i = [i for i, d in enumerate(dataset.dates) if d <= split_date]
    val_i = [i for i, d in enumerate(dataset.dates) if d > split_date]

    def subset(indices):
        return CatBoostDataset(
            dataset.feature_names,
            dataset.feature_version,
            dataset.dataset_identity,
            dataset.target_name,
            tuple(dataset.dates[i] for i in indices),
            tuple(dataset.X[i] for i in indices),
            tuple(dataset.y[i] for i in indices),
        )

    train, validation = subset(train_i), subset(val_i)
    if len(set(train.y)) < 2:
        raise ValueError("Temporal training split must contain at least two classes.")
    return CatBoostSplit(split_date, train, validation)


def _objective_for(dataset: CatBoostDataset, config: CatBoostConfig) -> str:
    if config.loss_function != "auto":
        return config.loss_function
    return "Logloss" if len(set(dataset.y)) == 2 else "MultiClass"


def build_catboost(
    config: CatBoostConfig = CatBoostConfig(),
    loss_function: str = "Logloss",
    random_seed: int | None = None,
) -> CatBoostClassifier:
    validate_catboost_config(config)
    if loss_function not in {"Logloss", "MultiClass"}:
        raise ValueError("Unsupported CatBoost loss_function.")
    if random_seed is None:
        random_seed = config.random_state
    metric = config.eval_metric
    if loss_function == "MultiClass" and metric.lower() == "logloss":
        metric = "MultiClass"
    return CatBoostClassifier(
        iterations=config.iterations,
        depth=config.depth,
        learning_rate=config.learning_rate,
        l2_leaf_reg=config.l2_leaf_reg,
        random_strength=config.random_strength,
        bagging_temperature=config.bagging_temperature,
        border_count=config.border_count,
        loss_function=loss_function,
        eval_metric=metric,
        random_seed=random_seed,
        thread_count=config.thread_count,
        verbose=config.verbose,
        allow_writing_files=config.allow_writing_files,
    )


def train_catboost(
    dataset: CatBoostDataset,
    config: CatBoostConfig = CatBoostConfig(),
    validation_dataset: CatBoostDataset | None = None,
) -> CatBoostClassifier:
    validate_catboost_dataset(dataset)
    validate_catboost_config(config)
    objective = _objective_for(dataset, config)
    model = build_catboost(config, objective)

    fit_kwargs: dict[str, Any] = {}
    if validation_dataset is not None:
        validate_catboost_dataset(validation_dataset)
        if set(validation_dataset.y) != set(dataset.y):
            raise ValueError(
                "Validation dataset must contain the same class labels as the training dataset."
            )
        fit_kwargs["eval_set"] = (np.asarray(validation_dataset.X, dtype=float), np.asarray(validation_dataset.y, dtype=int))
        if config.early_stopping_rounds is not None:
            fit_kwargs["early_stopping_rounds"] = config.early_stopping_rounds
    elif config.early_stopping_rounds is not None:
        raise ValueError("early_stopping_rounds requires validation_dataset.")

    model.fit(
        np.asarray(dataset.X, dtype=float),
        np.asarray(dataset.y, dtype=int),
        **fit_kwargs,
    )
    return model


def predict_classes(model: CatBoostClassifier, X) -> tuple[int, ...]:
    _validate_matrix(tuple(tuple(float(v) for v in row) for row in X))
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*feature names.*", category=UserWarning)
        return tuple(int(v) for v in model.predict(np.asarray(X, dtype=float)).ravel())


def predict_probabilities(model: CatBoostClassifier, X) -> tuple[tuple[float, ...], ...]:
    _validate_matrix(tuple(tuple(float(v) for v in row) for row in X))
    raw = model.predict_proba(np.asarray(X, dtype=float))
    rows = []
    for row in raw:
        values = [max(0.0, float(v)) for v in row]
        total = sum(values)
        rows.append(tuple(v / total for v in values) if total else tuple(values))
    return tuple(rows)


def evaluate_catboost(model: CatBoostClassifier, dataset: CatBoostDataset) -> CatBoostMetrics:
    validate_catboost_dataset(dataset)
    predictions = predict_classes(model, dataset.X)
    probabilities = predict_probabilities(model, dataset.X)
    classes = get_model_classes(model)
    return CatBoostMetrics(
        float(accuracy_score(dataset.y, predictions)),
        float(precision_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(recall_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(f1_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(log_loss(dataset.y, probabilities, labels=classes)),
        tuple(tuple(int(v) for v in row) for row in confusion_matrix(dataset.y, predictions, labels=classes)),
    )


def get_feature_importances(
    model: CatBoostClassifier, feature_names: tuple[str, ...]
) -> CatBoostFeatureImportance:
    if not hasattr(model, "feature_importances_"):
        raise ValueError("Model has not been fitted.")
    if len(feature_names) != len(model.feature_importances_):
        raise ValueError("Feature-name width does not match model importances.")
    return CatBoostFeatureImportance(
        tuple(feature_names), tuple(float(v) for v in model.feature_importances_)
    )


def build_position_models(
    datasets: Mapping[str, CatBoostDataset],
    config: CatBoostConfig = CatBoostConfig(),
) -> PositionCatBoostModels:
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    return PositionCatBoostModels(
        tuple((position, train_catboost(datasets[position], config)) for position in sorted(datasets))
    )


def get_position_model(models: PositionCatBoostModels, position: str) -> CatBoostClassifier:
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")


def get_model_classes(model: CatBoostClassifier) -> tuple[int, ...]:
    if getattr(model, "classes_", None) is None:
        raise ValueError("Model must be fitted.")
    return tuple(int(v) for v in model.classes_)


def compare_with_baseline(
    metrics: CatBoostMetrics, baseline_log_loss: float
) -> CatBoostBaselineComparison:
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return CatBoostBaselineComparison(
        metrics.log_loss, float(baseline_log_loss), float(metrics.log_loss - baseline_log_loss)
    )


def _configuration_items(config: CatBoostConfig) -> tuple[tuple[str, str], ...]:
    keys = (
        "iterations", "depth", "learning_rate", "l2_leaf_reg", "random_strength",
        "bagging_temperature", "border_count", "loss_function", "eval_metric",
        "early_stopping_rounds", "random_state", "thread_count", "verbose",
        "allow_writing_files",
    )
    return tuple((key, json.dumps(getattr(config, key), sort_keys=True)) for key in sorted(keys))


def build_catboost_artifact(
    model: CatBoostClassifier, dataset: CatBoostDataset, config: CatBoostConfig
) -> CatBoostArtifact:
    validate_catboost_dataset(dataset)
    validate_catboost_config(config)
    if not hasattr(model, "classes_"):
        raise ValueError("Model must be fitted before artifact creation.")
    payload = {
        "classes": [int(v) for v in model.classes_],
        "configuration": list(_configuration_items(config)),
        "dataset_identity": dataset.dataset_identity,
        "feature_version": dataset.feature_version,
        "model_kind": MODEL_KIND,
        "model_version": CATBOOST_VERSION,
        "runtime_version": CATBOOST_RUNTIME_VERSION,
        "target_name": dataset.target_name,
    }
    identity = "catboost-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CatBoostArtifact(
        MODEL_KIND,
        CATBOOST_VERSION,
        CATBOOST_RUNTIME_VERSION,
        dataset.feature_version,
        dataset.dataset_identity,
        dataset.target_name,
        _configuration_items(config),
        tuple(int(v) for v in model.classes_),
        identity,
    )


def validate_catboost_model(
    model: CatBoostClassifier, dataset: CatBoostDataset
) -> CatBoostValidationResult:
    if not isinstance(model, CatBoostClassifier):
        return CatBoostValidationResult(INVALID, ("INVALID_MODEL_TYPE",))
    issues = []
    fitted = getattr(model, "classes_", None) is not None
    if not fitted:
        issues.append("MODEL_NOT_FITTED")
    else:
        if len(model.classes_) < 2:
            issues.append("INSUFFICIENT_MODEL_CLASSES")
        try:
            if model.n_features_in_ != len(dataset.feature_names):
                issues.append("FEATURE_WIDTH_MISMATCH")
        except AttributeError:
            issues.append("MISSING_FEATURE_WIDTH")
    return CatBoostValidationResult(VALID if not issues else INVALID, tuple(issues))


def validate_catboost_version_references(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
    dataset: CatBoostDataset,
) -> None:
    validate_feature_version_reference(feature_reference)
    validate_dataset_version_reference(dataset_reference)
    validate_catboost_dataset(dataset)
    if feature_reference.feature_version != dataset.feature_version:
        raise ValueError("Feature version reference does not match model dataset.")
    if dataset_reference.identity != dataset.dataset_identity:
        raise ValueError("Dataset version reference does not match model dataset.")


def save_catboost_model(model: CatBoostClassifier, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_catboost_model(path: str | Path) -> CatBoostClassifier:
    model = joblib.load(Path(path))
    if not isinstance(model, CatBoostClassifier):
        raise TypeError("Persisted artifact is not a CatBoostClassifier model.")
    return model


def reproduce_catboost_artifact(
    first: CatBoostArtifact, second: CatBoostArtifact
) -> CatBoostReproducibilityResult:
    return CatBoostReproducibilityResult(
        first == second, first.artifact_identity, second.artifact_identity
    )


def validate_catboost_pipeline(
    dataset: CatBoostDataset, config: CatBoostConfig, model: CatBoostClassifier
) -> CatBoostValidationResult:
    issues = []
    try:
        validate_catboost_dataset(dataset)
        validate_catboost_config(config)
    except (TypeError, ValueError) as exc:
        issues.append(str(exc))
    issues.extend(validate_catboost_model(model, dataset).issues)
    return CatBoostValidationResult(VALID if not issues else INVALID, tuple(issues))


def build_temporal_split_from_sequence_dataset(
    sequence_dataset: SequenceDataset,
    dataset_identity: str,
    split_date: date,
    target_index: int = 0,
) -> CatBoostSplit:
    return split_catboost_dataset_temporally(
        build_catboost_dataset_from_sequence_dataset(
            sequence_dataset, dataset_identity, target_index
        ),
        split_date,
    )
