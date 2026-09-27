from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


CHANGE_DIRECTIONS: tuple[str, ...] = (
    "INCREASE",
    "DECREASE",
    "UNCHANGED",
)

MISSING_CHANGE_DIRECTION = "MISSING"


@dataclass(frozen=True)
class TemporalPositionChange:
    position: str
    previous_date: date
    current_date: date
    previous_value: int | None
    current_value: int | None
    change: int | None
    absolute_change: int | None
    direction: str


@dataclass(frozen=True)
class TemporalPositionChangeDetection:
    position: str
    observation_count: int
    change_count: int
    changes: tuple[TemporalPositionChange, ...]


@dataclass(frozen=True)
class TemporalPositionChangeDetectionResult:
    position_count: int
    positions: tuple[str, ...]
    detections: tuple[TemporalPositionChangeDetection, ...]


def _validate_observation(
    observation: tuple[date, int | None],
) -> tuple[date, int | None]:
    if not isinstance(observation, tuple) or len(observation) != 2:
        raise TypeError(
            "observations must contain (date, value) tuples"
        )

    observation_date, value = observation

    if not isinstance(observation_date, date):
        raise TypeError(
            "observation dates must be datetime.date instances"
        )

    if value is not None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                "observation values must be integers or None"
            )

        if value < 0 or value > 9:
            raise ValueError(
                "observation values must be between 0 and 9"
            )

    return observation_date, value


def _validate_observations(
    observations: Iterable[tuple[date, int | None]],
) -> tuple[tuple[date, int | None], ...]:
    if isinstance(observations, (str, bytes)):
        raise TypeError(
            "observations must be an iterable of (date, value) tuples"
        )

    try:
        materialized = tuple(observations)
    except TypeError as exc:
        raise TypeError(
            "observations must be an iterable of (date, value) tuples"
        ) from exc

    validated = tuple(
        _validate_observation(observation)
        for observation in materialized
    )

    dates = tuple(
        observation_date
        for observation_date, _ in validated
    )

    if len(set(dates)) != len(dates):
        raise ValueError(
            "observations must not contain duplicate dates"
        )

    return tuple(
        sorted(
            validated,
            key=lambda item: item[0],
        )
    )


def _detect_change(
    position: str,
    previous: tuple[date, int | None],
    current: tuple[date, int | None],
) -> TemporalPositionChange:
    previous_date, previous_value = previous
    current_date, current_value = current

    if previous_value is None or current_value is None:
        return TemporalPositionChange(
            position=position,
            previous_date=previous_date,
            current_date=current_date,
            previous_value=previous_value,
            current_value=current_value,
            change=None,
            absolute_change=None,
            direction=MISSING_CHANGE_DIRECTION,
        )

    change = current_value - previous_value

    if change > 0:
        direction = "INCREASE"
    elif change < 0:
        direction = "DECREASE"
    else:
        direction = "UNCHANGED"

    return TemporalPositionChange(
        position=position,
        previous_date=previous_date,
        current_date=current_date,
        previous_value=previous_value,
        current_value=current_value,
        change=change,
        absolute_change=abs(change),
        direction=direction,
    )


def build_temporal_position_change_detection(
    position: str,
    observations: Iterable[tuple[date, int | None]],
) -> TemporalPositionChangeDetection:
    if not isinstance(position, str) or not position:
        raise TypeError(
            "position must be a non-empty string"
        )

    validated = _validate_observations(observations)

    changes = tuple(
        _detect_change(
            position,
            previous,
            current,
        )
        for previous, current in zip(
            validated,
            validated[1:],
        )
    )

    return TemporalPositionChangeDetection(
        position=position,
        observation_count=len(validated),
        change_count=len(changes),
        changes=changes,
    )


def build_temporal_position_change_detection_result(
    observations_by_position: dict[
        str,
        Iterable[tuple[date, int | None]],
    ],
) -> TemporalPositionChangeDetectionResult:
    if not isinstance(observations_by_position, dict):
        raise TypeError(
            "observations_by_position must be a dictionary"
        )

    positions = tuple(observations_by_position.keys())

    if len(set(positions)) != len(positions):
        raise ValueError(
            "observations_by_position must not contain duplicate positions"
        )

    detections = tuple(
        build_temporal_position_change_detection(
            position,
            observations_by_position[position],
        )
        for position in positions
    )

    return TemporalPositionChangeDetectionResult(
        position_count=len(positions),
        positions=positions,
        detections=detections,
    )


def get_temporal_position_change_detection(
    result: TemporalPositionChangeDetectionResult,
    position: str,
) -> TemporalPositionChangeDetection:
    if not isinstance(
        result,
        TemporalPositionChangeDetectionResult,
    ):
        raise TypeError(
            "result must be a TemporalPositionChangeDetectionResult"
        )

    for detection in result.detections:
        if detection.position == position:
            return detection

    raise ValueError(
        f"Temporal position change detection not found: {position}"
    )


def iter_temporal_position_changes(
    detection: TemporalPositionChangeDetection,
) -> tuple[TemporalPositionChange, ...]:
    if not isinstance(
        detection,
        TemporalPositionChangeDetection,
    ):
        raise TypeError(
            "detection must be a TemporalPositionChangeDetection"
        )

    return detection.changes


def iter_temporal_position_change_detections(
    result: TemporalPositionChangeDetectionResult,
) -> tuple[TemporalPositionChangeDetection, ...]:
    if not isinstance(
        result,
        TemporalPositionChangeDetectionResult,
    ):
        raise TypeError(
            "result must be a TemporalPositionChangeDetectionResult"
        )

    return result.detections