from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from analytics.learning_to_rank_model import LearningToRankPrediction

PANEL_RANKING_VERSION = "42.0.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class PanelCandidateInput:
    panel: str
    panel_family_id: str | None = None
    jodi_family_id: str | None = None


@dataclass(frozen=True)
class PanelRankedCandidate:
    panel: str
    probability: float
    score: float
    rank: int
    panel_family_id: str | None
    jodi_family_id: str | None


@dataclass(frozen=True)
class PanelRankingObservation:
    group_id: str
    target_date: date
    target_position: str
    candidates: tuple[PanelRankedCandidate, ...]
    actual_panel: str | None
    top_probability: float
    probability_margin: float
    ranking_identity: str
@dataclass(frozen=True)
class PanelRankingReport:
    version: str
    source_model_identities: tuple[str, ...]
    observations: tuple[PanelRankingObservation, ...]
    top_k: int
    report_identity: str


@dataclass(frozen=True)
class PanelRankingValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _panel(value: str) -> str:
    value = str(value).strip()
    if len(value) != 3 or not value.isdigit():
        raise ValueError("panel must be a three-digit string.")
    return value


def _probabilities(prediction: LearningToRankPrediction) -> dict[int, float]:
    if len(prediction.candidate_digits) != 10:
        raise ValueError("each position prediction must contain ten digits.")
    if len(prediction.probabilities) != 10:
        raise ValueError("each position prediction must contain ten probabilities.")
    result = {
        int(digit): float(probability)
        for digit, probability in zip(
            prediction.candidate_digits, prediction.probabilities
        )
    }
    if set(result) != set(range(10)):
        raise ValueError("position prediction must contain digits 0 through 9.")
    total = sum(result.values())
    if total <= 0 or abs(total - 1.0) > 1e-6:
        raise ValueError("position probabilities must sum to one.")
    if any(not math.isfinite(value) or value < 0 for value in result.values()):
        raise ValueError("position probabilities must be finite and non-negative.")
    return result


def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()


def _validate_top_k(top_k: int) -> int:
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k must be an integer.")
    if top_k < 1:
        raise ValueError("top_k must be positive.")
    return min(top_k, 10_000)
def rank_panels(
    first_prediction: LearningToRankPrediction,
    second_prediction: LearningToRankPrediction,
    third_prediction: LearningToRankPrediction,
    candidates: Sequence[PanelCandidateInput],
    group_id: str,
    target_date: date,
    target_position: str = "panel",
    actual_panel: str | None = None,
    top_k: int = 20,
) -> PanelRankingObservation:
    _validate_top_k(top_k)
    if not group_id.strip():
        raise ValueError("group_id must be non-empty.")
    if not isinstance(target_date, date):
        raise TypeError("target_date must be a date.")
    if not target_position.strip():
        raise ValueError("target_position must be non-empty.")
    position_predictions = (
        first_prediction,
        second_prediction,
        third_prediction,
    )
    position_probs = [
        _probabilities(prediction) for prediction in position_predictions
    ]
    materialized = tuple(candidates)
    if not materialized:
        raise ValueError("at least one panel candidate is required.")
    seen: set[str] = set()
    scored: list[tuple[PanelCandidateInput, float]] = []
    for candidate in materialized:
        panel = _panel(candidate.panel)
        if panel in seen:
            raise ValueError("panel candidates must be unique.")
        seen.add(panel)
        probability = (
            position_probs[0][int(panel[0])]
            * position_probs[1][int(panel[1])]
            * position_probs[2][int(panel[2])]
        )
        scored.append((candidate, probability))
    total = sum(probability for _, probability in scored)
    if total <= 0:
        raise ValueError("panel candidate probabilities have zero mass.")
    ordered = sorted(
        scored,
        key=lambda item: (-item[1] / total, item[0].panel),
    )
    visible = ordered[: min(top_k, len(ordered))]
    ranked = tuple(
        PanelRankedCandidate(
            panel=_panel(candidate.panel),
            probability=probability / total,
            score=(probability / total) * 100.0,
            rank=index,
            panel_family_id=candidate.panel_family_id,
            jodi_family_id=candidate.jodi_family_id,
        )
        for index, (candidate, probability) in enumerate(visible, start=1)
    )
    margin = (
        ranked[0].probability - ranked[1].probability
        if len(ranked) > 1
        else ranked[0].probability
    )
    identity = _identity(
        "panel-ranking-",
        (
            PANEL_RANKING_VERSION,
            group_id,
            target_date,
            target_position,
            tuple((item.panel, item.probability, item.rank) for item in ranked),
            *(prediction.group_id for prediction in position_predictions),
        ),
    )
    return PanelRankingObservation(
        group_id=group_id,
        target_date=target_date,
        target_position=target_position,
        candidates=ranked,
        actual_panel=_panel(actual_panel) if actual_panel is not None else None,
        top_probability=ranked[0].probability,
        probability_margin=margin,
        ranking_identity=identity,
    )
def rank_panels_from_predictions(
    predictions: Sequence[LearningToRankPrediction],
    candidates: Sequence[PanelCandidateInput],
    group_id: str,
    target_date: date,
    target_position: str = "panel",
    actual_panel: str | None = None,
    top_k: int = 20,
) -> PanelRankingObservation:
    if len(predictions) != 3:
        raise ValueError("panel ranking requires exactly three position predictions.")
    return rank_panels(
        predictions[0],
        predictions[1],
        predictions[2],
        candidates,
        group_id,
        target_date,
        target_position,
        actual_panel,
        top_k,
    )


def build_panel_ranking_report(
    observations: Sequence[PanelRankingObservation],
    source_model_identities: Sequence[str],
    top_k: int = 20,
) -> PanelRankingReport:
    _validate_top_k(top_k)
    materialized = tuple(observations)
    identities = tuple(source_model_identities)
    if not materialized:
        raise ValueError("at least one panel ranking observation is required.")
    if len(identities) != 3 or any(not value for value in identities):
        raise ValueError("exactly three non-empty source model identities are required.")
    if len({item.group_id for item in materialized}) != len(materialized):
        raise ValueError("observation group_id values must be unique.")
    payload = {
        "version": PANEL_RANKING_VERSION,
        "models": identities,
        "observations": [item.ranking_identity for item in materialized],
        "top_k": top_k,
    }
    return PanelRankingReport(
        PANEL_RANKING_VERSION,
        identities,
        materialized,
        top_k,
        _identity("panel-ranking-report-", payload),
    )


def validate_panel_ranking(
    ranking: PanelRankingObservation,
) -> PanelRankingValidationResult:
    if not isinstance(ranking, PanelRankingObservation):
        return PanelRankingValidationResult(INVALID, ("INVALID_RANKING_TYPE",))
    issues: list[str] = []
    if not ranking.group_id.strip():
        issues.append("MISSING_GROUP_ID")
    if not isinstance(ranking.target_date, date):
        issues.append("INVALID_TARGET_DATE")
    if not ranking.candidates:
        issues.append("NO_CANDIDATES")
    expected = list(range(1, len(ranking.candidates) + 1))
    if [item.rank for item in ranking.candidates] != expected:
        issues.append("INVALID_RANKS")
    panels = [item.panel for item in ranking.candidates]
    if len(set(panels)) != len(panels):
        issues.append("DUPLICATE_PANELS")
    for item in ranking.candidates:
        try:
            _panel(item.panel)
        except ValueError:
            issues.append("INVALID_PANEL")
        if not math.isfinite(item.probability) or not 0 <= item.probability <= 1:
            issues.append("INVALID_PROBABILITY")
        if not math.isfinite(item.score) or not 0 <= item.score <= 100:
            issues.append("INVALID_SCORE")
    if not math.isfinite(ranking.top_probability):
        issues.append("INVALID_TOP_PROBABILITY")
    if not math.isfinite(ranking.probability_margin):
        issues.append("INVALID_MARGIN")
    if ranking.actual_panel is not None:
        try:
            _panel(ranking.actual_panel)
        except ValueError:
            issues.append("INVALID_ACTUAL_PANEL")
    if not ranking.ranking_identity.startswith("panel-ranking-"):
        issues.append("INVALID_RANKING_IDENTITY")
    return PanelRankingValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )
def validate_panel_ranking_report(
    report: PanelRankingReport,
) -> PanelRankingValidationResult:
    if not isinstance(report, PanelRankingReport):
        return PanelRankingValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != PANEL_RANKING_VERSION:
        issues.append("INVALID_VERSION")
    if len(report.source_model_identities) != 3:
        issues.append("INVALID_SOURCE_MODEL_COUNT")
    if not report.observations:
        issues.append("NO_OBSERVATIONS")
    if report.top_k < 1:
        issues.append("INVALID_TOP_K")
    group_ids = [item.group_id for item in report.observations]
    if len(set(group_ids)) != len(group_ids):
        issues.append("DUPLICATE_GROUP_ID")
    for observation in report.observations:
        validation = validate_panel_ranking(observation)
        if not validation.is_valid:
            issues.append("INVALID_OBSERVATION")
    if not report.report_identity.startswith("panel-ranking-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return PanelRankingValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def panel_values(ranking: PanelRankingObservation) -> tuple[str, ...]:
    return tuple(item.panel for item in ranking.candidates)


def top_panel(ranking: PanelRankingObservation) -> PanelRankedCandidate:
    if not ranking.candidates:
        raise ValueError("ranking contains no panels.")
    return ranking.candidates[0]


def panel_ranking_summary(report: PanelRankingReport) -> dict[str, object]:
    validation = validate_panel_ranking_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "observations": len(report.observations),
        "top_k": report.top_k,
        "source_model_identities": report.source_model_identities,
        "report_identity": report.report_identity,
    }


__all__ = [
    "PANEL_RANKING_VERSION",
    "VALID",
    "INVALID",
    "PanelCandidateInput",
    "PanelRankedCandidate",
    "PanelRankingObservation",
    "PanelRankingReport",
    "PanelRankingValidationResult",
    "rank_panels",
    "rank_panels_from_predictions",
    "build_panel_ranking_report",
    "validate_panel_ranking",
    "validate_panel_ranking_report",
    "panel_values",
    "top_panel",
    "panel_ranking_summary",
]