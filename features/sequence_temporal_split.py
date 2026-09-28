from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.sequence_dataset import (
    SequenceDataset,
    SequenceSample,
)


# ---------------------------------------------------------------------------
# Temporal split contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TemporalSplitConfig:
    """
    Configuration for a deterministic chronological train/validation split.

    Samples whose target_date is on or before split_date belong to training.

    Samples whose target_date is strictly after split_date belong to
    validation.
    """

    split_date: date


@dataclass(frozen=True)
class TemporalSequenceSplit:
    """
    Immutable result of a chronological train/validation split.
    """

    split_date: date
    train_samples: tuple[SequenceSample, ...]
    validation_samples: tuple[SequenceSample, ...]

    @property
    def train_count(self) -> int:
        return len(self.train_samples)

    @property
    def validation_count(self) -> int:
        return len(self.validation_samples)

    @property
    def total_count(self) -> int:
        return (
            self.train_count
            + self.validation_count
        )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_temporal_split_config(
    config: TemporalSplitConfig,
) -> None:
    """
    Validate temporal split configuration.
    """

    if not isinstance(
        config,
        TemporalSplitConfig,
    ):
        raise TypeError(
            "config must be a TemporalSplitConfig."
        )

    if not isinstance(
        config.split_date,
        date,
    ):
        raise TypeError(
            "split_date must be a date."
        )


def _validate_dataset(
    dataset: SequenceDataset,
) -> None:
    if not isinstance(
        dataset,
        SequenceDataset,
    ):
        raise TypeError(
            "dataset must be a SequenceDataset."
        )

    previous_target_date: date | None = None

    for sample in dataset.samples:
        if not isinstance(
            sample,
            SequenceSample,
        ):
            raise TypeError(
                "dataset.samples must contain "
                "SequenceSample objects."
            )

        if previous_target_date is not None:
            if sample.target_date <= previous_target_date:
                raise ValueError(
                    (
                        "Sequence samples must be strictly "
                        "chronological by target_date."
                    )
                )

        previous_target_date = sample.target_date


def _validate_split_result(
    split: TemporalSequenceSplit,
) -> None:
    """
    Validate the invariants of an already-created split.
    """

    if not isinstance(
        split,
        TemporalSequenceSplit,
    ):
        raise TypeError(
            "split must be a TemporalSequenceSplit."
        )

    if not isinstance(
        split.split_date,
        date,
    ):
        raise TypeError(
            "split_date must be a date."
        )

    for sample in split.train_samples:
        if sample.target_date > split.split_date:
            raise ValueError(
                (
                    "Training sample target_date must be "
                    "on or before split_date."
                )
            )

    for sample in split.validation_samples:
        if sample.target_date <= split.split_date:
            raise ValueError(
                (
                    "Validation sample target_date must be "
                    "strictly after split_date."
                )
            )

    train_indices = {
        sample.sample_index
        for sample in split.train_samples
    }

    validation_indices = {
        sample.sample_index
        for sample in split.validation_samples
    }

    if train_indices.intersection(
        validation_indices
    ):
        raise ValueError(
            "A sequence sample cannot exist in both train and validation."
        )

    combined = (
        split.train_samples
        + split.validation_samples
    )

    combined_sorted = tuple(
        sorted(
            combined,
            key=lambda sample: (
                sample.target_date,
                sample.sample_index,
            ),
        )
    )

    if len(combined_sorted) != len(combined):
        raise ValueError(
            "Temporal split contains duplicate samples."
        )


# ---------------------------------------------------------------------------
# Main temporal split
# ---------------------------------------------------------------------------


def split_sequence_dataset_temporally(
    dataset: SequenceDataset,
    config: TemporalSplitConfig,
) -> TemporalSequenceSplit:
    """
    Split a SequenceDataset into chronological train and validation samples.

    Rule:

        target_date <= split_date
            -> training

        target_date > split_date
            -> validation

    The original sample order is preserved.
    No randomization or shuffling is performed.
    """

    validate_temporal_split_config(
        config
    )

    _validate_dataset(
        dataset
    )

    train_samples: list[SequenceSample] = []
    validation_samples: list[SequenceSample] = []

    for sample in dataset.samples:
        if sample.target_date <= config.split_date:
            train_samples.append(
                sample
            )
        else:
            validation_samples.append(
                sample
            )

    split = TemporalSequenceSplit(
        split_date=config.split_date,
        train_samples=tuple(
            train_samples
        ),
        validation_samples=tuple(
            validation_samples
        ),
    )

    _validate_split_result(
        split
    )

    return split


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------


def get_train_samples(
    split: TemporalSequenceSplit,
) -> tuple[SequenceSample, ...]:
    if not isinstance(
        split,
        TemporalSequenceSplit,
    ):
        raise TypeError(
            "split must be a TemporalSequenceSplit."
        )

    return split.train_samples


def get_validation_samples(
    split: TemporalSequenceSplit,
) -> tuple[SequenceSample, ...]:
    if not isinstance(
        split,
        TemporalSequenceSplit,
    ):
        raise TypeError(
            "split must be a TemporalSequenceSplit."
        )

    return split.validation_samples


def get_train_count(
    split: TemporalSequenceSplit,
) -> int:
    if not isinstance(
        split,
        TemporalSequenceSplit,
    ):
        raise TypeError(
            "split must be a TemporalSequenceSplit."
        )

    return split.train_count


def get_validation_count(
    split: TemporalSequenceSplit,
) -> int:
    if not isinstance(
        split,
        TemporalSequenceSplit,
    ):
        raise TypeError(
            "split must be a TemporalSequenceSplit."
        )

    return split.validation_count


def get_total_split_count(
    split: TemporalSequenceSplit,
) -> int:
    if not isinstance(
        split,
        TemporalSequenceSplit,
    ):
        raise TypeError(
            "split must be a TemporalSequenceSplit."
        )

    return split.total_count