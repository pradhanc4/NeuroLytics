from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from features.feature_artifact import FeatureArtifact, is_feature_artifact_valid

FEATURE_DRIFT_VERSION = "54.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEFAULT_PERIOD_DAYS = 7
DEFAULT_THRESHOLD = 0.20
DEFAULT_BINS = 10
NUMERIC_TYPES = {"int", "integer", "float", "number", "numeric", "double"}


@dataclass(frozen=True)
class FeatureDriftRule:
    feature_name: str
    threshold: float = DEFAULT_THRESHOLD


@dataclass(frozen=True)
class FeatureDriftObservation:
    feature_name: str
    baseline_period_start: date
    comparison_period_start: date
    baseline_count: int
    comparison_count: int
    baseline_missing_rate: float
    comparison_missing_rate: float
    baseline_mean: float
    comparison_mean: float
    baseline_std: float
    comparison_std: float
    psi: float
    threshold: float
    drifted: bool


@dataclass(frozen=True)
class FeatureDriftReport:
    version: str
    feature_version: str
    source_artifact_count: int
    source_feature_names: tuple[str, ...]
    period_days: int
    rules: tuple[FeatureDriftRule, ...]
    bin_count: int
    observations: tuple[FeatureDriftObservation, ...]
    drifted_features: tuple[str, ...]
    drifted_periods: tuple[tuple[str, date], ...]
    drifted: bool
    report_identity: str


@dataclass(frozen=True)
class FeatureDriftValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()


def _schema_map(artifact: FeatureArtifact):
    return {schema.feature_name: schema for schema in artifact.schemas}


def _validate_source(
    source: Sequence[FeatureArtifact],
) -> tuple[FeatureArtifact, ...]:
    values = tuple(source)
    if len(values) < 2:
        raise ValueError("at least two feature artifacts are required.")
    for artifact in values:
        if not isinstance(artifact, FeatureArtifact):
            raise TypeError("source must contain only FeatureArtifact instances.")
        if not is_feature_artifact_valid(artifact):
            raise ValueError("all feature artifacts must be valid and leakage-clean.")
    ordered = tuple(sorted(values, key=lambda item: item.target_date))
    if len({item.target_date for item in ordered}) != len(ordered):
        raise ValueError("feature artifact target dates must be unique.")
    first = ordered[0]
    for artifact in ordered[1:]:
        if artifact.feature_version != first.feature_version:
            raise ValueError("all feature artifacts must use the same feature version.")
        if artifact.feature_names != first.feature_names:
            raise ValueError("all feature artifacts must use identical feature names and order.")
    return ordered


def _normalize_rules(
    source: tuple[FeatureArtifact, ...],
    rules: Sequence[FeatureDriftRule] | None,
) -> tuple[FeatureDriftRule, ...]:
    available = set(source[0].feature_names)
    schemas = _schema_map(source[0])
    if rules is None:
        values = tuple(
            FeatureDriftRule(name)
            for name in source[0].feature_names
            if schemas[name].data_type.lower() in NUMERIC_TYPES
        )
    else:
        values = tuple(rules)
    if not values:
        raise ValueError("at least one numeric feature-drift rule is required.")
    if len({rule.feature_name for rule in values}) != len(values):
        raise ValueError("feature-drift rule feature names must be unique.")
    for rule in values:
        if rule.feature_name not in available:
            raise ValueError("feature-drift feature is not present: " + rule.feature_name)
        if not math.isfinite(rule.threshold) or rule.threshold <= 0:
            raise ValueError("drift threshold must be finite and positive.")
    return values

def _periods(source: tuple[FeatureArtifact, ...], period_days: int):
    anchor = source[0].target_date
    groups: dict[date, list[FeatureArtifact]] = {}
    for item in source:
        offset = (item.target_date - anchor).days
        start = anchor + timedelta(days=(offset // period_days) * period_days)
        groups.setdefault(start, []).append(item)
    return tuple((start, tuple(groups[start])) for start in sorted(groups))


def _raw_values(
    items: Sequence[FeatureArtifact],
    feature_name: str,
) -> tuple[object, ...]:
    return tuple(item.feature_values[feature_name] for item in items)


def _numeric_values(
    values: Sequence[object],
    feature_name: str,
) -> tuple[float, ...]:
    result: list[float] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                "feature values must be finite numeric values or None: "
                + feature_name
            )
        if not math.isfinite(float(value)):
            raise ValueError("feature values must be finite: " + feature_name)
        result.append(float(value))
    return tuple(result)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _psi(
    baseline: Sequence[float],
    comparison: Sequence[float],
    bins: int,
) -> float:
    low = min(min(baseline), min(comparison))
    high = max(max(baseline), max(comparison))
    if math.isclose(low, high, rel_tol=0.0, abs_tol=1e-15):
        return 0.0
    width = (high - low) / bins
    epsilon = 1e-12

    def counts(values: Sequence[float]) -> list[int]:
        result = [0] * bins
        for value in values:
            index = min(bins - 1, int((value - low) / width))
            result[index] += 1
        return result

    base_counts = counts(baseline)
    comparison_counts = counts(comparison)
    total = 0.0
    for base_count, comparison_count in zip(base_counts, comparison_counts):
        base_probability = max(base_count / len(baseline), epsilon)
        comparison_probability = max(
            comparison_count / len(comparison), epsilon
        )
        total += (
            (comparison_probability - base_probability)
            * math.log(comparison_probability / base_probability)
        )
    return total


def build_feature_drift_report(
    source: Sequence[FeatureArtifact],
    *,
    period_days: int = DEFAULT_PERIOD_DAYS,
    rules: Sequence[FeatureDriftRule] | None = None,
    bin_count: int = DEFAULT_BINS,
) -> FeatureDriftReport:
    ordered = _validate_source(source)
    if isinstance(period_days, bool) or not isinstance(period_days, int) or period_days < 1:
        raise ValueError("period_days must be an integer >= 1.")
    if isinstance(bin_count, bool) or not isinstance(bin_count, int) or bin_count < 2:
        raise ValueError("bin_count must be an integer >= 2.")
    normalized = _normalize_rules(ordered, rules)
    grouped = _periods(ordered, period_days)
    if len(grouped) < 2:
        raise ValueError("at least two populated periods are required for feature drift monitoring.")
    baseline_start, baseline_items = grouped[0]
    observations: list[FeatureDriftObservation] = []
    total_baseline = len(baseline_items)

    for rule in normalized:
        baseline_raw = _raw_values(baseline_items, rule.feature_name)
        baseline_values = _numeric_values(baseline_raw, rule.feature_name)
        if not baseline_values:
            raise ValueError("baseline contains no numeric observations: " + rule.feature_name)
        baseline_missing = sum(value is None for value in baseline_raw) / total_baseline
        baseline_mean = _mean(baseline_values)
        baseline_std = _std(baseline_values)

        for comparison_start, comparison_items in grouped[1:]:
            comparison_raw = _raw_values(comparison_items, rule.feature_name)
            comparison_values = _numeric_values(comparison_raw, rule.feature_name)
            if not comparison_values:
                raise ValueError(
                    "comparison contains no numeric observations: "
                    + rule.feature_name
                )
            comparison_missing = (
                sum(value is None for value in comparison_raw) / len(comparison_raw)
            )
            psi = _psi(baseline_values, comparison_values, bin_count)
            observations.append(
                FeatureDriftObservation(
                    rule.feature_name,
                    baseline_start,
                    comparison_start,
                    len(baseline_values),
                    len(comparison_values),
                    baseline_missing,
                    comparison_missing,
                    baseline_mean,
                    _mean(comparison_values),
                    baseline_std,
                    _std(comparison_values),
                    psi,
                    rule.threshold,
                    psi >= rule.threshold,
                )
            )

    drifted_features = tuple(
        dict.fromkeys(
            observation.feature_name
            for observation in observations
            if observation.drifted
        )
    )
    drifted_periods = tuple(
        (observation.feature_name, observation.comparison_period_start)
        for observation in observations
        if observation.drifted
    )
    payload = {
        "version": FEATURE_DRIFT_VERSION,
        "feature_version": ordered[0].feature_version,
        "source_artifact_count": len(ordered),
        "source_feature_names": ordered[0].feature_names,
        "period_days": period_days,
        "rules": [(rule.feature_name, rule.threshold) for rule in normalized],
        "bin_count": bin_count,
        "observations": [
            (
                item.feature_name,
                item.baseline_period_start,
                item.comparison_period_start,
                item.baseline_count,
                item.comparison_count,
                item.baseline_missing_rate,
                item.comparison_missing_rate,
                item.baseline_mean,
                item.comparison_mean,
                item.baseline_std,
                item.comparison_std,
                item.psi,
                item.threshold,
                item.drifted,
            )
            for item in observations
        ],
    }
    return FeatureDriftReport(
        FEATURE_DRIFT_VERSION,
        ordered[0].feature_version,
        len(ordered),
        ordered[0].feature_names,
        period_days,
        normalized,
        bin_count,
        tuple(observations),
        drifted_features,
        drifted_periods,
        bool(drifted_features),
        _identity("feature-drift-report-", payload),
    )


def feature_drift_summary(report: FeatureDriftReport) -> dict[str, object]:
    validation = validate_feature_drift_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "feature_version": report.feature_version,
        "source_artifact_count": report.source_artifact_count,
        "period_days": report.period_days,
        "rules": report.rules,
        "bin_count": report.bin_count,
        "comparisons": len(report.observations),
        "drifted_features": report.drifted_features,
        "drifted_periods": report.drifted_periods,
        "drifted": report.drifted,
        "report_identity": report.report_identity,
    }


def feature_drift_feature_names(report: FeatureDriftReport) -> tuple[str, ...]:
    return tuple(rule.feature_name for rule in report.rules)


def feature_drift_observations(
    report: FeatureDriftReport,
    feature_name: str,
) -> tuple[FeatureDriftObservation, ...]:
    return tuple(
        item for item in report.observations
        if item.feature_name == feature_name
    )

def validate_feature_drift_report(
    report: FeatureDriftReport,
) -> FeatureDriftValidationResult:
    if not isinstance(report, FeatureDriftReport):
        return FeatureDriftValidationResult(INVALID, ("INVALID_REPORT_TYPE",))

    issues: list[str] = []
    if report.version != FEATURE_DRIFT_VERSION:
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
    if len({rule.feature_name for rule in report.rules}) != len(report.rules):
        issues.append("DUPLICATE_RULE_FEATURES")

    declared = {rule.feature_name for rule in report.rules}
    for rule in report.rules:
        if rule.feature_name not in report.source_feature_names:
            issues.append("UNKNOWN_FEATURE")
        if not math.isfinite(rule.threshold) or rule.threshold <= 0:
            issues.append("INVALID_THRESHOLD")

    comparison_periods = {
        item.comparison_period_start for item in report.observations
    }
    if comparison_periods and len(report.observations) != (
        len(comparison_periods) * len(report.rules)
    ):
        issues.append("OBSERVATION_CARDINALITY_MISMATCH")

    seen: set[tuple[str, date]] = set()
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
        for value in (
            item.baseline_missing_rate,
            item.comparison_missing_rate,
            item.baseline_mean,
            item.comparison_mean,
            item.baseline_std,
            item.comparison_std,
            item.psi,
            item.threshold,
        ):
            if not math.isfinite(value):
                issues.append("NONFINITE_OBSERVATION")
        if not 0.0 <= item.baseline_missing_rate <= 1.0:
            issues.append("INVALID_BASELINE_MISSING_RATE")
        if not 0.0 <= item.comparison_missing_rate <= 1.0:
            issues.append("INVALID_COMPARISON_MISSING_RATE")
        if item.baseline_std < 0 or item.comparison_std < 0:
            issues.append("INVALID_STANDARD_DEVIATION")
        if item.psi < 0:
            issues.append("INVALID_PSI")
        if item.drifted != (item.psi >= item.threshold):
            issues.append("DRIFT_FLAG_MISMATCH")

    expected_features = tuple(
        dict.fromkeys(
            item.feature_name
            for item in report.observations
            if item.drifted
        )
    )
    expected_periods = tuple(
        (item.feature_name, item.comparison_period_start)
        for item in report.observations
        if item.drifted
    )
    if report.drifted_features != expected_features:
        issues.append("DRIFTED_FEATURE_MISMATCH")
    if report.drifted_periods != expected_periods:
        issues.append("DRIFTED_PERIOD_MISMATCH")
    if report.drifted != bool(report.drifted_features):
        issues.append("OVERALL_DRIFT_MISMATCH")
    if not report.report_identity.startswith("feature-drift-report-"):
        issues.append("INVALID_REPORT_IDENTITY")

    return FeatureDriftValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "FEATURE_DRIFT_VERSION",
    "VALID",
    "INVALID",
    "DEFAULT_PERIOD_DAYS",
    "DEFAULT_THRESHOLD",
    "DEFAULT_BINS",
    "FeatureDriftRule",
    "FeatureDriftObservation",
    "FeatureDriftReport",
    "FeatureDriftValidationResult",
    "build_feature_drift_report",
    "feature_drift_summary",
    "feature_drift_feature_names",
    "feature_drift_observations",
    "validate_feature_drift_report",
]
