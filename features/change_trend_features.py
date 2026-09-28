"""
NeuroLytics - Change and Trend Features

Phase 14.13:
Point-in-time-safe change and trend feature expansion.

Rules:
- Only observations before target_date are used.
- Historical observations are ordered chronologically.
- Zero is a valid value.
- Missing calendar dates do not create observations.
- No future information is used.
- Feature names are deterministic.
- No prediction or model logic exists in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import sqrt
from typing import Any

from features.feature_config import FeatureConfig
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)


POSITIONS: tuple[str, ...] = (
    "col1",
    "col2",
    "col3",
    "col4",
    "col5",
    "col6",
    "col7",
    "col8",
)


@dataclass(frozen=True)
class ChangeTrendFeatureRecord:
    """One change/trend feature."""

    position: str
    window: int | None
    feature_name: str
    feature_group: str
    metric: str
    value: Any


@dataclass(frozen=True)
class ChangeTrendFeatureResult:
    """Complete change/trend feature result."""

    target_date: date
    records: tuple[ChangeTrendFeatureRecord, ...]


def _validate_history(
    history: tuple[HistoricalFeatureObservation, ...],
) -> None:
    if not isinstance(history, tuple):
        raise TypeError(
            "history must be a tuple of HistoricalFeatureObservation."
        )

    for observation in history:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "history must contain only "
                "HistoricalFeatureObservation objects."
            )


def _validate_target_date(target_date: Any) -> None:
    if not isinstance(target_date, date):
        raise TypeError(
            "target_date must be a date."
        )


def _validate_config(config: FeatureConfig) -> None:
    if not isinstance(config, FeatureConfig):
        raise TypeError(
            "config must be a FeatureConfig."
        )


def _historical_observations_before(
    history: tuple[HistoricalFeatureObservation, ...],
    target_date: date,
) -> tuple[HistoricalFeatureObservation, ...]:
    """Return only observations strictly before target_date."""
    return tuple(
        observation
        for observation in history
        if observation.result_date < target_date
    )


def _position_index(position: str) -> int:
    if position not in POSITIONS:
        raise ValueError(
            f"Unknown position: {position}"
        )

    return POSITIONS.index(position)


def _position_values(
    observations: tuple[HistoricalFeatureObservation, ...],
    position: str,
) -> tuple[int, ...]:
    index = _position_index(position)

    return tuple(
        observation.positions[index]
        for observation in observations
    )


def _build_change_records(
    observations: tuple[HistoricalFeatureObservation, ...],
    position: str,
) -> list[ChangeTrendFeatureRecord]:
    """
    Build latest-vs-previous change features.

    If fewer than two historical observations exist, change
    features are unavailable and represented as None.
    """
    values = _position_values(
        observations,
        position,
    )

    if len(values) < 2:
        change = None
        absolute_change = None
        direction = None
        changed = None
    else:
        previous_value = values[-2]
        latest_value = values[-1]

        change = latest_value - previous_value
        absolute_change = abs(change)

        if change > 0:
            direction = "INCREASE"
        elif change < 0:
            direction = "DECREASE"
        else:
            direction = "UNCHANGED"

        changed = 1 if change != 0 else 0

    return [
        ChangeTrendFeatureRecord(
            position=position,
            window=None,
            feature_name=f"{position}_change",
            feature_group="change",
            metric="change",
            value=change,
        ),
        ChangeTrendFeatureRecord(
            position=position,
            window=None,
            feature_name=f"{position}_absolute_change",
            feature_group="change",
            metric="absolute_change",
            value=absolute_change,
        ),
        ChangeTrendFeatureRecord(
            position=position,
            window=None,
            feature_name=f"{position}_change_direction",
            feature_group="change",
            metric="direction",
            value=direction,
        ),
        ChangeTrendFeatureRecord(
            position=position,
            window=None,
            feature_name=f"{position}_changed",
            feature_group="change",
            metric="changed",
            value=changed,
        ),
    ]


def _calculate_mean(
    values: tuple[int, ...],
) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)


def _calculate_std(
    values: tuple[int, ...],
) -> float | None:
    if not values:
        return None

    mean = _calculate_mean(values)

    if mean is None:
        return None

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / len(values)

    return sqrt(variance)


def _calculate_slope(
    values: tuple[int, ...],
) -> float | None:
    """
    Calculate simple least-squares slope.

    X values are observation indexes:
        0, 1, 2, ...

    Y values are the position digits.

    A single observation has no measurable slope.
    """
    if len(values) < 2:
        return None

    x_values = tuple(range(len(values)))

    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(values) / len(values)

    numerator = sum(
        (x - x_mean) * (y - y_mean)
        for x, y in zip(x_values, values)
    )

    denominator = sum(
        (x - x_mean) ** 2
        for x in x_values
    )

    if denominator == 0:
        return None

    return numerator / denominator


def _build_trend_records(
    observations: tuple[HistoricalFeatureObservation, ...],
    position: str,
    window: int,
) -> list[ChangeTrendFeatureRecord]:
    """
    Build trend statistics over the latest observation-count window.
    """
    values = _position_values(
        observations,
        position,
    )

    selected = values[-window:]

    if not selected:
        mean = None
        minimum = None
        maximum = None
        value_range = None
        standard_deviation = None
        first_to_last_change = None
        slope = None
    else:
        selected_tuple = tuple(selected)

        mean = _calculate_mean(
            selected_tuple
        )

        minimum = min(selected_tuple)
        maximum = max(selected_tuple)

        value_range = maximum - minimum

        standard_deviation = _calculate_std(
            selected_tuple
        )

        if len(selected_tuple) >= 2:
            first_to_last_change = (
                selected_tuple[-1]
                - selected_tuple[0]
            )
        else:
            first_to_last_change = None

        slope = _calculate_slope(
            selected_tuple
        )

    metrics = (
        ("mean", mean),
        ("min", minimum),
        ("max", maximum),
        ("range", value_range),
        ("std", standard_deviation),
        ("change", first_to_last_change),
        ("slope", slope),
    )

    return [
        ChangeTrendFeatureRecord(
            position=position,
            window=window,
            feature_name=(
                f"{position}_trend_{metric}_{window}"
            ),
            feature_group="trend",
            metric=metric,
            value=value,
        )
        for metric, value in metrics
    ]


def build_change_trend_features(
    history: tuple[HistoricalFeatureObservation, ...],
    target_date: date,
    config: FeatureConfig,
) -> ChangeTrendFeatureResult:
    """
    Build point-in-time-safe change and trend features.
    """
    _validate_history(history)
    _validate_target_date(target_date)
    _validate_config(config)

    observations = _historical_observations_before(
        history,
        target_date,
    )

    records: list[ChangeTrendFeatureRecord] = []

    if config.change_features_enabled:
        for position in config.positions:
            records.extend(
                _build_change_records(
                    observations=observations,
                    position=position,
                )
            )

    if config.trend_features_enabled:
        for position in config.positions:
            for window in config.trend_windows:
                records.extend(
                    _build_trend_records(
                        observations=observations,
                        position=position,
                        window=window,
                    )
                )

    return ChangeTrendFeatureResult(
        target_date=target_date,
        records=tuple(records),
    )


def get_change_trend_feature_value(
    result: ChangeTrendFeatureResult,
    feature_name: str,
) -> Any:
    """Return one change/trend feature value."""
    if not isinstance(
        result,
        ChangeTrendFeatureResult,
    ):
        raise TypeError(
            "result must be a ChangeTrendFeatureResult."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Change/trend feature not found: {feature_name}"
    )


def get_change_trend_feature_names(
    result: ChangeTrendFeatureResult,
) -> tuple[str, ...]:
    """Return deterministic feature names."""
    if not isinstance(
        result,
        ChangeTrendFeatureResult,
    ):
        raise TypeError(
            "result must be a ChangeTrendFeatureResult."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_change_trend_feature_values(
    result: ChangeTrendFeatureResult,
) -> dict[str, Any]:
    """Return feature name/value mapping."""
    if not isinstance(
        result,
        ChangeTrendFeatureResult,
    ):
        raise TypeError(
            "result must be a ChangeTrendFeatureResult."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }