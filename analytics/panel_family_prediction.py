from __future__ import annotations

from datetime import date
from typing import Sequence

from analytics.family_master import (
    panel_family_for_digit,
    panel_family_for_panel,
    panels_for_digit,
)
from analytics.learning_to_rank_model import LearningToRankPrediction
OPERATIONAL_TOP_K = (1, 2, 3, 5, 10)

from analytics.panel_ranking import (
    PanelCandidateInput,
    PanelRankingObservation,
    rank_panels_from_predictions,
    validate_panel_ranking,
)

PANEL_FAMILY_CONSTRAINED_VERSION = "43.2.0"


def _prediction_from_candidates(
    candidates: Sequence[dict],
    *,
    group_id: str,
    target_date: date,
) -> LearningToRankPrediction:
    if len(candidates) != 10:
        raise ValueError("Panel digit prediction must contain exactly ten digits.")
    probabilities = {int(item["digit"]): float(item["probability"]) for item in candidates}
    if set(probabilities) != set(range(10)):
        raise ValueError("Panel digit prediction must contain digits 0 through 9.")
    total = sum(probabilities.values())
    if total <= 0:
        raise ValueError("Panel digit prediction has zero probability mass.")
    normalized = tuple(probabilities[digit] / total for digit in range(10))
    ranked = sorted(range(10), key=lambda digit: (-normalized[digit], digit))
    return LearningToRankPrediction(
        group_id=group_id,
        target_date=target_date,
        candidate_digits=tuple(range(10)),
        scores=normalized,
        probabilities=normalized,
        ranks=tuple(ranked.index(digit) + 1 for digit in range(10)),
        actual_digit=None,
        top_candidate=ranked[0],
        top_k_candidates=tuple(ranked[:3]),
    )


def family_constrained_panel_candidates(
    jodi_digit: str | int,
    *,
    jodi_family_id: str | None = None,
    panel_types: Sequence[str] | None = None,
) -> tuple[PanelCandidateInput, ...]:
    """Return only authoritative panels belonging to the Jodi digit family."""
    digit = str(jodi_digit).strip()
    if len(digit) != 1 or not digit.isdigit():
        raise ValueError("Jodi digit must be one digit from 0 through 9.")
    expected_family = panel_family_for_digit(digit)
    if jodi_family_id is not None and not str(jodi_family_id).strip():
        raise ValueError("jodi_family_id cannot be empty.")
    panels = panels_for_digit(digit, panel_types)
    result = tuple(
        PanelCandidateInput(
            panel=panel,
            panel_family_id=expected_family,
            jodi_family_id=jodi_family_id,
        )
        for panel in panels
    )
    for candidate in result:
        if panel_family_for_panel(candidate.panel) != expected_family:
            raise ValueError(
                f"Panel family constraint violation: {candidate.panel} "
                f"does not belong to family {expected_family}."
            )
    return result


def rank_family_constrained_panels(
    *,
    jodi: str,
    first_candidates: Sequence[dict],
    second_candidates: Sequence[dict],
    third_candidates: Sequence[dict],
    target_date: date,
    group_id: str,
    jodi_family_id: str | None = None,
    top_k: int = 10,
    panel_types: Sequence[str] | None = None,
) -> dict[str, object]:
    """Rank panels separately for each Jodi digit using hard family constraints."""
    jodi = str(jodi).strip()
    if len(jodi) != 2 or not jodi.isdigit():
        raise ValueError("jodi must contain exactly two digits.")
    if top_k not in OPERATIONAL_TOP_K:
        raise ValueError(
            f"operational top_k must be one of {OPERATIONAL_TOP_K}."
        )

    predictions = (
        _prediction_from_candidates(first_candidates, group_id=group_id + ":p1", target_date=target_date),
        _prediction_from_candidates(second_candidates, group_id=group_id + ":p2", target_date=target_date),
        _prediction_from_candidates(third_candidates, group_id=group_id + ":p3", target_date=target_date),
    )

    output: dict[str, object] = {
        "version": PANEL_FAMILY_CONSTRAINED_VERSION,
        "jodi": jodi,
        "jodi_family_id": jodi_family_id,
        "hard_family_constraint": True,
        "operational_top_k": list(OPERATIONAL_TOP_K),
        "digits": {},
    }

    for label, digit in (("first", jodi[0]), ("second", jodi[1])):
        candidates = family_constrained_panel_candidates(
            digit,
            jodi_family_id=jodi_family_id,
            panel_types=panel_types,
        )
        ranking = rank_panels_from_predictions(
            predictions,
            candidates,
            group_id=group_id + f":{label}:{digit}",
            target_date=target_date,
            target_position=f"panel_family_{digit}",
            top_k=top_k,
        )
        validation = validate_panel_ranking(ranking)
        if not validation.is_valid:
            raise ValueError(
                "Panel ranking validation failed: "
                + ", ".join(validation.issues)
            )
        if any(
            panel_family_for_panel(item.panel) != digit
            for item in ranking.candidates
        ):
            raise ValueError(
                f"Hard panel-family constraint failed for Jodi digit {digit}."
            )
        output["digits"][label] = {
            "digit": digit,
            "panel_family_id": panel_family_for_digit(digit),
            "candidate_count": len(candidates),
            "ranking": ranking,
            "candidates": ranking.candidates,
            "top_k": ranking.candidates[:top_k],
        }

    return output


__all__ = [
    "PANEL_FAMILY_CONSTRAINED_VERSION",
    "family_constrained_panel_candidates",
    "rank_family_constrained_panels",
]
