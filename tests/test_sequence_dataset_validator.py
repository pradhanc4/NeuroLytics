from datetime import date

import pytest

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.sequence_dataset import (
    SequenceDataset,
    SequenceDatasetConfig,
)
from features.sequence_dataset_validator import (
    build_validated_sequence_dataset,
    get_validated_sequence_sample_count,
    validate_complete_sequence_dataset,
    validate_sequence_window_target_alignment,
)
from features.sequence_targets import (
    SequenceTarget,
    SequenceTargetDataset,
    build_sequence_targets,
)
from features.sequence_windows import (
    SequenceWindowDataset,
    build_sequence_windows,
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


def config(**overrides):
    values = {
        "sequence_length": 3,
        "input_positions": POSITIONS,
        "target_positions": ("col1",),
        "feature_names": (),
        "allow_incomplete_sequences": False,
    }

    values.update(overrides)

    return SequenceDatasetConfig(**values)


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


def history():
    return (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
        observation("2026-01-04", 4),
        observation("2026-01-05", 5),
        observation("2026-01-06", 6),
    )


def build_components(
    observations=None,
    cfg=None,
):
    observations = (
        history()
        if observations is None
        else observations
    )

    cfg = (
        config()
        if cfg is None
        else cfg
    )

    windows = build_sequence_windows(
        observations,
        cfg,
    )

    targets = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    return windows, targets, cfg


def test_validated_dataset_is_created():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert isinstance(dataset, SequenceDataset)


def test_validated_dataset_contains_aligned_samples():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert [
        sample.sample_index
        for sample in dataset.samples
    ] == [0, 1, 2]


def test_sample_target_dates_are_after_sequences():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    for sample in dataset.samples:
        assert sample.target_date > sample.sequence_end_date


def test_sample_target_values_are_preserved():
    observations = (
        observation(
            "2026-01-01",
            1,
            positions=(1, 2, 3, 4, 5, 6, 7, 8),
        ),
        observation(
            "2026-01-02",
            2,
            positions=(9, 8, 7, 6, 5, 4, 3, 2),
        ),
    )

    cfg = config(
        sequence_length=1,
        target_positions=("col2", "col8"),
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.samples[0].target == (8, 2)


def test_zero_target_is_preserved():
    observations = (
        observation(
            "2026-01-01",
            1,
            positions=(1, 2, 3, 4, 5, 6, 7, 8),
        ),
        observation(
            "2026-01-02",
            2,
            positions=(0, 0, 0, 0, 0, 0, 0, 0),
        ),
    )

    cfg = config(
        sequence_length=1,
        target_positions=("col1", "col8"),
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.samples[0].target == (0, 0)


def test_input_features_are_preserved():
    windows, targets, cfg = build_components(
        cfg=config(
            sequence_length=3,
            input_positions=("col1", "col3"),
        )
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.samples[0].features == (
        (1, 3),
        (1, 3),
        (1, 3),
    )


def test_sequence_length_is_preserved():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.sequence_length == 3

    assert all(
        sample.sequence_length == 3
        for sample in dataset.samples
    )


def test_input_positions_are_preserved():
    cfg = config(
        input_positions=("col2", "col5"),
        sequence_length=2,
    )

    windows, targets, _ = build_components(
        cfg=cfg
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.input_positions == (
        "col2",
        "col5",
    )


def test_target_positions_are_preserved():
    cfg = config(
        target_positions=("col3", "col8"),
        sequence_length=2,
    )

    windows, targets, _ = build_components(
        cfg=cfg
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.target_positions == (
        "col3",
        "col8",
    )


def test_feature_names_are_preserved():
    cfg = config(
        feature_names=(
            "col1_value",
            "col2_value",
        )
    )

    windows, targets, _ = build_components(
        cfg=cfg
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.feature_names == (
        "col1_value",
        "col2_value",
    )


def test_alignment_validation_accepts_valid_components():
    windows, targets, _ = build_components()

    validate_sequence_window_target_alignment(
        windows,
        targets,
    )


def test_target_for_unknown_window_is_rejected():
    windows, _, cfg = build_components()

    invalid_target = SequenceTarget(
        window_index=999,
        target_date=date(2026, 1, 7),
        target_positions=cfg.target_positions,
        target=(1,),
        result_id=7,
        market_id=1,
    )

    invalid_targets = SequenceTargetDataset(
        target_positions=cfg.target_positions,
        targets=(invalid_target,),
    )

    with pytest.raises(ValueError):
        validate_sequence_window_target_alignment(
            windows,
            invalid_targets,
        )


def test_duplicate_target_window_is_rejected():
    windows, targets, cfg = build_components()

    first = targets.targets[0]

    duplicate = SequenceTarget(
        window_index=first.window_index,
        target_date=first.target_date,
        target_positions=first.target_positions,
        target=first.target,
        result_id=first.result_id,
        market_id=first.market_id,
    )

    invalid_targets = SequenceTargetDataset(
        target_positions=cfg.target_positions,
        targets=(
            first,
            duplicate,
        ),
    )

    with pytest.raises(ValueError):
        validate_sequence_window_target_alignment(
            windows,
            invalid_targets,
        )


def test_target_inside_input_window_is_rejected():
    windows, _, cfg = build_components()

    window = windows.windows[0]

    invalid_target = SequenceTarget(
        window_index=window.window_index,
        target_date=window.sequence_end_date,
        target_positions=cfg.target_positions,
        target=(1,),
        result_id=window.result_ids[-1],
        market_id=1,
    )

    invalid_targets = SequenceTargetDataset(
        target_positions=cfg.target_positions,
        targets=(invalid_target,),
    )

    with pytest.raises(ValueError):
        validate_sequence_window_target_alignment(
            windows,
            invalid_targets,
        )


def test_target_date_before_sequence_end_is_rejected():
    windows, _, cfg = build_components()

    window = windows.windows[0]

    invalid_target = SequenceTarget(
        window_index=window.window_index,
        target_date=window.sequence_start_date,
        target_positions=cfg.target_positions,
        target=(1,),
        result_id=99,
        market_id=1,
    )

    invalid_targets = SequenceTargetDataset(
        target_positions=cfg.target_positions,
        targets=(invalid_target,),
    )

    with pytest.raises(ValueError):
        validate_sequence_window_target_alignment(
            windows,
            invalid_targets,
        )


def test_target_result_inside_window_is_rejected():
    windows, _, cfg = build_components()

    window = windows.windows[0]

    invalid_target = SequenceTarget(
        window_index=window.window_index,
        target_date=date(2026, 1, 4),
        target_positions=cfg.target_positions,
        target=(1,),
        result_id=window.result_ids[0],
        market_id=1,
    )

    invalid_targets = SequenceTargetDataset(
        target_positions=cfg.target_positions,
        targets=(invalid_target,),
    )

    with pytest.raises(ValueError):
        validate_sequence_window_target_alignment(
            windows,
            invalid_targets,
        )


def test_target_position_mismatch_is_rejected():
    windows, _, _ = build_components()

    invalid_target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 4),
        target_positions=("col2",),
        target=(2,),
        result_id=4,
        market_id=1,
    )

    invalid_targets = SequenceTargetDataset(
        target_positions=("col1",),
        targets=(invalid_target,),
    )

    with pytest.raises(ValueError):
        validate_sequence_window_target_alignment(
            windows,
            invalid_targets,
        )


def test_window_position_mismatch_is_rejected():
    windows, targets, cfg = build_components(
        cfg=config(
            input_positions=("col2",),
        )
    )

    altered = SequenceWindowDataset(
        configured_sequence_length=windows.configured_sequence_length,
        input_positions=("col1",),
        allow_incomplete_sequences=(
            windows.allow_incomplete_sequences
        ),
        windows=windows.windows,
    )

    with pytest.raises(ValueError):
        build_validated_sequence_dataset(
            altered,
            targets,
            cfg,
        )


def test_target_position_configuration_mismatch_is_rejected():
    windows, targets, cfg = build_components()

    altered = SequenceTargetDataset(
        target_positions=("col2",),
        targets=targets.targets,
    )

    with pytest.raises(ValueError):
        build_validated_sequence_dataset(
            windows,
            altered,
            cfg,
        )


def test_sequence_length_configuration_mismatch_is_rejected():
    windows, targets, _ = build_components()

    cfg = config(
        sequence_length=4
    )

    with pytest.raises(ValueError):
        build_validated_sequence_dataset(
            windows,
            targets,
            cfg,
        )


def test_no_target_means_no_final_sample():
    observations = history()

    cfg = config(
        sequence_length=3
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert len(dataset.samples) == (
        len(windows.windows) - 1
    )


def test_empty_components_produce_empty_dataset():
    cfg = config(
        sequence_length=3
    )

    windows = build_sequence_windows(
        (),
        cfg,
    )

    targets = SequenceTargetDataset(
        target_positions=cfg.target_positions,
        targets=(),
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.samples == ()


def test_final_dataset_passes_validation():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    validate_complete_sequence_dataset(
        dataset,
        cfg,
    )


def test_final_dataset_sample_count():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert get_validated_sequence_sample_count(
        dataset,
        cfg,
    ) == 3


def test_final_dataset_is_immutable():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    with pytest.raises(AttributeError):
        dataset.samples = ()


def test_samples_have_strictly_increasing_indices():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    indices = [
        sample.sample_index
        for sample in dataset.samples
    ]

    assert indices == sorted(indices)
    assert len(indices) == len(set(indices))


def test_target_dates_are_strictly_increasing():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    dates = [
        sample.target_date
        for sample in dataset.samples
    ]

    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))


def test_repeated_validation_is_deterministic():
    windows, targets, cfg = build_components()

    first = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    second = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert first == second


def test_incomplete_windows_are_not_integrated_into_fixed_length_dataset():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
        observation("2026-01-04", 4),
    )

    cfg = config(
        sequence_length=5,
        allow_incomplete_sequences=True,
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    with pytest.raises(ValueError):
        build_validated_sequence_dataset(
            windows,
            targets,
            cfg,
        )


def test_all_target_positions_are_integrated():
    cfg = config(
        sequence_length=2,
        target_positions=POSITIONS,
    )

    windows, targets, _ = build_components(
        cfg=cfg
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.samples[0].target == (
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    )


def test_input_and_target_can_use_different_positions():
    cfg = config(
        sequence_length=2,
        input_positions=("col1", "col2"),
        target_positions=("col7", "col8"),
    )

    windows, targets, _ = build_components(
        cfg=cfg
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.input_positions == (
        "col1",
        "col2",
    )

    assert dataset.target_positions == (
        "col7",
        "col8",
    )

    assert dataset.samples[0].features == (
        (1, 2),
        (1, 2),
    )

    assert dataset.samples[0].target == (
        7,
        8,
    )


def test_target_cannot_be_same_date_as_sequence_end():
    windows, _, cfg = build_components()

    window = windows.windows[0]

    invalid_target = SequenceTarget(
        window_index=window.window_index,
        target_date=window.sequence_end_date,
        target_positions=cfg.target_positions,
        target=(1,),
        result_id=99,
        market_id=1,
    )

    invalid_targets = SequenceTargetDataset(
        target_positions=cfg.target_positions,
        targets=(invalid_target,),
    )

    with pytest.raises(ValueError):
        validate_sequence_window_target_alignment(
            windows,
            invalid_targets,
        )


def test_final_dataset_preserves_market_independent_target_values():
    observations = (
        observation(
            "2026-01-01",
            1,
            market_id=10,
        ),
        observation(
            "2026-01-02",
            2,
            market_id=20,
            positions=(9, 8, 7, 6, 5, 4, 3, 2),
        ),
    )

    cfg = config(
        sequence_length=1,
        target_positions=("col1", "col8"),
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert dataset.samples[0].target == (
        9,
        2,
    )


def test_complete_dataset_validation_rejects_wrong_config():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    wrong_config = config(
        sequence_length=4
    )

    with pytest.raises(ValueError):
        validate_complete_sequence_dataset(
            dataset,
            wrong_config,
        )


def test_complete_dataset_validation_rejects_wrong_target_positions():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    wrong_config = config(
        target_positions=("col2",)
    )

    with pytest.raises(ValueError):
        validate_complete_sequence_dataset(
            dataset,
            wrong_config,
        )


def test_complete_dataset_validation_rejects_wrong_feature_names():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    wrong_config = config(
        feature_names=("different_feature",)
    )

    with pytest.raises(ValueError):
        validate_complete_sequence_dataset(
            dataset,
            wrong_config,
        )


def test_validator_does_not_modify_windows():
    windows, targets, cfg = build_components()

    original = windows

    build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert windows == original


def test_validator_does_not_modify_targets():
    windows, targets, cfg = build_components()

    original = targets

    build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert targets == original


def test_dataset_sample_features_remain_tuples():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert all(
        isinstance(row, tuple)
        for sample in dataset.samples
        for row in sample.features
    )


def test_dataset_sample_targets_remain_tuples():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    assert all(
        isinstance(sample.target, tuple)
        for sample in dataset.samples
    )


def test_dataset_has_no_future_target_relative_to_previous_sample():
    windows, targets, cfg = build_components()

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    for first, second in zip(
        dataset.samples,
        dataset.samples[1:],
    ):
        assert second.target_date > first.target_date