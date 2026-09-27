from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable


STABILITY_LEVELS: tuple[str, ...] = (
    "HIGH",
    "MEDIUM",
    "LOW",
    "INSUFFICIENT_DATA",
)

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
class CrossPositionRelationshipWindow:
    position_a: str
    position_b: str
    window_index: int
    observation_count: int
    valid_pair_count: int
    correlation: float | None
    direction: str
    strength: str


@dataclass(frozen=True)
class CrossPositionRelationshipStability:
    position_a: str
    position_b: str
    window_size: int
    window_count: int
    valid_window_count: int
    windows: tuple[CrossPositionRelationshipWindow, ...]
    direction_change_count: int
    strength_change_count: int
    direction_consistency: float
    strength_consistency: float
    stability_percentage: float
    stability_level: str


def _validate_position(position: str) -> None:
    if not isinstance(position, str):
        raise TypeError("position must be a string")

    if not position.strip():
        raise ValueError("position must not be empty")


def _validate_window_size(window_size: int) -> None:
    if isinstance(window_size, bool):
        raise TypeError(
            "window_size must be an integer"
        )

    if not isinstance(window_size, int):
        raise TypeError(
            "window_size must be an integer"
        )

    if window_size < 2:
        raise ValueError(
            "window_size must be at least 2"
        )


def _validate_value(
    value: int | float | None,
) -> None:
    if value is None:
        return

    if isinstance(value, bool):
        raise TypeError(
            "position values must be numeric or None"
        )

    if not isinstance(value, (int, float)):
        raise TypeError(
            "position values must be numeric or None"
        )


def _validate_observations(
    observations: Iterable[
        tuple[int | float | None, int | float | None]
    ],
) -> tuple[
    tuple[int | float | None, int | float | None], ...
]:
    if isinstance(observations, (str, bytes)):
        raise TypeError(
            "observations must be an iterable of value pairs"
        )

    try:
        materialized = tuple(observations)
    except TypeError as exc:
        raise TypeError(
            "observations must be an iterable of value pairs"
        ) from exc

    validated = []

    for observation in materialized:
        if not isinstance(observation, (tuple, list)):
            raise TypeError(
                "each observation must contain two values"
            )

        if len(observation) != 2:
            raise ValueError(
                "each observation must contain exactly two values"
            )

        value_a, value_b = observation

        _validate_value(value_a)
        _validate_value(value_b)

        validated.append((value_a, value_b))

    return tuple(validated)


def _valid_pairs(
    observations: Iterable[
        tuple[int | float | None, int | float | None]
    ],
) -> tuple[tuple[float, float], ...]:
    pairs = []

    for value_a, value_b in observations:
        if value_a is None or value_b is None:
            continue

        pairs.append(
            (float(value_a), float(value_b))
        )

    return tuple(pairs)


def _calculate_correlation(
    pairs: tuple[tuple[float, float], ...],
) -> float | None:
    if len(pairs) < 2:
        return None

    mean_a = sum(
        value_a
        for value_a, _ in pairs
    ) / len(pairs)

    mean_b = sum(
        value_b
        for _, value_b in pairs
    ) / len(pairs)

    deviations_a = tuple(
        value_a - mean_a
        for value_a, _ in pairs
    )

    deviations_b = tuple(
        value_b - mean_b
        for _, value_b in pairs
    )

    squared_a = sum(
        deviation * deviation
        for deviation in deviations_a
    )

    squared_b = sum(
        deviation * deviation
        for deviation in deviations_b
    )

    if squared_a == 0.0 or squared_b == 0.0:
        return None

    numerator = sum(
        deviation_a * deviation_b
        for deviation_a, deviation_b in zip(
            deviations_a,
            deviations_b,
        )
    )

    denominator = sqrt(
        squared_a * squared_b
    )

    if denominator == 0.0:
        return None

    return numerator / denominator


def _classify_direction(
    correlation: float | None,
) -> str:
    if correlation is None:
        return "INSUFFICIENT_DATA"

    if correlation > 0:
        return "POSITIVE"

    if correlation < 0:
        return "NEGATIVE"

    return "NEUTRAL"


def _classify_strength(
    correlation: float | None,
) -> str:
    if correlation is None:
        return "INSUFFICIENT_DATA"

    absolute_correlation = abs(correlation)

    if absolute_correlation == 0:
        return "NONE"

    if absolute_correlation < 0.30:
        return "WEAK"

    if absolute_correlation < 0.70:
        return "MODERATE"

    return "STRONG"


def _build_window(
    position_a: str,
    position_b: str,
    window_index: int,
    observations: tuple[
        tuple[int | float | None, int | float | None], ...
    ],
) -> CrossPositionRelationshipWindow:
    pairs = _valid_pairs(observations)

    correlation = _calculate_correlation(pairs)

    return CrossPositionRelationshipWindow(
        position_a=position_a,
        position_b=position_b,
        window_index=window_index,
        observation_count=len(observations),
        valid_pair_count=len(pairs),
        correlation=correlation,
        direction=_classify_direction(
            correlation
        ),
        strength=_classify_strength(
            correlation
        ),
    )


def _build_windows(
    position_a: str,
    position_b: str,
    observations: tuple[
        tuple[int | float | None, int | float | None], ...
    ],
    window_size: int,
) -> tuple[CrossPositionRelationshipWindow, ...]:
    windows = []

    for start in range(
        0,
        len(observations),
        window_size,
    ):
        window_observations = observations[
            start:start + window_size
        ]

        if not window_observations:
            continue

        windows.append(
            _build_window(
                position_a,
                position_b,
                len(windows) + 1,
                window_observations,
            )
        )

    return tuple(windows)


def _count_direction_changes(
    windows: tuple[CrossPositionRelationshipWindow, ...],
) -> int:
    valid_windows = tuple(
        window
        for window in windows
        if window.direction != "INSUFFICIENT_DATA"
    )

    if len(valid_windows) < 2:
        return 0

    return sum(
        1
        for previous, current in zip(
            valid_windows,
            valid_windows[1:],
        )
        if previous.direction != current.direction
    )


def _count_strength_changes(
    windows: tuple[CrossPositionRelationshipWindow, ...],
) -> int:
    valid_windows = tuple(
        window
        for window in windows
        if window.strength != "INSUFFICIENT_DATA"
    )

    if len(valid_windows) < 2:
        return 0

    return sum(
        1
        for previous, current in zip(
            valid_windows,
            valid_windows[1:],
        )
        if previous.strength != current.strength
    )


def _calculate_direction_consistency(
    windows: tuple[CrossPositionRelationshipWindow, ...],
) -> float:
    valid_windows = tuple(
        window
        for window in windows
        if window.direction != "INSUFFICIENT_DATA"
    )

    if len(valid_windows) < 2:
        return 0.0

    transitions = len(valid_windows) - 1

    unchanged_transitions = sum(
        1
        for previous, current in zip(
            valid_windows,
            valid_windows[1:],
        )
        if previous.direction == current.direction
    )

    return (
        unchanged_transitions
        / transitions
        * 100.0
    )


def _calculate_strength_consistency(
    windows: tuple[CrossPositionRelationshipWindow, ...],
) -> float:
    valid_windows = tuple(
        window
        for window in windows
        if window.strength != "INSUFFICIENT_DATA"
    )

    if len(valid_windows) < 2:
        return 0.0

    transitions = len(valid_windows) - 1

    unchanged_transitions = sum(
        1
        for previous, current in zip(
            valid_windows,
            valid_windows[1:],
        )
        if previous.strength == current.strength
    )

    return (
        unchanged_transitions
        / transitions
        * 100.0
    )


def _classify_stability(
    valid_window_count: int,
    direction_consistency: float,
) -> str:
    if valid_window_count < 2:
        return "INSUFFICIENT_DATA"

    if direction_consistency >= 80.0:
        return "HIGH"

    if direction_consistency >= 50.0:
        return "MEDIUM"

    return "LOW"


def build_cross_position_relationship_stability(
    position_a: str,
    position_b: str,
    observations: Iterable[
        tuple[int | float | None, int | float | None]
    ],
    window_size: int,
) -> CrossPositionRelationshipStability:
    _validate_position(position_a)
    _validate_position(position_b)

    if position_a == position_b:
        raise ValueError(
            "position_a and position_b must be different"
        )

    _validate_window_size(window_size)

    validated_observations = _validate_observations(
        observations
    )

    windows = _build_windows(
        position_a,
        position_b,
        validated_observations,
        window_size,
    )

    valid_window_count = sum(
        1
        for window in windows
        if window.direction != "INSUFFICIENT_DATA"
    )

    direction_change_count = (
        _count_direction_changes(windows)
    )

    strength_change_count = (
        _count_strength_changes(windows)
    )

    direction_consistency = (
        _calculate_direction_consistency(windows)
    )

    strength_consistency = (
        _calculate_strength_consistency(windows)
    )

    stability_percentage = direction_consistency

    return CrossPositionRelationshipStability(
        position_a=position_a,
        position_b=position_b,
        window_size=window_size,
        window_count=len(windows),
        valid_window_count=valid_window_count,
        windows=windows,
        direction_change_count=direction_change_count,
        strength_change_count=strength_change_count,
        direction_consistency=direction_consistency,
        strength_consistency=strength_consistency,
        stability_percentage=stability_percentage,
        stability_level=_classify_stability(
            valid_window_count,
            direction_consistency,
        ),
    )


def get_cross_position_relationship_stability_window(
    result: CrossPositionRelationshipStability,
    window_index: int,
) -> CrossPositionRelationshipWindow:
    if not isinstance(
        result,
        CrossPositionRelationshipStability,
    ):
        raise TypeError(
            "result must be a "
            "CrossPositionRelationshipStability"
        )

    for window in result.windows:
        if window.window_index == window_index:
            return window

    raise ValueError(
        f"Window not found: {window_index}"
    )


def iter_cross_position_relationship_stability_windows(
    result: CrossPositionRelationshipStability,
) -> tuple[CrossPositionRelationshipWindow, ...]:
    if not isinstance(
        result,
        CrossPositionRelationshipStability,
    ):
        raise TypeError(
            "result must be a "
            "CrossPositionRelationshipStability"
        )

    return result.windows