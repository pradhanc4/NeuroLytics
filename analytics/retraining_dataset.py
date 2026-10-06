from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

from analytics.retraining_decision import RETRAIN, RetrainingDecisionReport, validate_retraining_decision_report
from features.feature_artifact import FeatureArtifact, is_feature_artifact_valid, serialize_feature_artifact

RETRAINING_DATASET_VERSION = "63.0.0"
VALID = "VALID"
INVALID = "INVALID"
TRAIN = "TRAIN"
VALIDATION = "VALIDATION"
TEST = "TEST"
SPLIT_NAMES = (TRAIN, VALIDATION, TEST)

@dataclass(frozen=True)
class RetrainingDatasetConfig:
    train_ratio: float = 0.70
    validation_ratio: float = 0.15
    test_ratio: float = 0.15
    minimum_rows: int = 3
    require_targets: bool = True

@dataclass(frozen=True)
class RetrainingDatasetRow:
    target_date: date
    feature_values: tuple[tuple[str, int | float | str | bool | None], ...]
    target: int | float | str
    split: str
    feature_artifact_identity: str

@dataclass(frozen=True)
class RetrainingDatasetReport:
    version: str
    dataset_id: str
    model_identity: str
    decision_identity: str
    data_identity: str
    feature_version: str
    feature_names: tuple[str, ...]
    rows: tuple[RetrainingDatasetRow, ...]
    train_dates: tuple[date, ...]
    validation_dates: tuple[date, ...]
    test_dates: tuple[date, ...]
    excluded_dates: tuple[date, ...]
    config: RetrainingDatasetConfig
    report_identity: str

@dataclass(frozen=True)
class RetrainingDatasetValidationResult:
    status: str
    issues: tuple[str, ...]
    @property
    def is_valid(self) -> bool:
        return self.status == VALID

def _finite(v: float, name: str) -> None:
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
        raise ValueError(f"{name} must be finite numeric")

def _identity(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "retraining-dataset-report-" + hashlib.sha256(raw).hexdigest()

def _artifact_identity(artifact: FeatureArtifact) -> str:
    return "feature-artifact-" + hashlib.sha256(serialize_feature_artifact(artifact).encode()).hexdigest()

def _validate_config(config: RetrainingDatasetConfig) -> None:
    if not isinstance(config, RetrainingDatasetConfig):
        raise TypeError("config must be RetrainingDatasetConfig")
    for value, name in ((config.train_ratio, "train_ratio"), (config.validation_ratio, "validation_ratio"), (config.test_ratio, "test_ratio")):
        _finite(value, name)
        if value <= 0 or value >= 1:
            raise ValueError(f"{name} must be between 0 and 1")
    if not math.isclose(config.train_ratio + config.validation_ratio + config.test_ratio, 1.0, rel_tol=0, abs_tol=1e-12):
        raise ValueError("split ratios must sum to 1")
    if not isinstance(config.minimum_rows, int) or isinstance(config.minimum_rows, bool) or config.minimum_rows < 1:
        raise ValueError("minimum_rows must be a positive integer")
    if not isinstance(config.require_targets, bool):
        raise ValueError("require_targets must be boolean")

def _validate_artifacts(artifacts: Sequence[FeatureArtifact]) -> tuple[FeatureArtifact, ...]:
    aa = tuple(artifacts)
    if not aa:
        raise ValueError("at least one feature artifact is required")
    for artifact in aa:
        if not isinstance(artifact, FeatureArtifact):
            raise TypeError("all artifacts must be FeatureArtifact")
        if not is_feature_artifact_valid(artifact):
            raise ValueError("all feature artifacts must be VALID and leakage CLEAN")
        if len(artifact.feature_names) != len(artifact.feature_values):
            raise ValueError("feature artifact name/value counts must match")
    dates = tuple(a.target_date for a in aa)
    if len(set(dates)) != len(dates):
        raise ValueError("duplicate feature artifact target dates")
    versions = {a.feature_version for a in aa}
    if len(versions) != 1:
        raise ValueError("all feature artifacts must use the same feature version")
    names = {a.feature_names for a in aa}
    if len(names) != 1:
        raise ValueError("all feature artifacts must use identical feature names and order")
    return tuple(sorted(aa, key=lambda x: x.target_date))

def _validate_targets(targets: Mapping[date, int | float | str], dates: set[date]) -> None:
    if not isinstance(targets, Mapping):
        raise TypeError("targets must be a mapping of date to target")
    for target_date, target in targets.items():
        if not isinstance(target_date, date):
            raise TypeError("target mapping keys must be dates")
        if target is None or isinstance(target, bool) or not isinstance(target, (int, float, str)):
            raise ValueError("targets must be scalar non-boolean values")
        if isinstance(target, float) and not math.isfinite(target):
            raise ValueError("numeric targets must be finite")
    if not dates.issubset(set(targets)):
        missing = sorted(dates - set(targets))
        raise ValueError(f"missing targets for feature dates: {missing}")

def _split_dates(dates: tuple[date, ...], config: RetrainingDatasetConfig):
    n = len(dates)
    train_n = max(1, int(math.floor(n * config.train_ratio)))
    val_n = max(1, int(math.floor(n * config.validation_ratio)))
    if train_n + val_n >= n:
        val_n = 1
        train_n = n - 2
    test_n = n - train_n - val_n
    if train_n < 1 or val_n < 1 or test_n < 1:
        raise ValueError("dataset requires at least one row in each split")
    return dates[:train_n], dates[train_n:train_n + val_n], dates[train_n + val_n:]

def build_retraining_dataset_report(
    dataset_id: str,
    decision_report: RetrainingDecisionReport,
    artifacts: Sequence[FeatureArtifact],
    targets: Mapping[date, int | float | str],
    data_identity: str,
    *,
    config: RetrainingDatasetConfig = RetrainingDatasetConfig(),
) -> RetrainingDatasetReport:
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("dataset_id must not be empty")
    if not isinstance(data_identity, str) or not data_identity.strip():
        raise ValueError("data_identity must not be empty")
    if not isinstance(decision_report, RetrainingDecisionReport):
        raise TypeError("decision_report must be RetrainingDecisionReport")
    decision_validation = validate_retraining_decision_report(decision_report)
    if not decision_validation.is_valid:
        raise ValueError("decision report is invalid")
    if decision_report.decision.decision != RETRAIN:
        raise ValueError("retraining dataset requires a RETRAIN decision")
    _validate_config(config)
    aa = _validate_artifacts(artifacts)
    if len(aa) < config.minimum_rows:
        raise ValueError("artifact count is below minimum_rows")
    dates = tuple(a.target_date for a in aa)
    _validate_targets(targets, set(dates))
    train_dates, validation_dates, test_dates = _split_dates(dates, config)
    split_by_date = {d: TRAIN for d in train_dates}
    split_by_date.update({d: VALIDATION for d in validation_dates})
    split_by_date.update({d: TEST for d in test_dates})
    rows = []
    identities = []
    for artifact in aa:
        identity = _artifact_identity(artifact)
        identities.append(identity)
        values = tuple((name, artifact.feature_values[name]) for name in artifact.feature_names)
        rows.append(RetrainingDatasetRow(artifact.target_date, values, targets[artifact.target_date], split_by_date[artifact.target_date], identity))
    payload = (RETRAINING_DATASET_VERSION, dataset_id, decision_report.report_identity, decision_report.model_identity, data_identity, aa[0].feature_version, aa[0].feature_names, tuple(rows), config)
    return RetrainingDatasetReport(RETRAINING_DATASET_VERSION, dataset_id, decision_report.model_identity, decision_report.report_identity, data_identity, aa[0].feature_version, aa[0].feature_names, tuple(rows), train_dates, validation_dates, test_dates, (), config, _identity(payload))

def retraining_dataset_summary(report: RetrainingDatasetReport):
    validation = validate_retraining_dataset_report(report)
    return {"status": validation.status, "version": report.version, "dataset_id": report.dataset_id, "model_identity": report.model_identity, "decision_identity": report.decision_identity, "data_identity": report.data_identity, "feature_version": report.feature_version, "row_count": len(report.rows), "train_count": len(report.train_dates), "validation_count": len(report.validation_dates), "test_count": len(report.test_dates), "report_identity": report.report_identity}

def retraining_dataset_rows(report: RetrainingDatasetReport, split: str | None = None):
    if split is None: return report.rows
    if split not in SPLIT_NAMES: raise ValueError("invalid split")
    return tuple(row for row in report.rows if row.split == split)

def retraining_dataset_feature_names(report: RetrainingDatasetReport): return report.feature_names

def validate_retraining_dataset_report(report: RetrainingDatasetReport) -> RetrainingDatasetValidationResult:
    if not isinstance(report, RetrainingDatasetReport): return RetrainingDatasetValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues=[]
    if report.version != RETRAINING_DATASET_VERSION: issues.append("INVALID_VERSION")
    if not report.dataset_id.strip(): issues.append("MISSING_DATASET_ID")
    if not report.model_identity.strip(): issues.append("MISSING_MODEL_IDENTITY")
    if not report.decision_identity.strip(): issues.append("MISSING_DECISION_IDENTITY")
    if not report.data_identity.strip(): issues.append("MISSING_DATA_IDENTITY")
    if not report.feature_version.strip(): issues.append("MISSING_FEATURE_VERSION")
    try: _validate_config(report.config)
    except (TypeError, ValueError): issues.append("INVALID_CONFIG")
    if len(report.feature_names) != len(set(report.feature_names)) or any(not isinstance(x,str) or not x.strip() for x in report.feature_names): issues.append("INVALID_FEATURE_NAMES")
    dates=[]
    for row in report.rows:
        if not isinstance(row, RetrainingDatasetRow): issues.append("INVALID_ROW"); continue
        if row.split not in SPLIT_NAMES: issues.append("INVALID_SPLIT")
        if not isinstance(row.target_date, date): issues.append("INVALID_ROW_DATE")
        if not isinstance(row.target, (int,float,str)) or isinstance(row.target,bool): issues.append("INVALID_TARGET")
        if isinstance(row.target,float) and not math.isfinite(row.target): issues.append("NONFINITE_TARGET")
        if tuple(name for name,_ in row.feature_values) != report.feature_names: issues.append("FEATURE_ORDER_MISMATCH")
        if not row.feature_artifact_identity.strip(): issues.append("MISSING_ARTIFACT_IDENTITY")
        dates.append(row.target_date)
    if len(dates) != len(set(dates)): issues.append("DUPLICATE_ROW_DATES")
    expected_train=tuple(d for d in dates if next((r for r in report.rows if r.target_date==d),None).split==TRAIN)
    expected_val=tuple(d for d in dates if next((r for r in report.rows if r.target_date==d),None).split==VALIDATION)
    expected_test=tuple(d for d in dates if next((r for r in report.rows if r.target_date==d),None).split==TEST)
    if report.train_dates != expected_train: issues.append("TRAIN_DATES_MISMATCH")
    if report.validation_dates != expected_val: issues.append("VALIDATION_DATES_MISMATCH")
    if report.test_dates != expected_test: issues.append("TEST_DATES_MISMATCH")
    if set(report.excluded_dates) & set(dates): issues.append("EXCLUDED_DATE_OVERLAP")
    if not report.report_identity.startswith("retraining-dataset-report-"): issues.append("INVALID_REPORT_IDENTITY")
    return RetrainingDatasetValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))

__all__=["RETRAINING_DATASET_VERSION","VALID","INVALID","TRAIN","VALIDATION","TEST","SPLIT_NAMES","RetrainingDatasetConfig","RetrainingDatasetRow","RetrainingDatasetReport","RetrainingDatasetValidationResult","build_retraining_dataset_report","retraining_dataset_summary","retraining_dataset_rows","retraining_dataset_feature_names","validate_retraining_dataset_report"]
