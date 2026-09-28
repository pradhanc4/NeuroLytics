from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from features.historical_data_loader import POSITIONS


@dataclass(frozen=True)
class SequenceDatasetConfig:
    """Explicit Phase 16.1 configuration contract."""

    sequence_length: int
    input_positions: tuple[str, ...]
    target_positions: tuple[str, ...]
    feature_names: tuple[str, ...] = ()
    allow_incomplete_sequences: bool = False


@dataclass(frozen=True)
class SequenceSample:
    """Immutable structural representation of one sequence sample."""

    sample_index: int
    sequence_start_date: date
    sequence_end_date: date
    target_date: date
    sequence_length: int
    positions: tuple[str, ...]
    features: tuple[tuple[Any, ...], ...]
    target: tuple[Any, ...]


@dataclass(frozen=True)
class SequenceDataset:
    """Immutable structural representation of a sequence dataset."""

    sequence_length: int
    input_positions: tuple[str, ...]
    target_positions: tuple[str, ...]
    feature_names: tuple[str, ...]
    samples: tuple[SequenceSample, ...]


def _positive_int(
    value: int,
    name: str,
) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"{name} must be an integer."
        )

    if value <= 0:
        raise ValueError(
            f"{name} must be greater than zero."
        )


def _positions(
    value: tuple[str, ...],
    name: str,
) -> None:
    if not isinstance(value, tuple):
        raise TypeError(
            f"{name} must be a tuple of position names."
        )

    if not value:
        raise ValueError(
            f"{name} must contain at least one position."
        )

    if len(set(value)) != len(value):
        raise ValueError(
            f"{name} must not contain duplicate positions."
        )

    for position in value:
        if not isinstance(position, str):
            raise TypeError(
                f"{name} must contain only strings."
            )

        if position not in POSITIONS:
            raise ValueError(
                f"Unsupported position in {name}: {position}"
            )


def _feature_names(
    value: tuple[str, ...],
) -> None:
    if not isinstance(value, tuple):
        raise TypeError(
            "feature_names must be a tuple of strings."
        )

    if len(set(value)) != len(value):
        raise ValueError(
            "feature_names must not contain duplicates."
        )

    for name in value:
        if not isinstance(name, str):
            raise TypeError(
                "feature_names must contain only strings."
            )

        if not name.strip():
            raise ValueError(
                "feature_names must not contain empty strings."
            )


def validate_sequence_dataset_config(
    config: SequenceDatasetConfig,
) -> None:
    """Validate the Phase 16.1 configuration contract."""

    if not isinstance(
        config,
        SequenceDatasetConfig,
    ):
        raise TypeError(
            "config must be a SequenceDatasetConfig instance."
        )

    _positive_int(
        config.sequence_length,
        "sequence_length",
    )

    _positions(
        config.input_positions,
        "input_positions",
    )

    _positions(
        config.target_positions,
        "target_positions",
    )

    _feature_names(
        config.feature_names,
    )

    if not isinstance(
        config.allow_incomplete_sequences,
        bool,
    ):
        raise TypeError(
            "allow_incomplete_sequences must be a boolean."
        )


def validate_sequence_sample(
    sample: SequenceSample,
) -> None:
    """Validate one immutable sequence sample."""

    if not isinstance(
        sample,
        SequenceSample,
    ):
        raise TypeError(
            "sample must be a SequenceSample instance."
        )

    if (
        isinstance(sample.sample_index, bool)
        or not isinstance(sample.sample_index, int)
    ):
        raise TypeError(
            "sample_index must be an integer."
        )

    if sample.sample_index < 0:
        raise ValueError(
            "sample_index must not be negative."
        )

    _positive_int(
        sample.sequence_length,
        "sample.sequence_length",
    )

    _positions(
        sample.positions,
        "sample.positions",
    )

    if len(sample.features) != sample.sequence_length:
        raise ValueError(
            "features row count must equal sequence_length."
        )

    if sample.target_date <= sample.sequence_end_date:
        raise ValueError(
            "target_date must be after sequence_end_date."
        )

    for row in sample.features:
        if not isinstance(row, tuple):
            raise TypeError(
                "Each feature row must be a tuple."
            )


def build_sequence_dataset(
    config: SequenceDatasetConfig,
    samples: tuple[SequenceSample, ...] = (),
) -> SequenceDataset:
    """
    Build a validated Phase 16.1 dataset contract.

    Window construction belongs to Phase 16.2 and target construction
    belongs to Phase 16.3. This function only validates
    already-constructed samples.
    """

    validate_sequence_dataset_config(
        config
    )

    if not isinstance(
        samples,
        tuple,
    ):
        raise TypeError(
            "samples must be a tuple of SequenceSample objects."
        )

    previous_index = None

    for sample in samples:
        validate_sequence_sample(
            sample
        )

        if sample.positions != config.input_positions:
            raise ValueError(
                "Sample positions must match "
                "config.input_positions."
            )

        if sample.sequence_length != config.sequence_length:
            raise ValueError(
                "Sample sequence_length must match "
                "config.sequence_length."
            )

        if (
            previous_index is not None
            and sample.sample_index <= previous_index
        ):
            raise ValueError(
                "Sample indices must be strictly increasing."
            )

        previous_index = sample.sample_index

    return SequenceDataset(
        sequence_length=config.sequence_length,
        input_positions=config.input_positions,
        target_positions=config.target_positions,
        feature_names=config.feature_names,
        samples=samples,
    )


def validate_sequence_dataset(
    dataset: SequenceDataset,
) -> None:
    """Validate an immutable sequence dataset."""

    if not isinstance(
        dataset,
        SequenceDataset,
    ):
        raise TypeError(
            "dataset must be a SequenceDataset instance."
        )

    _positive_int(
        dataset.sequence_length,
        "dataset.sequence_length",
    )

    _positions(
        dataset.input_positions,
        "dataset.input_positions",
    )

    _positions(
        dataset.target_positions,
        "dataset.target_positions",
    )

    _feature_names(
        dataset.feature_names,
    )

    previous_index = None

    for sample in dataset.samples:
        validate_sequence_sample(
            sample
        )

        if sample.sequence_length != dataset.sequence_length:
            raise ValueError(
                "Sample sequence_length must match "
                "dataset.sequence_length."
            )

        if sample.positions != dataset.input_positions:
            raise ValueError(
                "Sample positions must match "
                "dataset.input_positions."
            )

        if (
            previous_index is not None
            and sample.sample_index <= previous_index
        ):
            raise ValueError(
                "Sample indices must be strictly increasing."
            )

        previous_index = sample.sample_index


def get_sequence_sample_count(
    dataset: SequenceDataset,
) -> int:
    """Return the number of sequence samples."""

    validate_sequence_dataset(
        dataset
    )

    return len(
        dataset.samples
    )


def get_sequence_sample(
    dataset: SequenceDataset,
    sample_index: int,
) -> SequenceSample:
    """Return one sequence sample by deterministic index."""

    validate_sequence_dataset(
        dataset
    )

    if (
        isinstance(sample_index, bool)
        or not isinstance(sample_index, int)
    ):
        raise TypeError(
            "sample_index must be an integer."
        )

    for sample in dataset.samples:
        if sample.sample_index == sample_index:
            return sample

    raise ValueError(
        f"Sequence sample not found: {sample_index}"
    )


def get_sequence_feature_names(
    dataset: SequenceDataset,
) -> tuple[str, ...]:
    """Return feature names defined by the dataset contract."""

    validate_sequence_dataset(
        dataset
    )

    return dataset.feature_names


def get_sequence_input_positions(
    dataset: SequenceDataset,
) -> tuple[str, ...]:
    """Return configured input positions."""

    validate_sequence_dataset(
        dataset
    )

    return dataset.input_positions


def get_sequence_target_positions(
    dataset: SequenceDataset,
) -> tuple[str, ...]:
    """Return configured target positions."""

    validate_sequence_dataset(
        dataset
    )

    return dataset.target_positions