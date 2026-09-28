from __future__ import annotations

from features.sequence_dataset import (
    SequenceDataset,
    SequenceDatasetConfig,
    SequenceSample,
    build_sequence_dataset,
    validate_sequence_dataset,
    validate_sequence_dataset_config,
)
from features.sequence_targets import (
    SequenceTargetDataset,
    validate_sequence_target_dataset,
)
from features.sequence_windows import (
    SequenceWindowDataset,
    validate_sequence_window_dataset,
)


def validate_sequence_window_target_alignment(
    windows: SequenceWindowDataset,
    targets: SequenceTargetDataset,
) -> None:
    """
    Validate the structural relationship between sequence windows
    and sequence targets.

    Every target must belong to exactly one existing window and
    must occur strictly after that window.
    """

    validate_sequence_window_dataset(
        windows
    )

    validate_sequence_target_dataset(
        targets
    )

    window_by_index = {
        window.window_index: window
        for window in windows.windows
    }

    target_indices = set()

    for target in targets.targets:
        if target.window_index in target_indices:
            raise ValueError(
                "Duplicate target for window index: "
                f"{target.window_index}"
            )

        target_indices.add(
            target.window_index
        )

        window = window_by_index.get(
            target.window_index
        )

        if window is None:
            raise ValueError(
                "Target references a window that does not exist: "
                f"{target.window_index}"
            )

        if target.target_date <= window.sequence_end_date:
            raise ValueError(
                "Target date must be strictly after "
                "sequence end date for window: "
                f"{target.window_index}"
            )

        if target.result_id in window.result_ids:
            raise ValueError(
                "Target result_id is already present inside "
                "the input sequence for window: "
                f"{target.window_index}"
            )

        if target.target_positions != targets.target_positions:
            raise ValueError(
                "Target positions are inconsistent with "
                "the target dataset."
            )


def _build_samples(
    windows: SequenceWindowDataset,
    targets: SequenceTargetDataset,
    config: SequenceDatasetConfig,
) -> tuple[SequenceSample, ...]:
    """Build final SequenceSample records after validation."""

    target_by_window = {
        target.window_index: target
        for target in targets.targets
    }

    samples: list[SequenceSample] = []

    for window in windows.windows:
        target = target_by_window.get(
            window.window_index
        )

        if target is None:
            continue

        sample = SequenceSample(
            sample_index=window.window_index,
            sequence_start_date=window.sequence_start_date,
            sequence_end_date=window.sequence_end_date,
            target_date=target.target_date,
            sequence_length=window.sequence_length,
            positions=window.positions,
            features=window.features,
            target=target.target,
        )

        samples.append(
            sample
        )

    return tuple(samples)


def build_validated_sequence_dataset(
    windows: SequenceWindowDataset,
    targets: SequenceTargetDataset,
    config: SequenceDatasetConfig,
) -> SequenceDataset:
    """
    Build the final validated Phase 16 sequence dataset.

    This function performs integration-level validation only.

    It does not:
    - construct new windows
    - construct new targets
    - perform prediction
    - train models
    - perform temporal splitting
    """

    validate_sequence_dataset_config(
        config
    )

    validate_sequence_window_dataset(
        windows
    )

    validate_sequence_target_dataset(
        targets
    )

    if windows.input_positions != config.input_positions:
        raise ValueError(
            "Window input positions must match "
            "dataset configuration."
        )

    if targets.target_positions != config.target_positions:
        raise ValueError(
            "Target positions must match "
            "dataset configuration."
        )

    if (
        windows.configured_sequence_length
        != config.sequence_length
    ):
        raise ValueError(
            "Window sequence length must match "
            "dataset configuration."
        )

    validate_sequence_window_target_alignment(
        windows,
        targets,
    )

    samples = _build_samples(
        windows,
        targets,
        config,
    )

    dataset = build_sequence_dataset(
        config,
        samples,
    )

    validate_sequence_dataset(
        dataset
    )

    return dataset


def validate_complete_sequence_dataset(
    dataset: SequenceDataset,
    config: SequenceDatasetConfig,
) -> None:
    """
    Validate an already-built final sequence dataset
    against its configuration contract.
    """

    validate_sequence_dataset_config(
        config
    )

    validate_sequence_dataset(
        dataset
    )

    if dataset.sequence_length != config.sequence_length:
        raise ValueError(
            "Dataset sequence length must match "
            "configuration."
        )

    if dataset.input_positions != config.input_positions:
        raise ValueError(
            "Dataset input positions must match "
            "configuration."
        )

    if dataset.target_positions != config.target_positions:
        raise ValueError(
            "Dataset target positions must match "
            "configuration."
        )

    if dataset.feature_names != config.feature_names:
        raise ValueError(
            "Dataset feature names must match "
            "configuration."
        )

    previous_target_date = None

    for sample in dataset.samples:
        if sample.target_date <= sample.sequence_end_date:
            raise ValueError(
                "Target date must be strictly after "
                "sequence end date."
            )

        if previous_target_date is not None:
            if sample.target_date <= previous_target_date:
                raise ValueError(
                    "Target dates must be strictly increasing."
                )

        previous_target_date = sample.target_date


def get_validated_sequence_sample_count(
    dataset: SequenceDataset,
    config: SequenceDatasetConfig,
) -> int:
    """Return the number of validated sequence samples."""

    validate_complete_sequence_dataset(
        dataset,
        config,
    )

    return len(
        dataset.samples
    )