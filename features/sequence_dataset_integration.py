from __future__ import annotations

from dataclasses import dataclass

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.sequence_dataset import (
    SequenceDataset,
    SequenceDatasetConfig,
)
from features.sequence_dataset_validator import (
    build_validated_sequence_dataset,
)
from features.sequence_leakage_validator import (
    CLEAN,
    SequenceLeakageResult,
    validate_sequence_components_point_in_time,
    validate_sequence_dataset_point_in_time,
)
from features.sequence_targets import (
    SequenceTargetDataset,
    build_sequence_targets,
)
from features.sequence_temporal_split import (
    TemporalSequenceSplit,
    TemporalSplitConfig,
    split_sequence_dataset_temporally,
)
from features.sequence_windows import (
    SequenceWindowDataset,
    build_sequence_windows,
)


@dataclass(frozen=True)
class SequenceDatasetIntegrationResult:
    """Complete integrated output of the Phase 16 sequence pipeline."""

    sequence_config: SequenceDatasetConfig
    temporal_split_config: TemporalSplitConfig

    windows: SequenceWindowDataset
    targets: SequenceTargetDataset
    dataset: SequenceDataset

    component_leakage: SequenceLeakageResult
    dataset_leakage: SequenceLeakageResult

    temporal_split: TemporalSequenceSplit

    @property
    def sample_count(self) -> int:
        return len(self.dataset.samples)

    @property
    def window_count(self) -> int:
        return len(self.windows.windows)

    @property
    def target_count(self) -> int:
        return len(self.targets.targets)

    @property
    def train_count(self) -> int:
        return self.temporal_split.train_count

    @property
    def validation_count(self) -> int:
        return self.temporal_split.validation_count

    @property
    def is_leakage_free(self) -> bool:
        return (
            self.component_leakage.status == CLEAN
            and self.dataset_leakage.status == CLEAN
        )


def _validate_observations(
    observations: tuple[HistoricalFeatureObservation, ...],
) -> None:
    if not isinstance(observations, tuple):
        raise TypeError(
            "observations must be a tuple of HistoricalFeatureObservation objects."
        )

    for observation in observations:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "observations must contain only "
                "HistoricalFeatureObservation objects."
            )


def _validate_sequence_config(
    config: SequenceDatasetConfig,
) -> None:
    if not isinstance(
        config,
        SequenceDatasetConfig,
    ):
        raise TypeError(
            "sequence_config must be a SequenceDatasetConfig."
        )


def _validate_temporal_split_config(
    config: TemporalSplitConfig,
) -> None:
    if not isinstance(
        config,
        TemporalSplitConfig,
    ):
        raise TypeError(
            "temporal_split_config must be a TemporalSplitConfig."
        )


def _require_clean_leakage_result(
    result: SequenceLeakageResult,
    stage: str,
) -> None:
    if not isinstance(
        result,
        SequenceLeakageResult,
    ):
        raise TypeError(
            f"{stage} leakage validation must return "
            "a SequenceLeakageResult."
        )

    if result.status != CLEAN:
        raise ValueError(
            f"{stage} sequence leakage validation failed: "
            f"{result.issues}"
        )


def build_sequence_dataset_integration(
    observations: tuple[HistoricalFeatureObservation, ...],
    sequence_config: SequenceDatasetConfig,
    temporal_split_config: TemporalSplitConfig,
) -> SequenceDatasetIntegrationResult:
    """
    Build the complete Phase 16 sequence dataset pipeline.

    The function intentionally orchestrates existing Phase 16 components.
    It does not duplicate sequence-window construction, target construction,
    dataset validation, leakage validation, or temporal splitting logic.
    """

    _validate_observations(observations)
    _validate_sequence_config(sequence_config)
    _validate_temporal_split_config(temporal_split_config)

    # ---------------------------------------------------------------
    # 16.2 — Sequence windows
    # ---------------------------------------------------------------
    windows = build_sequence_windows(
        observations,
        sequence_config,
    )

    # ---------------------------------------------------------------
    # 16.3 — Sequence targets
    # ---------------------------------------------------------------
    targets = build_sequence_targets(
        windows,
        observations,
        sequence_config,
    )

    # ---------------------------------------------------------------
    # 16.5 — Component-level PIT / leakage validation
    # ---------------------------------------------------------------
    component_leakage = validate_sequence_components_point_in_time(
        windows,
        targets,
        observations,
    )

    _require_clean_leakage_result(
        component_leakage,
        "Component",
    )

    # ---------------------------------------------------------------
    # 16.4 — Validated final sequence dataset
    # ---------------------------------------------------------------
    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        sequence_config,
    )

    # ---------------------------------------------------------------
    # 16.5 — Final dataset PIT / leakage validation
    # ---------------------------------------------------------------
    dataset_leakage = validate_sequence_dataset_point_in_time(
        dataset,
        observations,
    )

    _require_clean_leakage_result(
        dataset_leakage,
        "Dataset",
    )

    # ---------------------------------------------------------------
    # 16.6 — Temporal train / validation split
    # ---------------------------------------------------------------
    temporal_split = split_sequence_dataset_temporally(
        dataset,
        temporal_split_config,
    )

    return SequenceDatasetIntegrationResult(
        sequence_config=sequence_config,
        temporal_split_config=temporal_split_config,
        windows=windows,
        targets=targets,
        dataset=dataset,
        component_leakage=component_leakage,
        dataset_leakage=dataset_leakage,
        temporal_split=temporal_split,
    )


def get_integrated_dataset(
    result: SequenceDatasetIntegrationResult,
) -> SequenceDataset:
    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a SequenceDatasetIntegrationResult."
        )

    return result.dataset


def get_integrated_temporal_split(
    result: SequenceDatasetIntegrationResult,
) -> TemporalSequenceSplit:
    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a SequenceDatasetIntegrationResult."
        )

    return result.temporal_split


def get_integrated_train_samples(
    result: SequenceDatasetIntegrationResult,
):
    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a SequenceDatasetIntegrationResult."
        )

    return result.temporal_split.train_samples


def get_integrated_validation_samples(
    result: SequenceDatasetIntegrationResult,
):
    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a SequenceDatasetIntegrationResult."
        )

    return result.temporal_split.validation_samples


def get_integrated_sample_count(
    result: SequenceDatasetIntegrationResult,
) -> int:
    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a SequenceDatasetIntegrationResult."
        )

    return result.sample_count


def get_integrated_train_count(
    result: SequenceDatasetIntegrationResult,
) -> int:
    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a SequenceDatasetIntegrationResult."
        )

    return result.train_count


def get_integrated_validation_count(
    result: SequenceDatasetIntegrationResult,
) -> int:
    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a SequenceDatasetIntegrationResult."
        )

    return result.validation_count


def is_integrated_dataset_leakage_free(
    result: SequenceDatasetIntegrationResult,
) -> bool:
    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a SequenceDatasetIntegrationResult."
        )

    return result.is_leakage_free