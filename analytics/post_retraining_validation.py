from __future__ import annotations

import hashlib, json, math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from analytics.automated_retraining import (
    AutomatedRetrainingReport, RetrainedModelArtifact, validate_automated_retraining_report,
    load_retrained_model, automated_retraining_metrics,
)
from analytics.retraining_dataset import RetrainingDatasetReport, TRAIN, VALIDATION, TEST, validate_retraining_dataset_report

POST_RETRAINING_VALIDATION_VERSION = "65.0.0"
VALID, INVALID = "VALID", "INVALID"
PASS, FAIL = "PASS", "FAIL"

@dataclass(frozen=True)
class PostRetrainingValidationConfig:
    require_persistence: bool = False
    require_validation: bool = True
    require_test: bool = True
    minimum_accuracy: float = 0.0
    minimum_f1: float = 0.0
    maximum_log_loss: float | None = None
    require_reproducible_identity: bool = True

@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    status: str
    detail: str

@dataclass(frozen=True)
class PostRetrainingValidationReport:
    version: str
    validation_id: str
    status: str
    dataset_identity: str
    retraining_report_identity: str
    model_identity: str
    artifact_identity: str
    checks: tuple[ValidationCheck, ...]
    passed_checks: tuple[str, ...]
    failed_checks: tuple[str, ...]
    train_accuracy: float
    validation_accuracy: float | None
    test_accuracy: float | None
    train_f1: float
    validation_f1: float | None
    test_f1: float | None
    train_log_loss: float
    validation_log_loss: float | None
    test_log_loss: float | None
    report_identity: str

@dataclass(frozen=True)
class PostRetrainingValidationResult:
    status: str
    issues: tuple[str, ...]
    @property
    def is_valid(self) -> bool: return self.status == VALID

def _hash(payload: object) -> str:
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()
    return "post-retraining-validation-report-"+hashlib.sha256(raw).hexdigest()

def _finite(v,name):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)): raise ValueError(f"{name} must be finite numeric")

def validate_post_retraining_validation_config(config: PostRetrainingValidationConfig):
    if not isinstance(config,PostRetrainingValidationConfig): raise TypeError("config must be PostRetrainingValidationConfig")
    if not isinstance(config.require_persistence,bool) or not isinstance(config.require_validation,bool) or not isinstance(config.require_test,bool) or not isinstance(config.require_reproducible_identity,bool): raise ValueError("boolean configuration fields must be boolean")
    for v,n in ((config.minimum_accuracy,"minimum_accuracy"),(config.minimum_f1,"minimum_f1")):
        _finite(v,n)
        if not 0<=v<=1: raise ValueError(f"{n} must be between 0 and 1")
    if config.maximum_log_loss is not None:
        _finite(config.maximum_log_loss,"maximum_log_loss")
        if config.maximum_log_loss<0: raise ValueError("maximum_log_loss must be non-negative")

def _check(cid,ok,detail): return ValidationCheck(cid,PASS if ok else FAIL,detail)

def build_post_retraining_validation_report(
    validation_id: str,
    retraining_report: AutomatedRetrainingReport,
    dataset_report: RetrainingDatasetReport,
    *,
    model=None,
    persistence_path: str | Path | None = None,
    config: PostRetrainingValidationConfig = PostRetrainingValidationConfig(),
) -> PostRetrainingValidationReport:
    if not isinstance(validation_id,str) or not validation_id.strip(): raise ValueError("validation_id must not be empty")
    validate_post_retraining_validation_config(config)
    rv=validate_automated_retraining_report(retraining_report)
    dv=validate_retraining_dataset_report(dataset_report)
    if not rv.is_valid: raise ValueError("retraining report is invalid")
    if not dv.is_valid: raise ValueError("dataset report is invalid")
    if retraining_report.dataset_identity!=dataset_report.report_identity: raise ValueError("retraining/dataset identity mismatch")
    if persistence_path is None and retraining_report.artifact.persistence_path:
        persistence_path=retraining_report.artifact.persistence_path
    checks=[]
    checks.append(_check("DATASET_LINEAGE",retraining_report.dataset_identity==dataset_report.report_identity,"dataset identity matches"))
    checks.append(_check("DECISION_LINEAGE",bool(retraining_report.decision_identity==dataset_report.decision_identity),"decision identity matches"))
    checks.append(_check("FEATURE_VERSION_LINEAGE",retraining_report.artifact.feature_version==dataset_report.feature_version,"feature version matches"))
    checks.append(_check("FEATURE_NAME_LINEAGE",retraining_report.artifact.feature_names==dataset_report.feature_names,"feature names/order match"))
    checks.append(_check("MODEL_ARTIFACT_LINEAGE",retraining_report.artifact.model_identity==retraining_report.model_identity,"model identity matches artifact"))
    checks.append(_check("ARTIFACT_IDENTITY",retraining_report.artifact.artifact_identity.startswith("retrained-artifact-"),"artifact identity format is valid"))
    checks.append(_check("MODEL_VERSION",retraining_report.model_version==retraining_report.artifact.model_version,"model version matches artifact"))
    checks.append(_check("TRAIN_ROWS",retraining_report.train_metrics.row_count==len(dataset_report.train_dates),"TRAIN row count matches dataset"))
    checks.append(_check("VALIDATION_ROWS",(retraining_report.validation_metrics is None)==(len(dataset_report.validation_dates)==0),"VALIDATION presence matches dataset"))
    checks.append(_check("TEST_ROWS",(retraining_report.test_metrics is None)==(len(dataset_report.test_dates)==0),"TEST presence matches dataset"))
    checks.append(_check("MODEL_CLASSES",len(retraining_report.artifact.target_classes)>=2,"artifact contains at least two classes"))
    for metric in automated_retraining_metrics(retraining_report):
        checks.append(_check(f"{metric.split}_METRIC_BOUNDS",0<=metric.accuracy<=1 and 0<=metric.f1<=1 and metric.log_loss>=0,"metrics are finite and bounded"))
    if config.require_validation: checks.append(_check("VALIDATION_REQUIRED",retraining_report.validation_metrics is not None,"validation metrics are present"))
    if config.require_test: checks.append(_check("TEST_REQUIRED",retraining_report.test_metrics is not None,"test metrics are present"))
    if config.minimum_accuracy>0:
        checks.extend(_check(f"{m.split}_MIN_ACCURACY",m.accuracy>=config.minimum_accuracy,f"accuracy={m.accuracy} threshold={config.minimum_accuracy}") for m in automated_retraining_metrics(retraining_report))
    if config.minimum_f1>0:
        checks.extend(_check(f"{m.split}_MIN_F1",m.f1>=config.minimum_f1,f"f1={m.f1} threshold={config.minimum_f1}") for m in automated_retraining_metrics(retraining_report))
    if config.maximum_log_loss is not None:
        checks.extend(_check(f"{m.split}_MAX_LOG_LOSS",m.log_loss<=config.maximum_log_loss,f"log_loss={m.log_loss} threshold={config.maximum_log_loss}") for m in automated_retraining_metrics(retraining_report))
    path=Path(persistence_path) if persistence_path else None
    if config.require_persistence or path is not None:
        checks.append(_check("PERSISTENCE_PATH",path is not None and path.exists(),"persisted artifact path exists"))
    if path is not None and path.exists():
        loaded=load_retrained_model(path)
        checks.append(_check("PERSISTED_MODEL_KIND",type(loaded).__name__=="RandomForestClassifier","persisted artifact is RandomForestClassifier"))
        checks.append(_check("PERSISTED_MODEL_CLASSES",tuple(int(x) for x in loaded.classes_)==retraining_report.artifact.target_classes,"persisted classes match lineage"))
    if model is not None:
        checks.append(_check("MODEL_SUPPLIED",hasattr(model,"predict") and hasattr(model,"predict_proba"),"supplied model exposes prediction API"))
        if hasattr(model,"classes_"): checks.append(_check("MODEL_CLASSES_MATCH",tuple(int(x) for x in model.classes_)==retraining_report.artifact.target_classes,"supplied model classes match lineage"))
    passed=tuple(c.check_id for c in checks if c.status==PASS); failed=tuple(c.check_id for c in checks if c.status==FAIL)
    status=VALID if not failed else INVALID
    report_identity=_hash((POST_RETRAINING_VALIDATION_VERSION,validation_id,status,dataset_report.report_identity,retraining_report.report_identity,retraining_report.model_identity,retraining_report.artifact.artifact_identity,checks,config))
    vm=retraining_report.validation_metrics; tm=retraining_report.test_metrics
    return PostRetrainingValidationReport(POST_RETRAINING_VALIDATION_VERSION,validation_id,status,dataset_report.report_identity,retraining_report.report_identity,retraining_report.model_identity,retraining_report.artifact.artifact_identity,tuple(checks),passed,failed,retraining_report.train_metrics.accuracy,vm.accuracy if vm else None,tm.accuracy if tm else None,retraining_report.train_metrics.f1,vm.f1 if vm else None,tm.f1 if tm else None,retraining_report.train_metrics.log_loss,vm.log_loss if vm else None,tm.log_loss if tm else None,report_identity)

def validate_post_retraining_validation_report(report: PostRetrainingValidationReport)->PostRetrainingValidationResult:
    if not isinstance(report,PostRetrainingValidationReport): return PostRetrainingValidationResult(INVALID,("INVALID_REPORT_TYPE",))
    issues=[]
    if report.version!=POST_RETRAINING_VALIDATION_VERSION: issues.append("INVALID_VERSION")
    if not report.validation_id.strip(): issues.append("MISSING_VALIDATION_ID")
    if report.status not in (VALID,INVALID): issues.append("INVALID_STATUS")
    if len(report.checks)!=len(report.passed_checks)+len(report.failed_checks): issues.append("CHECK_COUNT_MISMATCH")
    ids=tuple(c.check_id for c in report.checks)
    if len(ids)!=len(set(ids)): issues.append("DUPLICATE_CHECK_IDS")
    if set(report.passed_checks)&set(report.failed_checks): issues.append("CHECK_OVERLAP")
    if set(ids)!=set(report.passed_checks)|set(report.failed_checks): issues.append("CHECK_RECONCILIATION")
    if (report.status==VALID)!=(len(report.failed_checks)==0): issues.append("STATUS_CONSISTENCY")
    for c in report.checks:
        if c.status not in (PASS,FAIL): issues.append("INVALID_CHECK_STATUS")
        if not c.check_id.strip(): issues.append("MISSING_CHECK_ID")
    for v,n in ((report.train_accuracy,"train_accuracy"),(report.train_f1,"train_f1"),(report.train_log_loss,"train_log_loss")):
        try: _finite(v,n)
        except ValueError: issues.append("NONFINITE_METRIC")
    if not 0<=report.train_accuracy<=1 or not 0<=report.train_f1<=1 or report.train_log_loss<0: issues.append("METRIC_BOUNDS")
    for v in (report.validation_accuracy,report.validation_f1,report.validation_log_loss,report.test_accuracy,report.test_f1,report.test_log_loss):
        if v is not None:
            try: _finite(v,"optional_metric")
            except ValueError: issues.append("NONFINITE_OPTIONAL_METRIC")
    for v in (report.validation_accuracy,report.test_accuracy,report.validation_f1,report.test_f1):
        if v is not None and not 0<=v<=1: issues.append("OPTIONAL_METRIC_BOUNDS")
    for v in (report.validation_log_loss,report.test_log_loss):
        if v is not None and v<0: issues.append("OPTIONAL_LOG_LOSS_BOUNDS")
    if not report.report_identity.startswith("post-retraining-validation-report-"): issues.append("INVALID_REPORT_IDENTITY")
    return PostRetrainingValidationResult(VALID if not issues else INVALID,tuple(sorted(set(issues))))

def post_retraining_validation_summary(report):
    v=validate_post_retraining_validation_report(report)
    return {"status":v.status,"version":report.version,"validation_id":report.validation_id,"dataset_identity":report.dataset_identity,"retraining_report_identity":report.retraining_report_identity,"model_identity":report.model_identity,"artifact_identity":report.artifact_identity,"passed_checks":len(report.passed_checks),"failed_checks":len(report.failed_checks),"report_identity":report.report_identity}

def post_retraining_validation_checks(report): return report.checks

def post_retraining_validation_failures(report): return report.failed_checks

__all__=["POST_RETRAINING_VALIDATION_VERSION","VALID","INVALID","PASS","FAIL","PostRetrainingValidationConfig","ValidationCheck","PostRetrainingValidationReport","PostRetrainingValidationResult","validate_post_retraining_validation_config","build_post_retraining_validation_report","validate_post_retraining_validation_report","post_retraining_validation_summary","post_retraining_validation_checks","post_retraining_validation_failures"]
