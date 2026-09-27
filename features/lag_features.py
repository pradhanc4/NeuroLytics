from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from features.feature_config import FeatureConfig, validate_feature_config
from features.point_in_time import (
    PointInTimeHistory,
    get_point_in_time_observations,
)


@dataclass(frozen=True)
class LagFeatureRecord:
    """One lag feature value for one historical position."""

    position: str
    lag: int
    feature_name: str
    value: int | None


@dataclass(frozen=True)
class LagFeatureResult:
    """Complete lag-feature output for one point in time."""

    target_date: date
    records: tuple[LagFeatureRecord, ...]


def _build_feature_name(
    position: str,
    lag: int,
) -> str:
    """Build a deterministic lag-feature name."""

    return f"{position}_lag_{lag}"


def _get_lag_value(
    history: PointInTimeHistory,
    position_index: int,
    lag: int,
) -> int | None:
    """
    Return the value at the requested historical lag.

    lag=1 means the most recent observation before the target date.
    """

    observations = get_point_in_time_observations(history)

    if len(observations) < lag:
        return None

    observation = observations[-lag]

    return observation.positions[position_index]


def build_lag_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> LagFeatureResult:
    """
    Build leakage-safe lag features.

    Only observations already available before the target date are used.
    """

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    validate_feature_config(config)

    records: list[LagFeatureRecord] = []

    for position_index, position in enumerate(
        config.positions
    ):
        for lag in config.lag_windows:
            records.append(
                LagFeatureRecord(
                    position=position,
                    lag=lag,
                    feature_name=_build_feature_name(
                        position,
                        lag,
                    ),
                    value=_get_lag_value(
                        history,
                        position_index,
                        lag,
                    ),
                )
            )

    return LagFeatureResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_lag_feature_value(
    result: LagFeatureResult,
    feature_name: str,
) -> int | None:
    """Return one lag feature value by deterministic feature name."""

    if not isinstance(
        result,
        LagFeatureResult,
    ):
        raise TypeError(
            "result must be a LagFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Lag feature not found: {feature_name}"
    )


def get_lag_feature_names(
    result: LagFeatureResult,
) -> tuple[str, ...]:
    """Return all generated lag feature names."""

    if not isinstance(
        result,
        LagFeatureResult,
    ):
        raise TypeError(
            "result must be a LagFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_lag_feature_values(
    result: LagFeatureResult,
) -> Mapping[str, int | None]:
    """Return lag features as a deterministic name-to-value mapping."""

    if not isinstance(
        result,
        LagFeatureResult,
    ):
        raise TypeError(
            "result must be a LagFeatureResult instance."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }