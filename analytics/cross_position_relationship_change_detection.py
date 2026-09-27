from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


RELATIONSHIP_DIRECTIONS: tuple[str, ...] = (
    "POSITIVE",
    "NEGATIVE",
    "NEUTRAL",
    "INSUFFICIENT_DATA",
)

RELATIONSHIP_STRENGTHS: tuple[str, ...] = (
    "NONE",
    "WEAK",
    "MODERATE",
    "STRONG",
    "INSUFFICIENT_DATA",
)


@dataclass(frozen=True)
class CrossPositionRelationshipChange:
    position_a: str
    position_b: str
    previous_window_index: int
    current_window_index: int
    previous_correlation: float | None
    current_correlation: float | None
    correlation_change: float | None
    absolute_correlation_change: float | None
    previous_direction: str
    current_direction: str
    previous_strength: str
    current_strength: str
    direction_changed: bool
    strength_changed: bool
    relationship_changed: bool


@dataclass(frozen=True)
class CrossPositionRelationshipChangeDetection:
    position_a: str
    position_b: str
    window_count: int
    comparison_count: int
    changes: tuple[CrossPositionRelationshipChange, ...]
    direction_change_count: int
    strength_change_count: int
    relationship_change_count: int
    insufficient_data_change_count: int


def _validate_position(position: str) -> None:
    if not isinstance(position, str):
        raise TypeError("position must be a string")
    if not position.strip():
        raise ValueError("position must not be empty")


def _validate_window_index(window_index: int) -> None:
    if isinstance(window_index, bool):
        raise TypeError("window_index must be an integer")
    if not isinstance(window_index, int):
        raise TypeError("window_index must be an integer")
    if window_index < 1:
        raise ValueError("window_index must be at least 1")


def _validate_correlation(correlation: float | None) -> None:
    if correlation is None:
        return
    if isinstance(correlation, bool):
        raise TypeError("correlation must be numeric or None")
    if not isinstance(correlation, (int, float)):
        raise TypeError("correlation must be numeric or None")
    if not isfinite(float(correlation)):
        raise ValueError("correlation must be finite or None")


def _validate_direction(direction: str) -> None:
    if not isinstance(direction, str):
        raise TypeError("direction must be a string")
    if direction not in RELATIONSHIP_DIRECTIONS:
        raise ValueError(f"Invalid relationship direction: {direction}")


def _validate_strength(strength: str) -> None:
    if not isinstance(strength, str):
        raise TypeError("strength must be a string")
    if strength not in RELATIONSHIP_STRENGTHS:
        raise ValueError(f"Invalid relationship strength: {strength}")


def _validate_window(
    window: object,
) -> tuple[int, float | None, str, str]:
    required_attributes = (
        "window_index",
        "correlation",
        "direction",
        "strength",
    )

    for attribute in required_attributes:
        if not hasattr(window, attribute):
            raise TypeError(
                "each window must contain window_index, correlation, "
                "direction, and strength"
            )

    window_index = getattr(window, "window_index")
    correlation = getattr(window, "correlation")
    direction = getattr(window, "direction")
    strength = getattr(window, "strength")

    _validate_window_index(window_index)
    _validate_correlation(correlation)
    _validate_direction(direction)
    _validate_strength(strength)

    return (
        window_index,
        None if correlation is None else float(correlation),
        direction,
        strength,
    )


def _validate_windows(
    windows: Iterable[object],
) -> tuple[tuple[int, float | None, str, str], ...]:
    if isinstance(windows, (str, bytes)):
        raise TypeError("windows must be an iterable of relationship windows")

    try:
        materialized = tuple(windows)
    except TypeError as exc:
        raise TypeError(
            "windows must be an iterable of relationship windows"
        ) from exc

    validated = tuple(_validate_window(window) for window in materialized)

    if not validated:
        return ()

    window_indices = tuple(item[0] for item in validated)

    if len(set(window_indices)) != len(window_indices):
        raise ValueError("window_index values must be unique")

    if window_indices != tuple(sorted(window_indices)):
        raise ValueError("windows must be ordered by window_index")

    return validated


def _calculate_correlation_change(
    previous_correlation: float | None,
    current_correlation: float | None,
) -> float | None:
    if previous_correlation is None or current_correlation is None:
        return None

    return current_correlation - previous_correlation


def _calculate_absolute_correlation_change(
    previous_correlation: float | None,
    current_correlation: float | None,
) -> float | None:
    if previous_correlation is None or current_correlation is None:
        return None

    return abs(current_correlation) - abs(previous_correlation)


def _build_change(
    position_a: str,
    position_b: str,
    previous_window: tuple[int, float | None, str, str],
    current_window: tuple[int, float | None, str, str],
) -> CrossPositionRelationshipChange:
    (
        previous_window_index,
        previous_correlation,
        previous_direction,
        previous_strength,
    ) = previous_window

    (
        current_window_index,
        current_correlation,
        current_direction,
        current_strength,
    ) = current_window

    correlation_change = _calculate_correlation_change(
        previous_correlation,
        current_correlation,
    )

    absolute_correlation_change = _calculate_absolute_correlation_change(
        previous_correlation,
        current_correlation,
    )

    direction_changed = previous_direction != current_direction
    strength_changed = previous_strength != current_strength

    relationship_changed = (
        direction_changed
        or strength_changed
        or correlation_change is not None
        and correlation_change != 0.0
    )

    return CrossPositionRelationshipChange(
        position_a=position_a,
        position_b=position_b,
        previous_window_index=previous_window_index,
        current_window_index=current_window_index,
        previous_correlation=previous_correlation,
        current_correlation=current_correlation,
        correlation_change=correlation_change,
        absolute_correlation_change=absolute_correlation_change,
        previous_direction=previous_direction,
        current_direction=current_direction,
        previous_strength=previous_strength,
        current_strength=current_strength,
        direction_changed=direction_changed,
        strength_changed=strength_changed,
        relationship_changed=relationship_changed,
    )


def _count_direction_changes(
    changes: tuple[CrossPositionRelationshipChange, ...],
) -> int:
    return sum(change.direction_changed for change in changes)


def _count_strength_changes(
    changes: tuple[CrossPositionRelationshipChange, ...],
) -> int:
    return sum(change.strength_changed for change in changes)


def _count_relationship_changes(
    changes: tuple[CrossPositionRelationshipChange, ...],
) -> int:
    return sum(change.relationship_changed for change in changes)


def _count_insufficient_data_changes(
    changes: tuple[CrossPositionRelationshipChange, ...],
) -> int:
    return sum(
        1
        for change in changes
        if change.previous_direction == "INSUFFICIENT_DATA"
        or change.current_direction == "INSUFFICIENT_DATA"
        or change.previous_strength == "INSUFFICIENT_DATA"
        or change.current_strength == "INSUFFICIENT_DATA"
    )


def build_cross_position_relationship_change_detection(
    position_a: str,
    position_b: str,
    windows: Iterable[object],
) -> CrossPositionRelationshipChangeDetection:
    _validate_position(position_a)
    _validate_position(position_b)

    if position_a == position_b:
        raise ValueError("position_a and position_b must be different")

    validated_windows = _validate_windows(windows)

    changes = tuple(
        _build_change(
            position_a,
            position_b,
            previous_window,
            current_window,
        )
        for previous_window, current_window in zip(
            validated_windows,
            validated_windows[1:],
        )
    )

    return CrossPositionRelationshipChangeDetection(
        position_a=position_a,
        position_b=position_b,
        window_count=len(validated_windows),
        comparison_count=len(changes),
        changes=changes,
        direction_change_count=_count_direction_changes(changes),
        strength_change_count=_count_strength_changes(changes),
        relationship_change_count=_count_relationship_changes(changes),
        insufficient_data_change_count=_count_insufficient_data_changes(changes),
    )


def get_cross_position_relationship_change(
    result: CrossPositionRelationshipChangeDetection,
    previous_window_index: int,
    current_window_index: int,
) -> CrossPositionRelationshipChange:
    if not isinstance(
        result,
        CrossPositionRelationshipChangeDetection,
    ):
        raise TypeError(
            "result must be a "
            "CrossPositionRelationshipChangeDetection"
        )

    _validate_window_index(previous_window_index)
    _validate_window_index(current_window_index)

    for change in result.changes:
        if (
            change.previous_window_index == previous_window_index
            and change.current_window_index == current_window_index
        ):
            return change

    raise ValueError(
        "Relationship change not found for windows "
        f"{previous_window_index} -> {current_window_index}"
    )


def iter_cross_position_relationship_changes(
    result: CrossPositionRelationshipChangeDetection,
) -> tuple[CrossPositionRelationshipChange, ...]:
    if not isinstance(
        result,
        CrossPositionRelationshipChangeDetection,
    ):
        raise TypeError(
            "result must be a "
            "CrossPositionRelationshipChangeDetection"
        )

    return result.changes