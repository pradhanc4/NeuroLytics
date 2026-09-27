from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.temporal_position_change_classification import (
    CLASSIFICATION_MISSING,
    CLASSIFICATION_UNCHANGED,
    TemporalPositionChangeClassification,
    TemporalPositionChangeClassificationResult,
)


MOVEMENT_DIRECTIONS: tuple[str, ...] = (
    "INCREASE",
    "DECREASE",
    "UNCHANGED",
    CLASSIFICATION_MISSING,
)

MAGNITUDE_CLASSES: tuple[str, ...] = (
    "LOW",
    "MEDIUM",
    "HIGH",
    CLASSIFICATION_UNCHANGED,
    CLASSIFICATION_MISSING,
)


@dataclass(frozen=True)
class TemporalPositionChangePositionSummary:
    position: str
    change_count: int
    increase_count: int
    decrease_count: int
    unchanged_count: int
    missing_count: int
    low_count: int
    medium_count: int
    high_count: int
    valid_change_count: int
    increase_percentage: float
    decrease_percentage: float
    unchanged_percentage: float
    missing_percentage: float
    low_percentage: float
    medium_percentage: float
    high_percentage: float


@dataclass(frozen=True)
class TemporalPositionChangeSummary:
    position_count: int
    positions: tuple[str, ...]
    total_change_count: int
    total_increase_count: int
    total_decrease_count: int
    total_unchanged_count: int
    total_missing_count: int
    total_low_count: int
    total_medium_count: int
    total_high_count: int
    total_valid_change_count: int
    increase_percentage: float
    decrease_percentage: float
    unchanged_percentage: float
    missing_percentage: float
    low_percentage: float
    medium_percentage: float
    high_percentage: float
    position_summaries: tuple[
        TemporalPositionChangePositionSummary, ...
    ]


def _validate_classification(
    classification: TemporalPositionChangeClassification,
) -> None:
    if not isinstance(
        classification,
        TemporalPositionChangeClassification,
    ):
        raise TypeError(
            "classifications must contain only "
            "TemporalPositionChangeClassification instances"
        )


def _validate_result(
    result: TemporalPositionChangeClassificationResult,
) -> None:
    if not isinstance(
        result,
        TemporalPositionChangeClassificationResult,
    ):
        raise TypeError(
            "results must contain only "
            "TemporalPositionChangeClassificationResult instances"
        )

    for classification in result.classifications:
        _validate_classification(classification)


def _validate_results(
    results: Iterable[
        TemporalPositionChangeClassificationResult
    ],
) -> tuple[
    TemporalPositionChangeClassificationResult, ...
]:
    if isinstance(results, (str, bytes)):
        raise TypeError(
            "results must be an iterable of "
            "TemporalPositionChangeClassificationResult"
        )

    try:
        materialized = tuple(results)
    except TypeError as exc:
        raise TypeError(
            "results must be an iterable of "
            "TemporalPositionChangeClassificationResult"
        ) from exc

    for result in materialized:
        _validate_result(result)

    positions = tuple(
        result.position
        for result in materialized
    )

    if len(set(positions)) != len(positions):
        raise ValueError(
            "results must not contain duplicate positions"
        )

    return materialized


def _percentage(
    count: int,
    total: int,
) -> float:
    if total == 0:
        return 0.0

    return count / total * 100.0


def _build_position_summary(
    result: TemporalPositionChangeClassificationResult,
) -> TemporalPositionChangePositionSummary:
    classifications = result.classifications

    increase_count = sum(
        1
        for item in classifications
        if item.direction == "INCREASE"
    )

    decrease_count = sum(
        1
        for item in classifications
        if item.direction == "DECREASE"
    )

    unchanged_count = sum(
        1
        for item in classifications
        if item.direction == "UNCHANGED"
    )

    missing_count = sum(
        1
        for item in classifications
        if item.magnitude_class == CLASSIFICATION_MISSING
    )

    low_count = sum(
        1
        for item in classifications
        if item.magnitude_class == "LOW"
    )

    medium_count = sum(
        1
        for item in classifications
        if item.magnitude_class == "MEDIUM"
    )

    high_count = sum(
        1
        for item in classifications
        if item.magnitude_class == "HIGH"
    )

    valid_change_count = (
        increase_count
        + decrease_count
        + unchanged_count
    )

    change_count = len(classifications)

    return TemporalPositionChangePositionSummary(
        position=result.position,
        change_count=change_count,
        increase_count=increase_count,
        decrease_count=decrease_count,
        unchanged_count=unchanged_count,
        missing_count=missing_count,
        low_count=low_count,
        medium_count=medium_count,
        high_count=high_count,
        valid_change_count=valid_change_count,
        increase_percentage=_percentage(
            increase_count,
            change_count,
        ),
        decrease_percentage=_percentage(
            decrease_count,
            change_count,
        ),
        unchanged_percentage=_percentage(
            unchanged_count,
            change_count,
        ),
        missing_percentage=_percentage(
            missing_count,
            change_count,
        ),
        low_percentage=_percentage(
            low_count,
            change_count,
        ),
        medium_percentage=_percentage(
            medium_count,
            change_count,
        ),
        high_percentage=_percentage(
            high_count,
            change_count,
        ),
    )


def build_temporal_position_change_summary(
    results: Iterable[
        TemporalPositionChangeClassificationResult
    ],
) -> TemporalPositionChangeSummary:
    materialized = _validate_results(results)

    positions = tuple(
        result.position
        for result in materialized
    )

    position_summaries = tuple(
        _build_position_summary(result)
        for result in materialized
    )

    total_change_count = sum(
        summary.change_count
        for summary in position_summaries
    )

    total_increase_count = sum(
        summary.increase_count
        for summary in position_summaries
    )

    total_decrease_count = sum(
        summary.decrease_count
        for summary in position_summaries
    )

    total_unchanged_count = sum(
        summary.unchanged_count
        for summary in position_summaries
    )

    total_missing_count = sum(
        summary.missing_count
        for summary in position_summaries
    )

    total_low_count = sum(
        summary.low_count
        for summary in position_summaries
    )

    total_medium_count = sum(
        summary.medium_count
        for summary in position_summaries
    )

    total_high_count = sum(
        summary.high_count
        for summary in position_summaries
    )

    total_valid_change_count = (
        total_increase_count
        + total_decrease_count
        + total_unchanged_count
    )

    return TemporalPositionChangeSummary(
        position_count=len(materialized),
        positions=positions,
        total_change_count=total_change_count,
        total_increase_count=total_increase_count,
        total_decrease_count=total_decrease_count,
        total_unchanged_count=total_unchanged_count,
        total_missing_count=total_missing_count,
        total_low_count=total_low_count,
        total_medium_count=total_medium_count,
        total_high_count=total_high_count,
        total_valid_change_count=total_valid_change_count,
        increase_percentage=_percentage(
            total_increase_count,
            total_change_count,
        ),
        decrease_percentage=_percentage(
            total_decrease_count,
            total_change_count,
        ),
        unchanged_percentage=_percentage(
            total_unchanged_count,
            total_change_count,
        ),
        missing_percentage=_percentage(
            total_missing_count,
            total_change_count,
        ),
        low_percentage=_percentage(
            total_low_count,
            total_change_count,
        ),
        medium_percentage=_percentage(
            total_medium_count,
            total_change_count,
        ),
        high_percentage=_percentage(
            total_high_count,
            total_change_count,
        ),
        position_summaries=position_summaries,
    )


def build_temporal_position_change_summary_result(
    results: Iterable[
        TemporalPositionChangeClassificationResult
    ],
) -> TemporalPositionChangeSummary:
    return build_temporal_position_change_summary(results)


def get_temporal_position_change_position_summary(
    result: TemporalPositionChangeSummary,
    position: str,
) -> TemporalPositionChangePositionSummary:
    if not isinstance(
        result,
        TemporalPositionChangeSummary,
    ):
        raise TypeError(
            "result must be a TemporalPositionChangeSummary"
        )

    for summary in result.position_summaries:
        if summary.position == position:
            return summary

    raise ValueError(
        f"Position summary not found: {position}"
    )


def iter_temporal_position_change_position_summaries(
    result: TemporalPositionChangeSummary,
) -> tuple[TemporalPositionChangePositionSummary, ...]:
    if not isinstance(
        result,
        TemporalPositionChangeSummary,
    ):
        raise TypeError(
            "result must be a TemporalPositionChangeSummary"
        )

    return result.position_summaries