from datetime import date

import pytest

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.sequence_dataset import (
    SequenceDatasetConfig,
)
from features.sequence_dataset_integration import (
    SequenceDatasetIntegrationResult,
    build_sequence_dataset_integration,
    get_integrated_dataset,
    get_integrated_sample_count,
    get_integrated_temporal_split,
    get_integrated_train_count,
    get_integrated_train_samples,
    get_integrated_validation_count,
    get_integrated_validation_samples,
    is_integrated_dataset_leakage_free,
)
from features.sequence_leakage_validator import (
    CLEAN,
)
from features.sequence_temporal_split import (
    TemporalSplitConfig,
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


def observation(
    day,
    result_id,
    market_id=1,
    positions=(1, 2, 3, 4, 5, 6, 7, 8),
):
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=market_id,
        result_date=date.fromisoformat(day),
        positions=positions,
    )


def base_observations():
    return (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
        observation("2026-01-04", 4),
        observation("2026-01-05", 5),
        observation("2026-01-06", 6),
    )


def config(
    sequence_length=3,
    input_positions=POSITIONS,
    target_positions=("col1",),
):
    return SequenceDatasetConfig(
        sequence_length=sequence_length,
        input_positions=input_positions,
        target_positions=target_positions,
    )


def split_config(
    split_date=date(2026, 1, 4),
):
    return TemporalSplitConfig(
        split_date=split_date,
    )


def build_clean_result():
    return build_sequence_dataset_integration(
        base_observations(),
        config(),
        split_config(),
    )


def test_integration_returns_expected_result_type():
    result = build_clean_result()

    assert isinstance(
        result,
        SequenceDatasetIntegrationResult,
    )


def test_integration_builds_windows():
    result = build_clean_result()

    assert result.window_count == 4


def test_integration_builds_targets():
    result = build_clean_result()

    assert result.target_count == 3


def test_integration_builds_final_dataset():
    result = build_clean_result()

    assert result.sample_count == 3


def test_integration_component_leakage_is_clean():
    result = build_clean_result()

    assert result.component_leakage.status == CLEAN
    assert result.component_leakage.issues == ()


def test_integration_dataset_leakage_is_clean():
    result = build_clean_result()

    assert result.dataset_leakage.status == CLEAN
    assert result.dataset_leakage.issues == ()


def test_integration_is_leakage_free():
    result = build_clean_result()

    assert result.is_leakage_free is True
    assert is_integrated_dataset_leakage_free(result) is True


def test_integration_temporal_split_is_created():
    result = build_clean_result()

    assert result.temporal_split.split_date == date(
        2026,
        1,
        4,
    )


def test_training_samples_are_on_or_before_split_date():
    result = build_clean_result()

    assert all(
        sample.target_date <= date(2026, 1, 4)
        for sample in result.temporal_split.train_samples
    )


def test_validation_samples_are_after_split_date():
    result = build_clean_result()

    assert all(
        sample.target_date > date(2026, 1, 4)
        for sample in result.temporal_split.validation_samples
    )


def test_train_and_validation_samples_do_not_overlap():
    result = build_clean_result()

    train_indices = {
        sample.sample_index
        for sample in result.temporal_split.train_samples
    }

    validation_indices = {
        sample.sample_index
        for sample in result.temporal_split.validation_samples
    }

    assert train_indices.isdisjoint(validation_indices)


def test_all_final_samples_are_preserved_by_split():
    result = build_clean_result()

    assert (
        result.train_count
        + result.validation_count
        == result.sample_count
    )


def test_train_count_accessor():
    result = build_clean_result()

    assert get_integrated_train_count(result) == 1


def test_validation_count_accessor():
    result = build_clean_result()

    assert get_integrated_validation_count(result) == 2


def test_sample_count_accessor():
    result = build_clean_result()

    assert get_integrated_sample_count(result) == 3


def test_dataset_accessor():
    result = build_clean_result()

    assert get_integrated_dataset(result) is result.dataset


def test_temporal_split_accessor():
    result = build_clean_result()

    assert get_integrated_temporal_split(result) is result.temporal_split


def test_train_samples_accessor():
    result = build_clean_result()

    assert (
        get_integrated_train_samples(result)
        == result.temporal_split.train_samples
    )


def test_validation_samples_accessor():
    result = build_clean_result()

    assert (
        get_integrated_validation_samples(result)
        == result.temporal_split.validation_samples
    )


def test_empty_history_produces_empty_integration():
    result = build_sequence_dataset_integration(
        (),
        config(),
        split_config(),
    )

    assert result.window_count == 0
    assert result.target_count == 0
    assert result.sample_count == 0
    assert result.train_count == 0
    assert result.validation_count == 0
    assert result.is_leakage_free is True


def test_integration_is_deterministic():
    observations = base_observations()
    sequence_config = config()
    temporal_config = split_config()

    first = build_sequence_dataset_integration(
        observations,
        sequence_config,
        temporal_config,
    )

    second = build_sequence_dataset_integration(
        observations,
        sequence_config,
        temporal_config,
    )

    assert first == second


def test_invalid_observations_type_is_rejected():
    with pytest.raises(TypeError):
        build_sequence_dataset_integration(
            [],
            config(),
            split_config(),
        )


def test_invalid_observation_member_is_rejected():
    with pytest.raises(TypeError):
        build_sequence_dataset_integration(
            ("invalid",),
            config(),
            split_config(),
        )


def test_invalid_sequence_config_is_rejected():
    with pytest.raises(TypeError):
        build_sequence_dataset_integration(
            base_observations(),
            "invalid",
            split_config(),
        )


def test_invalid_temporal_split_config_is_rejected():
    with pytest.raises(TypeError):
        build_sequence_dataset_integration(
            base_observations(),
            config(),
            "invalid",
        )


def test_different_split_date_changes_train_validation_boundary():
    result = build_sequence_dataset_integration(
        base_observations(),
        config(),
        TemporalSplitConfig(
            split_date=date(2026, 1, 5),
        ),
    )

    assert result.train_count == 2
    assert result.validation_count == 1


def test_result_preserves_sequence_configuration():
    sequence_config = config(
        sequence_length=3,
    )

    result = build_sequence_dataset_integration(
        base_observations(),
        sequence_config,
        split_config(),
    )

    assert result.sequence_config == sequence_config


def test_result_preserves_temporal_split_configuration():
    temporal_config = split_config()

    result = build_sequence_dataset_integration(
        base_observations(),
        config(),
        temporal_config,
    )

    assert result.temporal_split_config == temporal_config