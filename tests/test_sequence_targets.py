from datetime import date

import pytest

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.sequence_dataset import (
    SequenceDatasetConfig,
)
from features.sequence_targets import (
    SequenceTarget,
    SequenceTargetDataset,
    build_sequence_targets,
    get_sequence_target,
    get_sequence_target_count,
    get_sequence_target_date,
    get_sequence_target_values,
    get_sequence_targets,
    validate_sequence_target,
    validate_sequence_target_dataset,
)
from features.sequence_windows import (
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
    )


def build_windows(
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

    return build_sequence_windows(
        observations,
        cfg,
    )


def test_empty_windows_return_empty_targets():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
    )

    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert isinstance(
        result,
        SequenceTargetDataset,
    )
    assert result.targets == ()


def test_targets_are_created_from_following_observation():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert [
        target.result_id
        for target in result.targets
    ] == [4, 5]


def test_target_window_mapping_is_correct():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert [
        target.window_index
        for target in result.targets
    ] == [0, 1]


def test_target_dates_are_immediately_after_window_dates():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert result.targets[0].target_date == date(
        2026,
        1,
        4,
    )

    assert result.targets[1].target_date == date(
        2026,
        1,
        5,
    )

    assert (
        result.targets[0].target_date
        > windows.windows[0].sequence_end_date
    )

    assert (
        result.targets[1].target_date
        > windows.windows[1].sequence_end_date
    )


def test_target_values_are_extracted_from_configured_position():
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
        observation(
            "2026-01-03",
            3,
            positions=(0, 1, 2, 3, 4, 5, 6, 7),
        ),
    )

    cfg = config(
        sequence_length=2,
        target_positions=("col3", "col8"),
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert result.targets[0].target == (2, 7)


def test_zero_target_values_are_preserved():
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
        observation(
            "2026-01-03",
            3,
            positions=(1, 1, 1, 1, 1, 1, 1, 1),
        ),
    )

    cfg = config(
        sequence_length=2,
        target_positions=("col1", "col8"),
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert result.targets[0].target == (1, 1)


def test_target_zero_is_not_treated_as_missing():
    observations = (
        observation(
            "2026-01-01",
            1,
            positions=(1, 2, 3, 4, 5, 6, 7, 8),
        ),
        observation(
            "2026-01-02",
            2,
            positions=(0, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    cfg = config(
        sequence_length=1,
        target_positions=("col1",),
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert result.targets[0].target == (0,)


def test_last_window_has_no_target_when_no_following_observation():
    observations = history()
    cfg = config(sequence_length=2)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert [
        target.window_index
        for target in result.targets
    ] == [0, 1, 2]

    assert all(
        target.result_id <= 5
        for target in result.targets
    )


def test_target_is_never_the_window_final_observation():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    for target in result.targets:
        window = next(
            window
            for window in windows.windows
            if window.window_index == target.window_index
        )

        assert target.result_id not in window.result_ids


def test_target_date_is_strictly_after_sequence_end():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    for target in result.targets:
        window = next(
            window
            for window in windows.windows
            if window.window_index == target.window_index
        )

        assert (
            target.target_date
            > window.sequence_end_date
        )


def test_target_positions_are_preserved():
    observations = history()

    cfg = config(
        sequence_length=2,
        target_positions=("col2", "col4", "col8"),
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert result.target_positions == (
        "col2",
        "col4",
        "col8",
    )

    assert result.targets[0].target_positions == (
        "col2",
        "col4",
        "col8",
    )


def test_target_market_id_is_preserved():
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
        ),
    )

    cfg = config(
        sequence_length=1,
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert result.targets[0].market_id == 20


def test_target_result_id_is_preserved():
    observations = history()
    cfg = config(sequence_length=2)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert result.targets[0].result_id == 3


def test_incomplete_windows_can_receive_targets():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
        observation("2026-01-04", 4),
    )

    cfg = config(
        sequence_length=3,
        allow_incomplete_sequences=True,
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert [
        target.window_index
        for target in result.targets
    ] == [0, 1, 2]

    assert [
        target.result_id
        for target in result.targets
    ] == [2, 3, 4]


def test_incomplete_window_at_end_has_no_target():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
    )

    cfg = config(
        sequence_length=3,
        allow_incomplete_sequences=True,
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert [
        target.window_index
        for target in result.targets
    ] == [0, 1]

    assert [
        target.result_id
        for target in result.targets
    ] == [2, 3]


def test_target_count_is_deterministic():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert get_sequence_target_count(result) == 2


def test_get_target_by_window_index():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    target = get_sequence_target(
        result,
        0,
    )

    assert target.result_id == 4


def test_missing_target_is_rejected():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    with pytest.raises(ValueError):
        get_sequence_target(
            result,
            2,
        )


def test_get_target_values():
    observations = history()
    cfg = config(
        sequence_length=3,
        target_positions=("col1", "col2"),
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert get_sequence_target_values(
        result.targets[0]
    ) == (1, 2)


def test_get_target_date():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert get_sequence_target_date(
        result.targets[0]
    ) == date(2026, 1, 4)


def test_target_dataset_is_immutable():
    observations = history()
    cfg = config(sequence_length=3)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    with pytest.raises(AttributeError):
        result.targets = ()


def test_target_is_immutable():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=("col1",),
        target=(1,),
        result_id=2,
        market_id=1,
    )

    with pytest.raises(AttributeError):
        target.target = (9,)


def test_valid_target_passes_validation():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=("col1",),
        target=(1,),
        result_id=2,
        market_id=1,
    )

    validate_sequence_target(target)


def test_invalid_target_type_is_rejected():
    with pytest.raises(TypeError):
        validate_sequence_target("invalid")


def test_target_width_must_match_positions():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=("col1", "col2"),
        target=(1,),
        result_id=2,
        market_id=1,
    )

    with pytest.raises(ValueError):
        validate_sequence_target(target)


def test_duplicate_target_positions_are_rejected():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=("col1", "col1"),
        target=(1, 1),
        result_id=2,
        market_id=1,
    )

    with pytest.raises(ValueError):
        validate_sequence_target(target)


def test_invalid_target_position_is_rejected():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=("invalid",),
        target=(1,),
        result_id=2,
        market_id=1,
    )

    with pytest.raises(ValueError):
        validate_sequence_target(target)


def test_non_tuple_target_positions_are_rejected():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=["col1"],
        target=(1,),
        result_id=2,
        market_id=1,
    )

    with pytest.raises(TypeError):
        validate_sequence_target(target)


def test_non_tuple_target_values_are_rejected():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=("col1",),
        target=[1],
        result_id=2,
        market_id=1,
    )

    with pytest.raises(TypeError):
        validate_sequence_target(target)


def test_boolean_window_index_is_rejected():
    target = SequenceTarget(
        window_index=True,
        target_date=date(2026, 1, 2),
        target_positions=("col1",),
        target=(1,),
        result_id=2,
        market_id=1,
    )

    with pytest.raises(TypeError):
        validate_sequence_target(target)


def test_boolean_result_id_is_rejected():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=("col1",),
        target=(1,),
        result_id=True,
        market_id=1,
    )

    with pytest.raises(TypeError):
        validate_sequence_target(target)


def test_boolean_market_id_is_rejected():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=("col1",),
        target=(1,),
        result_id=2,
        market_id=True,
    )

    with pytest.raises(TypeError):
        validate_sequence_target(target)


def test_invalid_target_dataset_type_is_rejected():
    with pytest.raises(TypeError):
        validate_sequence_target_dataset(
            "invalid"
        )


def test_target_dataset_positions_must_match_targets():
    target = SequenceTarget(
        window_index=0,
        target_date=date(2026, 1, 2),
        target_positions=("col1",),
        target=(1,),
        result_id=2,
        market_id=1,
    )

    dataset = SequenceTargetDataset(
        target_positions=("col2",),
        targets=(target,),
    )

    with pytest.raises(ValueError):
        validate_sequence_target_dataset(
            dataset
        )


def test_target_indices_must_be_strictly_increasing():
    targets = (
        SequenceTarget(
            window_index=1,
            target_date=date(2026, 1, 2),
            target_positions=("col1",),
            target=(1,),
            result_id=2,
            market_id=1,
        ),
        SequenceTarget(
            window_index=1,
            target_date=date(2026, 1, 3),
            target_positions=("col1",),
            target=(2,),
            result_id=3,
            market_id=1,
        ),
    )

    dataset = SequenceTargetDataset(
        target_positions=("col1",),
        targets=targets,
    )

    with pytest.raises(ValueError):
        validate_sequence_target_dataset(
            dataset
        )


def test_repeated_target_construction_is_identical():
    observations = history()
    cfg = config(
        sequence_length=3,
        target_positions=("col1", "col8"),
    )

    windows = build_windows(
        observations,
        cfg,
    )

    first = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    second = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert first == second


def test_target_observations_must_be_chronological():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-03", 2),
        observation("2026-01-02", 3),
    )

    cfg = config(sequence_length=1)

    windows = build_sequence_windows(
        (
            observations[0],
            observations[1],
        ),
        cfg,
    )

    with pytest.raises(ValueError):
        build_sequence_targets(
            windows,
            observations,
            cfg,
        )


def test_duplicate_result_ids_are_rejected():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 1),
    )

    cfg = config(sequence_length=1)

    windows = build_sequence_windows(
        (
            observations[0],
        ),
        cfg,
    )

    with pytest.raises(ValueError):
        build_sequence_targets(
            windows,
            observations,
            cfg,
        )


def test_target_does_not_use_an_unrelated_future_observation():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
        observation("2026-01-04", 4),
    )

    cfg = config(sequence_length=2)

    windows = build_sequence_windows(
        observations[:3],
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations[:3],
        cfg,
    )

    assert result.targets[0].result_id == 3
    assert result.targets[0].target_date == date(
        2026,
        1,
        3,
    )


def test_target_positions_can_be_single_position():
    observations = history()

    cfg = config(
        sequence_length=2,
        target_positions=("col8",),
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert result.targets[0].target == (8,)


def test_all_positions_can_be_targets():
    observations = history()

    cfg = config(
        sequence_length=2,
        target_positions=POSITIONS,
    )

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert result.targets[0].target == (
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    )


def test_target_count_matches_windows_with_following_observation():
    observations = history()

    cfg = config(sequence_length=2)

    windows = build_windows(
        observations,
        cfg,
    )

    result = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    assert len(result.targets) == len(
        windows.windows
    ) - 1