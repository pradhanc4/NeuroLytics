from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Sequence

from analytics.model_comparison import (
    ModelComparisonReport,
    ModelMetricComparison,
    validate_model_comparison_report,
)

CHAMPION_CHALLENGER_VERSION = "59.0.0"
VALID = "VALID"
INVALID = "INVALID"
CHAMPION = "CHAMPION"
CHALLENGER = "CHALLENGER"
ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
VALID_ROLES = (CHAMPION, CHALLENGER)
VALID_STATES = (ACTIVE, INACTIVE)


@dataclass(frozen=True)
class ModelRoleAssignment:
    model_identity: str
    role: str
    state: str = ACTIVE
    assignment_reason: str = ""
    source_identity: str = ""


@dataclass(frozen=True)
class ChampionChallengerEvidence:
    model_identity: str
    champion_identity: str
    health_score: float
    champion_health_score: float
    absolute_change_vs_champion: float
    relative_change_vs_champion: float | None
    comparison_source_identity: str


@dataclass(frozen=True)
class ChampionChallengerReport:
    version: str
    framework_id: str
    comparison_source_identity: str
    baseline_period: str
    comparison_period: str
    champion: ModelRoleAssignment
    challengers: tuple[ModelRoleAssignment, ...]
    evidence: tuple[ChampionChallengerEvidence, ...]
    eligible_models: tuple[str, ...]
    inactive_models: tuple[str, ...]
    report_identity: str


@dataclass(frozen=True)
class ChampionChallengerValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()


def _relative_change(baseline: float, comparison: float) -> float | None:
    if abs(baseline) <= 1e-12:
        return None
    return (comparison - baseline) / abs(baseline)


def _validate_assignment(item: ModelRoleAssignment) -> None:
    if not isinstance(item.model_identity, str) or not item.model_identity.strip():
        raise ValueError("model_identity must not be empty.")
    if item.role not in VALID_ROLES:
        raise ValueError("invalid model role.")
    if item.state not in VALID_STATES:
        raise ValueError("invalid model state.")
    if not isinstance(item.assignment_reason, str):
        raise ValueError("assignment_reason must be a string.")
    if not isinstance(item.source_identity, str):
        raise ValueError("source_identity must be a string.")


def _comparison_lookup(report: ModelComparisonReport) -> dict[str, ModelMetricComparison]:
    return {
        item.model_identity: item
        for item in report.metric_comparisons
        if item.metric == "health_score"
    }


def build_champion_challenger_report(
    framework_id: str,
    comparison_report: ModelComparisonReport,
    champion: ModelRoleAssignment,
    challengers: Sequence[ModelRoleAssignment],
) -> ChampionChallengerReport:
    if not isinstance(framework_id, str) or not framework_id.strip():
        raise ValueError("framework_id must not be empty.")
    if not isinstance(comparison_report, ModelComparisonReport):
        raise TypeError("comparison_report must be a ModelComparisonReport.")
    validation = validate_model_comparison_report(comparison_report)
    if not validation.is_valid:
        raise ValueError("invalid comparison report: " + ", ".join(validation.issues))
    _validate_assignment(champion)
    if champion.role != CHAMPION:
        raise ValueError("champion assignment must use CHAMPION role.")
    if champion.state != ACTIVE:
        raise ValueError("champion must be ACTIVE.")
    challenger_values = tuple(challengers)
    if not challenger_values:
        raise ValueError("at least one challenger is required.")
    for item in challenger_values:
        _validate_assignment(item)
        if item.role != CHALLENGER:
            raise ValueError("challenger assignment must use CHALLENGER role.")
    all_ids = (champion.model_identity,) + tuple(item.model_identity for item in challenger_values)
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("champion and challengers must have unique model identities.")
    if champion.model_identity not in comparison_report.common_models:
        raise ValueError("champion must be a common model in the comparison report.")
    for item in challenger_values:
        if item.model_identity not in comparison_report.common_models:
            raise ValueError("challenger must be a common model in the comparison report.")
        if item.state != ACTIVE:
            raise ValueError("challengers must be ACTIVE.")
    lookup = _comparison_lookup(comparison_report)
    champion_metric = lookup[champion.model_identity]
    evidence = []
    for item in challenger_values:
        metric = lookup[item.model_identity]
        evidence.append(
            ChampionChallengerEvidence(
                item.model_identity,
                champion.model_identity,
                metric.comparison_value,
                champion_metric.comparison_value,
                metric.comparison_value - champion_metric.comparison_value,
                _relative_change(champion_metric.comparison_value, metric.comparison_value),
                comparison_report.report_identity,
            )
        )
    eligible = tuple(sorted(all_ids))
    all_common = set(comparison_report.common_models)
    inactive = tuple(sorted(all_common - set(all_ids)))
    payload = {
        "version": CHAMPION_CHALLENGER_VERSION,
        "framework_id": framework_id,
        "comparison_source_identity": comparison_report.report_identity,
        "baseline_period": comparison_report.baseline_period,
        "comparison_period": comparison_report.comparison_period,
        "champion": (
            champion.model_identity, champion.role, champion.state,
            champion.assignment_reason, champion.source_identity,
        ),
        "challengers": [
            (item.model_identity, item.role, item.state, item.assignment_reason, item.source_identity)
            for item in challenger_values
        ],
        "evidence": [
            (
                item.model_identity, item.champion_identity, item.health_score,
                item.champion_health_score, item.absolute_change_vs_champion,
                item.relative_change_vs_champion, item.comparison_source_identity,
            )
            for item in evidence
        ],
        "eligible_models": eligible,
        "inactive_models": inactive,
    }
    return ChampionChallengerReport(
        CHAMPION_CHALLENGER_VERSION,
        framework_id,
        comparison_report.report_identity,
        comparison_report.baseline_period,
        comparison_report.comparison_period,
        champion,
        challenger_values,
        tuple(evidence),
        eligible,
        inactive,
        _identity("champion-challenger-report-", payload),
    )


def champion_challenger_summary(report: ChampionChallengerReport) -> dict[str, object]:
    validation = validate_champion_challenger_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "framework_id": report.framework_id,
        "champion": report.champion.model_identity,
        "challengers": tuple(item.model_identity for item in report.challengers),
        "eligible_models": report.eligible_models,
        "inactive_models": report.inactive_models,
        "baseline_period": report.baseline_period,
        "comparison_period": report.comparison_period,
        "evidence_count": len(report.evidence),
        "report_identity": report.report_identity,
    }


def champion_challenger_evidence(
    report: ChampionChallengerReport,
    model_identity: str | None = None,
) -> tuple[ChampionChallengerEvidence, ...]:
    if model_identity is None:
        return report.evidence
    return tuple(item for item in report.evidence if item.model_identity == model_identity)


def champion_challenger_models(report: ChampionChallengerReport) -> tuple[str, ...]:
    return (report.champion.model_identity,) + tuple(item.model_identity for item in report.challengers)


def validate_champion_challenger_report(
    report: ChampionChallengerReport,
) -> ChampionChallengerValidationResult:
    if not isinstance(report, ChampionChallengerReport):
        return ChampionChallengerValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != CHAMPION_CHALLENGER_VERSION:
        issues.append("INVALID_VERSION")
    if not report.framework_id.strip():
        issues.append("MISSING_FRAMEWORK_ID")
    if not report.comparison_source_identity.strip():
        issues.append("MISSING_COMPARISON_SOURCE")
    if not report.baseline_period.strip() or not report.comparison_period.strip():
        issues.append("MISSING_PERIOD")
    try:
        _validate_assignment(report.champion)
    except (TypeError, ValueError):
        issues.append("INVALID_CHAMPION_ASSIGNMENT")
    if report.champion.role != CHAMPION:
        issues.append("INVALID_CHAMPION_ROLE")
    if report.champion.state != ACTIVE:
        issues.append("INACTIVE_CHAMPION")
    if not report.challengers:
        issues.append("NO_CHALLENGERS")
    for item in report.challengers:
        try:
            _validate_assignment(item)
        except (TypeError, ValueError):
            issues.append("INVALID_CHALLENGER_ASSIGNMENT")
            continue
        if item.role != CHALLENGER:
            issues.append("INVALID_CHALLENGER_ROLE")
        if item.state != ACTIVE:
            issues.append("INACTIVE_CHALLENGER")
    ids = (report.champion.model_identity,) + tuple(item.model_identity for item in report.challengers)
    if len(set(ids)) != len(ids):
        issues.append("DUPLICATE_ROLE_MODELS")
    # The source report identity is preserved as immutable lineage.
    # Full source-object validation remains the responsibility of Phase 58.
    if not report.champion.model_identity.strip():
        issues.append("MISSING_CHAMPION_IDENTITY")
    common_from_evidence = {item.model_identity for item in report.evidence}
    if report.challengers and common_from_evidence != {item.model_identity for item in report.challengers}:
        issues.append("EVIDENCE_MODEL_MISMATCH")
    for item in report.evidence:
        if item.champion_identity != report.champion.model_identity:
            issues.append("EVIDENCE_CHAMPION_MISMATCH")
        if not math.isfinite(item.health_score) or not 0 <= item.health_score <= 1:
            issues.append("INVALID_EVIDENCE_SCORE")
        if not math.isfinite(item.champion_health_score) or not 0 <= item.champion_health_score <= 1:
            issues.append("INVALID_CHAMPION_SCORE")
        if not math.isfinite(item.absolute_change_vs_champion):
            issues.append("NONFINITE_EVIDENCE_CHANGE")
        expected_change = item.health_score - item.champion_health_score
        if not math.isclose(
            item.absolute_change_vs_champion, expected_change, rel_tol=0.0, abs_tol=1e-12
        ):
            issues.append("EVIDENCE_CHANGE_MISMATCH")
        if item.relative_change_vs_champion is not None and not math.isfinite(item.relative_change_vs_champion):
            issues.append("NONFINITE_EVIDENCE_RELATIVE_CHANGE")
        expected_relative = _relative_change(item.champion_health_score, item.health_score)
        if item.relative_change_vs_champion is None:
            if expected_relative is not None:
                issues.append("EVIDENCE_RELATIVE_MISMATCH")
        elif expected_relative is None or not math.isclose(
            item.relative_change_vs_champion, expected_relative, rel_tol=0.0, abs_tol=1e-12
        ):
            issues.append("EVIDENCE_RELATIVE_MISMATCH")
        if not item.comparison_source_identity.strip():
            issues.append("MISSING_EVIDENCE_SOURCE")
    expected_ids = tuple(sorted(ids))
    if report.eligible_models != expected_ids:
        issues.append("ELIGIBLE_MODELS_MISMATCH")
    if set(report.inactive_models) & set(ids):
        issues.append("ACTIVE_IN_INACTIVE_COLLECTION")
    if len(set(report.inactive_models)) != len(report.inactive_models):
        issues.append("DUPLICATE_INACTIVE_MODELS")
    if not report.report_identity.startswith("champion-challenger-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return ChampionChallengerValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


__all__ = [
    "CHAMPION_CHALLENGER_VERSION", "VALID", "INVALID", "CHAMPION", "CHALLENGER",
    "ACTIVE", "INACTIVE", "VALID_ROLES", "VALID_STATES", "ModelRoleAssignment",
    "ChampionChallengerEvidence", "ChampionChallengerReport",
    "ChampionChallengerValidationResult", "build_champion_challenger_report",
    "champion_challenger_summary", "champion_challenger_evidence",
    "champion_challenger_models", "validate_champion_challenger_report",
]
