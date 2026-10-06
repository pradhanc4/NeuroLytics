from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, log_loss

from analytics.retraining_dataset import (
    TEST, TRAIN, VALIDATION, RetrainingDatasetReport,
    validate_retraining_dataset_report,
)

AUTOMATED_RETRAINING_VERSION = "64.0.0"
VALID = "VALID"
INVALID = "INVALID"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
MODEL_KIND = "random_forest"

@dataclass(frozen=True)
class AutomatedRetrainingConfig:
    n_estimators: int = 100
    max_depth: int | None = None
    min_samples_split: int = 2
    min_samples_leaf: int = 1
    random_state: int = 0
    n_jobs: int = 1
    minimum_train_rows: int = 3
    require_validation: bool = True
    require_test: bool = True

@dataclass(frozen=True)
class RetrainingSplitMetrics:
    split: str
    row_count: int
    accuracy: float
    f1: float
    log_loss: float

@dataclass(frozen=True)
class RetrainedModelArtifact:
    model_kind: str
    model_version: str
    model_identity: str
    dataset_identity: str
    decision_identity: str
    data_identity: str
    feature_version: str
    feature_names: tuple[str, ...]
    target_classes: tuple[int, ...]
    configuration: tuple[tuple[str, str], ...]
    artifact_identity: str
    persistence_path: str

@dataclass(frozen=True)
class AutomatedRetrainingReport:
    version: str
    run_id: str
    status: str
    dataset_identity: str
    decision_identity: str
    model_identity: str
    model_version: str
    artifact: RetrainedModelArtifact
    train_metrics: RetrainingSplitMetrics
    validation_metrics: RetrainingSplitMetrics | None
    test_metrics: RetrainingSplitMetrics | None
    report_identity: str

@dataclass(frozen=True)
class AutomatedRetrainingValidationResult:
    status: str
    issues: tuple[str, ...]
    @property
    def is_valid(self) -> bool:
        return self.status == VALID

def _finite(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric")

def _hash(payload: object, prefix: str) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(raw).hexdigest()

def validate_automated_retraining_config(config: AutomatedRetrainingConfig) -> None:
    if not isinstance(config, AutomatedRetrainingConfig): raise TypeError("config must be AutomatedRetrainingConfig")
    for value, name in ((config.n_estimators,"n_estimators"),(config.min_samples_split,"min_samples_split"),(config.min_samples_leaf,"min_samples_leaf"),(config.minimum_train_rows,"minimum_train_rows"),(config.n_jobs,"n_jobs")):
        if not isinstance(value,int) or isinstance(value,bool) or value <= 0: raise ValueError(f"{name} must be a positive integer")
    if config.max_depth is not None and (not isinstance(config.max_depth,int) or isinstance(config.max_depth,bool) or config.max_depth <= 0): raise ValueError("max_depth must be None or positive integer")
    if not isinstance(config.random_state,int) or isinstance(config.random_state,bool): raise ValueError("random_state must be integer")
    if not isinstance(config.require_validation,bool) or not isinstance(config.require_test,bool): raise ValueError("split requirements must be boolean")

def _numeric_matrix(report: RetrainingDatasetReport, split: str):
    rows = tuple(row for row in report.rows if row.split == split)
    X=[]; y=[]
    for row in rows:
        values=[]
        for name,value in row.feature_values:
            if value is None or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(float(value)):
                raise ValueError(f"feature {name} contains non-numeric or non-finite value")
            values.append(float(value))
        if not isinstance(row.target,int) or isinstance(row.target,bool):
            raise ValueError("automated retraining currently requires integer class targets")
        X.append(tuple(values)); y.append(int(row.target))
    return rows, tuple(X), tuple(y)

def _metrics(model, split: str, X, y) -> RetrainingSplitMetrics:
    if not X: raise ValueError(f"{split} split cannot be empty")
    pred=tuple(int(v) for v in model.predict(X)); proba=model.predict_proba(X)
    return RetrainingSplitMetrics(split,len(y),float(accuracy_score(y,pred)),float(f1_score(y,pred,average="weighted",zero_division=0)),float(log_loss(y,proba,labels=model.classes_)))

def build_automated_retraining_report(
    run_id: str,
    dataset_report: RetrainingDatasetReport,
    *,
    config: AutomatedRetrainingConfig = AutomatedRetrainingConfig(),
    persistence_path: str | Path | None = None,
) -> AutomatedRetrainingReport:
    if not isinstance(run_id,str) or not run_id.strip(): raise ValueError("run_id must not be empty")
    validation=validate_retraining_dataset_report(dataset_report)
    if not validation.is_valid: raise ValueError("retraining dataset report is invalid")
    validate_automated_retraining_config(config)
    train_rows,X_train,y_train=_numeric_matrix(dataset_report,TRAIN)
    if len(train_rows)<config.minimum_train_rows: raise ValueError("training rows are below minimum_train_rows")
    if len(set(y_train))<2: raise ValueError("training data requires at least two target classes")
    val_rows,X_val,y_val=_numeric_matrix(dataset_report,VALIDATION)
    test_rows,X_test,y_test=_numeric_matrix(dataset_report,TEST)
    if config.require_validation and not val_rows: raise ValueError("validation split is required")
    if config.require_test and not test_rows: raise ValueError("test split is required")
    model=RandomForestClassifier(n_estimators=config.n_estimators,max_depth=config.max_depth,min_samples_split=config.min_samples_split,min_samples_leaf=config.min_samples_leaf,random_state=config.random_state,n_jobs=config.n_jobs)
    model.fit(X_train,y_train)
    train_metrics=_metrics(model,TRAIN,X_train,y_train)
    validation_metrics=_metrics(model,VALIDATION,X_val,y_val) if val_rows else None
    test_metrics=_metrics(model,TEST,X_test,y_test) if test_rows else None
    configuration=tuple((k,json.dumps(v,sort_keys=True)) for k,v in sorted({"n_estimators":config.n_estimators,"max_depth":config.max_depth,"min_samples_split":config.min_samples_split,"min_samples_leaf":config.min_samples_leaf,"random_state":config.random_state,"n_jobs":config.n_jobs}.items()))
    model_identity=_hash((MODEL_KIND,automated_retraining_version(),dataset_report.dataset_id,dataset_report.feature_version,configuration,tuple(int(v) for v in model.classes_)),"model-version-")
    artifact_identity=_hash((model_identity,dataset_report.report_identity,dataset_report.data_identity),"retrained-artifact-")
    saved_path=""
    if persistence_path is not None:
        target=Path(persistence_path); target.parent.mkdir(parents=True,exist_ok=True); joblib.dump(model,target); saved_path=str(target)
    artifact=RetrainedModelArtifact(MODEL_KIND,automated_retraining_version(),model_identity,dataset_report.report_identity,dataset_report.decision_identity,dataset_report.data_identity,dataset_report.feature_version,dataset_report.feature_names,tuple(int(v) for v in model.classes_),configuration,artifact_identity,saved_path)
    report_identity=_hash((AUTOMATED_RETRAINING_VERSION,run_id,COMPLETED,dataset_report.report_identity,artifact,train_metrics,validation_metrics,test_metrics),"automated-retraining-report-")
    return AutomatedRetrainingReport(AUTOMATED_RETRAINING_VERSION,run_id,COMPLETED,dataset_report.report_identity,dataset_report.decision_identity,model_identity,automated_retraining_version(),artifact,train_metrics,validation_metrics,test_metrics,report_identity)

def automated_retraining_version(): return AUTOMATED_RETRAINING_VERSION

def automated_retraining_summary(report: AutomatedRetrainingReport):
    validation=validate_automated_retraining_report(report)
    return {"status":validation.status,"version":report.version,"run_id":report.run_id,"dataset_identity":report.dataset_identity,"decision_identity":report.decision_identity,"model_identity":report.model_identity,"model_version":report.model_version,"artifact_identity":report.artifact.artifact_identity,"train_rows":report.train_metrics.row_count,"validation_rows":report.validation_metrics.row_count if report.validation_metrics else 0,"test_rows":report.test_metrics.row_count if report.test_metrics else 0,"report_identity":report.report_identity}

def automated_retraining_artifact(report): return report.artifact

def automated_retraining_metrics(report): return tuple(x for x in (report.train_metrics,report.validation_metrics,report.test_metrics) if x is not None)

def validate_automated_retraining_report(report: AutomatedRetrainingReport) -> AutomatedRetrainingValidationResult:
    if not isinstance(report,AutomatedRetrainingReport): return AutomatedRetrainingValidationResult(INVALID,("INVALID_REPORT_TYPE",))
    issues=[]
    if report.version!=AUTOMATED_RETRAINING_VERSION: issues.append("INVALID_VERSION")
    for value,name in ((report.run_id,"RUN_ID"),(report.dataset_identity,"DATASET_IDENTITY"),(report.decision_identity,"DECISION_IDENTITY"),(report.model_identity,"MODEL_IDENTITY"),(report.model_version,"MODEL_VERSION"),(report.report_identity,"REPORT_IDENTITY")):
        if not isinstance(value,str) or not value.strip(): issues.append("MISSING_"+name)
    if report.status!=COMPLETED: issues.append("INVALID_STATUS")
    if report.artifact.model_identity!=report.model_identity: issues.append("MODEL_IDENTITY_MISMATCH")
    if report.artifact.dataset_identity!=report.dataset_identity: issues.append("DATASET_IDENTITY_MISMATCH")
    if report.artifact.decision_identity!=report.decision_identity: issues.append("DECISION_IDENTITY_MISMATCH")
    if report.artifact.model_version!=report.model_version: issues.append("MODEL_VERSION_MISMATCH")
    if len(report.artifact.feature_names)!=len(set(report.artifact.feature_names)): issues.append("DUPLICATE_FEATURE_NAMES")
    for metric in (report.train_metrics,report.validation_metrics,report.test_metrics):
        if metric is None: continue
        if metric.split not in (TRAIN,VALIDATION,TEST): issues.append("INVALID_METRIC_SPLIT")
        if metric.row_count<1: issues.append("INVALID_METRIC_ROW_COUNT")
        for value,name in ((metric.accuracy,"accuracy"),(metric.f1,"f1"),(metric.log_loss,"log_loss")):
            try: _finite(value,name)
            except ValueError: issues.append("NONFINITE_METRIC")
        if not 0<=metric.accuracy<=1 or not 0<=metric.f1<=1 or metric.log_loss<0: issues.append("METRIC_BOUNDS")
    if not report.report_identity.startswith("automated-retraining-report-"): issues.append("INVALID_REPORT_IDENTITY")
    return AutomatedRetrainingValidationResult(VALID if not issues else INVALID,tuple(sorted(set(issues))))

def save_retrained_model(model: RandomForestClassifier, path: str | Path) -> Path:
    if not isinstance(model,RandomForestClassifier) or not hasattr(model,"classes_"): raise ValueError("model must be a fitted RandomForestClassifier")
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); joblib.dump(model,target); return target

def load_retrained_model(path: str | Path) -> RandomForestClassifier:
    model=joblib.load(Path(path))
    if not isinstance(model,RandomForestClassifier): raise TypeError("persisted artifact is not a RandomForestClassifier")
    return model

__all__=["AUTOMATED_RETRAINING_VERSION","VALID","INVALID","COMPLETED","FAILED","MODEL_KIND","AutomatedRetrainingConfig","RetrainingSplitMetrics","RetrainedModelArtifact","AutomatedRetrainingReport","AutomatedRetrainingValidationResult","validate_automated_retraining_config","build_automated_retraining_report","automated_retraining_version","automated_retraining_summary","automated_retraining_artifact","automated_retraining_metrics","validate_automated_retraining_report","save_retrained_model","load_retrained_model"]
