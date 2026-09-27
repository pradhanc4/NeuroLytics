from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.temporal_position_change_detection import (
    MISSING_CHANGE_DIRECTION,
    TemporalPositionChange,
)


CHANGE_MAGNITUDE_CLASSES: tuple[str, ...] = (
    "LOW",
    "MEDIUM",
    "HIGH",
)

CLASSIFICATION_MISSING = "MISSING"
CLASSIFICATION_UNCHANGED = "UNCHANGED"


@dataclass(frozen=True)
class TemporalPositionChangeClassification:
    position: str
    previous_date: object
    current_date: object
    previous_value: int | None
    current_value: int | None
    change: int | None
    absolute_change: int | None
    direction: str
    magnitude_class: str


@dataclass(frozen=True)
class TemporalPositionChangeClassificationResult:
    position: str
    change_count: int
    classifications: tuple[
        TemporalPositionChangeClassification, ...
    ]


@dataclass(frozen=True)
class TemporalPositionChangeClassificationCollection:
    position_count: int
    positions: tuple[str, ...]
    results: tuple[
        TemporalPositionChangeClassificationResult, ...
    ]


def _validate_change(
    change: TemporalPositionChange,
) -> None:
    if not isinstance(change, TemporalPositionChange):
        raise TypeError(
            "changes must contain only TemporalPositionChange instances"
        )


def _validate_changes(
    changes: Iterable[TemporalPositionChange],
) -> tuple[TemporalPositionChange, ...]:
    if isinstance(changes, (str, bytes)):
        raise TypeError(
            "changes must be an iterable of TemporalPositionChange"
        )

    try:
        materialized = tuple(changes)
    except TypeError as exc:
        raise TypeError(
            "changes must be an iterable of TemporalPositionChange"
        ) from exc

    for change in materialized:
        _validate_change(change)

    return materialized


def _classify_magnitude(
    change: TemporalPositionChange,
) -> str:
    if (
        change.direction == MISSING_CHANGE_DIRECTION
        or change.absolute_change is None
    ):
        return CLASSIFICATION_MISSING

    if change.absolute_change == 0:
        return CLASSIFICATION_UNCHANGED

    if change.absolute_change < 2:
        return "LOW"

    if change.absolute_change < 5:
        return "MEDIUM"

    return "HIGH"


def classify_temporal_position_change(
    change: TemporalPositionChange,
) -> TemporalPositionChangeClassification:
    _validate_change(change)

    return TemporalPositionChangeClassification(
        position=change.position,
        previous_date=change.previous_date,
        current_date=change.current_date,
        previous_value=change.previous_value,
        current_value=change.current_value,
        change=change.change,
        absolute_change=change.absolute_change,
        direction=change.direction,
        magnitude_class=_classify_magnitude(change),
    )


def build_temporal_position_change_classification(
    position: str,
    changes: Iterable[TemporalPositionChange],
) -> TemporalPositionChangeClassificationResult:
    if not isinstance(position, str) or not position:
        raise TypeError(
            "position must be a non-empty string"
        )

    materialized = _validate_changes(changes)

    for change in materialized:
        if change.position != position:
            raise ValueError(
                "all changes must belong to the supplied position"
            )

    classifications = tuple(
        classify_temporal_position_change(change)
        for change in materialized
    )

    return TemporalPositionChangeClassificationResult(
        position=position,
        change_count=len(classifications),
        classifications=classifications,
    )


def build_temporal_position_change_classification_collection(
    results: Iterable[
        TemporalPositionChangeClassificationResult
    ],
) -> TemporalPositionChangeClassificationCollection:
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
        if not isinstance(
            result,
            TemporalPositionChangeClassificationResult,
        ):
            raise TypeError(
                "results must contain only "
                "TemporalPositionChangeClassificationResult instances"
            )

    positions = tuple(
        result.position
        for result in materialized
    )

    if len(set(positions)) != len(positions):
        raise ValueError(
            "results must not contain duplicate positions"
        )

    return TemporalPositionChangeClassificationCollection(
        position_count=len(materialized),
        positions=positions,
        results=materialized,
    )


def get_temporal_position_change_classification(
    result: TemporalPositionChangeClassificationResult,
    index: int,
) -> TemporalPositionChangeClassification:
    if not isinstance(
        result,
        TemporalPositionChangeClassificationResult,
    ):
        raise TypeError(
            "result must be a TemporalPositionChangeClassificationResult"
        )

    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError(
            "index must be an integer"
        )

    try:
        return result.classifications[index]
    except IndexError as exc:
        raise ValueError(
            f"classification index not found: {index}"
        ) from exc


def iter_temporal_position_change_classifications(
    result: TemporalPositionChangeClassificationResult,
) -> tuple[TemporalPositionChangeClassification, ...]:
    if not isinstance(
        result,
        TemporalPositionChangeClassificationResult,
    ):
        raise TypeError(
            "result must be a TemporalPositionChangeClassificationResult"
        )

    return result.classifications


def get_classification_counts(
    result: TemporalPositionChangeClassificationResult,
) -> tuple[tuple[str, int], ...]:
    if not isinstance(
        result,
        TemporalPositionChangeClassificationResult,
    ):
        raise TypeError(
            "result must be a TemporalPositionChangeClassificationResult"
        )

    counts: dict[str, int] = {}
    order: list[str] = []

    for classification in result.classifications:
        category = classification.magnitude_class

        if category not in counts:
            counts[category] = 0
            order.append(category)

        counts[category] += 1

    return tuple(
        (category, counts[category])
        for category in order
    )