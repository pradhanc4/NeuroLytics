from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from analytics.actual_vs_ranked import (
    ActualVsRankedReport,
    validate_actual_vs_ranked_report,
)

MODEL_DRIFT_VERSION = "49.0.0"
VALID = "VALID"
INVALID = "INVALID"
DEFAULT_METRICS = ("top_probability", "cumulative_probability")
DEFAULT_THRESHOLD = 0.20
DEFAULT_BINS = 10

@dataclass(frozen=True)
class ModelDriftRule:
    metric: str
    threshold: float = DEFAULT_THRESHOLD

@dataclass(frozen=True)
class ModelDriftObservation:
    metric: str
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
class ModelDriftReport:
    version: str
    source_type: str
    source_report_identity: str
    period_days: int
    rules: tuple[ModelDriftRule, ...]
    bin_count: int
    observations: tuple[ModelDriftObservation, ...]
    drifted_metrics: tuple[str, ...]
    drifted_periods: tuple[tuple[str, date], ...]
    drifted: bool
    report_identity: str

@dataclass(frozen=True)
class ModelDriftValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()

def _metric_value(item, metric: str) -> float:
    if metric == "top_probability":
        return item.top_probability
    if metric == "cumulative_probability":
        return item.cumulative_probability_at_max_k
    raise ValueError("unsupported model-drift metric: " + metric)

def _validate_rules(rules: Sequence[ModelDriftRule] | None) -> tuple[ModelDriftRule, ...]:
    values = tuple(rules) if rules is not None else tuple(ModelDriftRule(m) for m in DEFAULT_METRICS)
    if not values:
        raise ValueError("at least one model-drift rule is required.")
    if len({r.metric for r in values}) != len(values):
        raise ValueError("model-drift rule metrics must be unique.")
    for rule in values:
        if rule.metric not in DEFAULT_METRICS:
            raise ValueError("unsupported model-drift metric: " + rule.metric)
        if not math.isfinite(rule.threshold) or rule.threshold <= 0:
            raise ValueError("drift threshold must be finite and positive.")
    return values

def _periods(source: ActualVsRankedReport, period_days: int):
    ordered = sorted(source.observations, key=lambda x: (x.target_date, x.group_id))
    anchor = ordered[0].target_date
    groups = {}
    for item in ordered:
        offset = (item.target_date - anchor).days
        start = anchor.fromordinal(anchor.toordinal() + (offset // period_days) * period_days)
        groups.setdefault(start, []).append(item)
    return tuple((start, tuple(groups[start])) for start in sorted(groups))

def _psi(baseline: Sequence[float], comparison: Sequence[float], bins: int) -> float:
    edges = [i / bins for i in range(bins + 1)]
    epsilon = 1e-12
    def counts(values):
        result = [0] * bins
        for value in values:
            index = min(bins - 1, int(value * bins))
            result[index] += 1
        return result
    base_counts = counts(baseline)
    comp_counts = counts(comparison)
    base_total = len(baseline)
    comp_total = len(comparison)
    total = 0.0
    for b, c in zip(base_counts, comp_counts):
        bp = max(b / base_total, epsilon)
        cp = max(c / comp_total, epsilon)
        total += (cp - bp) * math.log(cp / bp)
    return total
def build_model_drift_report(
    source: ActualVsRankedReport,
    *,
    period_days: int = 7,
    rules: Sequence[ModelDriftRule] | None = None,
    bin_count: int = DEFAULT_BINS,
) -> ModelDriftReport:
    if not isinstance(source, ActualVsRankedReport):
        raise TypeError("source must be an ActualVsRankedReport.")
    validation = validate_actual_vs_ranked_report(source)
    if not validation.is_valid:
        raise ValueError("invalid Phase 45 source report: " + ", ".join(validation.issues))
    if period_days < 1:
        raise ValueError("period_days must be >= 1.")
    if isinstance(bin_count, bool) or not isinstance(bin_count, int) or bin_count < 2:
        raise ValueError("bin_count must be an integer >= 2.")
    normalized = _validate_rules(rules)
    grouped = _periods(source, period_days)
    if len(grouped) < 2:
        raise ValueError("at least two periods are required for model drift detection.")
    baseline_start, baseline_items = grouped[0]
    observations = []
    for rule in normalized:
        baseline_values = tuple(_metric_value(item, rule.metric) for item in baseline_items)
        for comparison_start, comparison_items in grouped[1:]:
            comparison_values = tuple(_metric_value(item, rule.metric) for item in comparison_items)
            psi = _psi(baseline_values, comparison_values, bin_count)
            observations.append(ModelDriftObservation(
                rule.metric,
                baseline_start,
                comparison_start,
                len(baseline_values),
                len(comparison_values),
                sum(baseline_values) / len(baseline_values),
                sum(comparison_values) / len(comparison_values),
                psi,
                rule.threshold,
                psi >= rule.threshold,
            ))
    drifted_metrics = tuple(dict.fromkeys(item.metric for item in observations if item.drifted))
    drifted_periods = tuple((item.metric, item.comparison_period_start) for item in observations if item.drifted)
    payload = {
        "version": MODEL_DRIFT_VERSION,
        "source_type": source.source_type,
        "source_report_identity": source.report_identity,
        "period_days": period_days,
        "rules": [(r.metric, r.threshold) for r in normalized],
        "bin_count": bin_count,
        "observations": [
            (o.metric, o.baseline_period_start, o.comparison_period_start,
             o.baseline_count, o.comparison_count, o.psi, o.threshold, o.drifted)
            for o in observations
        ],
    }
    return ModelDriftReport(
        MODEL_DRIFT_VERSION,
        source.source_type,
        source.report_identity,
        period_days,
        normalized,
        bin_count,
        tuple(observations),
        drifted_metrics,
        drifted_periods,
        bool(drifted_metrics),
        _identity("model-drift-report-", payload),
    )

def model_drift_summary(report: ModelDriftReport) -> dict[str, object]:
    validation = validate_model_drift_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "source_type": report.source_type,
        "source_report_identity": report.source_report_identity,
        "period_days": report.period_days,
        "rules": report.rules,
        "bin_count": report.bin_count,
        "comparisons": len(report.observations),
        "drifted_metrics": report.drifted_metrics,
        "drifted_periods": report.drifted_periods,
        "drifted": report.drifted,
        "report_identity": report.report_identity,
    }

def model_drift_metric_names(report: ModelDriftReport) -> tuple[str, ...]:
    return tuple(rule.metric for rule in report.rules)

def model_drift_observations(report: ModelDriftReport, metric: str) -> tuple[ModelDriftObservation, ...]:
    return tuple(item for item in report.observations if item.metric == metric)
def validate_model_drift_report(report: ModelDriftReport) -> ModelDriftValidationResult:
    if not isinstance(report, ModelDriftReport):
        return ModelDriftValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues = []
    if report.version != MODEL_DRIFT_VERSION:
        issues.append("INVALID_VERSION")
    if report.source_type not in {"panel", "jodi"}:
        issues.append("INVALID_SOURCE_TYPE")
    if not report.source_report_identity.strip():
        issues.append("MISSING_SOURCE_REPORT_IDENTITY")
    if report.period_days < 1:
        issues.append("INVALID_PERIOD_DAYS")
    if report.bin_count < 2:
        issues.append("INVALID_BIN_COUNT")
    if not report.rules:
        issues.append("NO_RULES")
    if len({r.metric for r in report.rules}) != len(report.rules):
        issues.append("DUPLICATE_RULE_METRICS")
    for rule in report.rules:
        if rule.metric not in DEFAULT_METRICS:
            issues.append("UNKNOWN_METRIC")
        if not math.isfinite(rule.threshold) or rule.threshold <= 0:
            issues.append("INVALID_THRESHOLD")
    expected = len(report.rules)
    if report.observations and len(report.observations) % expected != 0:
        issues.append("OBSERVATION_CARDINALITY_MISMATCH")
    seen = set()
    for item in report.observations:
        key = (item.metric, item.comparison_period_start)
        if key in seen:
            issues.append("DUPLICATE_OBSERVATION")
        seen.add(key)
        if item.metric not in {r.metric for r in report.rules}:
            issues.append("UNDECLARED_METRIC")
        if item.comparison_period_start <= item.baseline_period_start:
            issues.append("INVALID_COMPARISON_ORDER")
        if item.baseline_count < 1 or item.comparison_count < 1:
            issues.append("INVALID_SAMPLE_COUNT")
        if not all(math.isfinite(v) for v in (item.baseline_mean, item.comparison_mean, item.psi, item.threshold)):
            issues.append("NONFINITE_OBSERVATION")
        if not 0 <= item.baseline_mean <= 1 or not 0 <= item.comparison_mean <= 1:
            issues.append("INVALID_MEAN_BOUNDS")
        if item.psi < 0:
            issues.append("INVALID_PSI")
        if item.drifted != (item.psi >= item.threshold):
            issues.append("DRIFT_FLAG_MISMATCH")
    declared = {r.metric for r in report.rules}
    if set(report.drifted_metrics) - declared:
        issues.append("UNDECLARED_DRIFTED_METRIC")
    expected_metrics = tuple(dict.fromkeys(item.metric for item in report.observations if item.drifted))
    if report.drifted_metrics != expected_metrics:
        issues.append("DRIFTED_METRIC_MISMATCH")
    expected_periods = tuple((item.metric, item.comparison_period_start) for item in report.observations if item.drifted)
    if report.drifted_periods != expected_periods:
        issues.append("DRIFTED_PERIOD_MISMATCH")
    if report.drifted != bool(report.drifted_metrics):
        issues.append("OVERALL_DRIFT_MISMATCH")
    if not report.report_identity.startswith("model-drift-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return ModelDriftValidationResult(VALID if not issues else INVALID, tuple(sorted(set(issues))))

__all__ = [
    "MODEL_DRIFT_VERSION", "VALID", "INVALID", "DEFAULT_METRICS",
    "DEFAULT_THRESHOLD", "DEFAULT_BINS", "ModelDriftRule",
    "ModelDriftObservation", "ModelDriftReport",
    "ModelDriftValidationResult", "build_model_drift_report",
    "model_drift_summary", "model_drift_metric_names",
    "model_drift_observations", "validate_model_drift_report",
]
