from datetime import date

import pytest

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.sequence_dataset import (
    SequenceDatasetConfig,
)
from features.sequence_windows import (
    SequenceWindow,
    SequenceWindowDataset,
    build_sequence_windows,
    get_sequence_window,
    get_sequence_window_count,
    get_sequence_window_dates,
    get_sequence_window_features,
    get_sequence_windows,
    validate_sequence_window,
    validate_sequence_window_dataset,
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


def test_empty_history_returns_empty_dataset():
    result = build_sequence_windows(
        (),
        config(),
    )

    assert isinstance(
        result,
        SequenceWindowDataset,
    )
    assert result.windows == ()


def test_fixed_length_windows_are_created():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    assert get_sequence_window_count(result) == 3


def test_fixed_length_windows_are_sliding():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    windows = get_sequence_windows(result)

    assert [
        window.result_ids
        for window in windows
    ] == [
        (1, 2, 3),
        (2, 3, 4),
        (3, 4, 5),
    ]


def test_window_indices_are_deterministic():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    assert [
        window.window_index
        for window in result.windows
    ] == [0, 1, 2]


def test_window_dates_are_correct():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    windows = result.windows

    assert (
        windows[0].sequence_start_date
        == date(2026, 1, 1)
    )
    assert (
        windows[0].sequence_end_date
        == date(2026, 1, 3)
    )

    assert (
        windows[1].sequence_start_date
        == date(2026, 1, 2)
    )
    assert (
        windows[1].sequence_end_date
        == date(2026, 1, 4)
    )


def test_window_length_matches_configuration():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    assert all(
        window.sequence_length == 3
        for window in result.windows
    )


def test_insufficient_history_returns_no_complete_windows():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
    )

    result = build_sequence_windows(
        observations,
        config(sequence_length=3),
    )

    assert result.windows == ()


def test_zero_values_are_preserved():
    observations = (
        observation(
            "2026-01-01",
            1,
            positions=(0, 2, 0, 4, 0, 6, 0, 8),
        ),
        observation(
            "2026-01-02",
            2,
            positions=(1, 0, 3, 0, 5, 0, 7, 0),
        ),
    )

    result = build_sequence_windows(
        observations,
        config(
            sequence_length=2,
            input_positions=("col1", "col2"),
        ),
    )

    assert result.windows[0].features == (
        (0, 2),
        (1, 0),
    )


def test_only_configured_positions_are_extracted():
    result = build_sequence_windows(
        history(),
        config(
            sequence_length=2,
            input_positions=("col2", "col5", "col8"),
        ),
    )

    assert result.windows[0].features == (
        (2, 5, 8),
        (2, 5, 8),
    )


def test_result_ids_are_preserved():
    result = build_sequence_windows(
        history(),
        config(sequence_length=2),
    )

    assert result.windows[0].result_ids == (1, 2)
    assert result.windows[1].result_ids == (2, 3)


def test_market_ids_are_preserved():
    observations = (
        observation("2026-01-01", 1, market_id=10),
        observation("2026-01-02", 2, market_id=20),
        observation("2026-01-03", 3, market_id=30),
    )

    result = build_sequence_windows(
        observations,
        config(sequence_length=2),
    )

    assert result.windows[0].market_ids == (10, 20)
    assert result.windows[1].market_ids == (20, 30)


def test_non_tuple_observations_are_rejected():
    with pytest.raises(TypeError):
        build_sequence_windows(
            list(history()),
            config(),
        )


def test_invalid_observation_type_is_rejected():
    observations = (
        history()[0],
        "invalid",
        history()[2],
    )

    with pytest.raises(TypeError):
        build_sequence_windows(
            observations,
            config(),
        )


def test_duplicate_dates_are_rejected():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-01", 2),
        observation("2026-01-03", 3),
    )

    with pytest.raises(ValueError):
        build_sequence_windows(
            observations,
            config(sequence_length=2),
        )


def test_reverse_chronology_is_rejected():
    observations = (
        observation("2026-01-03", 3),
        observation("2026-01-02", 2),
        observation("2026-01-01", 1),
    )

    with pytest.raises(ValueError):
        build_sequence_windows(
            observations,
            config(sequence_length=2),
        )


def test_incomplete_windows_are_not_created_by_default():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
    )

    result = build_sequence_windows(
        observations,
        config(
            sequence_length=4,
            allow_incomplete_sequences=False,
        ),
    )

    assert result.windows == ()


def test_incomplete_windows_can_be_enabled():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
    )

    result = build_sequence_windows(
        observations,
        config(
            sequence_length=4,
            allow_incomplete_sequences=True,
        ),
    )

    assert [
        window.result_ids
        for window in result.windows
    ] == [
        (1,),
        (1, 2),
        (1, 2, 3),
    ]


def test_incomplete_windows_are_left_aligned_until_full():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
        observation("2026-01-04", 4),
    )

    result = build_sequence_windows(
        observations,
        config(
            sequence_length=3,
            allow_incomplete_sequences=True,
        ),
    )

    assert [
        window.result_ids
        for window in result.windows
    ] == [
        (1,),
        (1, 2),
        (1, 2, 3),
        (2, 3, 4),
    ]


def test_incomplete_windows_have_correct_lengths():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
    )

    result = build_sequence_windows(
        observations,
        config(
            sequence_length=5,
            allow_incomplete_sequences=True,
        ),
    )

    assert [
        window.sequence_length
        for window in result.windows
    ] == [1, 2, 3]


def test_window_end_dates_are_strictly_increasing():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    dates = [
        window.sequence_end_date
        for window in result.windows
    ]

    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))


def test_window_contains_no_future_observation():
    observations = history()

    result = build_sequence_windows(
        observations[:4],
        config(sequence_length=3),
    )

    assert all(
        all(
            result_id <= 4
            for result_id in window.result_ids
        )
        for window in result.windows
    )


def test_target_information_is_not_part_of_window():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    for window in result.windows:
        assert not hasattr(window, "target")
        assert not hasattr(window, "target_date")


def test_window_is_immutable():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    with pytest.raises(
        AttributeError
    ):
        result.windows[0].window_index = 99


def test_dataset_is_immutable():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    with pytest.raises(
        AttributeError
    ):
        result.windows = ()


def test_window_validation_accepts_valid_window():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    validate_sequence_window(
        result.windows[0]
    )


def test_invalid_window_type_is_rejected():
    with pytest.raises(TypeError):
        validate_sequence_window(
            "invalid"
        )


def test_window_index_must_not_be_negative():
    window = SequenceWindow(
        window_index=-1,
        sequence_start_date=date(2026, 1, 1),
        sequence_end_date=date(2026, 1, 1),
        sequence_length=1,
        configured_sequence_length=3,
        positions=("col1",),
        features=((1,),),
        result_ids=(1,),
        market_ids=(1,),
    )

    with pytest.raises(ValueError):
        validate_sequence_window(window)


def test_window_feature_row_count_must_match_length():
    window = SequenceWindow(
        window_index=0,
        sequence_start_date=date(2026, 1, 1),
        sequence_end_date=date(2026, 1, 2),
        sequence_length=2,
        configured_sequence_length=3,
        positions=("col1",),
        features=((1,),),
        result_ids=(1, 2),
        market_ids=(1, 1),
    )

    with pytest.raises(ValueError):
        validate_sequence_window(window)


def test_window_feature_width_must_match_positions():
    window = SequenceWindow(
        window_index=0,
        sequence_start_date=date(2026, 1, 1),
        sequence_end_date=date(2026, 1, 2),
        sequence_length=2,
        configured_sequence_length=3,
        positions=("col1", "col2"),
        features=((1,), (2,)),
        result_ids=(1, 2),
        market_ids=(1, 1),
    )

    with pytest.raises(ValueError):
        validate_sequence_window(window)


def test_window_dataset_validation():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    validate_sequence_window_dataset(
        result
    )


def test_invalid_window_dataset_type_is_rejected():
    with pytest.raises(TypeError):
        validate_sequence_window_dataset(
            "invalid"
        )


def test_get_window_by_index():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    window = get_sequence_window(
        result,
        1,
    )

    assert window.result_ids == (2, 3, 4)


def test_missing_window_is_rejected():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    with pytest.raises(ValueError):
        get_sequence_window(
            result,
            99,
        )


def test_window_index_type_is_validated():
    result = build_sequence_windows(
        history(),
        config(sequence_length=3),
    )

    with pytest.raises(TypeError):
        get_sequence_window(
            result,
            True,
        )


def test_get_window_features():
    result = build_sequence_windows(
        history(),
        config(
            sequence_length=2,
            input_positions=("col1", "col8"),
        ),
    )

    assert get_sequence_window_features(
        result.windows[0]
    ) == (
        (1, 8),
        (1, 8),
    )


def test_get_window_dates():
    result = build_sequence_windows(
        history(),
        config(sequence_length=2),
    )

    assert get_sequence_window_dates(
        result.windows[0]
    ) == (
        date(2026, 1, 1),
        date(2026, 1, 2),
    )


def test_repeated_builds_are_identical():
    observations = history()
    cfg = config(
        sequence_length=3,
        input_positions=("col1", "col3"),
    )

    first = build_sequence_windows(
        observations,
        cfg,
    )

    second = build_sequence_windows(
        observations,
        cfg,
    )

    assert first == second


def test_window_positions_match_configuration():
    result = build_sequence_windows(
        history(),
        config(
            sequence_length=2,
            input_positions=("col2", "col6"),
        ),
    )

    assert all(
        window.positions == ("col2", "col6")
        for window in result.windows
    )


def test_single_observation_can_form_incomplete_window():
    result = build_sequence_windows(
        (
            observation("2026-01-01", 1),
        ),
        config(
            sequence_length=3,
            allow_incomplete_sequences=True,
        ),
    )

    assert len(result.windows) == 1
    assert result.windows[0].result_ids == (1,)


def test_single_observation_cannot_form_complete_window():
    result = build_sequence_windows(
        (
            observation("2026-01-01", 1),
        ),
        config(
            sequence_length=3,
            allow_incomplete_sequences=False,
        ),
    )

    assert result.windows == ()