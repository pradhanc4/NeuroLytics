"""
Transition stability features.

Phase 15.11
-----------

Measures how concentrated historical position transitions are around
the most frequently observed transition.

Example:

    1 -> 2
    2 -> 3
    1 -> 2
    1 -> 2
    2 -> 3

Transition counts:

    1 -> 2 = 3
    2 -> 3 = 2

Therefore:

    dominant transition = 1 -> 2
    dominant count      = 3
    total transitions   = 5
    stability           = 60.0%

Design principles
-----------------
- Reuse PointInTimeHistory.
- Use only observations strictly before the target date.
- Use actual consecutive position-value transitions.
- Zero is a valid observed value.
- Respect configured position ordering.
- Stability is derived from transition concentration.
- No arbitrary stability thresholds.
- No probability, prediction, trend, or Markov logic.
- Do not modify sequence_features.py.
- Do not integrate into unified_dataset.py yet.
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
class TransitionStabilityRecord:
    """Transition-stability metrics for one position."""

    position: str
    dominant_from_value: int | None
    dominant_to_value: int | None
    dominant_transition: str | None
    dominant_transition_count: int
    transition_change_count: int
    total_transitions: int
    stability_percentage: float
    feature_name: str


@dataclass(frozen=True)
class TransitionStabilityResult:
    """Complete transition-stability output for one target date."""

    target_date: date
    records: tuple[TransitionStabilityRecord, ...]


def _get_position_index(
    position: str,
) -> int:
    """Return the zero-based index for a configured position."""

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


def _get_point_in_time_observations(
    history: PointInTimeHistory,
):
    """
    Return observations strictly before the target date.

    The explicit filter provides defensive leakage protection even
    when the supplied history contains target-date or future rows.
    """

    observations = get_point_in_time_observations(
        history
    )

    return tuple(
        observation
        for observation in observations
        if observation.result_date < history.target_date
    )


def _build_transitions(
    observations,
    position_index: int,
) -> tuple[tuple[int, int], ...]:
    """Build consecutive value transitions for one position."""

    if len(observations) < 2:
        return ()

    transitions = []

    for index in range(1, len(observations)):
        previous_value = observations[
            index - 1
        ].positions[position_index]

        current_value = observations[
            index
        ].positions[position_index]

        transitions.append(
            (
                previous_value,
                current_value,
            )
        )

    return tuple(transitions)


def _calculate_transition_counts(
    transitions: tuple[tuple[int, int], ...],
) -> dict[tuple[int, int], int]:
    """Count each observed transition."""

    counts: dict[tuple[int, int], int] = {}

    for transition in transitions:
        counts[transition] = (
            counts.get(transition, 0) + 1
        )

    return counts


def _get_dominant_transition(
    counts: dict[tuple[int, int], int],
) -> tuple[int, int] | None:
    """
    Return the most frequent transition.

    Ties are resolved deterministically by transition tuple ordering.
    """

    if not counts:
        return None

    return max(
        counts,
        key=lambda transition: (
            counts[transition],
            -transition[0],
            -transition[1],
        ),
    )


def _calculate_stability(
    transitions: tuple[tuple[int, int], ...],
) -> tuple[
    tuple[int, int] | None,
    int,
    int,
    int,
    float,
]:
    """
    Calculate dominant-transition stability.

    Returns:

        dominant_transition
        dominant_transition_count
        transition_change_count
        total_transitions
        stability_percentage
    """

    total_transitions = len(transitions)

    if total_transitions == 0:
        return (
            None,
            0,
            0,
            0,
            0.0,
        )

    counts = _calculate_transition_counts(
        transitions
    )

    dominant_transition = _get_dominant_transition(
        counts
    )

    if dominant_transition is None:
        return (
            None,
            0,
            0,
            total_transitions,
            0.0,
        )

    dominant_count = counts[
        dominant_transition
    ]

    transition_change_count = (
        total_transitions
        - dominant_count
    )

    stability_percentage = (
        dominant_count
        / total_transitions
        * 100.0
    )

    return (
        dominant_transition,
        dominant_count,
        transition_change_count,
        total_transitions,
        stability_percentage,
    )


def _build_transition_stability_records(
    observations,
    positions,
) -> list[TransitionStabilityRecord]:
    """Build deterministic stability records."""

    records: list[TransitionStabilityRecord] = []

    if len(observations) < 2:
        return records

    for position in positions:
        position_index = _get_position_index(
            position
        )

        transitions = _build_transitions(
            observations=observations,
            position_index=position_index,
        )

        (
            dominant_transition,
            dominant_count,
            transition_change_count,
            total_transitions,
            stability_percentage,
        ) = _calculate_stability(
            transitions
        )

        if dominant_transition is None:
            dominant_from_value = None
            dominant_to_value = None
            dominant_transition_name = None
        else:
            dominant_from_value = (
                dominant_transition[0]
            )
            dominant_to_value = (
                dominant_transition[1]
            )
            dominant_transition_name = (
                _build_transition_name(
                    dominant_from_value,
                    dominant_to_value,
                )
            )

        records.append(
            TransitionStabilityRecord(
                position=position,
                dominant_from_value=(
                    dominant_from_value
                ),
                dominant_to_value=(
                    dominant_to_value
                ),
                dominant_transition=(
                    dominant_transition_name
                ),
                dominant_transition_count=(
                    dominant_count
                ),
                transition_change_count=(
                    transition_change_count
                ),
                total_transitions=(
                    total_transitions
                ),
                stability_percentage=(
                    stability_percentage
                ),
                feature_name=(
                    f"{position}"
                    "_transition_stability_percentage"
                ),
            )
        )

    return records


def build_transition_stability_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> TransitionStabilityResult:
    """
    Build leakage-safe transition-stability features.

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

    if not config.transition_stability_features_enabled:
        return TransitionStabilityResult(
            target_date=history.target_date,
            records=(),
        )

    observations = _get_point_in_time_observations(
        history
    )

    records = _build_transition_stability_records(
        observations=observations,
        positions=config.positions,
    )

    return TransitionStabilityResult(
        target_date=history.target_date,
        records=tuple(records),
    )


def get_transition_stability_records(
    result: TransitionStabilityResult,
) -> tuple[TransitionStabilityRecord, ...]:
    """Return all transition-stability records."""

    if not isinstance(
        result,
        TransitionStabilityResult,
    ):
        raise TypeError(
            "result must be a TransitionStabilityResult instance."
        )

    return result.records


def get_transition_stability_feature_names(
    result: TransitionStabilityResult,
) -> tuple[str, ...]:
    """Return generated transition-stability feature names."""

    if not isinstance(
        result,
        TransitionStabilityResult,
    ):
        raise TypeError(
            "result must be a TransitionStabilityResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_transition_stability_value(
    result: TransitionStabilityResult,
    feature_name: str,
) -> TransitionStabilityRecord:
    """Return a transition-stability record by feature name."""

    if not isinstance(
        result,
        TransitionStabilityResult,
    ):
        raise TypeError(
            "result must be a TransitionStabilityResult instance."
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
        "Transition stability feature not found: "
        f"{feature_name}"
    )


__all__ = [
    "TransitionStabilityRecord",
    "TransitionStabilityResult",
    "build_transition_stability_features",
    "get_transition_stability_records",
    "get_transition_stability_feature_names",
    "get_transition_stability_value",
]