"""
NeuroLytics - Recency Bucket Features

Phase 14.12:
Classify observation-count recency into deterministic buckets.

This module is additive to the Phase 13/14 recency framework.

Rules:
- Only observations before target_date are used.
- Observation-count semantics are preserved.
- Zero is a valid digit.
- Missing calendar dates do not create observations.
- Unseen digits are explicitly represented as UNSEEN.
- Bucket boundaries are configurable.
- Feature names are deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from features.feature_config import FeatureConfig
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)


DIGITS: tuple[int, ...] = tuple(range(10))

DEFAULT_BUCKET_BOUNDARIES: tuple[int, ...] = (3, 7, 14)

UNSEEN_BUCKET = "UNSEEN"


@dataclass(frozen=True)
class RecencyBucketFeatureRecord:
    """One recency bucket feature."""

    position: str
    digit: int
    lookback: int
    feature_name: str
    metric: str
    value: Any


@dataclass(frozen=True)
class RecencyBucketFeatureResult:
    """Complete recency bucket feature result."""

    target_date: date
    records: tuple[RecencyBucketFeatureRecord, ...]


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


def _validate_boundaries(
    boundaries: tuple[int, ...],
) -> None:
    if not isinstance(boundaries, tuple):
        raise TypeError(
            "recency_bucket_boundaries must be a tuple."
        )

    if not boundaries:
        raise ValueError(
            "recency_bucket_boundaries must contain at least one boundary."
        )

    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        for value in boundaries
    ):
        raise ValueError(
            "recency_bucket_boundaries must contain only integers."
        )

    if any(value < 0 for value in boundaries):
        raise ValueError(
            "recency_bucket_boundaries must contain only "
            "non-negative integers."
        )

    if tuple(sorted(boundaries)) != boundaries:
        raise ValueError(
            "recency_bucket_boundaries must be strictly increasing."
        )

    if len(set(boundaries)) != len(boundaries):
        raise ValueError(
            "recency_bucket_boundaries must be strictly increasing."
        )


def _get_boundaries(
    config: FeatureConfig,
) -> tuple[int, ...]:
    boundaries = config.recency_bucket_boundaries

    _validate_boundaries(boundaries)

    return boundaries


def _get_bucket_labels(
    boundaries: tuple[int, ...],
) -> tuple[str, ...]:
    labels: list[str] = []

    labels.append(
        f"RECENT_0_{boundaries[0]}"
    )

    for index in range(1, len(boundaries)):
        previous_boundary = boundaries[index - 1]
        current_boundary = boundaries[index]

        labels.append(
            f"RECENT_{previous_boundary + 1}_{current_boundary}"
        )

    labels.append(
        f"STALE_{boundaries[-1] + 1}_PLUS"
    )

    return tuple(labels)


def _classify_distance(
    distance: int | None,
    boundaries: tuple[int, ...],
) -> tuple[str, int]:
    """
    Return bucket label and bucket index.

    Normal buckets use indexes 0..N-1.

    UNSEEN uses index N.
    """
    if distance is None:
        return (
            UNSEEN_BUCKET,
            len(boundaries),
        )

    if not isinstance(distance, int) or isinstance(distance, bool):
        raise TypeError(
            "recency distance must be an integer or None."
        )

    if distance < 0:
        raise ValueError(
            "recency distance cannot be negative."
        )

    labels = _get_bucket_labels(boundaries)

    for index, boundary in enumerate(boundaries):
        if distance <= boundary:
            return labels[index], index

    return (
        labels[-1],
        len(labels) - 1,
    )


def _get_observation_distance(
    history: tuple[HistoricalFeatureObservation, ...],
    target_date: date,
    position: str,
    digit: int,
    lookback: int,
) -> int | None:
    """
    Calculate observation-count distance.

    Latest historical observation:
        distance = 0

    Previous historical observation:
        distance = 1

    And so on.

    Only observations strictly before target_date are used.
    """
    position_index = (
        HistoricalFeatureObservation.__annotations__
    )

    del position_index

    observations = tuple(
        observation
        for observation in history
        if observation.result_date < target_date
    )

    selected = observations[-lookback:]

    positions = (
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    )

    index = positions.index(position)

    for distance, observation in enumerate(
        reversed(selected)
    ):
        if observation.positions[index] == digit:
            return distance

    return None


def _build_feature_name(
    position: str,
    digit: int,
    lookback: int,
    metric: str,
) -> str:
    return (
        f"{position}_digit_{digit}_recency_bucket_"
        f"{metric}_{lookback}"
    )


def _build_records_for_combination(
    history: tuple[HistoricalFeatureObservation, ...],
    target_date: date,
    position: str,
    digit: int,
    lookback: int,
    boundaries: tuple[int, ...],
) -> list[RecencyBucketFeatureRecord]:
    distance = _get_observation_distance(
        history=history,
        target_date=target_date,
        position=position,
        digit=digit,
        lookback=lookback,
    )

    bucket_label, bucket_index = _classify_distance(
        distance=distance,
        boundaries=boundaries,
    )

    labels = _get_bucket_labels(boundaries)

    records = [
        RecencyBucketFeatureRecord(
            position=position,
            digit=digit,
            lookback=lookback,
            feature_name=_build_feature_name(
                position,
                digit,
                lookback,
                "label",
            ),
            metric="label",
            value=bucket_label,
        ),
        RecencyBucketFeatureRecord(
            position=position,
            digit=digit,
            lookback=lookback,
            feature_name=_build_feature_name(
                position,
                digit,
                lookback,
                "index",
            ),
            metric="index",
            value=bucket_index,
        ),
    ]

    for index, label in enumerate(labels):
        records.append(
            RecencyBucketFeatureRecord(
                position=position,
                digit=digit,
                lookback=lookback,
                feature_name=_build_feature_name(
                    position,
                    digit,
                    lookback,
                    f"is_{label.lower()}",
                ),
                metric=f"is_{label.lower()}",
                value=1 if bucket_index == index else 0,
            )
        )

    records.append(
        RecencyBucketFeatureRecord(
            position=position,
            digit=digit,
            lookback=lookback,
            feature_name=_build_feature_name(
                position,
                digit,
                lookback,
                "is_unseen",
            ),
            metric="is_unseen",
            value=1 if distance is None else 0,
        )
    )

    return records


def build_recency_bucket_features(
    history: tuple[HistoricalFeatureObservation, ...],
    target_date: date,
    config: FeatureConfig,
) -> RecencyBucketFeatureResult:
    """
    Build point-in-time-safe recency bucket features.
    """
    _validate_history(history)
    _validate_target_date(target_date)
    _validate_config(config)

    if not config.recency_buckets_enabled:
        return RecencyBucketFeatureResult(
            target_date=target_date,
            records=(),
        )

    boundaries = _get_boundaries(config)

    records: list[RecencyBucketFeatureRecord] = []

    for position in config.positions:
        for digit in DIGITS:
            for lookback in config.recency_lookbacks:
                records.extend(
                    _build_records_for_combination(
                        history=history,
                        target_date=target_date,
                        position=position,
                        digit=digit,
                        lookback=lookback,
                        boundaries=boundaries,
                    )
                )

    return RecencyBucketFeatureResult(
        target_date=target_date,
        records=tuple(records),
    )


def get_recency_bucket_feature_value(
    result: RecencyBucketFeatureResult,
    feature_name: str,
) -> Any:
    """Return one feature value."""
    if not isinstance(
        result,
        RecencyBucketFeatureResult,
    ):
        raise TypeError(
            "result must be a RecencyBucketFeatureResult."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Recency bucket feature not found: {feature_name}"
    )


def get_recency_bucket_feature_names(
    result: RecencyBucketFeatureResult,
) -> tuple[str, ...]:
    """Return deterministic feature names."""
    if not isinstance(
        result,
        RecencyBucketFeatureResult,
    ):
        raise TypeError(
            "result must be a RecencyBucketFeatureResult."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_recency_bucket_feature_values(
    result: RecencyBucketFeatureResult,
) -> dict[str, Any]:
    """Return feature name/value mapping."""
    if not isinstance(
        result,
        RecencyBucketFeatureResult,
    ):
        raise TypeError(
            "result must be a RecencyBucketFeatureResult."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }