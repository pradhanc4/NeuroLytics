from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.feature_config import FeatureConfig, validate_feature_config
from features.point_in_time import (
    PointInTimeHistory,
    get_point_in_time_observations,
)


@dataclass(frozen=True)
class RollingFeatureRecord:
    """One rolling statistical feature for one position and window."""

    position: str
    window: int
    feature_name: str
    observation_count: int
    mean: float | None
    minimum: int | None
    maximum: int | None


@dataclass(frozen=True)
class RollingFeatureResult:
    """Complete rolling-feature output for one target date."""

    target_date: date
    records: tuple[RollingFeatureRecord, ...]


def _build_feature_name(
    position: str,
    window: int,
    statistic: str,
) -> str:
    """Build a deterministic rolling-feature name."""

    return f"{position}_rolling_{window}_{statistic}"


def _get_window_values(
    history: PointInTimeHistory,
    position_index: int,
    window: int,
) -> tuple[int, ...]:
    """
    Return the most recent available observations for a position.

    Only observations strictly before the target date are considered.
    """

    observations = get_point_in_time_observations(history)

    if not observations:
        return ()

    selected = observations[-window:]

    return tuple(
        observation.positions[position_index]
        for observation in selected
    )


def _calculate_mean(
    values: tuple[int, ...],
) -> float | None:
    """Calculate the arithmetic mean."""

    if not values:
        return None

    return sum(values) / len(values)


def _calculate_minimum(
    values: tuple[int, ...],
) -> int | None:
    """Calculate the minimum value."""

    if not values:
        return None

    return min(values)


def _calculate_maximum(
    values: tuple[int, ...],
) -> int | None:
    """Calculate the maximum value."""

    if not values:
        return None

    return max(values)


def build_rolling_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> RollingFeatureResult:
    """
    Build leakage-safe rolling statistical features.

    Rolling windows use only observations available before the
    target date. If fewer observations than the requested window
    exist, the available historical observations are used.
    """

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    validate_feature_config(config)

    records: list[RollingFeatureRecord] = []

    for position_index, position in enumerate(
        config.positions
    ):
        for window in config.rolling_windows:
            values = _get_window_values(
                history,
                position_index,
                window,
            )

            records.append(
                RollingFeatureRecord(
                    position=position,
                    window=window,
                    feature_name=_build_feature_name(
                        position,
                        window,
                        "mean",
                    ),
                    observation_count=len(values),
                    mean=_calculate_mean(values),
                    minimum=_calculate_minimum(values),
                    maximum=_calculate_maximum(values),
                )
            )

            records.append(
                RollingFeatureRecord(
                    position=position,
                    window=window,
                    feature_name=_build_feature_name(
                        position,
                        window,
                        "min",
                    ),
                    observation_count=len(values),
                    mean=None,
                    minimum=_calculate_minimum(values),
                    maximum=None,
                )
            )

            records.append(
                RollingFeatureRecord(
                    position=position,
                    window=window,
                    feature_name=_build_feature_name(
                        position,
                        window,
                        "max",
                    ),
                    observation_count=len(values),
                    mean=None,
                    minimum=None,
                    maximum=_calculate_maximum(values),
                )
            )

    return RollingFeatureResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_rolling_feature_value(
    result: RollingFeatureResult,
    feature_name: str,
) -> float | int | None:
    """Return the statistic represented by a rolling feature name."""

    if not isinstance(
        result,
        RollingFeatureResult,
    ):
        raise TypeError(
            "result must be a RollingFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            if feature_name.endswith("_mean"):
                return record.mean

            if feature_name.endswith("_min"):
                return record.minimum

            if feature_name.endswith("_max"):
                return record.maximum

    raise ValueError(
        f"Rolling feature not found: {feature_name}"
    )


def get_rolling_feature_names(
    result: RollingFeatureResult,
) -> tuple[str, ...]:
    """Return all generated rolling feature names."""

    if not isinstance(
        result,
        RollingFeatureResult,
    ):
        raise TypeError(
            "result must be a RollingFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )