from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.historical_data_loader import (
    HistoricalFeatureObservation,
    POSITIONS,
)
from features.sequence_dataset import (
    SequenceDatasetConfig,
    validate_sequence_dataset_config,
)
from features.sequence_windows import (
    SequenceWindow,
    SequenceWindowDataset,
    validate_sequence_window,
    validate_sequence_window_dataset,
)


@dataclass(frozen=True)
class SequenceTarget:
    """
    Immutable representation of one target observation.

    The target is always a historical observation occurring
    strictly after the corresponding input sequence.
    """

    window_index: int
    target_date: date
    target_positions: tuple[str, ...]
    target: tuple[int, ...]
    result_id: int
    market_id: int


@dataclass(frozen=True)
class SequenceTargetDataset:
    """
    Immutable collection of constructed sequence targets.
    """

    target_positions: tuple[str, ...]
    targets: tuple[SequenceTarget, ...]


def _position_index(position: str) -> int:
    """Return the source index for one configured position."""

    try:
        return POSITIONS.index(position)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported position: {position}"
        ) from exc


def _validate_observations(
    observations: tuple[HistoricalFeatureObservation, ...],
) -> None:
    """Validate historical observations used for target construction."""

    if not isinstance(observations, tuple):
        raise TypeError(
            "observations must be a tuple of "
            "HistoricalFeatureObservation objects."
        )

    previous_date = None

    for observation in observations:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "observations must contain only "
                "HistoricalFeatureObservation objects."
            )

        if len(observation.positions) != len(POSITIONS):
            raise ValueError(
                "Each observation must contain exactly "
                f"{len(POSITIONS)} positions."
            )

        if previous_date is not None:
            if observation.result_date <= previous_date:
                raise ValueError(
                    "observations must be strictly chronological "
                    "with unique result dates."
                )

        previous_date = observation.result_date


def _build_observation_index(
    observations: tuple[HistoricalFeatureObservation, ...],
) -> dict[int, HistoricalFeatureObservation]:
    """
    Build a deterministic result-id index.

    Result IDs are expected to identify individual historical
    observations within the loaded dataset.
    """

    index: dict[int, HistoricalFeatureObservation] = {}

    for observation in observations:
        if observation.result_id in index:
            raise ValueError(
                "Duplicate result_id found in observations: "
                f"{observation.result_id}"
            )

        index[observation.result_id] = observation

    return index


def _find_following_observation(
    window: SequenceWindow,
    observations: tuple[HistoricalFeatureObservation, ...],
) -> HistoricalFeatureObservation | None:
    """
    Return the immediately following historical observation.

    The lookup is based on the window's final result_id and
    requires the next observation to be strictly after the
    sequence end date.
    """

    for index, observation in enumerate(observations):
        if observation.result_id == window.result_ids[-1]:
            next_index = index + 1

            if next_index >= len(observations):
                return None

            candidate = observations[next_index]

            if candidate.result_date <= window.sequence_end_date:
                raise ValueError(
                    "Target observation must occur strictly after "
                    "the sequence end date."
                )

            return candidate

    raise ValueError(
        "Window final result_id was not found in observations: "
        f"{window.result_ids[-1]}"
    )


def _extract_target(
    observation: HistoricalFeatureObservation,
    target_positions: tuple[str, ...],
) -> tuple[int, ...]:
    """Extract configured target position values."""

    indexes = tuple(
        _position_index(position)
        for position in target_positions
    )

    return tuple(
        observation.positions[index]
        for index in indexes
    )


def validate_sequence_target(
    target: SequenceTarget,
) -> None:
    """Validate one Phase 16.3 target."""

    if not isinstance(
        target,
        SequenceTarget,
    ):
        raise TypeError(
            "target must be a SequenceTarget instance."
        )

    if (
        isinstance(target.window_index, bool)
        or not isinstance(target.window_index, int)
    ):
        raise TypeError(
            "window_index must be an integer."
        )

    if target.window_index < 0:
        raise ValueError(
            "window_index must not be negative."
        )

    if not isinstance(
        target.target_positions,
        tuple,
    ):
        raise TypeError(
            "target_positions must be a tuple."
        )

    if not target.target_positions:
        raise ValueError(
            "target_positions must contain at least one position."
        )

    if len(set(target.target_positions)) != len(
        target.target_positions
    ):
        raise ValueError(
            "target_positions must not contain duplicates."
        )

    for position in target.target_positions:
        if position not in POSITIONS:
            raise ValueError(
                f"Unsupported target position: {position}"
            )

    if not isinstance(
        target.target,
        tuple,
    ):
        raise TypeError(
            "target must be a tuple."
        )

    if len(target.target) != len(
        target.target_positions
    ):
        raise ValueError(
            "target width must equal the number of "
            "target positions."
        )

    if (
        isinstance(target.result_id, bool)
        or not isinstance(target.result_id, int)
    ):
        raise TypeError(
            "result_id must be an integer."
        )

    if (
        isinstance(target.market_id, bool)
        or not isinstance(target.market_id, int)
    ):
        raise TypeError(
            "market_id must be an integer."
        )


def build_sequence_targets(
    windows: SequenceWindowDataset,
    observations: tuple[HistoricalFeatureObservation, ...],
    config: SequenceDatasetConfig,
) -> SequenceTargetDataset:
    """
    Construct targets for chronological sequence windows.

    Each complete or incomplete input window receives the
    immediately following historical observation as its target,
    when such an observation exists.

    No prediction or model inference occurs here.
    """

    validate_sequence_dataset_config(
        config
    )

    validate_sequence_window_dataset(
        windows
    )

    _validate_observations(
        observations
    )

    _build_observation_index(
        observations
    )

    targets: list[SequenceTarget] = []

    for window in windows.windows:
        following = _find_following_observation(
            window,
            observations,
        )

        if following is None:
            continue

        target_values = _extract_target(
            following,
            config.target_positions,
        )

        target = SequenceTarget(
            window_index=window.window_index,
            target_date=following.result_date,
            target_positions=config.target_positions,
            target=target_values,
            result_id=following.result_id,
            market_id=following.market_id,
        )

        validate_sequence_target(
            target
        )

        if target.target_date <= window.sequence_end_date:
            raise ValueError(
                "Target date must be strictly after "
                "sequence end date."
            )

        targets.append(
            target
        )

    result = SequenceTargetDataset(
        target_positions=config.target_positions,
        targets=tuple(targets),
    )

    validate_sequence_target_dataset(
        result
    )

    return result


def validate_sequence_target_dataset(
    dataset: SequenceTargetDataset,
) -> None:
    """Validate the complete Phase 16.3 target dataset."""

    if not isinstance(
        dataset,
        SequenceTargetDataset,
    ):
        raise TypeError(
            "dataset must be a SequenceTargetDataset instance."
        )

    if not isinstance(
        dataset.target_positions,
        tuple,
    ):
        raise TypeError(
            "target_positions must be a tuple."
        )

    if not dataset.target_positions:
        raise ValueError(
            "target_positions must contain at least one position."
        )

    if len(set(dataset.target_positions)) != len(
        dataset.target_positions
    ):
        raise ValueError(
            "target_positions must not contain duplicates."
        )

    for position in dataset.target_positions:
        if position not in POSITIONS:
            raise ValueError(
                f"Unsupported target position: {position}"
            )

    if not isinstance(
        dataset.targets,
        tuple,
    ):
        raise TypeError(
            "targets must be a tuple."
        )

    previous_window_index = None

    for target in dataset.targets:
        validate_sequence_target(
            target
        )

        if target.target_positions != dataset.target_positions:
            raise ValueError(
                "Target positions must match dataset "
                "target_positions."
            )

        if (
            previous_window_index is not None
            and target.window_index
            <= previous_window_index
        ):
            raise ValueError(
                "Target window indices must be strictly increasing."
            )

        previous_window_index = target.window_index


def get_sequence_target_count(
    dataset: SequenceTargetDataset,
) -> int:
    """Return the number of constructed targets."""

    validate_sequence_target_dataset(
        dataset
    )

    return len(
        dataset.targets
    )


def get_sequence_target(
    dataset: SequenceTargetDataset,
    window_index: int,
) -> SequenceTarget:
    """Return the target associated with one window index."""

    validate_sequence_target_dataset(
        dataset
    )

    if (
        isinstance(window_index, bool)
        or not isinstance(window_index, int)
    ):
        raise TypeError(
            "window_index must be an integer."
        )

    for target in dataset.targets:
        if target.window_index == window_index:
            return target

    raise ValueError(
        f"Sequence target not found: {window_index}"
    )


def get_sequence_targets(
    dataset: SequenceTargetDataset,
) -> tuple[SequenceTarget, ...]:
    """Return all constructed sequence targets."""

    validate_sequence_target_dataset(
        dataset
    )

    return dataset.targets


def get_sequence_target_values(
    target: SequenceTarget,
) -> tuple[int, ...]:
    """Return target values for one sequence target."""

    validate_sequence_target(
        target
    )

    return target.target


def get_sequence_target_date(
    target: SequenceTarget,
) -> date:
    """Return the date associated with one target."""

    validate_sequence_target(
        target
    )

    return target.target_date