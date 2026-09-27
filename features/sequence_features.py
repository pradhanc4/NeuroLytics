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


@dataclass(frozen=True)
class SequenceFeatureRecord:
    """One sequence/transition feature."""

    position: str
    feature_name: str
    value: int | float | str | None


@dataclass(frozen=True)
class SequenceFeatureResult:
    """Complete sequence-feature output for one target date."""

    target_date: date
    window: int
    records: tuple[SequenceFeatureRecord, ...]


def _build_feature_name(
    position: str,
    feature: str,
) -> str:
    """Build a deterministic sequence feature name."""

    return f"{position}_sequence_{feature}"


def _get_position_index(
    position: str,
) -> int:
    """Convert col1-col8 into a zero-based position index."""

    return int(
        position.replace("col", "")
    ) - 1


def _get_window_observations(
    history: PointInTimeHistory,
    window: int,
):
    """Return the latest point-in-time observations."""

    observations = get_point_in_time_observations(
        history
    )

    if not observations:
        return ()

    return observations[-window:]


def _get_previous_and_latest_values(
    history: PointInTimeHistory,
    position: str,
) -> tuple[int | None, int | None]:
    """Return the previous and latest historical values."""

    observations = get_point_in_time_observations(
        history
    )

    if not observations:
        return None, None

    position_index = _get_position_index(
        position
    )

    latest = observations[-1].positions[
        position_index
    ]

    if len(observations) < 2:
        return None, latest

    previous = observations[-2].positions[
        position_index
    ]

    return previous, latest


def _calculate_transition_distance(
    previous: int | None,
    latest: int | None,
) -> int | None:
    """Calculate absolute digit movement."""

    if previous is None or latest is None:
        return None

    return abs(latest - previous)


def _build_transition_name(
    previous: int | None,
    latest: int | None,
) -> str | None:
    """Build a deterministic transition label."""

    if previous is None or latest is None:
        return None

    return f"{previous}_to_{latest}"


def _calculate_transition_counts(
    observations,
    position_index: int,
) -> dict[tuple[int, int], int]:
    """Count consecutive digit transitions."""

    counts: dict[tuple[int, int], int] = {}

    for index in range(1, len(observations)):
        previous = observations[index - 1].positions[
            position_index
        ]

        latest = observations[index].positions[
            position_index
        ]

        transition = (
            previous,
            latest,
        )

        counts[transition] = (
            counts.get(transition, 0) + 1
        )

    return counts


def _get_latest_transition(
    observations,
    position_index: int,
) -> tuple[int, int] | None:
    """Return the most recent historical transition."""

    if len(observations) < 2:
        return None

    previous = observations[-2].positions[
        position_index
    ]

    latest = observations[-1].positions[
        position_index
    ]

    return previous, latest


def build_sequence_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> SequenceFeatureResult:
    """
    Build leakage-safe sequence and transition features.

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

    window = config.rolling_windows[0]

    observations = _get_window_observations(
        history,
        window,
    )

    records: list[SequenceFeatureRecord] = []

    for position in config.positions:
        position_index = _get_position_index(
            position
        )

        previous, latest = (
            _get_previous_and_latest_values(
                history,
                position,
            )
        )

        transition = _build_transition_name(
            previous,
            latest,
        )

        distance = _calculate_transition_distance(
            previous,
            latest,
        )

        changed = (
            None
            if previous is None or latest is None
            else int(previous != latest)
        )

        records.extend(
            (
                SequenceFeatureRecord(
                    position=position,
                    feature_name=_build_feature_name(
                        position,
                        "previous_value",
                    ),
                    value=previous,
                ),
                SequenceFeatureRecord(
                    position=position,
                    feature_name=_build_feature_name(
                        position,
                        "latest_value",
                    ),
                    value=latest,
                ),
                SequenceFeatureRecord(
                    position=position,
                    feature_name=_build_feature_name(
                        position,
                        "transition",
                    ),
                    value=transition,
                ),
                SequenceFeatureRecord(
                    position=position,
                    feature_name=_build_feature_name(
                        position,
                        "transition_distance",
                    ),
                    value=distance,
                ),
                SequenceFeatureRecord(
                    position=position,
                    feature_name=_build_feature_name(
                        position,
                        "changed",
                    ),
                    value=changed,
                ),
            )
        )

        transition_counts = (
            _calculate_transition_counts(
                observations,
                position_index,
            )
        )

        latest_transition = (
            _get_latest_transition(
                observations,
                position_index,
            )
        )

        latest_transition_count = (
            0
            if latest_transition is None
            else transition_counts.get(
                latest_transition,
                0,
            )
        )

        total_transitions = max(
            len(observations) - 1,
            0,
        )

        transition_percentage = (
            None
            if (
                latest_transition is None
                or total_transitions == 0
            )
            else (
                latest_transition_count
                / total_transitions
                * 100.0
            )
        )

        records.extend(
            (
                SequenceFeatureRecord(
                    position=position,
                    feature_name=_build_feature_name(
                        position,
                        "latest_transition_count",
                    ),
                    value=(
                        None
                        if latest_transition is None
                        else latest_transition_count
                    ),
                ),
                SequenceFeatureRecord(
                    position=position,
                    feature_name=_build_feature_name(
                        position,
                        "latest_transition_percentage",
                    ),
                    value=transition_percentage,
                ),
            )
        )

    return SequenceFeatureResult(
        target_date=history.target_date,
        window=window,
        records=tuple(records),
    )


def get_sequence_feature_value(
    result: SequenceFeatureResult,
    feature_name: str,
):
    """Return one sequence feature value."""

    if not isinstance(
        result,
        SequenceFeatureResult,
    ):
        raise TypeError(
            "result must be a SequenceFeatureResult instance."
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
        f"Sequence feature not found: {feature_name}"
    )


def get_sequence_feature_names(
    result: SequenceFeatureResult,
) -> tuple[str, ...]:
    """Return all generated sequence feature names."""

    if not isinstance(
        result,
        SequenceFeatureResult,
    ):
        raise TypeError(
            "result must be a SequenceFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )