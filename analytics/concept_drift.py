from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from analytics.actual_vs_ranked import (
    ActualVsRankedReport,
    validate_actual_vs_ranked_report,
)
from features.feature_artifact import FeatureArtifact, is_feature_artifact_valid

CONCEPT_DRIFT_VERSION = "55.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEFAULT_PERIOD_DAYS = 7
DEFAULT_THRESHOLD = 0.10
DEFAULT_BINS = 5
NUMERIC_TYPES = {"int", "integer", "float", "number", "numeric", "double"}


@dataclass(frozen=True)
class ConceptDriftRule:
    feature_name: str
    threshold: float = DEFAULT_THRESHOLD


@dataclass(frozen=True)
class ConceptDriftObservation:
    feature_name: str
    baseline_period_start: date
    comparison_period_start: date
    baseline_observation_count: int
    comparison_observation_count: int
    baseline_outcome_rate: float
    comparison_outcome_rate: float
    conditional_rate_change: float
    threshold: float
    drifted: bool


@dataclass(frozen=True)
class ConceptDriftReport:
    version: str
    source_type: str
    feature_version: str
    source_feature_artifact_count: int
    source_outcome_report_identity: str
    period_days: int
    bin_count: int
    rules: tuple[ConceptDriftRule, ...]
    observations: tuple[ConceptDriftObservation, ...]
    drifted_features: tuple[str, ...]
    drifted_periods: tuple[tuple[str, date], ...]
    drifted: bool
    report_identity: str


@dataclass(frozen=True)
class ConceptDriftValidationResult:
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


def _validate_sources(
    features: Sequence[FeatureArtifact],
    outcomes: ActualVsRankedReport,
) -> tuple[FeatureArtifact, ...]:
    ordered = tuple(sorted(tuple(features), key=lambda item: item.target_date))
    if len(ordered) < 2:
        raise ValueError("at least two feature artifacts are required.")
    if not isinstance(outcomes, ActualVsRankedReport):
        raise TypeError("outcomes must be an ActualVsRankedReport.")
    outcome_validation = validate_actual_vs_ranked_report(outcomes)
    if not outcome_validation.is_valid:
        raise ValueError(
            "invalid Phase 45 outcome report: "
            + ", ".join(outcome_validation.issues)
        )
    for artifact in ordered:
        if not isinstance(artifact, FeatureArtifact):
            raise TypeError("features must contain FeatureArtifact instances.")
        if not is_feature_artifact_valid(artifact):
            raise ValueError("all feature artifacts must be valid and leakage-clean.")
    if len({item.target_date for item in ordered}) != len(ordered):
        raise ValueError("feature artifact target dates must be unique.")
    if len({item.target_date for item in outcomes.observations}) != len(
        outcomes.observations
    ):
        raise ValueError("outcome target dates must be unique.")
    first = ordered[0]
    for artifact in ordered[1:]:
        if artifact.feature_version != first.feature_version:
            raise ValueError("all feature artifacts must use the same feature version.")
        if artifact.feature_names != first.feature_names:
            raise ValueError("all feature artifacts must use identical feature names and order.")
    outcome_dates = {item.target_date for item in outcomes.observations}
    if {item.target_date for item in ordered} != outcome_dates:
        raise ValueError("feature and outcome dates must align exactly.")
    return ordered


def _rules(
    source: tuple[FeatureArtifact, ...],
    rules: Sequence[ConceptDriftRule] | None,
) -> tuple[ConceptDriftRule, ...]:
    schemas = {schema.feature_name: schema for schema in source[0].schemas}
    if rules is None:
        values = tuple(
            ConceptDriftRule(name)
            for name in source[0].feature_names
            if schemas[name].data_type.lower() in NUMERIC_TYPES
        )
    else:
        values = tuple(rules)
    if not values:
        raise ValueError("at least one numeric concept-drift rule is required.")
    if len({rule.feature_name for rule in values}) != len(values):
        raise ValueError("concept-drift rule feature names must be unique.")
    available = set(source[0].feature_names)
    for rule in values:
        if rule.feature_name not in available:
            raise ValueError("concept-drift feature is not present: " + rule.feature_name)
        if not math.isfinite(rule.threshold) or rule.threshold <= 0 or rule.threshold > 1:
            raise ValueError("concept-drift threshold must be in (0, 1].")
    return values


def _periods(
    source: tuple[FeatureArtifact, ...],
    period_days: int,
) -> tuple[tuple[date, tuple[FeatureArtifact, ...]], ...]:
    anchor = source[0].target_date
    groups: dict[date, list[FeatureArtifact]] = {}
    for item in source:
        offset = (item.target_date - anchor).days
        start = anchor + timedelta(days=(offset // period_days) * period_days)
        groups.setdefault(start, []).append(item)
    return tuple((start, tuple(groups[start])) for start in sorted(groups))


def _numeric(
    value: object,
    feature_name: str,
) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("feature value must be numeric or None: " + feature_name)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("feature value must be finite: " + feature_name)
    return result


def _edges(values: Sequence[float], bins: int) -> tuple[float, ...]:
    low, high = min(values), max(values)
    if math.isclose(low, high, rel_tol=0.0, abs_tol=1e-15):
        return tuple([low] * (bins + 1))
    width = (high - low) / bins
    return tuple(low + index * width for index in range(bins + 1))


def _bucket(value: float, edges: tuple[float, ...]) -> int:
    if len(set(edges)) == 1:
        return 0
    for index in range(len(edges) - 1):
        if value <= edges[index + 1] or index == len(edges) - 2:
            return index
    return len(edges) - 2


def _outcome_map(
    report: ActualVsRankedReport,
) -> dict[date, int | None]:
    return {
        item.target_date: (
            1 if item.actual_rank == 1 else 0 if item.actual_rank is not None else None
        )
        for item in report.observations
    }


def _conditional_change(
    baseline_items: Sequence[FeatureArtifact],
    comparison_items: Sequence[FeatureArtifact],
    feature_name: str,
    outcomes: dict[date, int | None],
    bins: int,
) -> tuple[int, int, float, float, float]:
    baseline_pairs = []
    for item in baseline_items:
        value = _numeric(item.feature_values[feature_name], feature_name)
        outcome = outcomes[item.target_date]
        if value is not None and outcome is not None:
            baseline_pairs.append((value, outcome))
    comparison_pairs = []
    for item in comparison_items:
        value = _numeric(item.feature_values[feature_name], feature_name)
        outcome = outcomes[item.target_date]
        if value is not None and outcome is not None:
            comparison_pairs.append((value, outcome))
    if not baseline_pairs or not comparison_pairs:
        raise ValueError("each populated period must contain paired numeric feature outcomes.")
    edges = _edges(tuple(value for value, _ in baseline_pairs), bins)
    base_counts = [0] * bins
    base_hits = [0] * bins
    comp_counts = [0] * bins
    comp_hits = [0] * bins
    for value, outcome in baseline_pairs:
        index = _bucket(value, edges)
        base_counts[index] += 1
        base_hits[index] += outcome
    for value, outcome in comparison_pairs:
        index = _bucket(value, edges)
        comp_counts[index] += 1
        comp_hits[index] += outcome
    weighted_change = 0.0
    total_comp = len(comparison_pairs)
    for index in range(bins):
        base_rate = base_hits[index] / base_counts[index] if base_counts[index] else 0.0
        comp_rate = comp_hits[index] / comp_counts[index] if comp_counts[index] else 0.0
        weighted_change += abs(comp_rate - base_rate) * (
            comp_counts[index] / total_comp
        )
    baseline_rate = sum(outcome for _, outcome in baseline_pairs) / len(baseline_pairs)
    comparison_rate = sum(outcome for _, outcome in comparison_pairs) / len(comparison_pairs)
    return len(baseline_pairs), len(comparison_pairs), baseline_rate, comparison_rate, weighted_change


def build_concept_drift_report(
    features: Sequence[FeatureArtifact],
    outcomes: ActualVsRankedReport,
    *,
    period_days: int = DEFAULT_PERIOD_DAYS,
    rules: Sequence[ConceptDriftRule] | None = None,
    bin_count: int = DEFAULT_BINS,
) -> ConceptDriftReport:
    source = _validate_sources(features, outcomes)
    if isinstance(period_days, bool) or not isinstance(period_days, int) or period_days < 1:
        raise ValueError("period_days must be an integer >= 1.")
    if isinstance(bin_count, bool) or not isinstance(bin_count, int) or bin_count < 2:
        raise ValueError("bin_count must be an integer >= 2.")
    normalized = _rules(source, rules)
    grouped = _periods(source, period_days)
    if len(grouped) < 2:
        raise ValueError("at least two populated periods are required for concept drift detection.")
    outcome_map = _outcome_map(outcomes)
    baseline_start, baseline_items = grouped[0]
    observations: list[ConceptDriftObservation] = []
    for rule in normalized:
        for comparison_start, comparison_items in grouped[1:]:
            base_count, comp_count, base_rate, comp_rate, change = _conditional_change(
                baseline_items, comparison_items, rule.feature_name,
                outcome_map, bin_count
            )
            observations.append(
                ConceptDriftObservation(
                    rule.feature_name,
                    baseline_start,
                    comparison_start,
                    base_count,
                    comp_count,
                    base_rate,
                    comp_rate,
                    change,
                    rule.threshold,
                    change >= rule.threshold,
                )
            )
    drifted_features = tuple(dict.fromkeys(
        item.feature_name for item in observations if item.drifted
    ))
    drifted_periods = tuple(
        (item.feature_name, item.comparison_period_start)
        for item in observations if item.drifted
    )
    payload = {
        "version": CONCEPT_DRIFT_VERSION,
        "source_type": outcomes.source_type,
        "feature_version": source[0].feature_version,
        "source_feature_artifact_count": len(source),
        "source_outcome_report_identity": outcomes.report_identity,
        "period_days": period_days,
        "bin_count": bin_count,
        "rules": [(rule.feature_name, rule.threshold) for rule in normalized],
        "observations": [
            (
                item.feature_name, item.baseline_period_start,
                item.comparison_period_start, item.baseline_observation_count,
                item.comparison_observation_count, item.baseline_outcome_rate,
                item.comparison_outcome_rate, item.conditional_rate_change,
                item.threshold, item.drifted
            )
            for item in observations
        ],
    }
    return ConceptDriftReport(
        CONCEPT_DRIFT_VERSION, outcomes.source_type, source[0].feature_version,
        len(source), outcomes.report_identity, period_days, bin_count,
        normalized, tuple(observations), drifted_features, drifted_periods,
        bool(drifted_features), _identity("concept-drift-report-", payload)
    )


def concept_drift_summary(report: ConceptDriftReport) -> dict[str, object]:
    validation = validate_concept_drift_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "feature_version": report.feature_version,
        "source_feature_artifact_count": report.source_feature_artifact_count,
        "period_days": report.period_days,
        "bin_count": report.bin_count,
        "comparisons": len(report.observations),
        "drifted_features": report.drifted_features,
        "drifted_periods": report.drifted_periods,
        "drifted": report.drifted,
        "report_identity": report.report_identity,
    }


def concept_drift_feature_names(report: ConceptDriftReport) -> tuple[str, ...]:
    return tuple(rule.feature_name for rule in report.rules)


def concept_drift_observations(
    report: ConceptDriftReport,
    feature_name: str,
) -> tuple[ConceptDriftObservation, ...]:
    return tuple(item for item in report.observations if item.feature_name == feature_name)


def validate_concept_drift_report(
    report: ConceptDriftReport,
) -> ConceptDriftValidationResult:
    if not isinstance(report, ConceptDriftReport):
        return ConceptDriftValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != CONCEPT_DRIFT_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.feature_version.strip():
        issues.append("MISSING_FEATURE_VERSION")
    if report.source_feature_artifact_count < 2:
        issues.append("INVALID_SOURCE_ARTIFACT_COUNT")
    if not report.source_outcome_report_identity.strip():
        issues.append("MISSING_OUTCOME_REPORT_IDENTITY")
    if report.period_days < 1:
        issues.append("INVALID_PERIOD_DAYS")
    if report.bin_count < 2:
        issues.append("INVALID_BIN_COUNT")
    if not report.rules:
        issues.append("NO_RULES")
    if len({rule.feature_name for rule in report.rules}) != len(report.rules):
        issues.append("DUPLICATE_RULE_FEATURES")
    for rule in report.rules:
        if not math.isfinite(rule.threshold) or rule.threshold <= 0 or rule.threshold > 1:
            issues.append("INVALID_THRESHOLD")
    if len(report.observations) != len(report.rules) * len(
        {item.comparison_period_start for item in report.observations}
    ):
        issues.append("OBSERVATION_CARDINALITY_MISMATCH")
    declared = {rule.feature_name for rule in report.rules}
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
        if item.baseline_observation_count < 1 or item.comparison_observation_count < 1:
            issues.append("INVALID_SAMPLE_COUNT")
        for value in (
            item.baseline_outcome_rate, item.comparison_outcome_rate,
            item.conditional_rate_change, item.threshold
        ):
            if not math.isfinite(value):
                issues.append("NONFINITE_OBSERVATION")
        if not 0 <= item.baseline_outcome_rate <= 1:
            issues.append("INVALID_BASELINE_RATE")
        if not 0 <= item.comparison_outcome_rate <= 1:
            issues.append("INVALID_COMPARISON_RATE")
        if not 0 <= item.conditional_rate_change <= 1:
            issues.append("INVALID_CONDITIONAL_CHANGE")
        if item.drifted != (item.conditional_rate_change >= item.threshold):
            issues.append("DRIFT_FLAG_MISMATCH")
    expected_features = tuple(dict.fromkeys(
        item.feature_name for item in report.observations if item.drifted
    ))
    expected_periods = tuple(
        (item.feature_name, item.comparison_period_start)
        for item in report.observations if item.drifted
    )
    if report.drifted_features != expected_features:
        issues.append("DRIFTED_FEATURE_MISMATCH")
    if report.drifted_periods != expected_periods:
        issues.append("DRIFTED_PERIOD_MISMATCH")
    if report.drifted != bool(report.drifted_features):
        issues.append("OVERALL_DRIFT_MISMATCH")
    if not report.report_identity.startswith("concept-drift-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return ConceptDriftValidationResult(
        VALID if not issues else INVALID, tuple(sorted(set(issues)))
    )


__all__ = [
    "CONCEPT_DRIFT_VERSION", "VALID", "INVALID",
    "DEFAULT_PERIOD_DAYS", "DEFAULT_THRESHOLD", "DEFAULT_BINS",
    "ConceptDriftRule", "ConceptDriftObservation", "ConceptDriftReport",
    "ConceptDriftValidationResult", "build_concept_drift_report",
    "concept_drift_summary", "concept_drift_feature_names",
    "concept_drift_observations", "validate_concept_drift_report",
]
