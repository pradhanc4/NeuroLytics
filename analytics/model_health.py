from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Sequence

MODEL_HEALTH_VERSION = "57.0.0"
VALID = "VALID"
INVALID = "INVALID"
HEALTHY = "HEALTHY"
DEGRADED = "DEGRADED"
CRITICAL = "CRITICAL"
VALID_STATUSES = (HEALTHY, DEGRADED, CRITICAL)
DEFAULT_HEALTHY_MIN = 0.80
DEFAULT_DEGRADED_MIN = 0.50
DEFAULT_WEIGHT = 1.0


@dataclass(frozen=True)
class HealthComponent:
    name: str
    score: float
    status: str
    weight: float = DEFAULT_WEIGHT
    source_identity: str = ""


@dataclass(frozen=True)
class HealthScore:
    weighted_score: float
    status: str
    component_count: int
    active_critical_components: tuple[str, ...]
    active_degraded_components: tuple[str, ...]


@dataclass(frozen=True)
class ModelHealthReport:
    version: str
    model_identity: str
    components: tuple[HealthComponent, ...]
    healthy_min: float
    degraded_min: float
    score: HealthScore
    report_identity: str


@dataclass(frozen=True)
class ModelHealthValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()


def _validate_component(component: HealthComponent) -> None:
    if not component.name.strip():
        raise ValueError("component name must not be empty.")
    if not math.isfinite(component.score) or not 0 <= component.score <= 1:
        raise ValueError("component score must be finite and in [0, 1].")
    if component.status not in VALID_STATUSES:
        raise ValueError("invalid component status: " + component.status)
    if not math.isfinite(component.weight) or component.weight <= 0:
        raise ValueError("component weight must be finite and positive.")


def _status(score: float, healthy_min: float, degraded_min: float) -> str:
    if score >= healthy_min:
        return HEALTHY
    if score >= degraded_min:
        return DEGRADED
    return CRITICAL


def _normalize(
    components: Sequence[HealthComponent],
    healthy_min: float,
    degraded_min: float,
) -> tuple[HealthComponent, ...]:
    values = tuple(components)
    if not values:
        raise ValueError("at least one health component is required.")
    if not math.isfinite(healthy_min) or not 0 < healthy_min <= 1:
        raise ValueError("healthy_min must be finite and in (0, 1].")
    if not math.isfinite(degraded_min) or not 0 <= degraded_min < healthy_min:
        raise ValueError("degraded_min must be finite, >= 0, and below healthy_min.")
    if len({item.name for item in values}) != len(values):
        raise ValueError("health component names must be unique.")
    for item in values:
        _validate_component(item)
        expected = _status(item.score, healthy_min, degraded_min)
        if item.status != expected:
            raise ValueError(
                f"component status does not match score for {item.name}: "
                f"expected {expected}, got {item.status}"
            )
    return values


def build_model_health_report(
    model_identity: str,
    components: Sequence[HealthComponent],
    *,
    healthy_min: float = DEFAULT_HEALTHY_MIN,
    degraded_min: float = DEFAULT_DEGRADED_MIN,
) -> ModelHealthReport:
    if not isinstance(model_identity, str) or not model_identity.strip():
        raise ValueError("model_identity must not be empty.")
    normalized = _normalize(components, healthy_min, degraded_min)
    total_weight = sum(item.weight for item in normalized)
    weighted_score = sum(item.score * item.weight for item in normalized) / total_weight
    component_status = _status(weighted_score, healthy_min, degraded_min)
    critical_components = tuple(item.name for item in normalized if item.status == CRITICAL)
    degraded_components = tuple(item.name for item in normalized if item.status == DEGRADED)
    score = HealthScore(
        weighted_score,
        component_status,
        len(normalized),
        critical_components,
        degraded_components,
    )
    payload = {
        "version": MODEL_HEALTH_VERSION,
        "model_identity": model_identity,
        "healthy_min": healthy_min,
        "degraded_min": degraded_min,
        "components": [
            (item.name, item.score, item.status, item.weight, item.source_identity)
            for item in normalized
        ],
        "score": (
            weighted_score,
            component_status,
            critical_components,
            degraded_components,
        ),
    }
    return ModelHealthReport(
        MODEL_HEALTH_VERSION,
        model_identity,
        normalized,
        healthy_min,
        degraded_min,
        score,
        _identity("model-health-report-", payload),
    )


def model_health_summary(report: ModelHealthReport) -> dict[str, object]:
    validation = validate_model_health_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "model_identity": report.model_identity,
        "weighted_score": report.score.weighted_score,
        "health_status": report.score.status,
        "component_count": report.score.component_count,
        "critical_components": report.score.active_critical_components,
        "degraded_components": report.score.active_degraded_components,
        "report_identity": report.report_identity,
    }


def model_health_component_names(report: ModelHealthReport) -> tuple[str, ...]:
    return tuple(item.name for item in report.components)


def model_health_component(
    report: ModelHealthReport,
    name: str,
) -> HealthComponent:
    for item in report.components:
        if item.name == name:
            return item
    raise KeyError(name)


def validate_model_health_report(
    report: ModelHealthReport,
) -> ModelHealthValidationResult:
    if not isinstance(report, ModelHealthReport):
        return ModelHealthValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != MODEL_HEALTH_VERSION:
        issues.append("INVALID_VERSION")
    if not report.model_identity.strip():
        issues.append("MISSING_MODEL_IDENTITY")
    if not math.isfinite(report.healthy_min) or not 0 < report.healthy_min <= 1:
        issues.append("INVALID_HEALTHY_MIN")
    if not math.isfinite(report.degraded_min) or not 0 <= report.degraded_min < report.healthy_min:
        issues.append("INVALID_DEGRADED_MIN")
    if not report.components:
        issues.append("NO_COMPONENTS")
    if len({item.name for item in report.components}) != len(report.components):
        issues.append("DUPLICATE_COMPONENTS")
    for item in report.components:
        try:
            _validate_component(item)
        except (TypeError, ValueError):
            issues.append("INVALID_COMPONENT")
            continue
        if item.status != _status(item.score, report.healthy_min, report.degraded_min):
            issues.append("COMPONENT_STATUS_MISMATCH")
    expected_weighted = (
        sum(item.score * item.weight for item in report.components)
        / sum(item.weight for item in report.components)
        if report.components else 0.0
    )
    if report.components and not math.isclose(
        report.score.weighted_score, expected_weighted, rel_tol=0.0, abs_tol=1e-12
    ):
        issues.append("WEIGHTED_SCORE_MISMATCH")
    if report.components:
        expected_status = _status(expected_weighted, report.healthy_min, report.degraded_min)
        if report.score.status != expected_status:
            issues.append("HEALTH_STATUS_MISMATCH")
        expected_critical = tuple(item.name for item in report.components if item.status == CRITICAL)
        expected_degraded = tuple(item.name for item in report.components if item.status == DEGRADED)
        if report.score.active_critical_components != expected_critical:
            issues.append("CRITICAL_COMPONENTS_MISMATCH")
        if report.score.active_degraded_components != expected_degraded:
            issues.append("DEGRADED_COMPONENTS_MISMATCH")
        if report.score.component_count != len(report.components):
            issues.append("COMPONENT_COUNT_MISMATCH")
    if not math.isfinite(report.score.weighted_score) or not 0 <= report.score.weighted_score <= 1:
        issues.append("INVALID_WEIGHTED_SCORE")
    if not report.report_identity.startswith("model-health-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return ModelHealthValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "MODEL_HEALTH_VERSION", "VALID", "INVALID", "HEALTHY", "DEGRADED",
    "CRITICAL", "VALID_STATUSES", "DEFAULT_HEALTHY_MIN",
    "DEFAULT_DEGRADED_MIN", "DEFAULT_WEIGHT", "HealthComponent",
    "HealthScore", "ModelHealthReport", "ModelHealthValidationResult",
    "build_model_health_report", "model_health_summary",
    "model_health_component_names", "model_health_component",
    "validate_model_health_report",
]
