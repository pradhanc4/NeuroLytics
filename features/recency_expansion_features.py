from __future__ import annotations

from dataclasses import dataclass
from datetime import date

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
class RecencyExpansionFeatureRecord:
    """One expanded recency metric for a position, digit, and lookback."""

    position: str
    digit: int
    lookback: int
    feature_name: str
    metric: str
    value: int | float | bool | None
    occurrence_count: int
    occurrence_rate: float
    observations_since_last_seen: int | None
    seen_within_lookback: bool


@dataclass(frozen=True)
class RecencyExpansionFeatureResult:
    """Complete expanded recency output for one target date."""

    target_date: date
    records: tuple[RecencyExpansionFeatureRecord, ...]


def _build_feature_name(
    position: str,
    digit: int,
    lookback: int,
    metric: str,
) -> str:
    return (
        f"{position}_digit_{digit}_"
        f"recency_{metric}_{lookback}"
    )


def _calculate_metrics(
    history: PointInTimeHistory,
    position_index: int,
    digit: int,
    lookback: int,
) -> tuple[int, float, int | None, bool]:
    """
    Calculate expanded recency metrics.

    Recency distance is based on observation order, matching Phase 13.

    The occurrence rate uses the configured lookback as the denominator.
    Therefore, if only 1 historical observation exists for a lookback of 3,
    one occurrence has rate 1/3.
    """

    observations = get_point_in_time_observations(history)

    if not observations:
        return 0, 0.0, None, False

    selected = observations[-lookback:]

    occurrence_count = sum(
        1
        for observation in selected
        if observation.positions[position_index] == digit
    )

    occurrence_rate = occurrence_count / float(lookback)

    last_distance: int | None = None

    for distance, observation in enumerate(
        reversed(selected)
    ):
        if observation.positions[position_index] == digit:
            last_distance = distance
            break

    return (
        occurrence_count,
        occurrence_rate,
        last_distance,
        last_distance is not None,
    )


def build_recency_expansion_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> RecencyExpansionFeatureResult:
    """
    Build leakage-safe expanded recency features.

    Four metrics are generated for every:

        position × digit × lookback

    Metrics:

        count
        rate
        last_distance
        seen
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

    records: list[RecencyExpansionFeatureRecord] = []

    for lookback in lookbacks:
        for position_index, position in enumerate(
            config.positions
        ):
            for digit in DIGITS:
                (
                    occurrence_count,
                    occurrence_rate,
                    last_distance,
                    seen,
                ) = _calculate_metrics(
                    history=history,
                    position_index=position_index,
                    digit=digit,
                    lookback=lookback,
                )

                records.extend(
                    (
                        RecencyExpansionFeatureRecord(
                            position=position,
                            digit=digit,
                            lookback=lookback,
                            feature_name=_build_feature_name(
                                position,
                                digit,
                                lookback,
                                "count",
                            ),
                            metric="count",
                            value=occurrence_count,
                            occurrence_count=occurrence_count,
                            occurrence_rate=occurrence_rate,
                            observations_since_last_seen=last_distance,
                            seen_within_lookback=seen,
                        ),
                        RecencyExpansionFeatureRecord(
                            position=position,
                            digit=digit,
                            lookback=lookback,
                            feature_name=_build_feature_name(
                                position,
                                digit,
                                lookback,
                                "rate",
                            ),
                            metric="rate",
                            value=occurrence_rate,
                            occurrence_count=occurrence_count,
                            occurrence_rate=occurrence_rate,
                            observations_since_last_seen=last_distance,
                            seen_within_lookback=seen,
                        ),
                        RecencyExpansionFeatureRecord(
                            position=position,
                            digit=digit,
                            lookback=lookback,
                            feature_name=_build_feature_name(
                                position,
                                digit,
                                lookback,
                                "last_distance",
                            ),
                            metric="last_distance",
                            value=last_distance,
                            occurrence_count=occurrence_count,
                            occurrence_rate=occurrence_rate,
                            observations_since_last_seen=last_distance,
                            seen_within_lookback=seen,
                        ),
                        RecencyExpansionFeatureRecord(
                            position=position,
                            digit=digit,
                            lookback=lookback,
                            feature_name=_build_feature_name(
                                position,
                                digit,
                                lookback,
                                "seen",
                            ),
                            metric="seen",
                            value=seen,
                            occurrence_count=occurrence_count,
                            occurrence_rate=occurrence_rate,
                            observations_since_last_seen=last_distance,
                            seen_within_lookback=seen,
                        ),
                    )
                )

    return RecencyExpansionFeatureResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_recency_expansion_feature_value(
    result: RecencyExpansionFeatureResult,
    feature_name: str,
) -> int | float | bool | None:
    """Return one expanded recency feature value."""

    if not isinstance(
        result,
        RecencyExpansionFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "RecencyExpansionFeatureResult instance."
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
        f"Recency expansion feature not found: "
        f"{feature_name}"
    )


def get_recency_expansion_feature_names(
    result: RecencyExpansionFeatureResult,
) -> tuple[str, ...]:
    """Return all expanded recency feature names."""

    if not isinstance(
        result,
        RecencyExpansionFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "RecencyExpansionFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_recency_expansion_feature_values(
    result: RecencyExpansionFeatureResult,
) -> dict[
    str,
    int | float | bool | None,
]:
    """Return all expanded recency features as a mapping."""

    if not isinstance(
        result,
        RecencyExpansionFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "RecencyExpansionFeatureResult instance."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }