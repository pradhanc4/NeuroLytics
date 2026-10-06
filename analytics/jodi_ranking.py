from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from analytics.learning_to_rank_model import LearningToRankPrediction

JODI_RANKING_VERSION = "43.1.0"
OPERATIONAL_TOP_K = (1, 2, 3, 5, 10)
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class JodiCandidateInput:
    jodi: str
    jodi_family_id: str | None = None
    panel_family_id: str | None = None
    first_panel_family_id: str | None = None
    second_panel_family_id: str | None = None


@dataclass(frozen=True)
class JodiRankedCandidate:
    jodi: str
    probability: float
    score: float
    rank: int
    jodi_family_id: str | None
    panel_family_id: str | None
    first_panel_family_id: str | None = None
    second_panel_family_id: str | None = None


@dataclass(frozen=True)
class JodiRankingObservation:
    group_id: str
    target_date: date
    target_position: str
    candidates: tuple[JodiRankedCandidate, ...]
    actual_jodi: str | None
    top_probability: float
    probability_margin: float
    ranking_identity: str


@dataclass(frozen=True)
class JodiRankingReport:
    version: str
    source_model_identities: tuple[str, ...]
    observations: tuple[JodiRankingObservation, ...]
    top_k: int
    report_identity: str


@dataclass(frozen=True)
class JodiRankingValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _jodi(value: str) -> str:
    value = str(value).strip()
    if len(value) != 2 or not value.isdigit():
        raise ValueError("jodi must be a two-digit string.")
    return value


def _probabilities(prediction: LearningToRankPrediction) -> dict[int, float]:
    if len(prediction.candidate_digits) != 10 or len(prediction.probabilities) != 10:
        raise ValueError("each position prediction must contain ten digits and probabilities.")
    result = {
        int(digit): float(probability)
        for digit, probability in zip(prediction.candidate_digits, prediction.probabilities)
    }
    if set(result) != set(range(10)):
        raise ValueError("position prediction must contain digits 0 through 9.")
    if any(not math.isfinite(value) or value < 0 for value in result.values()):
        raise ValueError("position probabilities must be finite and non-negative.")
    total = sum(result.values())
    if total <= 0 or abs(total - 1.0) > 1e-6:
        raise ValueError("position probabilities must sum to one.")
    return result


def _identity(prefix: str, payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return prefix + hashlib.sha256(encoded).hexdigest()


def _validate_top_k(top_k: int) -> int:
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise TypeError("top_k must be an integer.")
    if top_k < 1:
        raise ValueError("top_k must be positive.")
    return min(top_k, 100)


def rank_jodis(
    first_prediction: LearningToRankPrediction,
    second_prediction: LearningToRankPrediction,
    candidates: Sequence[JodiCandidateInput],
    group_id: str,
    target_date: date,
    target_position: str = "jodi",
    actual_jodi: str | None = None,
    top_k: int = 20,
) -> JodiRankingObservation:
    _validate_top_k(top_k)
    if not group_id.strip():
        raise ValueError("group_id must be non-empty.")
    if not isinstance(target_date, date):
        raise TypeError("target_date must be a date.")
    if not target_position.strip():
        raise ValueError("target_position must be non-empty.")

    position_probs = (
        _probabilities(first_prediction),
        _probabilities(second_prediction),
    )
    materialized = tuple(candidates)
    if not materialized:
        raise ValueError("at least one Jodi candidate is required.")

    seen: set[str] = set()
    scored: list[tuple[JodiCandidateInput, float]] = []
    for candidate in materialized:
        jodi = _jodi(candidate.jodi)
        if jodi in seen:
            raise ValueError("Jodi candidates must be unique.")
        seen.add(jodi)
        probability = position_probs[0][int(jodi[0])] * position_probs[1][int(jodi[1])]
        scored.append((candidate, probability))

    total = sum(probability for _, probability in scored)
    if total <= 0:
        raise ValueError("Jodi candidate probabilities have zero mass.")

    ordered = sorted(scored, key=lambda item: (-item[1] / total, item[0].jodi))
    visible = ordered[:min(top_k, len(ordered))]
    ranked = tuple(
        JodiRankedCandidate(
            jodi=_jodi(candidate.jodi),
            probability=probability / total,
            score=(probability / total) * 100.0,
            rank=index,
            jodi_family_id=candidate.jodi_family_id,
            panel_family_id=candidate.panel_family_id,
            first_panel_family_id=candidate.first_panel_family_id,
            second_panel_family_id=candidate.second_panel_family_id,
        )
        for index, (candidate, probability) in enumerate(visible, start=1)
    )
    margin = (
        ranked[0].probability - ranked[1].probability
        if len(ranked) > 1
        else ranked[0].probability
    )
    identity = _identity(
        "jodi-ranking-",
        (
            JODI_RANKING_VERSION,
            group_id,
            target_date,
            target_position,
            tuple((item.jodi, item.probability, item.rank) for item in ranked),
            first_prediction.group_id,
            second_prediction.group_id,
        ),
    )
    return JodiRankingObservation(
        group_id,
        target_date,
        target_position,
        ranked,
        _jodi(actual_jodi) if actual_jodi is not None else None,
        ranked[0].probability,
        margin,
        identity,
    )


def rank_jodis_from_predictions(
    predictions: Sequence[LearningToRankPrediction],
    candidates: Sequence[JodiCandidateInput],
    group_id: str,
    target_date: date,
    target_position: str = "jodi",
    actual_jodi: str | None = None,
    top_k: int = 20,
) -> JodiRankingObservation:
    if len(predictions) != 2:
        raise ValueError("Jodi ranking requires exactly two position predictions.")
    return rank_jodis(
        predictions[0],
        predictions[1],
        candidates,
        group_id,
        target_date,
        target_position,
        actual_jodi,
        top_k,
    )


def build_jodi_ranking_report(
    observations: Sequence[JodiRankingObservation],
    source_model_identities: Sequence[str],
    top_k: int = 20,
) -> JodiRankingReport:
    _validate_top_k(top_k)
    materialized = tuple(observations)
    identities = tuple(source_model_identities)
    if not materialized:
        raise ValueError("at least one Jodi ranking observation is required.")
    if len(identities) != 2 or any(not value for value in identities):
        raise ValueError("exactly two non-empty source model identities are required.")
    if len({item.group_id for item in materialized}) != len(materialized):
        raise ValueError("observation group_id values must be unique.")
    return JodiRankingReport(
        JODI_RANKING_VERSION,
        identities,
        materialized,
        top_k,
        _identity(
            "jodi-ranking-report-",
            {
                "version": JODI_RANKING_VERSION,
                "models": identities,
                "observations": [item.ranking_identity for item in materialized],
                "top_k": top_k,
            },
        ),
    )


def validate_jodi_ranking(
    ranking: JodiRankingObservation,
) -> JodiRankingValidationResult:
    if not isinstance(ranking, JodiRankingObservation):
        return JodiRankingValidationResult(INVALID, ("INVALID_RANKING_TYPE",))
    issues: list[str] = []
    if not ranking.group_id.strip():
        issues.append("MISSING_GROUP_ID")
    if not isinstance(ranking.target_date, date):
        issues.append("INVALID_TARGET_DATE")
    if not ranking.candidates:
        issues.append("NO_CANDIDATES")
    if [item.rank for item in ranking.candidates] != list(range(1, len(ranking.candidates) + 1)):
        issues.append("INVALID_RANKS")
    jodis = [item.jodi for item in ranking.candidates]
    if len(set(jodis)) != len(jodis):
        issues.append("DUPLICATE_JODIS")
    for item in ranking.candidates:
        try:
            _jodi(item.jodi)
        except ValueError:
            issues.append("INVALID_JODI")
        if not math.isfinite(item.probability) or not 0 <= item.probability <= 1:
            issues.append("INVALID_PROBABILITY")
        if not math.isfinite(item.score) or not 0 <= item.score <= 100:
            issues.append("INVALID_SCORE")
    if not math.isfinite(ranking.top_probability):
        issues.append("INVALID_TOP_PROBABILITY")
    if not math.isfinite(ranking.probability_margin):
        issues.append("INVALID_MARGIN")
    if ranking.actual_jodi is not None:
        try:
            _jodi(ranking.actual_jodi)
        except ValueError:
            issues.append("INVALID_ACTUAL_JODI")
    if not ranking.ranking_identity.startswith("jodi-ranking-"):
        issues.append("INVALID_RANKING_IDENTITY")
    return JodiRankingValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def validate_jodi_ranking_report(
    report: JodiRankingReport,
) -> JodiRankingValidationResult:
    if not isinstance(report, JodiRankingReport):
        return JodiRankingValidationResult(INVALID, ("INVALID_REPORT_TYPE",))
    issues: list[str] = []
    if report.version != JODI_RANKING_VERSION:
        issues.append("INVALID_VERSION")
    if len(report.source_model_identities) != 2:
        issues.append("INVALID_SOURCE_MODEL_COUNT")
    if not report.observations:
        issues.append("NO_OBSERVATIONS")
    if report.top_k < 1:
        issues.append("INVALID_TOP_K")
    if len({item.group_id for item in report.observations}) != len(report.observations):
        issues.append("DUPLICATE_GROUP_ID")
    for observation in report.observations:
        if not validate_jodi_ranking(observation).is_valid:
            issues.append("INVALID_OBSERVATION")
    if not report.report_identity.startswith("jodi-ranking-report-"):
        issues.append("INVALID_REPORT_IDENTITY")
    return JodiRankingValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def jodi_values(ranking: JodiRankingObservation) -> tuple[str, ...]:
    return tuple(item.jodi for item in ranking.candidates)


def _b1_prediction(
    candidates: Sequence[dict],
    *,
    group_id: str,
    target_date: date,
) -> LearningToRankPrediction:
    """Adapt B.1 digit-candidate dictionaries to the ranking contract."""
    # A classifier trained on a small chronological warm-up window may not
    # have observed every digit yet.  Missing classes are valid zero-probability
    # candidates; the authoritative Jodi universe still contains all 0-9 digits.
    if not candidates or len(candidates) > 10:
        raise ValueError("B.1 Jodi prediction must contain between one and ten digits.")
    by_digit = {int(item["digit"]): item for item in candidates}
    if any(digit < 0 or digit > 9 for digit in by_digit):
        raise ValueError("B.1 Jodi prediction contains an invalid digit.")
    if len(by_digit) != len(candidates):
        raise ValueError("B.1 Jodi prediction contains duplicate digits.")
    ordered = sorted(
        ((digit, float(item["probability"])) for digit, item in by_digit.items()),
        key=lambda item: (-item[1], item[0]),
    )
    probabilities = [0.0] * 10
    for digit, probability in ordered:
        if probability < 0 or not math.isfinite(probability):
            raise ValueError("B.1 probabilities must be finite and non-negative.")
        probabilities[digit] = probability
    total = sum(probabilities)
    if total <= 0:
        raise ValueError("B.1 probabilities must contain positive mass.")
    probabilities = [value / total for value in probabilities]
    ranked = sorted(range(10), key=lambda digit: (-probabilities[digit], digit))
    return LearningToRankPrediction(
        group_id=group_id,
        target_date=target_date,
        candidate_digits=tuple(range(10)),
        scores=tuple(probabilities),
        probabilities=tuple(probabilities),
        ranks=tuple(ranked.index(digit) + 1 for digit in range(10)),
        actual_digit=None,
        top_candidate=ranked[0],
        top_k_candidates=tuple(ranked[:3]),
    )


def build_authoritative_jodi_candidates() -> tuple[JodiCandidateInput, ...]:
    """Build the complete 00-99 Jodi universe with authoritative families."""
    from analytics.family_master import load_family_master

    master = load_family_master()
    jodi_lookup = {
        jodi: family_id
        for family_id, members in master["jodi_families"].items()
        for jodi in members
    }
    return tuple(
        JodiCandidateInput(
            jodi=f"{value:02d}",
            jodi_family_id=jodi_lookup[f"{value:02d}"],
            first_panel_family_id=str(value // 10),
            second_panel_family_id=str(value % 10),
        )
        for value in range(100)
    )


def rank_jodis_from_b1_outputs(
    first_candidates: Sequence[dict],
    second_candidates: Sequence[dict],
    *,
    group_id: str,
    target_date: date,
    actual_jodi: str | None = None,
    top_k: int = 10,
) -> JodiRankingObservation:
    """Rank all 100 Jodis from independent B.1 digit probabilities.

    The candidate universe is authoritative and exhaustive: every 00-99
    Jodi receives its exact Jodi-family mapping and both digit-level panel
    family mappings before ranking. No panel is generated at this stage.
    """
    if top_k not in OPERATIONAL_TOP_K and top_k != 100:
        raise ValueError(
            f"operational top_k must be one of {OPERATIONAL_TOP_K} or 100."
        )
    first = _b1_prediction(first_candidates, group_id=group_id + ":first", target_date=target_date)
    second = _b1_prediction(second_candidates, group_id=group_id + ":second", target_date=target_date)
    return rank_jodis(
        first,
        second,
        build_authoritative_jodi_candidates(),
        group_id=group_id,
        target_date=target_date,
        target_position="jodi_b2",
        actual_jodi=actual_jodi,
        top_k=top_k,
    )


def jodi_top_k_views(ranking: JodiRankingObservation) -> dict[int, tuple[JodiRankedCandidate, ...]]:
    """Return operational Top-1/2/3/5/10 views from one ranked universe."""
    return {
        k: ranking.candidates[: min(k, len(ranking.candidates))]
        for k in OPERATIONAL_TOP_K
    }


def panel_candidates_for_jodi(
    jodi: str,
    panel_types: Sequence[str] | None = None,
) -> dict[str, object]:
    """Return only panels belonging to each predicted Jodi digit's family."""
    from analytics.family_master import (
        jodi_family_for,
        panel_family_for_digit,
        panels_for_digit,
    )

    value = _jodi(jodi)
    first_digit, second_digit = value[0], value[1]
    first_family = panel_family_for_digit(first_digit)
    second_family = panel_family_for_digit(second_digit)
    first_panels = panels_for_digit(first_digit, panel_types)
    second_panels = panels_for_digit(second_digit, panel_types)
    return {
        "jodi": value,
        "jodi_family_id": jodi_family_for(value),
        "first_digit": {
            "digit": first_digit,
            "panel_family_id": first_family,
            "panels": first_panels,
        },
        "second_digit": {
            "digit": second_digit,
            "panel_family_id": second_family,
            "panels": second_panels,
        },
        "hard_constraint": True,
    }


def validate_jodi_family_constraint(ranking: JodiRankingObservation) -> JodiRankingValidationResult:
    """Verify every ranked Jodi carries the authoritative family constraints."""
    from analytics.family_master import load_family_master

    master = load_family_master()
    jodi_lookup = {
        jodi: family_id
        for family_id, members in master["jodi_families"].items()
        for jodi in members
    }
    issues: list[str] = []
    for candidate in ranking.candidates:
        expected_jodi_family = jodi_lookup[candidate.jodi]
        expected_first_family = candidate.jodi[0]
        expected_second_family = candidate.jodi[1]
        if candidate.jodi_family_id != expected_jodi_family:
            issues.append(f"JODI_FAMILY_MISMATCH:{candidate.jodi}")
        if candidate.first_panel_family_id != expected_first_family:
            issues.append(f"FIRST_PANEL_FAMILY_MISMATCH:{candidate.jodi}")
        if candidate.second_panel_family_id != expected_second_family:
            issues.append(f"SECOND_PANEL_FAMILY_MISMATCH:{candidate.jodi}")
    return JodiRankingValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def top_jodi(ranking: JodiRankingObservation) -> JodiRankedCandidate:
    if not ranking.candidates:
        raise ValueError("ranking contains no Jodis.")
    return ranking.candidates[0]


def jodi_ranking_summary(report: JodiRankingReport) -> dict[str, object]:
    validation = validate_jodi_ranking_report(report)
    return {
        "status": validation.status,
        "version": report.version,
        "observations": len(report.observations),
        "top_k": report.top_k,
        "source_model_identities": report.source_model_identities,
        "report_identity": report.report_identity,
    }


__all__ = [
    "JODI_RANKING_VERSION",
    "OPERATIONAL_TOP_K",
    "VALID",
    "INVALID",
    "JodiCandidateInput",
    "JodiRankedCandidate",
    "JodiRankingObservation",
    "JodiRankingReport",
    "JodiRankingValidationResult",
    "rank_jodis",
    "rank_jodis_from_predictions",
    "build_jodi_ranking_report",
    "validate_jodi_ranking",
    "validate_jodi_ranking_report",
    "jodi_values",
    "top_jodi",
    "jodi_ranking_summary",
    "build_authoritative_jodi_candidates",
    "rank_jodis_from_b1_outputs",
    "jodi_top_k_views",
    "validate_jodi_family_constraint",
    "panel_candidates_for_jodi",
]
