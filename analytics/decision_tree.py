from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import joblib
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, log_loss,
    precision_score, recall_score,
)
from sklearn.tree import DecisionTreeClassifier

from features.sequence_dataset import SequenceDataset, validate_sequence_dataset
from features.sequence_temporal_split import split_sequence_dataset_temporally
from features.versioning_contract import (
    DatasetVersionReference, FeatureVersionReference,
    validate_dataset_version_reference, validate_feature_version_reference,
)

DECISION_TREE_VERSION = "21.0.0"
MODEL_KIND = "decision_tree"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class DecisionTreeConfig:
    criterion: str = "gini"
    splitter: str = "best"
    max_depth: int | None = None
    min_samples_split: int = 2
    min_samples_leaf: int = 1
    max_features: int | float | str | None = None
    class_weight: str | dict[Any, float] | None = None
    random_state: int | None = 0


@dataclass(frozen=True)
class DecisionTreeDataset:
    feature_names: tuple[str, ...]
    feature_version: str
    dataset_identity: str
    target_name: str
    dates: tuple[date, ...]
    X: tuple[tuple[float, ...], ...]
    y: tuple[int, ...]


@dataclass(frozen=True)
class DecisionTreeSplit:
    split_date: date
    train: DecisionTreeDataset
    validation: DecisionTreeDataset


@dataclass(frozen=True)
class DecisionTreeMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    log_loss: float
    confusion_matrix: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class DecisionTreeArtifact:
    model_kind: str
    model_version: str
    feature_version: str
    dataset_identity: str
    target_name: str
    configuration: tuple[tuple[str, str], ...]
    classes: tuple[int, ...]
    artifact_identity: str


@dataclass(frozen=True)
class DecisionTreeValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


@dataclass(frozen=True)
class DecisionTreeBaselineComparison:
    decision_tree_log_loss: float
    baseline_log_loss: float
    difference: float


@dataclass(frozen=True)
class DecisionTreeReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str


@dataclass(frozen=True)
class PositionDecisionTreeModels:
    models: tuple[tuple[str, DecisionTreeClassifier], ...]


def validate_decision_tree_config(config: DecisionTreeConfig) -> None:
    if not isinstance(config, DecisionTreeConfig):
        raise TypeError("config must be a DecisionTreeConfig.")
    if config.criterion not in {"gini", "entropy", "log_loss"}:
        raise ValueError("Unsupported decision-tree criterion.")
    if config.splitter not in {"best", "random"}:
        raise ValueError("Unsupported decision-tree splitter.")
    if config.max_depth is not None and (
        not isinstance(config.max_depth, int) or config.max_depth <= 0
    ):
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


def validate_decision_tree_dataset(dataset: DecisionTreeDataset) -> None:
    if not isinstance(dataset, DecisionTreeDataset):
        raise TypeError("dataset must be a DecisionTreeDataset.")
    if not dataset.feature_version.strip():
        raise ValueError("feature_version must be non-empty.")
    if not dataset.dataset_identity.strip():
        raise ValueError("dataset_identity must be non-empty.")
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


def build_decision_tree_dataset(
    feature_names: tuple[str, ...],
    feature_version: str,
    dataset_identity: str,
    target_name: str,
    dates: tuple[date, ...],
    X: tuple[tuple[float, ...], ...],
    y: tuple[int, ...],
) -> DecisionTreeDataset:
    dataset = DecisionTreeDataset(
        tuple(feature_names), feature_version, dataset_identity, target_name,
        tuple(dates), tuple(tuple(float(v) for v in row) for row in X), tuple(y),
    )
    validate_decision_tree_dataset(dataset)
    return dataset


def build_decision_tree_dataset_from_sequence_dataset(
    dataset: SequenceDataset,
    dataset_identity: str,
    target_index: int = 0,
) -> DecisionTreeDataset:
    validate_sequence_dataset(dataset)
    if not dataset.samples:
        raise ValueError("Sequence dataset cannot be empty.")
    if not isinstance(target_index, int) or target_index < 0:
        raise ValueError("target_index must be a non-negative integer.")
    base_names = dataset.feature_names
    width = len(dataset.samples[0].features[0])
    if base_names:
        names = tuple(
            f"t{t}_{name}"
            for t in range(dataset.sequence_length)
            for name in base_names
        )
    else:
        names = tuple(
            f"t{t}_feature_{i}"
            for t in range(dataset.sequence_length)
            for i in range(width)
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
    return build_decision_tree_dataset(
        names,
        "sequence-" + "-".join(dataset.feature_names) if dataset.feature_names else "sequence",
        dataset_identity,
        dataset.target_positions[target_index],
        tuple(dates), tuple(rows), tuple(targets),
    )


def split_decision_tree_dataset_temporally(
    dataset: DecisionTreeDataset, split_date: date
) -> DecisionTreeSplit:
    validate_decision_tree_dataset(dataset)
    if not isinstance(split_date, date):
        raise TypeError("split_date must be a date.")
    train_i = [i for i, d in enumerate(dataset.dates) if d <= split_date]
    val_i = [i for i, d in enumerate(dataset.dates) if d > split_date]

    def subset(indices: list[int]) -> DecisionTreeDataset:
        return DecisionTreeDataset(
            dataset.feature_names, dataset.feature_version, dataset.dataset_identity,
            dataset.target_name, tuple(dataset.dates[i] for i in indices),
            tuple(dataset.X[i] for i in indices), tuple(dataset.y[i] for i in indices),
        )

    train, validation = subset(train_i), subset(val_i)
    if len(set(train.y)) < 2:
        raise ValueError("Temporal training split must contain at least two classes.")
    return DecisionTreeSplit(split_date, train, validation)


def build_decision_tree(config: DecisionTreeConfig = DecisionTreeConfig()) -> DecisionTreeClassifier:
    validate_decision_tree_config(config)
    return DecisionTreeClassifier(
        criterion=config.criterion, splitter=config.splitter,
        max_depth=config.max_depth, min_samples_split=config.min_samples_split,
        min_samples_leaf=config.min_samples_leaf, max_features=config.max_features,
        class_weight=config.class_weight, random_state=config.random_state,
    )


def train_decision_tree(
    dataset: DecisionTreeDataset,
    config: DecisionTreeConfig = DecisionTreeConfig(),
) -> DecisionTreeClassifier:
    validate_decision_tree_dataset(dataset)
    model = build_decision_tree(config)
    model.fit(dataset.X, dataset.y)
    return model


def predict_classes(model: DecisionTreeClassifier, X: tuple[tuple[float, ...], ...]) -> tuple[int, ...]:
    _validate_matrix(X)
    return tuple(int(v) for v in model.predict(X))


def predict_probabilities(
    model: DecisionTreeClassifier, X: tuple[tuple[float, ...], ...]
) -> tuple[tuple[float, ...], ...]:
    _validate_matrix(X)
    return tuple(tuple(float(v) for v in row) for row in model.predict_proba(X))


def evaluate_decision_tree(
    model: DecisionTreeClassifier, dataset: DecisionTreeDataset
) -> DecisionTreeMetrics:
    validate_decision_tree_dataset(dataset)
    predictions = predict_classes(model, dataset.X)
    probabilities = predict_probabilities(model, dataset.X)
    return DecisionTreeMetrics(
        float(accuracy_score(dataset.y, predictions)),
        float(precision_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(recall_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(f1_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(log_loss(dataset.y, probabilities, labels=model.classes_)),
        tuple(tuple(int(v) for v in row) for row in confusion_matrix(
            dataset.y, predictions, labels=model.classes_
        )),
    )


def build_position_models(
    datasets: Mapping[str, DecisionTreeDataset],
    config: DecisionTreeConfig = DecisionTreeConfig(),
) -> PositionDecisionTreeModels:
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    return PositionDecisionTreeModels(tuple(
        (position, train_decision_tree(datasets[position], config))
        for position in sorted(datasets)
    ))


def get_position_model(models: PositionDecisionTreeModels, position: str) -> DecisionTreeClassifier:
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")


def compare_with_baseline(
    metrics: DecisionTreeMetrics, baseline_log_loss: float
) -> DecisionTreeBaselineComparison:
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return DecisionTreeBaselineComparison(
        metrics.log_loss, float(baseline_log_loss),
        float(metrics.log_loss - baseline_log_loss),
    )


def _configuration_items(config: DecisionTreeConfig) -> tuple[tuple[str, str], ...]:
    values = {
        "criterion": config.criterion, "splitter": config.splitter,
        "max_depth": config.max_depth, "min_samples_split": config.min_samples_split,
        "min_samples_leaf": config.min_samples_leaf, "max_features": config.max_features,
        "class_weight": config.class_weight, "random_state": config.random_state,
    }
    return tuple((key, json.dumps(values[key], sort_keys=True)) for key in sorted(values))


def build_decision_tree_artifact(
    model: DecisionTreeClassifier,
    dataset: DecisionTreeDataset,
    config: DecisionTreeConfig,
) -> DecisionTreeArtifact:
    validate_decision_tree_dataset(dataset)
    validate_decision_tree_config(config)
    if not hasattr(model, "classes_"):
        raise ValueError("Model must be fitted before artifact creation.")
    payload = {
        "classes": [int(v) for v in model.classes_],
        "configuration": list(_configuration_items(config)),
        "dataset_identity": dataset.dataset_identity,
        "feature_version": dataset.feature_version,
        "model_kind": MODEL_KIND, "model_version": DECISION_TREE_VERSION,
        "target_name": dataset.target_name,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    identity = "decision-tree-" + hashlib.sha256(canonical.encode()).hexdigest()
    return DecisionTreeArtifact(
        MODEL_KIND, DECISION_TREE_VERSION, dataset.feature_version,
        dataset.dataset_identity, dataset.target_name, _configuration_items(config),
        tuple(int(v) for v in model.classes_), identity,
    )


def validate_decision_tree_model(
    model: DecisionTreeClassifier, dataset: DecisionTreeDataset
) -> DecisionTreeValidationResult:
    issues = []
    if not isinstance(model, DecisionTreeClassifier):
        return DecisionTreeValidationResult(INVALID, ("INVALID_MODEL_TYPE",))
    if not hasattr(model, "classes_"):
        issues.append("MODEL_NOT_FITTED")
    if hasattr(model, "classes_") and len(model.classes_) < 2:
        issues.append("INSUFFICIENT_MODEL_CLASSES")
    try:
        if model.n_features_in_ != len(dataset.feature_names):
            issues.append("FEATURE_WIDTH_MISMATCH")
    except AttributeError:
        issues.append("MISSING_FEATURE_WIDTH")
    return DecisionTreeValidationResult(VALID if not issues else INVALID, tuple(issues))


def validate_decision_tree_version_references(
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
    dataset: DecisionTreeDataset,
) -> None:
    validate_feature_version_reference(feature_reference)
    validate_dataset_version_reference(dataset_reference)
    validate_decision_tree_dataset(dataset)
    if feature_reference.feature_version != dataset.feature_version:
        raise ValueError("Feature version reference does not match model dataset.")
    if dataset_reference.identity != dataset.dataset_identity:
        raise ValueError("Dataset version reference does not match model dataset.")


def save_decision_tree_model(model: DecisionTreeClassifier, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_decision_tree_model(path: str | Path) -> DecisionTreeClassifier:
    model = joblib.load(Path(path))
    if not isinstance(model, DecisionTreeClassifier):
        raise TypeError("Persisted artifact is not a DecisionTreeClassifier model.")
    return model


def reproduce_decision_tree_artifact(
    first: DecisionTreeArtifact, second: DecisionTreeArtifact
) -> DecisionTreeReproducibilityResult:
    return DecisionTreeReproducibilityResult(
        first == second, first.artifact_identity, second.artifact_identity
    )


def validate_decision_tree_pipeline(
    dataset: DecisionTreeDataset,
    config: DecisionTreeConfig,
    model: DecisionTreeClassifier,
) -> DecisionTreeValidationResult:
    issues = []
    try:
        validate_decision_tree_dataset(dataset)
        validate_decision_tree_config(config)
    except (TypeError, ValueError) as exc:
        issues.append(str(exc))
    issues.extend(validate_decision_tree_model(model, dataset).issues)
    return DecisionTreeValidationResult(VALID if not issues else INVALID, tuple(issues))


def build_temporal_split_from_sequence_dataset(
    sequence_dataset: SequenceDataset,
    dataset_identity: str,
    split_date: date,
    target_index: int = 0,
) -> DecisionTreeSplit:
    dataset = build_decision_tree_dataset_from_sequence_dataset(
        sequence_dataset, dataset_identity, target_index
    )
    return split_decision_tree_dataset_temporally(dataset, split_date)


def get_model_classes(model: DecisionTreeClassifier) -> tuple[int, ...]:
    if not hasattr(model, "classes_"):
        raise ValueError("Model has not been fitted.")
    return tuple(int(v) for v in model.classes_)


__all__ = [
    "DECISION_TREE_VERSION", "MODEL_KIND", "VALID", "INVALID",
    "DecisionTreeConfig", "DecisionTreeDataset", "DecisionTreeSplit",
    "DecisionTreeMetrics", "DecisionTreeArtifact", "DecisionTreeValidationResult",
    "DecisionTreeBaselineComparison", "DecisionTreeReproducibilityResult",
    "PositionDecisionTreeModels", "validate_decision_tree_config",
    "validate_decision_tree_dataset", "build_decision_tree_dataset",
    "build_decision_tree_dataset_from_sequence_dataset",
    "split_decision_tree_dataset_temporally", "build_decision_tree",
    "train_decision_tree", "predict_classes", "predict_probabilities",
    "evaluate_decision_tree", "build_position_models", "get_position_model",
    "compare_with_baseline", "build_decision_tree_artifact",
    "validate_decision_tree_model", "validate_decision_tree_version_references",
    "save_decision_tree_model", "load_decision_tree_model",
    "reproduce_decision_tree_artifact", "validate_decision_tree_pipeline",
    "build_temporal_split_from_sequence_dataset", "get_model_classes",
]
