from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)


@dataclass(frozen=True)
class PointInTimeHistory:
    """Historical observations available strictly before a target date."""

    target_date: date
    observations: tuple[HistoricalFeatureObservation, ...]
    observation_count: int


def _validate_target_date(target_date: date) -> None:
    """Validate the target date."""

    if not isinstance(target_date, date):
        raise TypeError(
            "target_date must be a datetime.date instance."
        )


def _validate_observations(
    observations: Iterable[HistoricalFeatureObservation],
) -> tuple[HistoricalFeatureObservation, ...]:
    """Validate and chronologically order historical observations."""

    if isinstance(observations, (str, bytes)):
        raise TypeError(
            "observations must be an iterable of "
            "HistoricalFeatureObservation objects."
        )

    try:
        materialized = tuple(observations)
    except TypeError as exc:
        raise TypeError(
            "observations must be an iterable of "
            "HistoricalFeatureObservation objects."
        ) from exc

    for observation in materialized:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "observations must contain only "
                "HistoricalFeatureObservation objects."
            )

    dates = tuple(
        observation.result_date
        for observation in materialized
    )

    if len(set(dates)) != len(dates):
        raise ValueError(
            "Historical observations must not contain duplicate dates."
        )

    return tuple(
        sorted(
            materialized,
            key=lambda observation: observation.result_date,
        )
    )


def build_point_in_time_history(
    observations: Iterable[HistoricalFeatureObservation],
    target_date: date,
) -> PointInTimeHistory:
    """
    Build the historical information available before a target date.

    The target date itself is excluded.

    Any observation dated after the target date is also excluded.

    This function does not calculate features or predictions.
    """

    _validate_target_date(target_date)

    validated = _validate_observations(
        observations,
    )

    historical_observations = tuple(
        observation
        for observation in validated
        if observation.result_date < target_date
    )

    return PointInTimeHistory(
        target_date=target_date,
        observations=historical_observations,
        observation_count=len(historical_observations),
    )


def get_point_in_time_observations(
    history: PointInTimeHistory,
) -> tuple[HistoricalFeatureObservation, ...]:
    """Return observations available at the target point in time."""

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    return history.observations


def get_point_in_time_observation_count(
    history: PointInTimeHistory,
) -> int:
    """Return the number of observations available before the target date."""

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    return history.observation_count