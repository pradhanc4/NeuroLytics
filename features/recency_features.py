from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.feature_config import FeatureConfig, validate_feature_config
from features.point_in_time import (
    PointInTimeHistory,
    get_point_in_time_observations,
)


POSITIONS = (
    "col1",
    "col2",
    "col3",
    "col4",
    "col5",
    "col6",
    "col7",
    "col8",
)

DIGITS = tuple(range(10))


@dataclass(frozen=True)
class RecencyFeatureRecord:
    """One digit recency feature for one position."""

    position: str
    digit: int
    feature_name: str
    observations_since_last_seen: int | None
    seen_within_lookback: bool


@dataclass(frozen=True)
class RecencyFeatureResult:
    """Complete recency-feature output for one target date."""

    target_date: date
    lookback: int
    records: tuple[RecencyFeatureRecord, ...]


def _build_feature_name(
    position: str,
    digit: int,
) -> str:
    """Build a deterministic recency feature name."""

    return f"{position}_digit_{digit}_recency"


def _calculate_recency(
    history: PointInTimeHistory,
    position_index: int,
    digit: int,
    lookback: int,
) -> tuple[int | None, bool]:
    """
    Calculate observations since the last occurrence of a digit.

    The most recent available observation before the target date
    has distance 0, the previous observation has distance 1, etc.

    Only the configured lookback observations are considered.
    """

    observations = get_point_in_time_observations(history)

    if not observations:
        return None, False

    selected = observations[-lookback:]

    for distance, observation in enumerate(
        reversed(selected)
    ):
        if observation.positions[position_index] == digit:
            return distance, True

    return None, False


def build_recency_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> RecencyFeatureResult:
    """
    Build leakage-safe digit recency features.

    Only observations strictly before the target date are used.
    """

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    validate_feature_config(config)

    records: list[RecencyFeatureRecord] = []

    for position_index, position in enumerate(
        config.positions
    ):
        for digit in DIGITS:
            recency, seen = _calculate_recency(
                history=history,
                position_index=position_index,
                digit=digit,
                lookback=config.recency_lookback,
            )

            records.append(
                RecencyFeatureRecord(
                    position=position,
                    digit=digit,
                    feature_name=_build_feature_name(
                        position,
                        digit,
                    ),
                    observations_since_last_seen=recency,
                    seen_within_lookback=seen,
                )
            )

    return RecencyFeatureResult(
        target_date=history.target_date,
        lookback=config.recency_lookback,
        records=tuple(records),
    )


def get_recency_feature_value(
    result: RecencyFeatureResult,
    feature_name: str,
) -> int | None:
    """Return one recency value by feature name."""

    if not isinstance(
        result,
        RecencyFeatureResult,
    ):
        raise TypeError(
            "result must be a RecencyFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.observations_since_last_seen

    raise ValueError(
        f"Recency feature not found: {feature_name}"
    )


def get_recency_feature_seen(
    result: RecencyFeatureResult,
    feature_name: str,
) -> bool:
    """Return whether a digit was seen within the configured lookback."""

    if not isinstance(
        result,
        RecencyFeatureResult,
    ):
        raise TypeError(
            "result must be a RecencyFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.seen_within_lookback

    raise ValueError(
        f"Recency feature not found: {feature_name}"
    )


def get_recency_feature_names(
    result: RecencyFeatureResult,
) -> tuple[str, ...]:
    """Return all generated recency feature names."""

    if not isinstance(
        result,
        RecencyFeatureResult,
    ):
        raise TypeError(
            "result must be a RecencyFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )