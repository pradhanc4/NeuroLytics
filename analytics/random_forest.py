from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss, precision_score, recall_score

from features.sequence_dataset import SequenceDataset, validate_sequence_dataset
from features.versioning_contract import DatasetVersionReference, FeatureVersionReference, validate_dataset_version_reference, validate_feature_version_reference

RANDOM_FOREST_VERSION = "22.0.0"
MODEL_KIND = "random_forest"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class RandomForestConfig:
    n_estimators: int = 100
    criterion: str = "gini"
    max_depth: int | None = None
    min_samples_split: int = 2
    min_samples_leaf: int = 1
    max_features: int | float | str | None = "sqrt"
    bootstrap: bool = True
    oob_score: bool = False
    class_weight: str | dict[Any, float] | None = None
    max_samples: int | float | None = None
    random_state: int | None = 0
    n_jobs: int | None = 1


@dataclass(frozen=True)
class RandomForestDataset:
    feature_names: tuple[str, ...]
    feature_version: str
    dataset_identity: str
    target_name: str
    dates: tuple[date, ...]
    X: tuple[tuple[float, ...], ...]
    y: tuple[int, ...]


@dataclass(frozen=True)
class RandomForestSplit:
    split_date: date
    train: RandomForestDataset
    validation: RandomForestDataset


@dataclass(frozen=True)
class RandomForestMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    log_loss: float
    confusion_matrix: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class RandomForestFeatureImportance:
    feature_names: tuple[str, ...]
    importances: tuple[float, ...]


@dataclass(frozen=True)
class RandomForestArtifact:
    model_kind: str
    model_version: str
    feature_version: str
    dataset_identity: str
    target_name: str
    configuration: tuple[tuple[str, str], ...]
    classes: tuple[int, ...]
    artifact_identity: str


@dataclass(frozen=True)
class RandomForestValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


@dataclass(frozen=True)
class RandomForestBaselineComparison:
    random_forest_log_loss: float
    baseline_log_loss: float
    difference: float


@dataclass(frozen=True)
class RandomForestReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str


@dataclass(frozen=True)
class PositionRandomForestModels:
    models: tuple[tuple[str, RandomForestClassifier], ...]


def validate_random_forest_config(config: RandomForestConfig) -> None:
    if not isinstance(config, RandomForestConfig):
        raise TypeError("config must be a RandomForestConfig.")
    if not isinstance(config.n_estimators, int) or config.n_estimators <= 0:
        raise ValueError("n_estimators must be a positive integer.")
    if config.criterion not in {"gini", "entropy", "log_loss"}:
        raise ValueError("Unsupported random-forest criterion.")
    if config.max_depth is not None and (not isinstance(config.max_depth, int) or config.max_depth <= 0):
        raise ValueError("max_depth must be None or a positive integer.")
    if config.min_samples_split < 2:
        raise ValueError("min_samples_split must be at least 2.")
    if config.min_samples_leaf < 1:
        raise ValueError("min_samples_leaf must be at least 1.")
    if isinstance(config.max_features, int) and config.max_features < 1:
        raise ValueError("max_features integer must be positive.")
    if isinstance(config.max_features, float) and not 0 < config.max_features <= 1:
        raise ValueError("max_features float must be in (0, 1].")
    if isinstance(config.max_features, str) and config.max_features not in {"sqrt", "log2"}:
        raise ValueError("Unsupported max_features string.")
    if config.max_samples is not None:
        if isinstance(config.max_samples, int) and config.max_samples < 1:
            raise ValueError("max_samples integer must be positive.")
        if isinstance(config.max_samples, float) and not 0 < config.max_samples <= 1:
            raise ValueError("max_samples float must be in (0, 1].")
        if not isinstance(config.max_samples, (int, float)):
            raise ValueError("max_samples must be an integer, float, or None.")
        if not config.bootstrap:
            raise ValueError("max_samples requires bootstrap=True.")
    if config.oob_score and not config.bootstrap:
        raise ValueError("oob_score requires bootstrap=True.")


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


def validate_random_forest_dataset(dataset: RandomForestDataset) -> None:
    if not isinstance(dataset, RandomForestDataset):
        raise TypeError("dataset must be a RandomForestDataset.")
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
    if len(set(dataset.y)) < 2 and dataset.y:
        raise ValueError("Training data requires at least two classes.")


def build_random_forest_dataset(
    feature_names: tuple[str, ...], feature_version: str, dataset_identity: str,
    target_name: str, dates: tuple[date, ...],
    X: tuple[tuple[float, ...], ...], y: tuple[int, ...],
) -> RandomForestDataset:
    dataset = RandomForestDataset(
        tuple(feature_names), feature_version, dataset_identity, target_name,
        tuple(dates), tuple(tuple(float(v) for v in row) for row in X), tuple(y),
    )
    validate_random_forest_dataset(dataset)
    return dataset


def build_random_forest_dataset_from_sequence_dataset(
    dataset: SequenceDataset, dataset_identity: str, target_index: int = 0,
) -> RandomForestDataset:
    validate_sequence_dataset(dataset)
    if not dataset.samples:
        raise ValueError("Sequence dataset cannot be empty.")
    if not isinstance(target_index, int) or target_index < 0:
        raise ValueError("target_index must be a non-negative integer.")
    width = len(dataset.samples[0].features[0])
    names = (
        tuple(f"t{t}_{name}" for t in range(dataset.sequence_length) for name in dataset.feature_names)
        if dataset.feature_names
        else tuple(f"t{t}_feature_{i}" for t in range(dataset.sequence_length) for i in range(width))
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
    return build_random_forest_dataset(
        names,
        "sequence-" + "-".join(dataset.feature_names) if dataset.feature_names else "sequence",
        dataset_identity, dataset.target_positions[target_index],
        tuple(dates), tuple(rows), tuple(targets),
    )


def split_random_forest_dataset_temporally(dataset: RandomForestDataset, split_date: date) -> RandomForestSplit:
    validate_random_forest_dataset(dataset)
    if not isinstance(split_date, date):
        raise TypeError("split_date must be a date.")
    train_i = [i for i, d in enumerate(dataset.dates) if d <= split_date]
    val_i = [i for i, d in enumerate(dataset.dates) if d > split_date]

    def subset(indices: list[int]) -> RandomForestDataset:
        return RandomForestDataset(
            dataset.feature_names, dataset.feature_version, dataset.dataset_identity,
            dataset.target_name, tuple(dataset.dates[i] for i in indices),
            tuple(dataset.X[i] for i in indices), tuple(dataset.y[i] for i in indices),
        )

    train, validation = subset(train_i), subset(val_i)
    if len(set(train.y)) < 2:
        raise ValueError("Temporal training split must contain at least two classes.")
    return RandomForestSplit(split_date, train, validation)


def build_random_forest(config: RandomForestConfig = RandomForestConfig()) -> RandomForestClassifier:
    validate_random_forest_config(config)
    return RandomForestClassifier(
        n_estimators=config.n_estimators, criterion=config.criterion,
        max_depth=config.max_depth, min_samples_split=config.min_samples_split,
        min_samples_leaf=config.min_samples_leaf, max_features=config.max_features,
        bootstrap=config.bootstrap, oob_score=config.oob_score,
        class_weight=config.class_weight, max_samples=config.max_samples,
        random_state=config.random_state, n_jobs=config.n_jobs,
    )


def train_random_forest(
    dataset: RandomForestDataset, config: RandomForestConfig = RandomForestConfig()
) -> RandomForestClassifier:
    validate_random_forest_dataset(dataset)
    model = build_random_forest(config)
    model.fit(dataset.X, dataset.y)
    return model


def predict_classes(model: RandomForestClassifier, X: tuple[tuple[float, ...], ...]) -> tuple[int, ...]:
    _validate_matrix(X)
    return tuple(int(v) for v in model.predict(X))


def predict_probabilities(model: RandomForestClassifier, X: tuple[tuple[float, ...], ...]) -> tuple[tuple[float, ...], ...]:
    _validate_matrix(X)
    return tuple(tuple(float(v) for v in row) for row in model.predict_proba(X))


def evaluate_random_forest(model: RandomForestClassifier, dataset: RandomForestDataset) -> RandomForestMetrics:
    validate_random_forest_dataset(dataset)
    predictions = predict_classes(model, dataset.X)
    probabilities = predict_probabilities(model, dataset.X)
    return RandomForestMetrics(
        float(accuracy_score(dataset.y, predictions)),
        float(precision_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(recall_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(f1_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(log_loss(dataset.y, probabilities, labels=model.classes_)),
        tuple(tuple(int(v) for v in row) for row in confusion_matrix(dataset.y, predictions, labels=model.classes_)),
    )


def get_feature_importances(model: RandomForestClassifier, feature_names: tuple[str, ...]) -> RandomForestFeatureImportance:
    if not hasattr(model, "feature_importances_"):
        raise ValueError("Model has not been fitted.")
    if len(feature_names) != len(model.feature_importances_):
        raise ValueError("Feature-name width does not match model importances.")
    return RandomForestFeatureImportance(tuple(feature_names), tuple(float(v) for v in model.feature_importances_))


def build_position_models(
    datasets: Mapping[str, RandomForestDataset], config: RandomForestConfig = RandomForestConfig()
) -> PositionRandomForestModels:
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    return PositionRandomForestModels(tuple(
        (position, train_random_forest(datasets[position], config)) for position in sorted(datasets)
    ))


def get_position_model(models: PositionRandomForestModels, position: str) -> RandomForestClassifier:
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")


def compare_with_baseline(metrics: RandomForestMetrics, baseline_log_loss: float) -> RandomForestBaselineComparison:
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return RandomForestBaselineComparison(metrics.log_loss, float(baseline_log_loss), float(metrics.log_loss - baseline_log_loss))


def _configuration_items(config: RandomForestConfig) -> tuple[tuple[str, str], ...]:
    values = {
        "bootstrap": config.bootstrap, "class_weight": config.class_weight,
        "criterion": config.criterion, "max_depth": config.max_depth,
        "max_features": config.max_features, "max_samples": config.max_samples,
        "min_samples_leaf": config.min_samples_leaf, "min_samples_split": config.min_samples_split,
        "n_estimators": config.n_estimators, "n_jobs": config.n_jobs,
        "oob_score": config.oob_score, "random_state": config.random_state,
    }
    return tuple((key, json.dumps(values[key], sort_keys=True)) for key in sorted(values))


def build_random_forest_artifact(
    model: RandomForestClassifier, dataset: RandomForestDataset, config: RandomForestConfig
) -> RandomForestArtifact:
    validate_random_forest_dataset(dataset)
    validate_random_forest_config(config)
    if not hasattr(model, "classes_"):
        raise ValueError("Model must be fitted before artifact creation.")
    payload = {
        "classes": [int(v) for v in model.classes_],
        "configuration": list(_configuration_items(config)),
        "dataset_identity": dataset.dataset_identity,
        "feature_version": dataset.feature_version,
        "model_kind": MODEL_KIND, "model_version": RANDOM_FOREST_VERSION,
        "target_name": dataset.target_name,
    }
    identity = "random-forest-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return RandomForestArtifact(
        MODEL_KIND, RANDOM_FOREST_VERSION, dataset.feature_version,
        dataset.dataset_identity, dataset.target_name, _configuration_items(config),
        tuple(int(v) for v in model.classes_), identity,
    )


def validate_random_forest_model(model: RandomForestClassifier, dataset: RandomForestDataset) -> RandomForestValidationResult:
    issues: list[str] = []
    if not isinstance(model, RandomForestClassifier):
        return RandomForestValidationResult(INVALID, ("INVALID_MODEL_TYPE",))
    if not hasattr(model, "classes_"):
        issues.append("MODEL_NOT_FITTED")
    if hasattr(model, "classes_") and len(model.classes_) < 2:
        issues.append("INSUFFICIENT_MODEL_CLASSES")
    try:
        if model.n_features_in_ != len(dataset.feature_names):
            issues.append("FEATURE_WIDTH_MISMATCH")
    except AttributeError:
        issues.append("MISSING_FEATURE_WIDTH")
    return RandomForestValidationResult(VALID if not issues else INVALID, tuple(issues))


def validate_random_forest_version_references(
    feature_reference: FeatureVersionReference, dataset_reference: DatasetVersionReference,
    dataset: RandomForestDataset,
) -> None:
    validate_feature_version_reference(feature_reference)
    validate_dataset_version_reference(dataset_reference)
    validate_random_forest_dataset(dataset)
    if feature_reference.feature_version != dataset.feature_version:
        raise ValueError("Feature version reference does not match model dataset.")
    if dataset_reference.identity != dataset.dataset_identity:
        raise ValueError("Dataset version reference does not match model dataset.")


def save_random_forest_model(model: RandomForestClassifier, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_random_forest_model(path: str | Path) -> RandomForestClassifier:
    model = joblib.load(Path(path))
    if not isinstance(model, RandomForestClassifier):
        raise TypeError("Persisted artifact is not a RandomForestClassifier model.")
    return model


def reproduce_random_forest_artifact(
    first: RandomForestArtifact, second: RandomForestArtifact
) -> RandomForestReproducibilityResult:
    return RandomForestReproducibilityResult(first == second, first.artifact_identity, second.artifact_identity)


def validate_random_forest_pipeline(
    dataset: RandomForestDataset, config: RandomForestConfig, model: RandomForestClassifier
) -> RandomForestValidationResult:
    issues: list[str] = []
    try:
        validate_random_forest_dataset(dataset)
        validate_random_forest_config(config)
    except (TypeError, ValueError) as exc:
        issues.append(str(exc))
    issues.extend(validate_random_forest_model(model, dataset).issues)
    return RandomForestValidationResult(VALID if not issues else INVALID, tuple(issues))


def build_temporal_split_from_sequence_dataset(
    sequence_dataset: SequenceDataset, dataset_identity: str, split_date: date, target_index: int = 0
) -> RandomForestSplit:
    dataset = build_random_forest_dataset_from_sequence_dataset(sequence_dataset, dataset_identity, target_index)
    return split_random_forest_dataset_temporally(dataset, split_date)


def get_model_classes(model: RandomForestClassifier) -> tuple[int, ...]:
    if not hasattr(model, "classes_"):
        raise ValueError("Model has not been fitted.")
    return tuple(int(v) for v in model.classes_)


__all__ = [
    "RANDOM_FOREST_VERSION", "MODEL_KIND", "VALID", "INVALID",
    "RandomForestConfig", "RandomForestDataset", "RandomForestSplit",
    "RandomForestMetrics", "RandomForestFeatureImportance", "RandomForestArtifact",
    "RandomForestValidationResult", "RandomForestBaselineComparison",
    "RandomForestReproducibilityResult", "PositionRandomForestModels",
    "validate_random_forest_config", "validate_random_forest_dataset",
    "build_random_forest_dataset", "build_random_forest_dataset_from_sequence_dataset",
    "split_random_forest_dataset_temporally", "build_random_forest",
    "train_random_forest", "predict_classes", "predict_probabilities",
    "evaluate_random_forest", "get_feature_importances", "build_position_models",
    "get_position_model", "compare_with_baseline", "build_random_forest_artifact",
    "validate_random_forest_model", "validate_random_forest_version_references",
    "save_random_forest_model", "load_random_forest_model",
    "reproduce_random_forest_artifact", "validate_random_forest_pipeline",
    "build_temporal_split_from_sequence_dataset", "get_model_classes",
]
