from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.temporal_position_analysis import TemporalPositionAnalysis


@dataclass(frozen=True)
class TemporalPositionSummary:
    position_count: int
    positions: tuple[str, ...]
    total_observations: int
    total_change_count: int
    total_increase_count: int
    total_decrease_count: int
    total_unchanged_count: int
    average_first_value: float
    average_latest_value: float
    average_minimum: float
    average_maximum: float
    average_mean: float
    average_standard_deviation: float
    average_first_to_latest_change: float
    average_absolute_first_to_latest_change: float
    average_absolute_step_change: float
    maximum_absolute_step_change: int
    increase_percentage: float
    decrease_percentage: float
    unchanged_percentage: float


def _validate_analysis(
    analysis: TemporalPositionAnalysis,
) -> None:
    if not isinstance(analysis, TemporalPositionAnalysis):
        raise TypeError(
            "analyses must contain only TemporalPositionAnalysis instances"
        )


def _validate_analyses(
    analyses: Iterable[TemporalPositionAnalysis],
) -> tuple[TemporalPositionAnalysis, ...]:
    if isinstance(analyses, (str, bytes)):
        raise TypeError(
            "analyses must be an iterable of TemporalPositionAnalysis"
        )

    try:
        materialized = tuple(analyses)
    except TypeError as exc:
        raise TypeError(
            "analyses must be an iterable of TemporalPositionAnalysis"
        ) from exc

    for analysis in materialized:
        _validate_analysis(analysis)

    positions = tuple(
        analysis.position
        for analysis in materialized
    )

    if len(set(positions)) != len(positions):
        raise ValueError(
            "analyses must not contain duplicate positions"
        )

    return materialized


def _average(
    values: tuple[float, ...],
) -> float:
    if not values:
        return 0.0

    return sum(values) / len(values)


def build_temporal_position_summary(
    analyses: Iterable[TemporalPositionAnalysis],
) -> TemporalPositionSummary:
    materialized = _validate_analyses(analyses)

    positions = tuple(
        analysis.position
        for analysis in materialized
    )

    valid = tuple(
        analysis
        for analysis in materialized
        if analysis.observation_count > 0
    )

    total_observations = sum(
        analysis.observation_count
        for analysis in materialized
    )

    total_change_count = sum(
        analysis.change_count
        for analysis in materialized
    )

    total_increase_count = sum(
        analysis.increase_count
        for analysis in materialized
    )

    total_decrease_count = sum(
        analysis.decrease_count
        for analysis in materialized
    )

    total_unchanged_count = sum(
        analysis.unchanged_count
        for analysis in materialized
    )

    if not valid:
        return TemporalPositionSummary(
            position_count=len(materialized),
            positions=positions,
            total_observations=0,
            total_change_count=0,
            total_increase_count=0,
            total_decrease_count=0,
            total_unchanged_count=0,
            average_first_value=0.0,
            average_latest_value=0.0,
            average_minimum=0.0,
            average_maximum=0.0,
            average_mean=0.0,
            average_standard_deviation=0.0,
            average_first_to_latest_change=0.0,
            average_absolute_first_to_latest_change=0.0,
            average_absolute_step_change=0.0,
            maximum_absolute_step_change=0,
            increase_percentage=0.0,
            decrease_percentage=0.0,
            unchanged_percentage=0.0,
        )

    first_values = tuple(
        float(analysis.first_value)
        for analysis in valid
        if analysis.first_value is not None
    )

    latest_values = tuple(
        float(analysis.latest_value)
        for analysis in valid
        if analysis.latest_value is not None
    )

    minimums = tuple(
        float(analysis.minimum)
        for analysis in valid
        if analysis.minimum is not None
    )

    maximums = tuple(
        float(analysis.maximum)
        for analysis in valid
        if analysis.maximum is not None
    )

    return TemporalPositionSummary(
        position_count=len(materialized),
        positions=positions,
        total_observations=total_observations,
        total_change_count=total_change_count,
        total_increase_count=total_increase_count,
        total_decrease_count=total_decrease_count,
        total_unchanged_count=total_unchanged_count,
        average_first_value=_average(first_values),
        average_latest_value=_average(latest_values),
        average_minimum=_average(minimums),
        average_maximum=_average(maximums),
        average_mean=_average(
            tuple(
                analysis.mean
                for analysis in valid
            )
        ),
        average_standard_deviation=_average(
            tuple(
                analysis.standard_deviation
                for analysis in valid
            )
        ),
        average_first_to_latest_change=_average(
            tuple(
                float(analysis.first_to_latest_change)
                for analysis in valid
            )
        ),
        average_absolute_first_to_latest_change=_average(
            tuple(
                float(analysis.absolute_first_to_latest_change)
                for analysis in valid
            )
        ),
        average_absolute_step_change=_average(
            tuple(
                analysis.average_absolute_step_change
                for analysis in valid
            )
        ),
        maximum_absolute_step_change=max(
            analysis.maximum_absolute_step_change
            for analysis in valid
        ),
        increase_percentage=(
            total_increase_count / total_change_count * 100.0
            if total_change_count
            else 0.0
        ),
        decrease_percentage=(
            total_decrease_count / total_change_count * 100.0
            if total_change_count
            else 0.0
        ),
        unchanged_percentage=(
            total_unchanged_count / total_change_count * 100.0
            if total_change_count
            else 0.0
        ),
    )


def build_temporal_position_summary_result(
    analyses: Iterable[TemporalPositionAnalysis],
) -> TemporalPositionSummary:
    return build_temporal_position_summary(analyses)


def get_temporal_position_summary(
    analyses: Iterable[TemporalPositionAnalysis],
) -> TemporalPositionSummary:
    return build_temporal_position_summary(analyses)