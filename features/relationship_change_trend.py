from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import combinations

from analytics.cross_position_relationship_change_detection import (
    build_cross_position_relationship_change_detection,
)
from analytics.cross_position_relationship_stability import (
    build_cross_position_relationship_stability,
)
from features.feature_config import (
    FeatureConfig,
    validate_feature_config,
)
from features.point_in_time import (
    HistoricalFeatureObservation,
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

TREND_DIRECTIONS = (
    "INCREASING",
    "DECREASING",
    "STABLE",
    "INSUFFICIENT_DATA",
)


@dataclass(frozen=True)
class RelationshipChangeTrendRecord:
    """Relationship change/trend between two configured positions."""

    position_a: str
    position_b: str

    window_size: int
    previous_window_index: int
    current_window_index: int

    previous_correlation: float | None
    current_correlation: float | None

    correlation_change: float | None
    absolute_correlation_change: float | None

    previous_direction: str
    current_direction: str

    previous_strength: str
    current_strength: str

    direction_changed: bool
    strength_changed: bool
    relationship_changed: bool

    trend_direction: str
    feature_name: str


@dataclass(frozen=True)
class RelationshipChangeTrendResult:
    """Complete Phase 15.12 relationship change/trend output."""

    target_date: date
    records: tuple[RelationshipChangeTrendRecord, ...]


def _validate_position(position: str) -> None:
    if not isinstance(position, str):
        raise TypeError(
            "position must be a string."
        )

    if not position.strip():
        raise ValueError(
            "position must not be empty."
        )

    if position not in POSITIONS:
        raise ValueError(
            f"Unsupported position: {position}."
        )


def _validate_history(
    history: PointInTimeHistory,
) -> None:
    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )


def _validate_trend_window(
    window_size: int,
) -> None:
    if isinstance(window_size, bool):
        raise TypeError(
            "trend window must be an integer."
        )

    if not isinstance(window_size, int):
        raise TypeError(
            "trend window must be an integer."
        )

    if window_size < 2:
        raise ValueError(
            "relationship change/trend window must be at least 2."
        )


def _get_position_index(
    position: str,
) -> int:
    _validate_position(position)

    return POSITIONS.index(position)


def _get_point_in_time_observations(
    history: PointInTimeHistory,
) -> tuple[HistoricalFeatureObservation, ...]:
    """
    Return only observations strictly before the target date.

    The defensive filtering is intentional even when the supplied
    PointInTimeHistory is expected to already be point-in-time safe.
    """

    _validate_history(history)

    observations = get_point_in_time_observations(
        history
    )

    return tuple(
        observation
        for observation in observations
        if observation.result_date < history.target_date
    )


def _build_position_pair_observations(
    observations: tuple[HistoricalFeatureObservation, ...],
    position_a: str,
    position_b: str,
) -> tuple[tuple[int | float | None, int | float | None], ...]:
    """
    Extract one deterministic value pair per historical observation.
    """

    index_a = _get_position_index(position_a)
    index_b = _get_position_index(position_b)

    return tuple(
        (
            observation.positions[index_a],
            observation.positions[index_b],
        )
        for observation in observations
    )


def _build_position_pairs(
    positions: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    """
    Build deterministic unique position pairs.
    """

    for position in positions:
        _validate_position(position)

    return tuple(
        combinations(
            positions,
            2,
        )
    )


def _classify_trend_direction(
    correlation_change: float | None,
) -> str:
    """
    Classify the direction of correlation change.

    No arbitrary threshold is used.

    Positive change:
        INCREASING

    Negative change:
        DECREASING

    Zero change:
        STABLE

    Missing correlation:
        INSUFFICIENT_DATA
    """

    if correlation_change is None:
        return "INSUFFICIENT_DATA"

    if correlation_change > 0.0:
        return "INCREASING"

    if correlation_change < 0.0:
        return "DECREASING"

    return "STABLE"


def _build_feature_name(
    position_a: str,
    position_b: str,
    window_size: int,
    previous_window_index: int,
    current_window_index: int,
) -> str:
    return (
        f"{position_a}_{position_b}_"
        f"relationship_trend_"
        f"window_{window_size}_"
        f"{previous_window_index}_to_"
        f"{current_window_index}"
    )


def _build_record(
    position_a: str,
    position_b: str,
    window_size: int,
    change,
) -> RelationshipChangeTrendRecord:
    trend_direction = _classify_trend_direction(
        change.correlation_change
    )

    return RelationshipChangeTrendRecord(
        position_a=position_a,
        position_b=position_b,
        window_size=window_size,
        previous_window_index=(
            change.previous_window_index
        ),
        current_window_index=(
            change.current_window_index
        ),
        previous_correlation=(
            change.previous_correlation
        ),
        current_correlation=(
            change.current_correlation
        ),
        correlation_change=(
            change.correlation_change
        ),
        absolute_correlation_change=(
            change.absolute_correlation_change
        ),
        previous_direction=(
            change.previous_direction
        ),
        current_direction=(
            change.current_direction
        ),
        previous_strength=(
            change.previous_strength
        ),
        current_strength=(
            change.current_strength
        ),
        direction_changed=(
            change.direction_changed
        ),
        strength_changed=(
            change.strength_changed
        ),
        relationship_changed=(
            change.relationship_changed
        ),
        trend_direction=trend_direction,
        feature_name=_build_feature_name(
            position_a=position_a,
            position_b=position_b,
            window_size=window_size,
            previous_window_index=(
                change.previous_window_index
            ),
            current_window_index=(
                change.current_window_index
            ),
        ),
    )


def _build_relationship_change_records(
    observations: tuple[HistoricalFeatureObservation, ...],
    positions: tuple[str, ...],
    trend_windows: tuple[int, ...],
) -> list[RelationshipChangeTrendRecord]:
    records: list[RelationshipChangeTrendRecord] = []

    position_pairs = _build_position_pairs(
        positions
    )

    for window_size in trend_windows:
        _validate_trend_window(
            window_size
        )

        for position_a, position_b in position_pairs:
            pair_observations = (
                _build_position_pair_observations(
                    observations=observations,
                    position_a=position_a,
                    position_b=position_b,
                )
            )

            stability_result = (
                build_cross_position_relationship_stability(
                    position_a=position_a,
                    position_b=position_b,
                    observations=pair_observations,
                    window_size=window_size,
                )
            )

            change_result = (
                build_cross_position_relationship_change_detection(
                    position_a=position_a,
                    position_b=position_b,
                    windows=stability_result.windows,
                )
            )

            for change in change_result.changes:
                records.append(
                    _build_record(
                        position_a=position_a,
                        position_b=position_b,
                        window_size=window_size,
                        change=change,
                    )
                )

    return records


def build_relationship_change_trend_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> RelationshipChangeTrendResult:
    """
    Build leakage-safe relationship change/trend features.

    Phase 15.12 responsibilities:

    - reuse the existing relationship-window analytics;
    - reuse the existing relationship-change detector;
    - compare consecutive historical relationship windows;
    - expose correlation change and relationship-state changes;
    - classify the raw correlation movement as increasing,
      decreasing, stable, or insufficient data.

    This function does not perform:

    - prediction;
    - probability calculation;
    - Markov modeling;
    - arbitrary change thresholds;
    - future-data access;
    - unified dataset integration.
    """

    _validate_history(history)

    validate_feature_config(
        config
    )

    if not config.relationship_change_trend_features_enabled:
        return RelationshipChangeTrendResult(
            target_date=history.target_date,
            records=(),
        )

    observations = (
        _get_point_in_time_observations(
            history
        )
    )

    if not observations:
        return RelationshipChangeTrendResult(
            target_date=history.target_date,
            records=(),
        )

    records = _build_relationship_change_records(
        observations=observations,
        positions=config.positions,
        trend_windows=config.trend_windows,
    )

    return RelationshipChangeTrendResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_relationship_change_trend_records(
    result: RelationshipChangeTrendResult,
) -> tuple[RelationshipChangeTrendRecord, ...]:
    """Return all relationship change/trend records."""

    if not isinstance(
        result,
        RelationshipChangeTrendResult,
    ):
        raise TypeError(
            "result must be a "
            "RelationshipChangeTrendResult instance."
        )

    return result.records


def get_relationship_change_trend_feature_names(
    result: RelationshipChangeTrendResult,
) -> tuple[str, ...]:
    """Return deterministic relationship change/trend feature names."""

    if not isinstance(
        result,
        RelationshipChangeTrendResult,
    ):
        raise TypeError(
            "result must be a "
            "RelationshipChangeTrendResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_relationship_change_trend_value(
    result: RelationshipChangeTrendResult,
    feature_name: str,
) -> RelationshipChangeTrendRecord:
    """Return one relationship change/trend record by feature name."""

    if not isinstance(
        result,
        RelationshipChangeTrendResult,
    ):
        raise TypeError(
            "result must be a "
            "RelationshipChangeTrendResult instance."
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
            return record

    raise ValueError(
        "Relationship change/trend feature not found: "
        f"{feature_name}"
    )


__all__ = [
    "POSITIONS",
    "TREND_DIRECTIONS",
    "RelationshipChangeTrendRecord",
    "RelationshipChangeTrendResult",
    "build_relationship_change_trend_features",
    "get_relationship_change_trend_records",
    "get_relationship_change_trend_feature_names",
    "get_relationship_change_trend_value",
]