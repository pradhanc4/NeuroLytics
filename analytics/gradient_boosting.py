from sklearn.ensemble import GradientBoostingClassifier

GRADIENT_BOOSTING_VERSION = "24.0.0"
MODEL_KIND = "gradient_boosting"


def build_gradient_boosting(config=None, **kwargs):
    if config is not None:
        if kwargs:
            raise ValueError("Pass either config or keyword parameters, not both.")
        if not isinstance(config, GradientBoostingConfig):
            raise TypeError("config must be a GradientBoostingConfig.")
        return build_gradient_boosting_from_config(config)
    """Create a validated GradientBoostingClassifier for NeuroLytics."""
    allowed = {
        "n_estimators", "learning_rate", "max_depth", "min_samples_split",
        "min_samples_leaf", "subsample", "max_features", "criterion",
        "random_state", "n_iter_no_change", "validation_fraction", "tol",
    }
    unknown = set(kwargs) - allowed
    if unknown:
        raise ValueError(f"Unsupported Gradient Boosting configuration: {sorted(unknown)}")
    # sklearn deprecated criterion for GradientBoostingClassifier; it has no effect.
    # Keep accepting it for backward-compatible NeuroLytics configuration/artifacts,
    # but do not pass it to sklearn so current versions remain warning-free.
    estimator_kwargs = dict(kwargs)
    estimator_kwargs.pop("criterion", None)
    return GradientBoostingClassifier(**estimator_kwargs)


def train_gradient_boosting(X, y, **kwargs):
    """Fit and return a GradientBoostingClassifier."""
    model = build_gradient_boosting(**kwargs)
    model.fit(X, y)
    return model


def predict_classes(model, X):
    return tuple(int(value) for value in model.predict(X))


def predict_probabilities(model, X):
    return tuple(tuple(float(v) for v in row) for row in model.predict_proba(X))


def get_feature_importances(model):
    return tuple(float(v) for v in model.feature_importances_)


def get_model_classes(model):
    if not hasattr(model, "classes_"):
        raise ValueError("Model has not been fitted.")
    return tuple(int(v) for v in model.classes_)


__all__ = [
    "GRADIENT_BOOSTING_VERSION", "MODEL_KIND", "GradientBoostingClassifier",
    "build_gradient_boosting", "train_gradient_boosting", "predict_classes",
    "predict_probabilities", "get_feature_importances", "get_model_classes",
]
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json
import joblib
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, log_loss, confusion_matrix
from features.sequence_dataset import SequenceDataset, validate_sequence_dataset
from features.versioning_contract import DatasetVersionReference, FeatureVersionReference, validate_dataset_version_reference, validate_feature_version_reference


@dataclass(frozen=True)
class GradientBoostingConfig:
    n_estimators: int = 100
    learning_rate: float = 0.1
    max_depth: int = 3
    min_samples_split: int = 2
    min_samples_leaf: int = 1
    subsample: float = 1.0
    max_features: int | float | str | None = None
    criterion: str = "friedman_mse"
    random_state: int | None = 0
    n_iter_no_change: int | None = None
    validation_fraction: float = 0.1
    tol: float = 1e-4


@dataclass(frozen=True)
class GradientBoostingDataset:
    feature_names: tuple[str, ...]
    feature_version: str
    dataset_identity: str
    target_name: str
    dates: tuple[date, ...]
    X: tuple[tuple[float, ...], ...]
    y: tuple[int, ...]


@dataclass(frozen=True)
class GradientBoostingMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    log_loss: float
    confusion_matrix: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class GradientBoostingArtifact:
    model_kind: str
    model_version: str
    feature_version: str
    dataset_identity: str
    target_name: str
    configuration: tuple[tuple[str, str], ...]
    classes: tuple[int, ...]
    artifact_identity: str


@dataclass(frozen=True)
class GradientBoostingValidationResult:
    status: str
    issues: tuple[str, ...]
    @property
    def is_valid(self):
        return self.status == VALID


@dataclass(frozen=True)
class GradientBoostingBaselineComparison:
    gradient_boosting_log_loss: float
    baseline_log_loss: float
    difference: float


@dataclass(frozen=True)
class GradientBoostingReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str


@dataclass(frozen=True)
class PositionGradientBoostingModels:
    models: tuple[tuple[str, GradientBoostingClassifier], ...]
VALID = "VALID"
INVALID = "INVALID"


def validate_gradient_boosting_config(config):
    if not isinstance(config, GradientBoostingConfig):
        raise TypeError("config must be a GradientBoostingConfig.")
    if config.n_estimators <= 0 or config.learning_rate <= 0 or config.max_depth <= 0:
        raise ValueError("n_estimators, learning_rate and max_depth must be positive.")
    if config.min_samples_split < 2 or config.min_samples_leaf < 1:
        raise ValueError("Invalid sample-size configuration.")
    if not 0 < config.subsample <= 1:
        raise ValueError("subsample must be in (0, 1].")
    if isinstance(config.max_features, int) and config.max_features < 1:
        raise ValueError("max_features integer must be positive.")
    if isinstance(config.max_features, float) and not 0 < config.max_features <= 1:
        raise ValueError("max_features float must be in (0, 1].")
    if isinstance(config.max_features, str) and config.max_features not in {"sqrt", "log2"}:
        raise ValueError("Unsupported max_features string.")
    if config.criterion not in {"friedman_mse", "squared_error", "absolute_error", "huber"}:
        raise ValueError("Unsupported Gradient Boosting criterion.")
    if config.n_iter_no_change is not None and config.n_iter_no_change <= 0:
        raise ValueError("n_iter_no_change must be positive or None.")
    if not 0 < config.validation_fraction < 1 or config.tol < 0:
        raise ValueError("Invalid validation_fraction or tol.")


def _validate_matrix(X):
    if not isinstance(X, tuple):
        raise TypeError("X must be a tuple of rows.")
    width = None
    for row in X:
        if not isinstance(row, tuple) or not row:
            raise ValueError("Every feature row must be a non-empty tuple.")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in row):
            raise ValueError("Feature values must be numeric.")
        width = len(row) if width is None else width
        if len(row) != width:
            raise ValueError("Feature rows must have equal width.")
    return width or 0


def validate_gradient_boosting_dataset(dataset):
    if not isinstance(dataset, GradientBoostingDataset):
        raise TypeError("dataset must be a GradientBoostingDataset.")
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


def build_gradient_boosting_dataset(feature_names, feature_version, dataset_identity,
                                    target_name, dates, X, y):
    dataset = GradientBoostingDataset(
        tuple(feature_names), feature_version, dataset_identity, target_name,
        tuple(dates), tuple(tuple(float(v) for v in row) for row in X), tuple(y)
    )
    validate_gradient_boosting_dataset(dataset)
    return dataset


def split_gradient_boosting_dataset_temporally(dataset, split_date):
    validate_gradient_boosting_dataset(dataset)
    if not isinstance(split_date, date):
        raise TypeError("split_date must be a date.")
    train_i = [i for i, d in enumerate(dataset.dates) if d <= split_date]
    val_i = [i for i, d in enumerate(dataset.dates) if d > split_date]
    def subset(indices):
        return GradientBoostingDataset(
            dataset.feature_names, dataset.feature_version, dataset.dataset_identity,
            dataset.target_name, tuple(dataset.dates[i] for i in indices),
            tuple(dataset.X[i] for i in indices), tuple(dataset.y[i] for i in indices)
        )
    train, validation = subset(train_i), subset(val_i)
    if len(set(train.y)) < 2:
        raise ValueError("Temporal training split must contain at least two classes.")
    return split_date, train, validation
def build_gradient_boosting_from_config(config=GradientBoostingConfig()):
    validate_gradient_boosting_config(config)
    return GradientBoostingClassifier(
        n_estimators=config.n_estimators, learning_rate=config.learning_rate,
        max_depth=config.max_depth, min_samples_split=config.min_samples_split,
        min_samples_leaf=config.min_samples_leaf, subsample=config.subsample,
        max_features=config.max_features,
        random_state=config.random_state, n_iter_no_change=config.n_iter_no_change,
        validation_fraction=config.validation_fraction, tol=config.tol,
    )


def train_gradient_boosting_dataset(dataset, config=GradientBoostingConfig()):
    validate_gradient_boosting_dataset(dataset)
    model = build_gradient_boosting_from_config(config)
    model.fit(dataset.X, dataset.y)
    return model


def evaluate_gradient_boosting_dataset(model, dataset):
    validate_gradient_boosting_dataset(dataset)
    predictions = predict_classes(model, dataset.X)
    probabilities = predict_probabilities(model, dataset.X)
    return GradientBoostingMetrics(
        float(accuracy_score(dataset.y, predictions)),
        float(precision_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(recall_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(f1_score(dataset.y, predictions, average="weighted", zero_division=0)),
        float(log_loss(dataset.y, probabilities, labels=model.classes_)),
        tuple(tuple(int(v) for v in row)
              for row in confusion_matrix(dataset.y, predictions, labels=model.classes_)),
    )


def build_position_models_from_datasets(datasets: Mapping[str, GradientBoostingDataset],
                                        config=GradientBoostingConfig()):
    if not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    return PositionGradientBoostingModels(tuple(
        (name, train_gradient_boosting_dataset(datasets[name], config))
        for name in sorted(datasets)
    ))


def get_position_model(models, position):
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")


def compare_gradient_boosting_with_baseline(metrics, baseline_log_loss):
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return GradientBoostingBaselineComparison(
        metrics.log_loss, float(baseline_log_loss),
        float(metrics.log_loss - baseline_log_loss)
    )
def build_gradient_boosting_artifact(model, dataset, config):
    validate_gradient_boosting_dataset(dataset)
    validate_gradient_boosting_config(config)
    if not hasattr(model, "classes_"):
        raise ValueError("Model must be fitted before artifact creation.")
    values = {
        "n_estimators": config.n_estimators, "learning_rate": config.learning_rate,
        "max_depth": config.max_depth, "min_samples_split": config.min_samples_split,
        "min_samples_leaf": config.min_samples_leaf, "subsample": config.subsample,
        "max_features": config.max_features, "criterion": config.criterion,
        "random_state": config.random_state, "n_iter_no_change": config.n_iter_no_change,
        "validation_fraction": config.validation_fraction, "tol": config.tol,
    }
    configuration = tuple((k, json.dumps(values[k], sort_keys=True)) for k in sorted(values))
    payload = {
        "classes": [int(v) for v in model.classes_],
        "configuration": list(configuration),
        "dataset_identity": dataset.dataset_identity,
        "feature_version": dataset.feature_version,
        "model_kind": MODEL_KIND,
        "model_version": GRADIENT_BOOSTING_VERSION,
        "target_name": dataset.target_name,
    }
    identity = "gradient-boosting-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return GradientBoostingArtifact(
        MODEL_KIND, GRADIENT_BOOSTING_VERSION, dataset.feature_version,
        dataset.dataset_identity, dataset.target_name, configuration,
        tuple(int(v) for v in model.classes_), identity
    )


def validate_gradient_boosting_model(model, dataset):
    issues = []
    if not isinstance(model, GradientBoostingClassifier):
        return GradientBoostingValidationResult(INVALID, ("INVALID_MODEL_TYPE",))
    if not hasattr(model, "classes_"):
        issues.append("MODEL_NOT_FITTED")
    if hasattr(model, "classes_") and len(model.classes_) < 2:
        issues.append("INSUFFICIENT_MODEL_CLASSES")
    if hasattr(model, "n_features_in_") and model.n_features_in_ != len(dataset.feature_names):
        issues.append("FEATURE_WIDTH_MISMATCH")
    return GradientBoostingValidationResult(VALID if not issues else INVALID, tuple(issues))


def validate_gradient_boosting_pipeline(dataset, config, model):
    issues = []
    try:
        validate_gradient_boosting_dataset(dataset)
        validate_gradient_boosting_config(config)
    except (TypeError, ValueError) as exc:
        issues.append(str(exc))
    issues.extend(validate_gradient_boosting_model(model, dataset).issues)
    return GradientBoostingValidationResult(VALID if not issues else INVALID, tuple(issues))


def save_gradient_boosting_model(model, path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_gradient_boosting_model(path):
    model = joblib.load(Path(path))
    if not isinstance(model, GradientBoostingClassifier):
        raise TypeError("Persisted artifact is not a GradientBoostingClassifier model.")
    return model


def reproduce_gradient_boosting_artifact(first, second):
    return GradientBoostingReproducibilityResult(
        first == second, first.artifact_identity, second.artifact_identity
    )


def get_model_classes(model):
    if not hasattr(model, "classes_"):
        raise ValueError("Model has not been fitted.")
    return tuple(int(v) for v in model.classes_)


def get_gradient_boosting_feature_importances(model, feature_names):
    if len(feature_names) != len(model.feature_importances_):
        raise ValueError("Feature-name width does not match model importances.")
    return tuple(zip(tuple(feature_names), tuple(float(v) for v in model.feature_importances_)))


# Dataset-oriented aliases keep the public API explicit while preserving
# the simple classifier helpers defined at module level.
train_dataset = train_gradient_boosting_dataset
evaluate_dataset = evaluate_gradient_boosting_dataset
build_position_models = build_position_models_from_datasets
compare_with_baseline = compare_gradient_boosting_with_baseline
get_feature_importances = get_gradient_boosting_feature_importances
def train_gradient_boosting(dataset, config=GradientBoostingConfig()):
    return train_gradient_boosting_dataset(dataset, config)


def evaluate_gradient_boosting(model, dataset):
    return evaluate_gradient_boosting_dataset(model, dataset)


def build_position_models(datasets, config=GradientBoostingConfig()):
    return build_position_models_from_datasets(datasets, config)


def compare_with_baseline(metrics, baseline_log_loss):
    return compare_gradient_boosting_with_baseline(metrics, baseline_log_loss)


@dataclass(frozen=True)
class GradientBoostingFeatureImportance:
    feature_names: tuple[str, ...]
    importances: tuple[float, ...]


def get_feature_importances(model, feature_names):
    if not hasattr(model, "feature_importances_"):
        raise ValueError("Model has not been fitted.")
    if len(feature_names) != len(model.feature_importances_):
        raise ValueError("Feature-name width does not match model importances.")
    return GradientBoostingFeatureImportance(
        tuple(feature_names), tuple(float(v) for v in model.feature_importances_)
    )


__all__ = [
    "GRADIENT_BOOSTING_VERSION", "MODEL_KIND", "VALID", "INVALID",
    "GradientBoostingConfig", "GradientBoostingDataset", "GradientBoostingMetrics",
    "GradientBoostingArtifact", "GradientBoostingValidationResult",
    "GradientBoostingBaselineComparison", "GradientBoostingReproducibilityResult",
    "GradientBoostingFeatureImportance", "PositionGradientBoostingModels",
    "validate_gradient_boosting_config", "validate_gradient_boosting_dataset",
    "build_gradient_boosting", "build_gradient_boosting_from_config",
    "build_gradient_boosting_dataset", "build_gradient_boosting_dataset_from_sequence_dataset",
    "split_gradient_boosting_dataset_temporally",
    "train_gradient_boosting", "predict_classes", "predict_probabilities",
    "evaluate_gradient_boosting", "get_feature_importances", "build_position_models",
    "get_position_model", "compare_with_baseline", "build_gradient_boosting_artifact",
    "validate_gradient_boosting_model", "validate_gradient_boosting_pipeline",
    "save_gradient_boosting_model", "load_gradient_boosting_model",
    "reproduce_gradient_boosting_artifact", "get_model_classes",
]


def build_gradient_boosting_dataset_from_sequence_dataset(dataset: SequenceDataset, dataset_identity: str, target_index: int = 0):
    validate_sequence_dataset(dataset)
    if not dataset.samples:
        raise ValueError("Sequence dataset cannot be empty.")
    if target_index < 0 or target_index >= len(dataset.target_positions):
        raise ValueError("target_index is outside the target width.")
    names = tuple(
        f"t{t}_{name}" for t in range(dataset.sequence_length)
        for name in dataset.feature_names
    )
    rows, dates, targets = [], [], []
    for sample in dataset.samples:
        flat = tuple(float(v) for row in sample.features for v in row)
        if len(flat) != len(names):
            raise ValueError("Flattened feature width does not match feature_names.")
        rows.append(flat)
        dates.append(sample.target_date)
        targets.append(int(sample.target[target_index]))
    return build_gradient_boosting_dataset(
        names,
        "sequence-" + "-".join(dataset.feature_names),
        dataset_identity,
        dataset.target_positions[target_index],
        tuple(dates), tuple(rows), tuple(targets),
    )


def validate_gradient_boosting_version_references(feature_reference: FeatureVersionReference,
                                                   dataset_reference: DatasetVersionReference,
                                                   dataset: GradientBoostingDataset):
    validate_feature_version_reference(feature_reference)
    validate_dataset_version_reference(dataset_reference)
    validate_gradient_boosting_dataset(dataset)
    if feature_reference.feature_version != dataset.feature_version:
        raise ValueError("Feature version reference does not match model dataset.")
    if dataset_reference.identity != dataset.dataset_identity:
        raise ValueError("Dataset version reference does not match model dataset.")
