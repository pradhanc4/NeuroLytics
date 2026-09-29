from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import joblib
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, log_loss, precision_score, recall_score
from xgboost import XGBClassifier

from features.sequence_dataset import SequenceDataset, validate_sequence_dataset
from features.versioning_contract import DatasetVersionReference, FeatureVersionReference, validate_dataset_version_reference, validate_feature_version_reference

XGBOOST_VERSION = "25.0.0"
MODEL_KIND = "xgboost"
VALID = "VALID"
INVALID = "INVALID"

@dataclass(frozen=True)
class XGBoostConfig:
    n_estimators: int = 100
    max_depth: int = 6
    learning_rate: float = 0.1
    min_child_weight: float = 1.0
    subsample: float = 1.0
    colsample_bytree: float = 1.0
    gamma: float = 0.0
    reg_alpha: float = 0.0
    reg_lambda: float = 1.0
    objective: str = "auto"
    eval_metric: str = "logloss"
    early_stopping_rounds: int | None = None
    random_state: int | None = 0
    n_jobs: int = 1
    tree_method: str = "hist"

@dataclass(frozen=True)
class XGBoostDataset:
    feature_names: tuple[str, ...]
    feature_version: str
    dataset_identity: str
    target_name: str
    dates: tuple[date, ...]
    X: tuple[tuple[float, ...], ...]
    y: tuple[int, ...]

@dataclass(frozen=True)
class XGBoostSplit:
    split_date: date
    train: XGBoostDataset
    validation: XGBoostDataset

@dataclass(frozen=True)
class XGBoostMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float
    log_loss: float
    confusion_matrix: tuple[tuple[int, ...], ...]

@dataclass(frozen=True)
class XGBoostFeatureImportance:
    feature_names: tuple[str, ...]
    importances: tuple[float, ...]

@dataclass(frozen=True)
class XGBoostArtifact:
    model_kind: str
    model_version: str
    feature_version: str
    dataset_identity: str
    target_name: str
    configuration: tuple[tuple[str, str], ...]
    classes: tuple[int, ...]
    artifact_identity: str

@dataclass(frozen=True)
class XGBoostValidationResult:
    status: str
    issues: tuple[str, ...]
    @property
    def is_valid(self) -> bool:
        return self.status == VALID

@dataclass(frozen=True)
class XGBoostBaselineComparison:
    xgboost_log_loss: float
    baseline_log_loss: float
    difference: float

@dataclass(frozen=True)
class XGBoostReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str

@dataclass(frozen=True)
class PositionXGBoostModels:
    models: tuple[tuple[str, XGBClassifier], ...]

def validate_xgboost_config(config: XGBoostConfig) -> None:
    if not isinstance(config, XGBoostConfig): raise TypeError("config must be an XGBoostConfig.")
    if not isinstance(config.n_estimators, int) or config.n_estimators <= 0: raise ValueError("n_estimators must be a positive integer.")
    if not isinstance(config.max_depth, int) or config.max_depth < 0: raise ValueError("max_depth must be a non-negative integer.")
    if config.learning_rate <= 0: raise ValueError("learning_rate must be positive.")
    if config.min_child_weight < 0: raise ValueError("min_child_weight cannot be negative.")
    for name, value in (("subsample", config.subsample), ("colsample_bytree", config.colsample_bytree)):
        if not 0 < value <= 1: raise ValueError(f"{name} must be in (0, 1].")
    for name, value in (("gamma", config.gamma), ("reg_alpha", config.reg_alpha), ("reg_lambda", config.reg_lambda)):
        if value < 0: raise ValueError(f"{name} cannot be negative.")
    if config.objective not in {"auto", "binary:logistic", "multi:softprob", "multi:softmax"}: raise ValueError("Unsupported XGBoost objective.")
    if not isinstance(config.eval_metric, str) or not config.eval_metric.strip(): raise ValueError("eval_metric must be a non-empty string.")
    if config.early_stopping_rounds is not None and (not isinstance(config.early_stopping_rounds, int) or config.early_stopping_rounds <= 0): raise ValueError("early_stopping_rounds must be None or a positive integer.")
    if not isinstance(config.n_jobs, int) or config.n_jobs == 0: raise ValueError("n_jobs must be a non-zero integer.")
    if config.tree_method not in {"hist", "approx", "exact", "auto"}: raise ValueError("Unsupported tree_method.")

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

def validate_xgboost_dataset(dataset: XGBoostDataset) -> None:
    if not isinstance(dataset, XGBoostDataset): raise TypeError("dataset must be an XGBoostDataset.")
    if not dataset.feature_version.strip() or not dataset.dataset_identity.strip(): raise ValueError("feature_version and dataset_identity must be non-empty.")
    if len(dataset.X) != len(dataset.y) or len(dataset.X) != len(dataset.dates): raise ValueError("X, y and dates must have equal lengths.")
    if len(set(dataset.feature_names)) != len(dataset.feature_names): raise ValueError("feature_names must be unique.")
    if _validate_matrix(dataset.X) != len(dataset.feature_names): raise ValueError("Feature width must match feature_names.")
    if len(set(dataset.dates)) != len(dataset.dates): raise ValueError("Dataset dates must be unique.")
    if tuple(sorted(dataset.dates)) != dataset.dates: raise ValueError("Dataset dates must be chronological.")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in dataset.y): raise ValueError("Targets must be integer class labels.")
    if len(set(dataset.y)) < 2 and dataset.y: raise ValueError("Training data requires at least two classes.")

def build_xgboost_dataset(feature_names, feature_version, dataset_identity, target_name, dates, X, y) -> XGBoostDataset:
    dataset = XGBoostDataset(tuple(feature_names), feature_version, dataset_identity, target_name, tuple(dates), tuple(tuple(float(v) for v in row) for row in X), tuple(y))
    validate_xgboost_dataset(dataset)
    return dataset

def build_xgboost_dataset_from_sequence_dataset(dataset: SequenceDataset, dataset_identity: str, target_index: int = 0) -> XGBoostDataset:
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
    return build_xgboost_dataset(names, "sequence-" + "-".join(dataset.feature_names) if dataset.feature_names else "sequence", dataset_identity, dataset.target_positions[target_index], tuple(dates), tuple(rows), tuple(targets))

def split_xgboost_dataset_temporally(dataset: XGBoostDataset, split_date: date) -> XGBoostSplit:
    validate_xgboost_dataset(dataset)
    if not isinstance(split_date, date): raise TypeError("split_date must be a date.")
    train_i = [i for i,d in enumerate(dataset.dates) if d <= split_date]; val_i = [i for i,d in enumerate(dataset.dates) if d > split_date]
    def subset(indices):
        return XGBoostDataset(dataset.feature_names,dataset.feature_version,dataset.dataset_identity,dataset.target_name,tuple(dataset.dates[i] for i in indices),tuple(dataset.X[i] for i in indices),tuple(dataset.y[i] for i in indices))
    train, validation = subset(train_i), subset(val_i)
    if len(set(train.y)) < 2: raise ValueError("Temporal training split must contain at least two classes.")
    return XGBoostSplit(split_date, train, validation)

def _objective_for(dataset: XGBoostDataset, config: XGBoostConfig) -> str:
    if config.objective != "auto": return config.objective
    return "binary:logistic" if len(set(dataset.y)) == 2 else "multi:softprob"

def build_xgboost(config: XGBoostConfig = XGBoostConfig(), objective: str | None = None) -> XGBClassifier:
    validate_xgboost_config(config)
    selected = objective or ("binary:logistic" if config.objective == "auto" else config.objective)
    metric = config.eval_metric
    if selected in {"multi:softprob", "multi:softmax"} and metric == "logloss":
        metric = "mlogloss"
    return XGBClassifier(n_estimators=config.n_estimators,max_depth=config.max_depth,learning_rate=config.learning_rate,min_child_weight=config.min_child_weight,subsample=config.subsample,colsample_bytree=config.colsample_bytree,gamma=config.gamma,reg_alpha=config.reg_alpha,reg_lambda=config.reg_lambda,objective=selected,eval_metric=metric,early_stopping_rounds=config.early_stopping_rounds,random_state=config.random_state,n_jobs=config.n_jobs,tree_method=config.tree_method,verbosity=0)

def train_xgboost(dataset: XGBoostDataset, config: XGBoostConfig = XGBoostConfig(), validation_dataset: XGBoostDataset | None = None) -> XGBClassifier:
    validate_xgboost_dataset(dataset); validate_xgboost_config(config)
    model = build_xgboost(config, _objective_for(dataset, config))
    fit_kwargs = {}
    if validation_dataset is not None:
        validate_xgboost_dataset(validation_dataset)
        if set(validation_dataset.y) != set(dataset.y):
            raise ValueError("Validation dataset must contain the same class labels as the training dataset.")
        fit_kwargs["eval_set"] = [(validation_dataset.X, validation_dataset.y)]
    model.fit(dataset.X, dataset.y, **fit_kwargs)
    return model

def predict_classes(model: XGBClassifier, X) -> tuple[int, ...]:
    _validate_matrix(X); return tuple(int(v) for v in model.predict(X))

def predict_probabilities(model: XGBClassifier, X) -> tuple[tuple[float, ...], ...]:
    _validate_matrix(X)
    rows = []
    for row in model.predict_proba(X):
        values = [max(0.0, float(v)) for v in row]
        total = sum(values)
        rows.append(tuple(v / total for v in values) if total else tuple(values))
    return tuple(rows)

def evaluate_xgboost(model: XGBClassifier, dataset: XGBoostDataset) -> XGBoostMetrics:
    validate_xgboost_dataset(dataset); predictions = predict_classes(model,dataset.X); probabilities = predict_probabilities(model,dataset.X)
    return XGBoostMetrics(float(accuracy_score(dataset.y,predictions)),float(precision_score(dataset.y,predictions,average="weighted",zero_division=0)),float(recall_score(dataset.y,predictions,average="weighted",zero_division=0)),float(f1_score(dataset.y,predictions,average="weighted",zero_division=0)),float(log_loss(dataset.y,probabilities,labels=model.classes_)),tuple(tuple(int(v) for v in row) for row in confusion_matrix(dataset.y,predictions,labels=model.classes_)))

def get_feature_importances(model: XGBClassifier, feature_names: tuple[str,...]) -> XGBoostFeatureImportance:
    if not hasattr(model,"feature_importances_"): raise ValueError("Model has not been fitted.")
    if len(feature_names) != len(model.feature_importances_): raise ValueError("Feature-name width does not match model importances.")
    return XGBoostFeatureImportance(tuple(feature_names),tuple(float(v) for v in model.feature_importances_))

def build_position_models(datasets: Mapping[str,XGBoostDataset], config: XGBoostConfig = XGBoostConfig()) -> PositionXGBoostModels:
    if not isinstance(datasets,Mapping) or not datasets: raise ValueError("datasets must be a non-empty mapping.")
    return PositionXGBoostModels(tuple((position,train_xgboost(datasets[position],config)) for position in sorted(datasets)))

def get_position_model(models: PositionXGBoostModels, position: str) -> XGBClassifier:
    for name,model in models.models:
        if name == position: return model
    raise ValueError(f"Position model not found: {position}")

def get_model_classes(model: XGBClassifier) -> tuple[int,...]:
    if not hasattr(model,"classes_"): raise ValueError("Model must be fitted.")
    return tuple(int(v) for v in model.classes_)

def compare_with_baseline(metrics: XGBoostMetrics, baseline_log_loss: float) -> XGBoostBaselineComparison:
    if baseline_log_loss < 0: raise ValueError("baseline_log_loss cannot be negative.")
    return XGBoostBaselineComparison(metrics.log_loss,float(baseline_log_loss),float(metrics.log_loss-baseline_log_loss))

def _configuration_items(config: XGBoostConfig) -> tuple[tuple[str,str],...]:
    values={k:getattr(config,k) for k in ("n_estimators","max_depth","learning_rate","min_child_weight","subsample","colsample_bytree","gamma","reg_alpha","reg_lambda","objective","eval_metric","early_stopping_rounds","random_state","n_jobs","tree_method")}
    return tuple((k,json.dumps(values[k],sort_keys=True)) for k in sorted(values))

def build_xgboost_artifact(model: XGBClassifier, dataset: XGBoostDataset, config: XGBoostConfig) -> XGBoostArtifact:
    validate_xgboost_dataset(dataset); validate_xgboost_config(config)
    if not hasattr(model,"classes_"): raise ValueError("Model must be fitted before artifact creation.")
    payload={"classes":[int(v) for v in model.classes_],"configuration":list(_configuration_items(config)),"dataset_identity":dataset.dataset_identity,"feature_version":dataset.feature_version,"model_kind":MODEL_KIND,"model_version":XGBOOST_VERSION,"target_name":dataset.target_name}
    identity="xgboost-"+hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return XGBoostArtifact(MODEL_KIND,XGBOOST_VERSION,dataset.feature_version,dataset.dataset_identity,dataset.target_name,_configuration_items(config),tuple(int(v) for v in model.classes_),identity)

def validate_xgboost_model(model: XGBClassifier, dataset: XGBoostDataset) -> XGBoostValidationResult:
    if not isinstance(model,XGBClassifier): return XGBoostValidationResult(INVALID,("INVALID_MODEL_TYPE",))
    issues=[]
    if not hasattr(model,"classes_"): issues.append("MODEL_NOT_FITTED")
    if hasattr(model,"classes_") and len(model.classes_)<2: issues.append("INSUFFICIENT_MODEL_CLASSES")
    try:
        if model.n_features_in_ != len(dataset.feature_names): issues.append("FEATURE_WIDTH_MISMATCH")
    except AttributeError: issues.append("MISSING_FEATURE_WIDTH")
    return XGBoostValidationResult(VALID if not issues else INVALID,tuple(issues))

def validate_xgboost_version_references(feature_reference: FeatureVersionReference,dataset_reference: DatasetVersionReference,dataset: XGBoostDataset) -> None:
    validate_feature_version_reference(feature_reference); validate_dataset_version_reference(dataset_reference); validate_xgboost_dataset(dataset)
    if feature_reference.feature_version != dataset.feature_version: raise ValueError("Feature version reference does not match model dataset.")
    if dataset_reference.identity != dataset.dataset_identity: raise ValueError("Dataset version reference does not match model dataset.")

def save_xgboost_model(model: XGBClassifier,path: str|Path)->Path:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); joblib.dump(model,target); return target

def load_xgboost_model(path: str|Path)->XGBClassifier:
    model=joblib.load(Path(path))
    if not isinstance(model,XGBClassifier): raise TypeError("Persisted artifact is not an XGBClassifier model.")
    return model

def reproduce_xgboost_artifact(first:XGBoostArtifact,second:XGBoostArtifact)->XGBoostReproducibilityResult:
    return XGBoostReproducibilityResult(first==second,first.artifact_identity,second.artifact_identity)

def validate_xgboost_pipeline(dataset:XGBoostDataset,config:XGBoostConfig,model:XGBClassifier)->XGBoostValidationResult:
    issues=[]
    try: validate_xgboost_dataset(dataset); validate_xgboost_config(config)
    except (TypeError,ValueError) as exc: issues.append(str(exc))
    issues.extend(validate_xgboost_model(model,dataset).issues)
    return XGBoostValidationResult(VALID if not issues else INVALID,tuple(issues))

def build_temporal_split_from_sequence_dataset(sequence_dataset:SequenceDataset,dataset_identity:str,split_date:date,target_index:int=0)->XGBoostSplit:
    return split_xgboost_dataset_temporally(build_xgboost_dataset_from_sequence_dataset(sequence_dataset,dataset_identity,target_index),split_date)
