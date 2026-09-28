from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import sqrt

from features.feature_config import (
    FeatureConfig,
    get_recency_lookbacks,
    validate_feature_config,
)
from features.point_in_time import (
    PointInTimeHistory,
    get_point_in_time_observations,
)

DIGITS = tuple(range(10))


@dataclass(frozen=True)
class RecencyDistributionFeatureRecord:
    """One recency-distribution metric."""

    position: str
    digit: int
    lookback: int
    feature_name: str
    metric: str
    value: int | float | None

    occurrence_count: int
    occurrence_rate: float
    distances: tuple[int, ...]


@dataclass(frozen=True)
class RecencyDistributionFeatureResult:
    """Complete recency-distribution output."""

    target_date: date
    records: tuple[RecencyDistributionFeatureRecord, ...]


def _build_feature_name(
    position: str,
    digit: int,
    lookback: int,
    metric: str,
) -> str:
    return (
        f"{position}_digit_{digit}_"
        f"recency_distribution_{metric}_{lookback}"
    )


def _calculate_distances(
    history: PointInTimeHistory,
    position_index: int,
    digit: int,
    lookback: int,
) -> tuple[int, ...]:
    """
    Return observation distances for every occurrence.

    Distance 0 means the latest historical observation.
    Distance increases backward through the selected window.
    """

    observations = get_point_in_time_observations(history)

    if not observations:
        return ()

    selected = observations[-lookback:]

    distances: list[int] = []

    for distance, observation in enumerate(
        reversed(selected)
    ):
        if observation.positions[position_index] == digit:
            distances.append(distance)

    return tuple(distances)


def _calculate_metrics(
    distances: tuple[int, ...],
    lookback: int,
) -> tuple[int, float, float | None, int | None, int | None, float | None, int | None]:
    """
    Calculate distribution statistics from occurrence distances.
    """

    occurrence_count = len(distances)

    occurrence_rate = (
        occurrence_count / float(lookback)
    )

    if not distances:
        return (
            0,
            0.0,
            None,
            None,
            None,
            None,
            None,
        )

    mean_distance = (
        sum(distances) / float(occurrence_count)
    )

    min_distance = min(distances)
    max_distance = max(distances)

    variance = sum(
        (distance - mean_distance) ** 2
        for distance in distances
    ) / float(occurrence_count)

    std_distance = sqrt(variance)

    span = max_distance - min_distance

    return (
        occurrence_count,
        occurrence_rate,
        mean_distance,
        min_distance,
        max_distance,
        std_distance,
        span,
    )


def build_recency_distribution_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> RecencyDistributionFeatureResult:
    """
    Build leakage-safe recency-distribution features.

    Features describe the distribution of all occurrences of each
    digit inside each configured observation-count lookback.

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

    lookbacks = get_recency_lookbacks(config)

    records: list[
        RecencyDistributionFeatureRecord
    ] = []

    for lookback in lookbacks:
        for position_index, position in enumerate(
            config.positions
        ):
            for digit in DIGITS:
                distances = _calculate_distances(
                    history=history,
                    position_index=position_index,
                    digit=digit,
                    lookback=lookback,
                )

                (
                    occurrence_count,
                    occurrence_rate,
                    mean_distance,
                    min_distance,
                    max_distance,
                    std_distance,
                    span,
                ) = _calculate_metrics(
                    distances=distances,
                    lookback=lookback,
                )

                metrics = (
                    (
                        "count",
                        occurrence_count,
                    ),
                    (
                        "rate",
                        occurrence_rate,
                    ),
                    (
                        "mean_distance",
                        mean_distance,
                    ),
                    (
                        "min_distance",
                        min_distance,
                    ),
                    (
                        "max_distance",
                        max_distance,
                    ),
                    (
                        "std_distance",
                        std_distance,
                    ),
                    (
                        "span",
                        span,
                    ),
                )

                for metric, value in metrics:
                    records.append(
                        RecencyDistributionFeatureRecord(
                            position=position,
                            digit=digit,
                            lookback=lookback,
                            feature_name=_build_feature_name(
                                position,
                                digit,
                                lookback,
                                metric,
                            ),
                            metric=metric,
                            value=value,
                            occurrence_count=occurrence_count,
                            occurrence_rate=occurrence_rate,
                            distances=distances,
                        )
                    )

    return RecencyDistributionFeatureResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_recency_distribution_feature_value(
    result: RecencyDistributionFeatureResult,
    feature_name: str,
) -> int | float | None:
    """Return one recency-distribution feature value."""

    if not isinstance(
        result,
        RecencyDistributionFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "RecencyDistributionFeatureResult instance."
        )

    if not isinstance(
        feature_name,
        str,
    ):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Recency distribution feature not found: "
        f"{feature_name}"
    )


def get_recency_distribution_feature_names(
    result: RecencyDistributionFeatureResult,
) -> tuple[str, ...]:
    """Return all recency-distribution feature names."""

    if not isinstance(
        result,
        RecencyDistributionFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "RecencyDistributionFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_recency_distribution_feature_values(
    result: RecencyDistributionFeatureResult,
) -> dict[str, int | float | None]:
    """Return all recency-distribution features as a mapping."""

    if not isinstance(
        result,
        RecencyDistributionFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "RecencyDistributionFeatureResult instance."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }