from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import sqrt
from typing import Iterable

from analytics.statistical_foundation import ANALYSIS_COLUMNS


@dataclass(frozen=True)
class TemporalPositionAnalysis:
    position: str
    observation_count: int
    first_date: date | None
    latest_date: date | None
    first_value: int | None
    latest_value: int | None
    minimum: int | None
    maximum: int | None
    mean: float
    standard_deviation: float
    first_to_latest_change: int
    absolute_first_to_latest_change: int
    change_count: int
    increase_count: int
    decrease_count: int
    unchanged_count: int
    average_absolute_step_change: float
    maximum_absolute_step_change: int
    increase_percentage: float
    decrease_percentage: float
    unchanged_percentage: float


@dataclass(frozen=True)
class TemporalPositionAnalysisResult:
    position_count: int
    positions: tuple[str, ...]
    analyses: tuple[TemporalPositionAnalysis, ...]


def _population_standard_deviation(values: tuple[int, ...]) -> float:
    if not values:
        return 0.0

    mean = sum(values) / len(values)

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / len(values)

    return sqrt(variance)


def _validate_observation(
    observation: object,
    position: str,
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
                f"{position} values must be integers or None"
            )

        if value < 0 or value > 9:
            raise ValueError(
                f"{position} values must be between 0 and 9"
            )

    return observation_date, value


def _validate_observations(
    observations: Iterable[tuple[date, int | None]],
    position: str,
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
        _validate_observation(observation, position)
        for observation in materialized
    )

    dates = tuple(item[0] for item in validated)

    if len(set(dates)) != len(dates):
        raise ValueError(
            f"{position} observations must not contain duplicate dates"
        )

    return tuple(
        sorted(
            validated,
            key=lambda item: item[0],
        )
    )


def _build_analysis(
    position: str,
    observations: Iterable[tuple[date, int | None]],
) -> TemporalPositionAnalysis:
    validated = _validate_observations(
        observations,
        position,
    )

    valid = tuple(
        item
        for item in validated
        if item[1] is not None
    )

    if not valid:
        return TemporalPositionAnalysis(
            position=position,
            observation_count=0,
            first_date=None,
            latest_date=None,
            first_value=None,
            latest_value=None,
            minimum=None,
            maximum=None,
            mean=0.0,
            standard_deviation=0.0,
            first_to_latest_change=0,
            absolute_first_to_latest_change=0,
            change_count=0,
            increase_count=0,
            decrease_count=0,
            unchanged_count=0,
            average_absolute_step_change=0.0,
            maximum_absolute_step_change=0,
            increase_percentage=0.0,
            decrease_percentage=0.0,
            unchanged_percentage=0.0,
        )

    dates = tuple(item[0] for item in valid)
    values = tuple(item[1] for item in valid)

    first_value = values[0]
    latest_value = values[-1]

    changes = tuple(
        current - previous
        for previous, current in zip(
            values,
            values[1:],
        )
    )

    absolute_changes = tuple(
        abs(change)
        for change in changes
    )

    increase_count = sum(
        1
        for change in changes
        if change > 0
    )

    decrease_count = sum(
        1
        for change in changes
        if change < 0
    )

    unchanged_count = sum(
        1
        for change in changes
        if change == 0
    )

    change_count = len(changes)

    return TemporalPositionAnalysis(
        position=position,
        observation_count=len(values),
        first_date=dates[0],
        latest_date=dates[-1],
        first_value=first_value,
        latest_value=latest_value,
        minimum=min(values),
        maximum=max(values),
        mean=sum(values) / len(values),
        standard_deviation=_population_standard_deviation(values),
        first_to_latest_change=latest_value - first_value,
        absolute_first_to_latest_change=abs(
            latest_value - first_value
        ),
        change_count=change_count,
        increase_count=increase_count,
        decrease_count=decrease_count,
        unchanged_count=unchanged_count,
        average_absolute_step_change=(
            sum(absolute_changes) / len(absolute_changes)
            if absolute_changes
            else 0.0
        ),
        maximum_absolute_step_change=(
            max(absolute_changes)
            if absolute_changes
            else 0
        ),
        increase_percentage=(
            increase_count / change_count * 100.0
            if change_count
            else 0.0
        ),
        decrease_percentage=(
            decrease_count / change_count * 100.0
            if change_count
            else 0.0
        ),
        unchanged_percentage=(
            unchanged_count / change_count * 100.0
            if change_count
            else 0.0
        ),
    )


def build_temporal_position_analysis(
    observations_by_position: dict[
        str,
        Iterable[tuple[date, int | None]],
    ],
) -> TemporalPositionAnalysisResult:
    if not isinstance(observations_by_position, dict):
        raise TypeError(
            "observations_by_position must be a dictionary"
        )

    unknown_positions = set(observations_by_position) - set(
        ANALYSIS_COLUMNS
    )

    if unknown_positions:
        raise ValueError(
            "Unknown positions: "
            + ", ".join(sorted(unknown_positions))
        )

    positions = tuple(
        position
        for position in ANALYSIS_COLUMNS
        if position in observations_by_position
    )

    analyses = tuple(
        _build_analysis(
            position,
            observations_by_position[position],
        )
        for position in positions
    )

    return TemporalPositionAnalysisResult(
        position_count=len(positions),
        positions=positions,
        analyses=analyses,
    )


def get_temporal_position_analysis(
    result: TemporalPositionAnalysisResult,
    position: str,
) -> TemporalPositionAnalysis:
    if not isinstance(
        result,
        TemporalPositionAnalysisResult,
    ):
        raise TypeError(
            "result must be a TemporalPositionAnalysisResult"
        )

    for analysis in result.analyses:
        if analysis.position == position:
            return analysis

    raise ValueError(
        f"Temporal position analysis not found: {position}"
    )


def iter_temporal_position_analyses(
    result: TemporalPositionAnalysisResult,
) -> tuple[TemporalPositionAnalysis, ...]:
    if not isinstance(
        result,
        TemporalPositionAnalysisResult,
    ):
        raise TypeError(
            "result must be a TemporalPositionAnalysisResult"
        )

    return result.analyses