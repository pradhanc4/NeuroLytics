from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence

from analytics.family_master import jodi_family_for, panel_family_for_panel
from analytics.jodi_ranking import OPERATIONAL_TOP_K, JodiRankedCandidate
from analytics.panel_family_prediction import rank_family_constrained_panels

SCORING_VERSION = "43.3.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class JointPanelCandidate:
    jodi: str
    jodi_probability: float
    first_panel: str
    first_panel_probability: float
    second_panel: str
    second_panel_probability: float
    joint_score: float
    rank: int
    jodi_family_id: str
    first_panel_family_id: str
    second_panel_family_id: str


@dataclass(frozen=True)
class JointSelectionResult:
    version: str
    target_date: date
    group_id: str
    top_k: int
    candidates: tuple[JointPanelCandidate, ...]
    selected: JointPanelCandidate | None
    status: str
    issues: tuple[str, ...]


def _probability(item) -> float:
    value = getattr(item, "probability", None)
    if value is None:
        raise ValueError("ranking candidate is missing probability")
    return float(value)


def _panel_items(panel_result: dict, label: str, limit: int):
    section = panel_result["digits"][label]
    return tuple(section["ranking"].candidates[:limit])


def _validate_jodi(candidate: JodiRankedCandidate) -> list[str]:
    issues = []
    if candidate.jodi_family_id != jodi_family_for(candidate.jodi):
        issues.append("JODI_FAMILY_MISMATCH")
    if candidate.first_panel_family_id != candidate.jodi[0]:
        issues.append("FIRST_PANEL_FAMILY_MISMATCH")
    if candidate.second_panel_family_id != candidate.jodi[1]:
        issues.append("SECOND_PANEL_FAMILY_MISMATCH")
    return issues


def _validate_panel(panel: str, expected_family: str) -> bool:
    return panel_family_for_panel(panel) == expected_family


def build_joint_selection(
    *,
    jodi_ranking,
    first_candidates: Sequence[dict],
    second_candidates: Sequence[dict],
    third_candidates: Sequence[dict],
    target_date: date,
    group_id: str,
    top_k: int = 10,
    panel_types: Sequence[str] | None = None,
) -> JointSelectionResult:
    if top_k not in OPERATIONAL_TOP_K:
        raise ValueError(f"operational top_k must be one of {OPERATIONAL_TOP_K}")
    issues = []
    pool = []

    for jodi_candidate in jodi_ranking.candidates:
        jodi_issues = _validate_jodi(jodi_candidate)
        if jodi_issues:
            issues.extend(f"{item}:{jodi_candidate.jodi}" for item in jodi_issues)
            continue

        panel_result = rank_family_constrained_panels(
            jodi=jodi_candidate.jodi,
            first_candidates=first_candidates,
            second_candidates=second_candidates,
            third_candidates=third_candidates,
            target_date=target_date,
            group_id=group_id + ":" + jodi_candidate.jodi,
            jodi_family_id=jodi_candidate.jodi_family_id,
            top_k=top_k,
            panel_types=panel_types,
        )
        first_items = _panel_items(panel_result, "first", top_k)
        second_items = _panel_items(panel_result, "second", top_k)

        for first in first_items:
            for second in second_items:
                first_panel = str(first.panel)
                second_panel = str(second.panel)
                if not _validate_panel(first_panel, jodi_candidate.jodi[0]):
                    issues.append("FIRST_PANEL_CROSS_FAMILY:" + first_panel)
                    continue
                if not _validate_panel(second_panel, jodi_candidate.jodi[1]):
                    issues.append("SECOND_PANEL_CROSS_FAMILY:" + second_panel)
                    continue

                score = (
                    _probability(jodi_candidate)
                    * _probability(first)
                    * _probability(second)
                )
                pool.append(
                    JointPanelCandidate(
                        jodi=jodi_candidate.jodi,
                        jodi_probability=_probability(jodi_candidate),
                        first_panel=first_panel,
                        first_panel_probability=_probability(first),
                        second_panel=second_panel,
                        second_panel_probability=_probability(second),
                        joint_score=score,
                        rank=0,
                        jodi_family_id=jodi_candidate.jodi_family_id,
                        first_panel_family_id=jodi_candidate.jodi[0],
                        second_panel_family_id=jodi_candidate.jodi[1],
                    )
                )

    ordered = sorted(
        pool,
        key=lambda item: (
            -item.joint_score,
            item.jodi,
            item.first_panel,
            item.second_panel,
        ),
    )
    ranked = tuple(
        JointPanelCandidate(
            jodi=item.jodi,
            jodi_probability=item.jodi_probability,
            first_panel=item.first_panel,
            first_panel_probability=item.first_panel_probability,
            second_panel=item.second_panel,
            second_panel_probability=item.second_panel_probability,
            joint_score=item.joint_score,
            rank=index,
            jodi_family_id=item.jodi_family_id,
            first_panel_family_id=item.first_panel_family_id,
            second_panel_family_id=item.second_panel_family_id,
        )
        for index, item in enumerate(ordered[:top_k], start=1)
    )
    status = VALID if ranked and not issues else (VALID if ranked else INVALID)
    return JointSelectionResult(
        version=SCORING_VERSION,
        target_date=target_date,
        group_id=group_id,
        top_k=top_k,
        candidates=ranked,
        selected=ranked[0] if ranked else None,
        status=status,
        issues=tuple(sorted(set(issues))),
    )


def operational_views(result: JointSelectionResult) -> dict[int, tuple[JointPanelCandidate, ...]]:
    return {k: result.candidates[: min(k, len(result.candidates))] for k in OPERATIONAL_TOP_K}


__all__ = [
    "SCORING_VERSION",
    "VALID",
    "INVALID",
    "JointPanelCandidate",
    "JointSelectionResult",
    "build_joint_selection",
    "operational_views",
]
