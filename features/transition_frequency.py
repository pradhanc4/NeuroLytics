"""
Transition frequency features.

Phase 15.10
-----------

Calculates historical frequency for consecutive position-value transitions.

Design principles
-----------------
- Reuse the existing PointInTimeHistory infrastructure.
- Use only observations strictly before the target date.
- Count actual consecutive transitions.
- Preserve zero as a valid digit.
- Preserve configured position ordering.
- Provide transition counts and percentages.
- Do not calculate transition stability, trends, probabilities,
  predictions, or Markov metrics.
- Do not modify sequence_features.py.
- Do not integrate with unified_dataset.py yet.
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
class TransitionFrequencyRecord:
    """Frequency information for one position transition."""

    position: str
    from_value: int
    to_value: int
    transition: str
    count: int
    percentage: float
    total_transitions: int
    feature_name: str


@dataclass(frozen=True)
class TransitionFrequencyResult:
    """Complete transition-frequency output for one target date."""

    target_date: date
    records: tuple[TransitionFrequencyRecord, ...]


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
    """Build a deterministic transition identifier."""

    return f"{from_value}_to_{to_value}"


def _build_feature_name(
    position: str,
    transition: str,
    metric: str,
) -> str:
    """Build a deterministic transition-frequency feature name."""

    return (
        f"{position}_transition_frequency_"
        f"{metric}_{transition}"
    )


def _get_point_in_time_observations(
    history: PointInTimeHistory,
):
    """
    Return only observations strictly before the target date.

    The explicit date check provides defensive leakage protection even if
    the supplied PointInTimeHistory contains an observation at or after
    the target date.
    """

    observations = get_point_in_time_observations(
        history
    )

    return tuple(
        observation
        for observation in observations
        if observation.result_date < history.target_date
    )


def _calculate_transition_counts(
    observations,
    position_index: int,
) -> dict[tuple[int, int], int]:
    """Count consecutive transitions for one position."""

    counts: dict[tuple[int, int], int] = {}

    if len(observations) < 2:
        return counts

    for index in range(
        1,
        len(observations),
    ):
        previous_value = observations[
            index - 1
        ].positions[position_index]

        current_value = observations[
            index
        ].positions[position_index]

        transition = (
            previous_value,
            current_value,
        )

        counts[transition] = (
            counts.get(transition, 0) + 1
        )

    return counts


def _build_transition_frequency_records(
    observations,
    positions,
) -> list[TransitionFrequencyRecord]:
    """Build deterministic transition-frequency records."""

    records: list[TransitionFrequencyRecord] = []

    if len(observations) < 2:
        return records

    for position in positions:
        position_index = _get_position_index(
            position
        )

        counts = _calculate_transition_counts(
            observations,
            position_index,
        )

        total_transitions = max(
            len(observations) - 1,
            0,
        )

        for (
            from_value,
            to_value,
        ), count in counts.items():

            transition = _build_transition_name(
                from_value=from_value,
                to_value=to_value,
            )

            percentage = (
                0.0
                if total_transitions == 0
                else (
                    count
                    / total_transitions
                    * 100.0
                )
            )

            records.append(
                TransitionFrequencyRecord(
                    position=position,
                    from_value=from_value,
                    to_value=to_value,
                    transition=transition,
                    count=count,
                    percentage=percentage,
                    total_transitions=total_transitions,
                    feature_name=_build_feature_name(
                        position=position,
                        transition=transition,
                        metric="count",
                    ),
                )
            )

            records.append(
                TransitionFrequencyRecord(
                    position=position,
                    from_value=from_value,
                    to_value=to_value,
                    transition=transition,
                    count=count,
                    percentage=percentage,
                    total_transitions=total_transitions,
                    feature_name=_build_feature_name(
                        position=position,
                        transition=transition,
                        metric="percentage",
                    ),
                )
            )

    return records


def build_transition_frequency_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> TransitionFrequencyResult:
    """
    Build leakage-safe transition-frequency features.

    Only observations strictly before the target date are used.
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

    if not config.transition_frequency_features_enabled:
        return TransitionFrequencyResult(
            target_date=history.target_date,
            records=(),
        )

    observations = _get_point_in_time_observations(
        history
    )

    records = _build_transition_frequency_records(
        observations=observations,
        positions=config.positions,
    )

    return TransitionFrequencyResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_transition_frequency_records(
    result: TransitionFrequencyResult,
) -> tuple[TransitionFrequencyRecord, ...]:
    """Return all transition-frequency records."""

    if not isinstance(
        result,
        TransitionFrequencyResult,
    ):
        raise TypeError(
            "result must be a TransitionFrequencyResult instance."
        )

    return result.records


def get_transition_frequency_feature_names(
    result: TransitionFrequencyResult,
) -> tuple[str, ...]:
    """Return all generated transition-frequency feature names."""

    if not isinstance(
        result,
        TransitionFrequencyResult,
    ):
        raise TypeError(
            "result must be a TransitionFrequencyResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_transition_frequency_value(
    result: TransitionFrequencyResult,
    feature_name: str,
) -> TransitionFrequencyRecord:
    """Return one transition-frequency record by feature name."""

    if not isinstance(
        result,
        TransitionFrequencyResult,
    ):
        raise TypeError(
            "result must be a TransitionFrequencyResult instance."
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
        "Transition frequency feature not found: "
        f"{feature_name}"
    )


__all__ = [
    "TransitionFrequencyRecord",
    "TransitionFrequencyResult",
    "build_transition_frequency_features",
    "get_transition_frequency_records",
    "get_transition_frequency_feature_names",
    "get_transition_frequency_value",
]