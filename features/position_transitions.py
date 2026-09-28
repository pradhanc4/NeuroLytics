"""
Position transition features.

Phase 15.9
-----------

Builds deterministic position-value transitions between consecutive
point-in-time historical observations.

Position scope
--------------
    col1 through col8

Design principles
-----------------
- Reuse the existing PointInTimeHistory infrastructure.
- Use only observations strictly before the target date.
- Only consecutive historical observations form transitions.
- Preserve zero as a valid observed digit.
- Preserve the historical observation order.
- Expose the actual previous and current position values.
- Expose a deterministic transition identifier.
- Do not calculate transition frequency, counts, percentages, stability,
  trends, probability, or predictions.
- Do not duplicate the existing sequence_features transition-count logic.
- Keep this layer standalone until the planned Phase 15.13 integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.feature_config import (
    FeatureConfig,
    validate_feature_config,
)
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


@dataclass(frozen=True)
class PositionTransitionRecord:
    """One consecutive position-value transition."""

    position: str
    from_value: int
    to_value: int
    transition: str
    feature_name: str


@dataclass(frozen=True)
class PositionTransitionResult:
    """Complete position-transition output for one target date."""

    target_date: date
    records: tuple[PositionTransitionRecord, ...]


def _get_position_index(
    position: str,
) -> int:
    """Convert col1-col8 into a zero-based position index."""

    if not isinstance(position, str):
        raise TypeError(
            "position must be a string."
        )

    try:
        return POSITIONS.index(position)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported position: {position}"
        ) from exc


def _build_transition_name(
    from_value: int,
    to_value: int,
) -> str:
    """Build a deterministic position transition identifier."""

    return f"{from_value}_to_{to_value}"


def _build_feature_name(
    position: str,
    transition: str,
) -> str:
    """Build a deterministic position-transition feature name."""

    return (
        f"{position}_position_transition_"
        f"{transition}"
    )


def _get_point_in_time_observations(
    history: PointInTimeHistory,
):
    """
    Return only observations strictly before the target date.

    The explicit date check makes this layer defensive even when a caller
    supplies a PointInTimeHistory constructed outside the normal builder.
    """

    observations = get_point_in_time_observations(
        history
    )

    return tuple(
        observation
        for observation in observations
        if observation.result_date < history.target_date
    )


def _build_position_transition_records(
    observations,
    positions,
) -> list[PositionTransitionRecord]:
    """Build all consecutive transitions for the configured positions."""

    records: list[PositionTransitionRecord] = []

    if len(observations) < 2:
        return records

    for position in positions:
        position_index = _get_position_index(
            position
        )

        for index in range(
            1,
            len(observations),
        ):
            previous_observation = observations[
                index - 1
            ]

            current_observation = observations[
                index
            ]

            from_value = previous_observation.positions[
                position_index
            ]

            to_value = current_observation.positions[
                position_index
            ]

            transition = _build_transition_name(
                from_value=from_value,
                to_value=to_value,
            )

            feature_name = _build_feature_name(
                position=position,
                transition=transition,
            )

            records.append(
                PositionTransitionRecord(
                    position=position,
                    from_value=from_value,
                    to_value=to_value,
                    transition=transition,
                    feature_name=feature_name,
                )
            )

    return records


def build_position_transition_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> PositionTransitionResult:
    """
    Build leakage-safe position transitions.

    Only observations strictly before the target date are used.

    Each record represents one actual transition between two consecutive
    historical observations for one configured position.
    """

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    validate_feature_config(
        config
    )

    if not config.position_transition_features_enabled:
        return PositionTransitionResult(
            target_date=history.target_date,
            records=(),
        )

    observations = _get_point_in_time_observations(
        history
    )

    records = _build_position_transition_records(
        observations=observations,
        positions=config.positions,
    )

    return PositionTransitionResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_position_transition_records(
    result: PositionTransitionResult,
) -> tuple[PositionTransitionRecord, ...]:
    """Return all position-transition records."""

    if not isinstance(
        result,
        PositionTransitionResult,
    ):
        raise TypeError(
            "result must be a PositionTransitionResult instance."
        )

    return result.records


def get_position_transition_feature_names(
    result: PositionTransitionResult,
) -> tuple[str, ...]:
    """Return all generated position-transition feature names."""

    if not isinstance(
        result,
        PositionTransitionResult,
    ):
        raise TypeError(
            "result must be a PositionTransitionResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_position_transition_value(
    result: PositionTransitionResult,
    feature_name: str,
) -> PositionTransitionRecord:
    """Return one position-transition record by feature name."""

    if not isinstance(
        result,
        PositionTransitionResult,
    ):
        raise TypeError(
            "result must be a PositionTransitionResult instance."
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
        f"Position transition feature not found: "
        f"{feature_name}"
    )


__all__ = [
    "PositionTransitionRecord",
    "PositionTransitionResult",
    "build_position_transition_features",
    "get_position_transition_records",
    "get_position_transition_feature_names",
    "get_position_transition_value",
]