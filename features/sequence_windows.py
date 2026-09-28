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


@dataclass(frozen=True)
class SequenceWindow:
    """
    Immutable representation of one chronological input window.

    Phase 16.2 intentionally contains no target information.
    Target construction belongs to Phase 16.3.
    """

    window_index: int
    sequence_start_date: date
    sequence_end_date: date
    sequence_length: int
    configured_sequence_length: int
    positions: tuple[str, ...]
    features: tuple[tuple[int, ...], ...]
    result_ids: tuple[int, ...]
    market_ids: tuple[int, ...]


@dataclass(frozen=True)
class SequenceWindowDataset:
    """
    Immutable collection of Phase 16.2 sequence windows.
    """

    configured_sequence_length: int
    input_positions: tuple[str, ...]
    allow_incomplete_sequences: bool
    windows: tuple[SequenceWindow, ...]


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
    """Validate the chronological historical observation sequence."""

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


def _extract_features(
    observations: tuple[HistoricalFeatureObservation, ...],
    input_positions: tuple[str, ...],
) -> tuple[tuple[int, ...], ...]:
    """
    Extract configured position values from historical observations.

    The original observation ordering is preserved.
    """

    indexes = tuple(
        _position_index(position)
        for position in input_positions
    )

    return tuple(
        tuple(
            observation.positions[index]
            for index in indexes
        )
        for observation in observations
    )


def _build_window(
    observations: tuple[HistoricalFeatureObservation, ...],
    config: SequenceDatasetConfig,
    window_index: int,
) -> SequenceWindow:
    """Build one validated sequence window."""

    features = _extract_features(
        observations,
        config.input_positions,
    )

    return SequenceWindow(
        window_index=window_index,
        sequence_start_date=observations[0].result_date,
        sequence_end_date=observations[-1].result_date,
        sequence_length=len(observations),
        configured_sequence_length=config.sequence_length,
        positions=config.input_positions,
        features=features,
        result_ids=tuple(
            observation.result_id
            for observation in observations
        ),
        market_ids=tuple(
            observation.market_id
            for observation in observations
        ),
    )


def validate_sequence_window(
    window: SequenceWindow,
) -> None:
    """Validate one Phase 16.2 sequence window."""

    if not isinstance(
        window,
        SequenceWindow,
    ):
        raise TypeError(
            "window must be a SequenceWindow instance."
        )

    if (
        isinstance(window.window_index, bool)
        or not isinstance(window.window_index, int)
    ):
        raise TypeError(
            "window_index must be an integer."
        )

    if window.window_index < 0:
        raise ValueError(
            "window_index must not be negative."
        )

    if (
        isinstance(window.sequence_length, bool)
        or not isinstance(window.sequence_length, int)
    ):
        raise TypeError(
            "sequence_length must be an integer."
        )

    if window.sequence_length <= 0:
        raise ValueError(
            "sequence_length must be greater than zero."
        )

    if (
        isinstance(
            window.configured_sequence_length,
            bool,
        )
        or not isinstance(
            window.configured_sequence_length,
            int,
        )
    ):
        raise TypeError(
            "configured_sequence_length must be an integer."
        )

    if window.configured_sequence_length <= 0:
        raise ValueError(
            "configured_sequence_length must be greater than zero."
        )

    if window.sequence_length > window.configured_sequence_length:
        raise ValueError(
            "sequence_length cannot exceed "
            "configured_sequence_length."
        )

    if not isinstance(window.positions, tuple):
        raise TypeError(
            "positions must be a tuple."
        )

    if not window.positions:
        raise ValueError(
            "positions must contain at least one position."
        )

    if len(set(window.positions)) != len(window.positions):
        raise ValueError(
            "positions must not contain duplicates."
        )

    for position in window.positions:
        if position not in POSITIONS:
            raise ValueError(
                f"Unsupported position: {position}"
            )

    if len(window.features) != window.sequence_length:
        raise ValueError(
            "features row count must equal sequence_length."
        )

    for row in window.features:
        if not isinstance(row, tuple):
            raise TypeError(
                "Each feature row must be a tuple."
            )

        if len(row) != len(window.positions):
            raise ValueError(
                "Each feature row width must equal "
                "the number of configured positions."
            )

    if len(window.result_ids) != window.sequence_length:
        raise ValueError(
            "result_ids count must equal sequence_length."
        )

    if len(window.market_ids) != window.sequence_length:
        raise ValueError(
            "market_ids count must equal sequence_length."
        )

    if window.sequence_start_date > window.sequence_end_date:
        raise ValueError(
            "sequence_start_date cannot be after "
            "sequence_end_date."
        )


def build_sequence_windows(
    observations: tuple[HistoricalFeatureObservation, ...],
    config: SequenceDatasetConfig,
) -> SequenceWindowDataset:
    """
    Construct deterministic chronological sliding windows.

    Phase 16.2 responsibilities:
    - validate historical observations
    - preserve chronological ordering
    - construct fixed-length sliding windows
    - optionally retain incomplete leading windows
    - preserve zero values
    - preserve source result/market identifiers
    - never construct targets

    Target construction belongs exclusively to Phase 16.3.
    """

    validate_sequence_dataset_config(
        config
    )

    _validate_observations(
        observations
    )

    windows: list[SequenceWindow] = []

    if not observations:
        return SequenceWindowDataset(
            configured_sequence_length=config.sequence_length,
            input_positions=config.input_positions,
            allow_incomplete_sequences=(
                config.allow_incomplete_sequences
            ),
            windows=(),
        )

    sequence_length = config.sequence_length

    if config.allow_incomplete_sequences:
        start_index = 0

        for end_index in range(len(observations)):
            start_index = max(
                0,
                end_index - sequence_length + 1,
            )

            window_observations = observations[
                start_index : end_index + 1
            ]

            windows.append(
                _build_window(
                    window_observations,
                    config,
                    len(windows),
                )
            )

    else:
        if len(observations) < sequence_length:
            return SequenceWindowDataset(
                configured_sequence_length=sequence_length,
                input_positions=config.input_positions,
                allow_incomplete_sequences=False,
                windows=(),
            )

        for start_index in range(
            0,
            len(observations) - sequence_length + 1,
        ):
            end_index = (
                start_index + sequence_length
            )

            window_observations = observations[
                start_index:end_index
            ]

            windows.append(
                _build_window(
                    window_observations,
                    config,
                    len(windows),
                )
            )

    result = SequenceWindowDataset(
        configured_sequence_length=sequence_length,
        input_positions=config.input_positions,
        allow_incomplete_sequences=(
            config.allow_incomplete_sequences
        ),
        windows=tuple(windows),
    )

    validate_sequence_window_dataset(
        result
    )

    return result


def validate_sequence_window_dataset(
    dataset: SequenceWindowDataset,
) -> None:
    """Validate the complete Phase 16.2 window dataset."""

    if not isinstance(
        dataset,
        SequenceWindowDataset,
    ):
        raise TypeError(
            "dataset must be a SequenceWindowDataset instance."
        )

    if (
        isinstance(
            dataset.configured_sequence_length,
            bool,
        )
        or not isinstance(
            dataset.configured_sequence_length,
            int,
        )
    ):
        raise TypeError(
            "configured_sequence_length must be an integer."
        )

    if dataset.configured_sequence_length <= 0:
        raise ValueError(
            "configured_sequence_length must be greater than zero."
        )

    if not isinstance(
        dataset.input_positions,
        tuple,
    ):
        raise TypeError(
            "input_positions must be a tuple."
        )

    if not isinstance(
        dataset.allow_incomplete_sequences,
        bool,
    ):
        raise TypeError(
            "allow_incomplete_sequences must be a boolean."
        )

    if not isinstance(
        dataset.windows,
        tuple,
    ):
        raise TypeError(
            "windows must be a tuple."
        )

    previous_index = None
    previous_end_date = None

    for window in dataset.windows:
        validate_sequence_window(
            window
        )

        if (
            window.configured_sequence_length
            != dataset.configured_sequence_length
        ):
            raise ValueError(
                "Window configured sequence length must "
                "match dataset configuration."
            )

        if window.positions != dataset.input_positions:
            raise ValueError(
                "Window positions must match "
                "dataset input_positions."
            )

        if not dataset.allow_incomplete_sequences:
            if (
                window.sequence_length
                != dataset.configured_sequence_length
            ):
                raise ValueError(
                    "Incomplete windows are not allowed."
                )

        if previous_index is not None:
            if window.window_index <= previous_index:
                raise ValueError(
                    "Window indices must be strictly increasing."
                )

        if previous_end_date is not None:
            if (
                window.sequence_end_date
                <= previous_end_date
            ):
                raise ValueError(
                    "Window end dates must be strictly increasing."
                )

        previous_index = window.window_index
        previous_end_date = window.sequence_end_date


def get_sequence_window_count(
    dataset: SequenceWindowDataset,
) -> int:
    """Return the number of constructed windows."""

    validate_sequence_window_dataset(
        dataset
    )

    return len(
        dataset.windows
    )


def get_sequence_window(
    dataset: SequenceWindowDataset,
    window_index: int,
) -> SequenceWindow:
    """Return one deterministic sequence window."""

    validate_sequence_window_dataset(
        dataset
    )

    if (
        isinstance(window_index, bool)
        or not isinstance(window_index, int)
    ):
        raise TypeError(
            "window_index must be an integer."
        )

    for window in dataset.windows:
        if window.window_index == window_index:
            return window

    raise ValueError(
        f"Sequence window not found: {window_index}"
    )


def get_sequence_windows(
    dataset: SequenceWindowDataset,
) -> tuple[SequenceWindow, ...]:
    """Return all sequence windows."""

    validate_sequence_window_dataset(
        dataset
    )

    return dataset.windows


def get_sequence_window_features(
    window: SequenceWindow,
) -> tuple[tuple[int, ...], ...]:
    """Return the extracted feature rows for one window."""

    validate_sequence_window(
        window
    )

    return window.features


def get_sequence_window_dates(
    window: SequenceWindow,
) -> tuple[date, date]:
    """Return sequence start and end dates."""

    validate_sequence_window(
        window
    )

    return (
        window.sequence_start_date,
        window.sequence_end_date,
    )