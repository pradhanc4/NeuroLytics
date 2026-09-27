from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.feature_config import FeatureConfig, validate_feature_config
from features.point_in_time import (
    PointInTimeHistory,
    get_point_in_time_observations,
)


@dataclass(frozen=True)
class PositionFeatureRecord:
    """Position-level feature values for one target date."""

    position: str
    feature_name: str
    value: int | float | None


@dataclass(frozen=True)
class PositionFeatureResult:
    """Complete position-feature output for one target date."""

    target_date: date
    records: tuple[PositionFeatureRecord, ...]


def _build_feature_name(
    position: str,
    feature: str,
) -> str:
    """Build a deterministic position-feature name."""

    return f"{position}_{feature}"


def _get_latest_value(
    history: PointInTimeHistory,
    position_index: int,
) -> int | None:
    """Return the latest historical value before the target date."""

    observations = get_point_in_time_observations(history)

    if not observations:
        return None

    return observations[-1].positions[position_index]


def _is_even(value: int | None) -> int | None:
    """Return 1 for even, 0 for odd, and None when unavailable."""

    if value is None:
        return None

    return int(value % 2 == 0)


def _is_zero(value: int | None) -> int | None:
    """Return 1 when the value is zero."""

    if value is None:
        return None

    return int(value == 0)


def _is_high(value: int | None) -> int | None:
    """
    Return 1 for digits 5-9 and 0 for digits 0-4.
    """

    if value is None:
        return None

    return int(value >= 5)


def _calculate_position_mean(
    history: PointInTimeHistory,
    position_index: int,
) -> float | None:
    """Calculate the historical mean for one position."""

    observations = get_point_in_time_observations(history)

    if not observations:
        return None

    values = tuple(
        observation.positions[position_index]
        for observation in observations
    )

    return sum(values) / len(values)


def _calculate_position_minimum(
    history: PointInTimeHistory,
    position_index: int,
) -> int | None:
    """Calculate the historical minimum for one position."""

    observations = get_point_in_time_observations(history)

    if not observations:
        return None

    values = tuple(
        observation.positions[position_index]
        for observation in observations
    )

    return min(values)


def _calculate_position_maximum(
    history: PointInTimeHistory,
    position_index: int,
) -> int | None:
    """Calculate the historical maximum for one position."""

    observations = get_point_in_time_observations(history)

    if not observations:
        return None

    values = tuple(
        observation.positions[position_index]
        for observation in observations
    )

    return max(values)


def build_position_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> PositionFeatureResult:
    """
    Build leakage-safe position features.

    All historical summaries use only observations strictly before
    the target date.
    """

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    validate_feature_config(config)

    records: list[PositionFeatureRecord] = []

    for position_index, position in enumerate(
        config.positions
    ):
        latest_value = _get_latest_value(
            history,
            position_index,
        )

        features = (
            (
                "latest_value",
                latest_value,
            ),
            (
                "latest_is_even",
                _is_even(latest_value),
            ),
            (
                "latest_is_zero",
                _is_zero(latest_value),
            ),
            (
                "latest_is_high",
                _is_high(latest_value),
            ),
            (
                "historical_mean",
                _calculate_position_mean(
                    history,
                    position_index,
                ),
            ),
            (
                "historical_min",
                _calculate_position_minimum(
                    history,
                    position_index,
                ),
            ),
            (
                "historical_max",
                _calculate_position_maximum(
                    history,
                    position_index,
                ),
            ),
        )

        for feature, value in features:
            records.append(
                PositionFeatureRecord(
                    position=position,
                    feature_name=_build_feature_name(
                        position,
                        feature,
                    ),
                    value=value,
                )
            )

    return PositionFeatureResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_position_feature_value(
    result: PositionFeatureResult,
    feature_name: str,
) -> int | float | None:
    """Return one position feature value."""

    if not isinstance(
        result,
        PositionFeatureResult,
    ):
        raise TypeError(
            "result must be a PositionFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Position feature not found: {feature_name}"
    )


def get_position_feature_names(
    result: PositionFeatureResult,
) -> tuple[str, ...]:
    """Return all generated position feature names."""

    if not isinstance(
        result,
        PositionFeatureResult,
    ):
        raise TypeError(
            "result must be a PositionFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )