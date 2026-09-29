from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import warnings
from lightgbm import LGBMClassifier, early_stopping
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss, precision_score, recall_score

from features.sequence_dataset import SequenceDataset, validate_sequence_dataset
from features.versioning_contract import DatasetVersionReference, FeatureVersionReference, validate_dataset_version_reference, validate_feature_version_reference

LIGHTGBM_VERSION = "26.0.0"
MODEL_KIND = "lightgbm"
VALID = "VALID"
INVALID = "INVALID"

@dataclass(frozen=True)
class LightGBMConfig:
    n_estimators: int = 100
    num_leaves: int = 31
    max_depth: int = -1
    learning_rate: float = 0.1
    min_child_samples: int = 20
    subsample: float = 1.0
    colsample_bytree: float = 1.0
    reg_alpha: float = 0.0
    reg_lambda: float = 0.0
    objective: str = "auto"
    eval_metric: str = "logloss"
    early_stopping_rounds: int | None = None
    random_state: int | None = 0
    n_jobs: int = 1
    verbosity: int = -1

@dataclass(frozen=True)
class LightGBMDataset:
    feature_names: tuple[str, ...]
    feature_version: str
    dataset_identity: str
    target_name: str
    dates: tuple[date, ...]
    X: tuple[tuple[float, ...], ...]
    y: tuple[int, ...]

@dataclass(frozen=True)
class LightGBMSplit:
    split_date: date
    train: LightGBMDataset
    validation: LightGBMDataset

@dataclass(frozen=True)
class LightGBMMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    log_loss: float
    confusion_matrix: tuple[tuple[int, ...], ...]

@dataclass(frozen=True)
class LightGBMFeatureImportance:
    feature_names: tuple[str, ...]
    importances: tuple[float, ...]

@dataclass(frozen=True)
class LightGBMArtifact:
    model_kind: str
    model_version: str
    feature_version: str
    dataset_identity: str
    target_name: str
    configuration: tuple[tuple[str, str], ...]
    classes: tuple[int, ...]
    artifact_identity: str

@dataclass(frozen=True)
class LightGBMValidationResult:
    status: str
    issues: tuple[str, ...]
    @property
    def is_valid(self) -> bool:
        return self.status == VALID

@dataclass(frozen=True)
class LightGBMBaselineComparison:
    lightgbm_log_loss: float
    baseline_log_loss: float
    difference: float

@dataclass(frozen=True)
class LightGBMReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str

@dataclass(frozen=True)
class PositionLightGBMModels:
    models: tuple[tuple[str, LGBMClassifier], ...]
def validate_lightgbm_config(config: LightGBMConfig) -> None:
    if not isinstance(config, LightGBMConfig): raise TypeError("config must be a LightGBMConfig.")
    if not isinstance(config.n_estimators, int) or config.n_estimators <= 0: raise ValueError("n_estimators must be a positive integer.")
    if not isinstance(config.num_leaves, int) or config.num_leaves < 2: raise ValueError("num_leaves must be at least 2.")
    if not isinstance(config.max_depth, int) or config.max_depth == 0 or config.max_depth < -1: raise ValueError("max_depth must be -1 or a positive integer.")
    if config.learning_rate <= 0: raise ValueError("learning_rate must be positive.")
    if not isinstance(config.min_child_samples, int) or config.min_child_samples <= 0: raise ValueError("min_child_samples must be a positive integer.")
    for name, value in (("subsample", config.subsample), ("colsample_bytree", config.colsample_bytree)):
        if not 0 < value <= 1: raise ValueError(f"{name} must be in (0, 1].")
    for name, value in (("reg_alpha", config.reg_alpha), ("reg_lambda", config.reg_lambda)):
        if value < 0: raise ValueError(f"{name} cannot be negative.")
    if config.objective not in {"auto", "binary", "multiclass"}: raise ValueError("Unsupported LightGBM objective.")
    if not isinstance(config.eval_metric, str) or not config.eval_metric.strip(): raise ValueError("eval_metric must be a non-empty string.")
    if config.early_stopping_rounds is not None and (not isinstance(config.early_stopping_rounds, int) or config.early_stopping_rounds <= 0): raise ValueError("early_stopping_rounds must be None or a positive integer.")
    if not isinstance(config.n_jobs, int) or config.n_jobs == 0: raise ValueError("n_jobs must be a non-zero integer.")
    if not isinstance(config.verbosity, int): raise ValueError("verbosity must be an integer.")

def _validate_matrix(X: tuple[tuple[float, ...], ...]) -> int:
    if not isinstance(X, tuple): raise TypeError("X must be a tuple of rows.")
    width = None
    for row in X:
        if not isinstance(row, tuple) or not row: raise ValueError("Every feature row must be a non-empty tuple.")
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)): raise ValueError("Feature values must be numeric.")
        width = len(row) if width is None else width
        if len(row) != width: raise ValueError("Feature rows must have equal width.")
    return width or 0

def validate_lightgbm_dataset(dataset: LightGBMDataset) -> None:
    if not isinstance(dataset, LightGBMDataset): raise TypeError("dataset must be a LightGBMDataset.")
    if not dataset.feature_version.strip() or not dataset.dataset_identity.strip(): raise ValueError("feature_version and dataset_identity must be non-empty.")
    if len(dataset.X) != len(dataset.y) or len(dataset.X) != len(dataset.dates): raise ValueError("X, y and dates must have equal lengths.")
    if len(set(dataset.feature_names)) != len(dataset.feature_names): raise ValueError("feature_names must be unique.")
    if _validate_matrix(dataset.X) != len(dataset.feature_names): raise ValueError("Feature width must match feature_names.")
    if len(set(dataset.dates)) != len(dataset.dates): raise ValueError("Dataset dates must be unique.")
    if tuple(sorted(dataset.dates)) != dataset.dates: raise ValueError("Dataset dates must be chronological.")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in dataset.y): raise ValueError("Targets must be integer class labels.")
    if len(set(dataset.y)) < 2 and dataset.y: raise ValueError("Training data requires at least two classes.")

def build_lightgbm_dataset(feature_names, feature_version, dataset_identity, target_name, dates, X, y) -> LightGBMDataset:
    dataset = LightGBMDataset(tuple(feature_names), feature_version, dataset_identity, target_name, tuple(dates), tuple(tuple(float(v) for v in row) for row in X), tuple(y))
    validate_lightgbm_dataset(dataset)
    return dataset

def build_lightgbm_dataset_from_sequence_dataset(dataset: SequenceDataset, dataset_identity: str, target_index: int = 0) -> LightGBMDataset:
    validate_sequence_dataset(dataset)
    if not dataset.samples: raise ValueError("Sequence dataset cannot be empty.")
    if not isinstance(target_index, int) or target_index < 0: raise ValueError("target_index must be a non-negative integer.")
    names = tuple(f"t{t}_{name}" for t in range(dataset.sequence_length) for name in dataset.feature_names) if dataset.feature_names else tuple(f"t{t}_feature_{i}" for t in range(dataset.sequence_length) for i in range(len(dataset.samples[0].features[0])))
    rows, dates, targets = [], [], []
    for sample in dataset.samples:
        flat = tuple(float(v) for row in sample.features for v in row)
        if len(flat) != len(names): raise ValueError("Flattened feature width does not match feature_names.")
        if target_index >= len(sample.target): raise ValueError("target_index exceeds sample target width.")
        rows.append(flat); dates.append(sample.target_date); targets.append(int(sample.target[target_index]))
    return build_lightgbm_dataset(names, "sequence-" + "-".join(dataset.feature_names) if dataset.feature_names else "sequence", dataset_identity, dataset.target_positions[target_index], tuple(dates), tuple(rows), tuple(targets))

def split_lightgbm_dataset_temporally(dataset: LightGBMDataset, split_date: date) -> LightGBMSplit:
    validate_lightgbm_dataset(dataset)
    if not isinstance(split_date, date): raise TypeError("split_date must be a date.")
    train_i = [i for i,d in enumerate(dataset.dates) if d <= split_date]; val_i = [i for i,d in enumerate(dataset.dates) if d > split_date]
    def subset(indices): return LightGBMDataset(dataset.feature_names,dataset.feature_version,dataset.dataset_identity,dataset.target_name,tuple(dataset.dates[i] for i in indices),tuple(dataset.X[i] for i in indices),tuple(dataset.y[i] for i in indices))
    train, validation = subset(train_i), subset(val_i)
    if len(set(train.y)) < 2: raise ValueError("Temporal training split must contain at least two classes.")
    return LightGBMSplit(split_date, train, validation)

def _as_matrix(X):
    return np.asarray(X, dtype=float)

def _objective_for(dataset: LightGBMDataset, config: LightGBMConfig) -> str:
    if config.objective == "binary": return "binary"
    if config.objective == "multiclass": return "multiclass"
    return "binary" if len(set(dataset.y)) == 2 else "multiclass"

def build_lightgbm(config: LightGBMConfig = LightGBMConfig(), objective: str = "binary", num_classes: int = 2) -> LGBMClassifier:
    validate_lightgbm_config(config)
    if objective not in {"binary", "multiclass"}: raise ValueError("Unsupported LightGBM objective.")
    if objective == "multiclass" and num_classes < 3: raise ValueError("Multiclass LightGBM requires at least three classes.")
    metric = config.eval_metric
    if objective == "multiclass" and metric == "logloss": metric = "multi_logloss"
    return LGBMClassifier(objective=objective,n_estimators=config.n_estimators,num_leaves=config.num_leaves,max_depth=config.max_depth,learning_rate=config.learning_rate,min_child_samples=config.min_child_samples,subsample=config.subsample,colsample_bytree=config.colsample_bytree,reg_alpha=config.reg_alpha,reg_lambda=config.reg_lambda,random_state=config.random_state,n_jobs=config.n_jobs,verbosity=config.verbosity,metric=metric,num_class=num_classes if objective == "multiclass" else None)

def train_lightgbm(dataset: LightGBMDataset, config: LightGBMConfig = LightGBMConfig(), validation_dataset: LightGBMDataset | None = None) -> LGBMClassifier:
    validate_lightgbm_dataset(dataset); validate_lightgbm_config(config)
    objective = _objective_for(dataset, config); classes = len(set(dataset.y))
    model = build_lightgbm(config, objective, classes)
    fit_kwargs: dict[str, Any] = {}
    callbacks = []
    if validation_dataset is not None:
        validate_lightgbm_dataset(validation_dataset)
        if set(validation_dataset.y) != set(dataset.y): raise ValueError("Validation dataset must contain the same class labels as the training dataset.")
        fit_kwargs["eval_set"] = [(_as_matrix(validation_dataset.X), np.asarray(validation_dataset.y, dtype=int))]
        if config.early_stopping_rounds is not None: callbacks.append(early_stopping(config.early_stopping_rounds, verbose=False))
    elif config.early_stopping_rounds is not None:
        raise ValueError("early_stopping_rounds requires validation_dataset.")
    if callbacks: fit_kwargs["callbacks"] = callbacks
    model.fit(_as_matrix(dataset.X), np.asarray(dataset.y, dtype=int), **fit_kwargs)
    return model

def predict_classes(model: LGBMClassifier, X) -> tuple[int, ...]:
    _validate_matrix(X)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="X does not have valid feature names.*", category=UserWarning)
        return tuple(int(v) for v in model.predict(_as_matrix(X)))

def predict_probabilities(model: LGBMClassifier, X) -> tuple[tuple[float, ...], ...]:
    _validate_matrix(X); rows=[]
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="X does not have valid feature names.*", category=UserWarning)
        predicted = model.predict_proba(_as_matrix(X))
    for row in predicted:
        values=[max(0.0,float(v)) for v in row]; total=sum(values); rows.append(tuple(v/total for v in values) if total else tuple(values))
    return tuple(rows)

def evaluate_lightgbm(model: LGBMClassifier, dataset: LightGBMDataset) -> LightGBMMetrics:
    validate_lightgbm_dataset(dataset); predictions=predict_classes(model,dataset.X); probabilities=predict_probabilities(model,dataset.X)
    return LightGBMMetrics(float(accuracy_score(dataset.y,predictions)),float(precision_score(dataset.y,predictions,average="weighted",zero_division=0)),float(recall_score(dataset.y,predictions,average="weighted",zero_division=0)),float(f1_score(dataset.y,predictions,average="weighted",zero_division=0)),float(log_loss(dataset.y,probabilities,labels=model.classes_)),tuple(tuple(int(v) for v in row) for row in confusion_matrix(dataset.y,predictions,labels=model.classes_)))

def get_feature_importances(model: LGBMClassifier, feature_names: tuple[str,...]) -> LightGBMFeatureImportance:
    if not hasattr(model,"feature_importances_"): raise ValueError("Model has not been fitted.")
    if len(feature_names) != len(model.feature_importances_): raise ValueError("Feature-name width does not match model importances.")
    return LightGBMFeatureImportance(tuple(feature_names),tuple(float(v) for v in model.feature_importances_))

def build_position_models(datasets: Mapping[str,LightGBMDataset], config: LightGBMConfig = LightGBMConfig()) -> PositionLightGBMModels:
    if not isinstance(datasets,Mapping) or not datasets: raise ValueError("datasets must be a non-empty mapping.")
    return PositionLightGBMModels(tuple((position,train_lightgbm(datasets[position],config)) for position in sorted(datasets)))

def get_position_model(models: PositionLightGBMModels, position: str) -> LGBMClassifier:
    for name,model in models.models:
        if name == position: return model
    raise ValueError(f"Position model not found: {position}")

def get_model_classes(model: LGBMClassifier) -> tuple[int,...]:
    if not hasattr(model,"classes_"): raise ValueError("Model must be fitted.")
    return tuple(int(v) for v in model.classes_)

def compare_with_baseline(metrics: LightGBMMetrics, baseline_log_loss: float) -> LightGBMBaselineComparison:
    if baseline_log_loss < 0: raise ValueError("baseline_log_loss cannot be negative.")
    return LightGBMBaselineComparison(metrics.log_loss,float(baseline_log_loss),float(metrics.log_loss-baseline_log_loss))

def _configuration_items(config: LightGBMConfig) -> tuple[tuple[str,str],...]:
    keys=("n_estimators","num_leaves","max_depth","learning_rate","min_child_samples","subsample","colsample_bytree","reg_alpha","reg_lambda","objective","eval_metric","early_stopping_rounds","random_state","n_jobs","verbosity")
    return tuple((k,json.dumps(getattr(config,k),sort_keys=True)) for k in sorted(keys))

def build_lightgbm_artifact(model: LGBMClassifier, dataset: LightGBMDataset, config: LightGBMConfig) -> LightGBMArtifact:
    validate_lightgbm_dataset(dataset); validate_lightgbm_config(config)
    if not hasattr(model,"classes_"): raise ValueError("Model must be fitted before artifact creation.")
    payload={"classes":[int(v) for v in model.classes_],"configuration":list(_configuration_items(config)),"dataset_identity":dataset.dataset_identity,"feature_version":dataset.feature_version,"model_kind":MODEL_KIND,"model_version":LIGHTGBM_VERSION,"target_name":dataset.target_name}
    identity="lightgbm-"+hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return LightGBMArtifact(MODEL_KIND,LIGHTGBM_VERSION,dataset.feature_version,dataset.dataset_identity,dataset.target_name,_configuration_items(config),tuple(int(v) for v in model.classes_),identity)

def validate_lightgbm_model(model: LGBMClassifier, dataset: LightGBMDataset) -> LightGBMValidationResult:
    if not isinstance(model,LGBMClassifier): return LightGBMValidationResult(INVALID,("INVALID_MODEL_TYPE",))
    issues=[]
    if not hasattr(model,"classes_"): issues.append("MODEL_NOT_FITTED")
    if hasattr(model,"classes_") and len(model.classes_)<2: issues.append("INSUFFICIENT_MODEL_CLASSES")
    try:
        if model.n_features_in_ != len(dataset.feature_names): issues.append("FEATURE_WIDTH_MISMATCH")
    except AttributeError: issues.append("MISSING_FEATURE_WIDTH")
    return LightGBMValidationResult(VALID if not issues else INVALID,tuple(issues))

def validate_lightgbm_version_references(feature_reference: FeatureVersionReference,dataset_reference: DatasetVersionReference,dataset: LightGBMDataset) -> None:
    validate_feature_version_reference(feature_reference); validate_dataset_version_reference(dataset_reference); validate_lightgbm_dataset(dataset)
    if feature_reference.feature_version != dataset.feature_version: raise ValueError("Feature version reference does not match model dataset.")
    if dataset_reference.identity != dataset.dataset_identity: raise ValueError("Dataset version reference does not match model dataset.")

def save_lightgbm_model(model: LGBMClassifier,path: str|Path)->Path:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); joblib.dump(model,target); return target

def load_lightgbm_model(path: str|Path)->LGBMClassifier:
    model=joblib.load(Path(path))
    if not isinstance(model,LGBMClassifier): raise TypeError("Persisted artifact is not an LGBMClassifier model.")
    return model

def reproduce_lightgbm_artifact(first:LightGBMArtifact,second:LightGBMArtifact)->LightGBMReproducibilityResult:
    return LightGBMReproducibilityResult(first==second,first.artifact_identity,second.artifact_identity)

def validate_lightgbm_pipeline(dataset:LightGBMDataset,config:LightGBMConfig,model:LGBMClassifier)->LightGBMValidationResult:
    issues=[]
    try: validate_lightgbm_dataset(dataset); validate_lightgbm_config(config)
    except (TypeError,ValueError) as exc: issues.append(str(exc))
    issues.extend(validate_lightgbm_model(model,dataset).issues)
    return LightGBMValidationResult(VALID if not issues else INVALID,tuple(issues))

def build_temporal_split_from_sequence_dataset(sequence_dataset:SequenceDataset,dataset_identity:str,split_date:date,target_index:int=0)->LightGBMSplit:
    return split_lightgbm_dataset_temporally(build_lightgbm_dataset_from_sequence_dataset(sequence_dataset,dataset_identity,target_index),split_date)
