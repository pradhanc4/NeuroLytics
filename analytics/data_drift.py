from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from features.feature_artifact import FeatureArtifact, is_feature_artifact_valid

DATA_DRIFT_VERSION = "50.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEFAULT_THRESHOLD = 0.20
DEFAULT_BINS = 10

@dataclass(frozen=True)
class DataDriftRule:
    feature_name: str
    threshold: float = DEFAULT_THRESHOLD

@dataclass(frozen=True)
class DataDriftObservation:
    feature_name: str
    baseline_period_start: date
    comparison_period_start: date
    baseline_count: int
    comparison_count: int
    baseline_mean: float
    comparison_mean: float
    psi: float
    threshold: float
    drifted: bool

@dataclass(frozen=True)
class DataDriftReport:
    version: str
    feature_version: str
    source_artifact_count: int
    source_feature_names: tuple[str, ...]
    period_days: int
    rules: tuple[DataDriftRule, ...]
    bin_count: int
    observations: tuple[DataDriftObservation, ...]
    drifted_features: tuple[str, ...]
    drifted_periods: tuple[tuple[str, date], ...]
    drifted: bool
    report_identity: str

@dataclass(frozen=True)
class DataDriftValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()

def _schema_map(artifact: FeatureArtifact):
    return {schema.feature_name: schema for schema in artifact.schemas}

def _validate_source(source: Sequence[FeatureArtifact]) -> tuple[FeatureArtifact, ...]:
    values = tuple(source)
    if len(values) < 2:
        raise ValueError("at least two feature artifacts are required.")
    for artifact in values:
        if not isinstance(artifact, FeatureArtifact):
            raise TypeError("source must contain only FeatureArtifact instances.")
        if not is_feature_artifact_valid(artifact):
            raise ValueError("all feature artifacts must be valid and leakage-clean.")
    ordered = tuple(sorted(values, key=lambda x: x.target_date))
    if len({item.target_date for item in ordered}) != len(ordered):
        raise ValueError("feature artifact target dates must be unique.")
    first = ordered[0]
    for artifact in ordered[1:]:
        if artifact.feature_version != first.feature_version:
            raise ValueError("all feature artifacts must use the same feature version.")
        if artifact.feature_names != first.feature_names:
            raise ValueError("all feature artifacts must use identical feature names and order.")
    return ordered

def _normalize_rules(source: tuple[FeatureArtifact, ...], rules: Sequence[DataDriftRule] | None) -> tuple[DataDriftRule, ...]:
    available = set(source[0].feature_names)
    if rules is None:
        selected = []
        schemas = _schema_map(source[0])
        for name in source[0].feature_names:
            data_type = schemas[name].data_type.lower()
            if data_type in {"int", "integer", "float", "number", "numeric", "double"}:
                selected.append(DataDriftRule(name))
        values = tuple(selected)
    else:
        values = tuple(rules)
    if not values:
        raise ValueError("at least one numeric data-drift feature is required.")
    if len({rule.feature_name for rule in values}) != len(values):
        raise ValueError("data-drift rule feature names must be unique.")
    for rule in values:
        if rule.feature_name not in available:
            raise ValueError("data-drift feature is not present: " + rule.feature_name)
        if not math.isfinite(rule.threshold) or rule.threshold <= 0:
            raise ValueError("drift threshold must be finite and positive.")
    return values

def _periods(source: tuple[FeatureArtifact, ...], period_days: int):
    anchor = source[0].target_date
    groups = {}
    for item in source:
        offset = (item.target_date - anchor).days
        start = anchor + timedelta(days=(offset // period_days) * period_days)
        groups.setdefault(start, []).append(item)
    return tuple((start, tuple(groups[start])) for start in sorted(groups))

def _numeric_values(items: Sequence[FeatureArtifact], feature_name: str) -> tuple[float, ...]:
    result = []
    for item in items:
        value = item.feature_values[feature_name]
        if value is None or isinstance(value, bool):
            continue
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError("feature values must be finite numeric values or None: " + feature_name)
        result.append(float(value))
    return tuple(result)

def _psi(baseline: Sequence[float], comparison: Sequence[float], bins: int) -> float:
    low = min(min(baseline), min(comparison))
    high = max(max(baseline), max(comparison))
    if math.isclose(low, high, rel_tol=0.0, abs_tol=1e-15):
        return 0.0
    width = (high - low) / bins
    epsilon = 1e-12
    def counts(values):
        result = [0] * bins
        for value in values:
            index = min(bins - 1, int((value - low) / width))
            result[index] += 1
        return result
    base_counts, comp_counts = counts(baseline), counts(comparison)
    total = 0.0
    for b, c in zip(base_counts, comp_counts):
        bp = max(b / len(baseline), epsilon)
        cp = max(c / len(comparison), epsilon)
        total += (cp - bp) * math.log(cp / bp)
    return total
def build_data_drift_report(
    source: Sequence[FeatureArtifact],
    *,
    period_days: int = 7,
    rules: Sequence[DataDriftRule] | None = None,
    bin_count: int = DEFAULT_BINS,
) -> DataDriftReport:
    ordered = _validate_source(source)
    if period_days < 1:
        raise ValueError("period_days must be >= 1.")
    if isinstance(bin_count, bool) or not isinstance(bin_count, int) or bin_count < 2:
        raise ValueError("bin_count must be an integer >= 2.")
    normalized = _normalize_rules(ordered, rules)
    grouped = _periods(ordered, period_days)
    if len(grouped) < 2:
        raise ValueError("at least two populated periods are required for data drift detection.")
    baseline_start, baseline_items = grouped[0]
    observations = []
    for rule in normalized:
        baseline_values = _numeric_values(baseline_items, rule.feature_name)
        if not baseline_values:
            raise ValueError("baseline contains no numeric observations: " + rule.feature_name)
        for comparison_start, comparison_items in grouped[1:]:
            comparison_values = _numeric_values(comparison_items, rule.feature_name)
            if not comparison_values:
                raise ValueError("comparison contains no numeric observations: " + rule.feature_name)
            psi = _psi(baseline_values, comparison_values, bin_count)
            observations.append(DataDriftObservation(
                rule.feature_name, baseline_start, comparison_start,
                len(baseline_values), len(comparison_values),
                sum(baseline_values) / len(baseline_values),
                sum(comparison_values) / len(comparison_values),
                psi, rule.threshold, psi >= rule.threshold,
            ))
    drifted_features = tuple(dict.fromkeys(o.feature_name for o in observations if o.drifted))
    drifted_periods = tuple((o.feature_name, o.comparison_period_start) for o in observations if o.drifted)
    payload = {
        "version": DATA_DRIFT_VERSION,
        "feature_version": ordered[0].feature_version,
        "source_artifact_count": len(ordered),
        "source_feature_names": ordered[0].feature_names,
        "period_days": period_days,
        "rules": [(r.feature_name, r.threshold) for r in normalized],
        "bin_count": bin_count,
        "observations": [(o.feature_name, o.baseline_period_start, o.comparison_period_start,
                          o.baseline_count, o.comparison_count, o.baseline_mean,
                          o.comparison_mean, o.psi, o.threshold, o.drifted) for o in observations],
    }
    return DataDriftReport(
        DATA_DRIFT_VERSION, ordered[0].feature_version, len(ordered), ordered[0].feature_names,
        period_days, normalized, bin_count, tuple(observations), drifted_features,
        drifted_periods, bool(drifted_features), _identity("data-drift-report-", payload),
    )

def data_drift_summary(report: DataDriftReport) -> dict[str, object]:
    validation = validate_data_drift_report(report)
    return {"status": validation.status, "version": report.version,
            "feature_version": report.feature_version, "source_artifact_count": report.source_artifact_count,
            "period_days": report.period_days, "rules": report.rules, "bin_count": report.bin_count,
            "comparisons": len(report.observations), "drifted_features": report.drifted_features,
            "drifted_periods": report.drifted_periods, "drifted": report.drifted,
            "report_identity": report.report_identity}

def data_drift_feature_names(report: DataDriftReport) -> tuple[str, ...]:
    return tuple(rule.feature_name for rule in report.rules)

def data_drift_observations(report: DataDriftReport, feature_name: str) -> tuple[DataDriftObservation, ...]:
    return tuple(item for item in report.observations if item.feature_name == feature_name)
def validate_data_drift_report(report: DataDriftReport) -> DataDriftValidationResult:
    if not isinstance(report, DataDriftReport):
        return DataDriftValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues = []
    if report.version != DATA_DRIFT_VERSION:
        issues.append("INVALID_VERSION")
    if not report.feature_version.strip():
        issues.append("MISSING_FEATURE_VERSION")
    if report.source_artifact_count < 2:
        issues.append("INVALID_SOURCE_ARTIFACT_COUNT")
    if not report.source_feature_names:
        issues.append("NO_SOURCE_FEATURE_NAMES")
    if report.period_days < 1:
        issues.append("INVALID_PERIOD_DAYS")
    if report.bin_count < 2:
        issues.append("INVALID_BIN_COUNT")
    if not report.rules:
        issues.append("NO_RULES")
    if len({r.feature_name for r in report.rules}) != len(report.rules):
        issues.append("DUPLICATE_RULE_FEATURES")
    for rule in report.rules:
        if rule.feature_name not in report.source_feature_names:
            issues.append("UNKNOWN_FEATURE")
        if not math.isfinite(rule.threshold) or rule.threshold <= 0:
            issues.append("INVALID_THRESHOLD")
    expected_per_feature = len({o.comparison_period_start for o in report.observations})
    if expected_per_feature and len(report.observations) != expected_per_feature * len(report.rules):
        issues.append("OBSERVATION_CARDINALITY_MISMATCH")
    seen = set()
    declared = {r.feature_name for r in report.rules}
    for item in report.observations:
        key = (item.feature_name, item.comparison_period_start)
        if key in seen:
            issues.append("DUPLICATE_OBSERVATION")
        seen.add(key)
        if item.feature_name not in declared:
            issues.append("UNDECLARED_FEATURE")
        if item.comparison_period_start <= item.baseline_period_start:
            issues.append("INVALID_COMPARISON_ORDER")
        if item.baseline_count < 1 or item.comparison_count < 1:
            issues.append("INVALID_SAMPLE_COUNT")
        if not all(math.isfinite(v) for v in (item.baseline_mean, item.comparison_mean, item.psi, item.threshold)):
            issues.append("NONFINITE_OBSERVATION")
        if item.psi < 0:
            issues.append("INVALID_PSI")
        if item.drifted != (item.psi >= item.threshold):
            issues.append("DRIFT_FLAG_MISMATCH")
    expected_features = tuple(dict.fromkeys(o.feature_name for o in report.observations if o.drifted))
    expected_periods = tuple((o.feature_name, o.comparison_period_start) for o in report.observations if o.drifted)
    if report.drifted_features != expected_features:
        issues.append("DRIFTED_FEATURE_MISMATCH")
    if report.drifted_periods != expected_periods:
        issues.append("DRIFTED_PERIOD_MISMATCH")
    if report.drifted != bool(report.drifted_features):
        issues.append("OVERALL_DRIFT_MISMATCH")
    if not report.report_identity.startswith("data-drift-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return DataDriftValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))

__all__ = [
    "DATA_DRIFT_VERSION", "VALID", "INVALID", "DEFAULT_THRESHOLD", "DEFAULT_BINS",
    "DataDriftRule", "DataDriftObservation", "DataDriftReport", "DataDriftValidationResult",
    "build_data_drift_report", "data_drift_summary", "data_drift_feature_names",
    "data_drift_observations", "validate_data_drift_report",
]
