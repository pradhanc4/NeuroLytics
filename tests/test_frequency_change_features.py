from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.frequency_change_features import (
    FrequencyChangeFeatureResult,
    build_frequency_change_features,
    get_frequency_change_feature_names,
    get_frequency_change_feature_value,
)
from features.historical_data_loader import HistoricalFeatureObservation


def _observation(
    result_id: int,
    result_date: date,
    values: dict[str, int],
) -> HistoricalFeatureObservation:
    positions = (
        values.get("col1", 0),
        values.get("col2", 0),
        values.get("col3", 0),
        values.get("col4", 0),
        values.get("col5", 0),
        values.get("col6", 0),
        values.get("col7", 0),
        values.get("col8", 0),
    )

    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=positions,
    )


def _config(
    comparison_windows: tuple[tuple[int, int], ...] = ((1, 2),),
    positions: tuple[str, ...] = (
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    ),
) -> FeatureConfig:
    return FeatureConfig(
        positions=positions,
        frequency_comparison_windows=comparison_windows,
    )


def _feature_name(
    position: str,
    comparison_index: int,
    older_window: int,
    recent_window: int,
    digit: int,
) -> str:
    return (
        f"{position}_frequency_change_"
        f"{comparison_index}_"
        f"{older_window}_"
        f"{recent_window}_"
        f"{digit}"
    )


def test_build_frequency_change_features_returns_expected_result_type():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(),
    )

    assert isinstance(result, FrequencyChangeFeatureResult)


def test_target_date_is_never_used():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 9},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(positions=("col1",)),
    )

    value = get_frequency_change_feature_value(
        result,
        _feature_name("col1", 1, 1, 2, 1),
    )

    assert value == 0.0


def test_future_observation_is_never_used():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
        _observation(
            2,
            date(2026, 1, 3),
            {"col1": 9},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(positions=("col1",)),
    )

    value = get_frequency_change_feature_value(
        result,
        _feature_name("col1", 1, 1, 2, 1),
    )

    assert value == 0.0


def test_frequency_change_is_recent_minus_older():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 2},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 1},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(positions=("col1",)),
    )

    value = get_frequency_change_feature_value(
        result,
        _feature_name("col1", 1, 1, 2, 2),
    )

    assert value == -50.0


def test_negative_frequency_change_is_supported():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 2},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(positions=("col1",)),
    )

    value = get_frequency_change_feature_value(
        result,
        _feature_name("col1", 1, 1, 2, 2),
    )

    assert value == 50.0


def test_same_windows_produce_zero_change():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 2},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(
            comparison_windows=((2, 2),),
            positions=("col1",),
        ),
    )

    value = get_frequency_change_feature_value(
        result,
        _feature_name("col1", 1, 2, 2, 2),
    )

    assert value == 0.0


def test_zero_is_counted_as_valid_digit():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 0},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 1},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(positions=("col1",)),
    )

    value = get_frequency_change_feature_value(
        result,
        _feature_name("col1", 1, 1, 2, 0),
    )

    assert value == -50.0


def test_older_window_is_limited_to_requested_observations():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 7},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 1},
        ),
        _observation(
            3,
            date(2026, 1, 3),
            {"col1": 2},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 4),
        history=history,
        config=_config(
            comparison_windows=((2, 1),),
            positions=("col1",),
        ),
    )

    value = get_frequency_change_feature_value(
        result,
        _feature_name("col1", 1, 2, 1, 2),
    )

    assert value == -50.0


def test_multiple_positions_are_supported():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {
                "col1": 1,
                "col2": 2,
            },
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {
                "col1": 2,
                "col2": 2,
            },
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(
            positions=("col1", "col2"),
        ),
    )

    assert get_frequency_change_feature_value(
        result,
        _feature_name("col1", 1, 1, 2, 2),
    ) == 50.0

    assert get_frequency_change_feature_value(
        result,
        _feature_name("col2", 1, 1, 2, 2),
    ) == 0.0


def test_all_digits_are_generated():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 3},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 4},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(positions=("col1",)),
    )

    names = get_frequency_change_feature_names(result)

    for digit in range(10):
        assert _feature_name(
            "col1",
            1,
            1,
            2,
            digit,
        ) in names


def test_all_positions_are_generated():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {
                "col1": 1,
                "col2": 2,
                "col3": 3,
                "col4": 4,
                "col5": 5,
                "col6": 6,
                "col7": 7,
                "col8": 8,
            },
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(),
    )

    names = get_frequency_change_feature_names(result)

    for position in range(1, 9):
        assert _feature_name(
            f"col{position}",
            1,
            1,
            2,
            0,
        ) in names


def test_multiple_comparison_windows_are_supported():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 2},
        ),
        _observation(
            3,
            date(2026, 1, 3),
            {"col1": 3},
        ),
        _observation(
            4,
            date(2026, 1, 4),
            {"col1": 4},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 5),
        history=history,
        config=_config(
            comparison_windows=((1, 2), (2, 2)),
            positions=("col1",),
        ),
    )

    names = get_frequency_change_feature_names(result)

    assert _feature_name(
        "col1",
        1,
        1,
        2,
        0,
    ) in names

    assert _feature_name(
        "col1",
        2,
        2,
        2,
        0,
    ) in names


def test_empty_history_returns_zero_filled_feature_set():
    result = build_frequency_change_features(
        target_date=date(2026, 1, 1),
        history=[],
        config=_config(),
    )

    assert result.target_date == date(2026, 1, 1)
    assert len(result.records) == 80

    for record in result.records:
        assert record.value == 0.0


def test_no_history_before_target_returns_zero_filled_feature_set():
    history = [
        _observation(
            1,
            date(2026, 1, 2),
            {"col1": 1},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 1),
        history=history,
        config=_config(),
    )

    assert len(result.records) == 80

    for record in result.records:
        assert record.value == 0.0


def test_target_date_must_be_date():
    with pytest.raises(TypeError):
        build_frequency_change_features(
            target_date="2026-01-01",
            history=[],
            config=_config(),
        )


def test_history_must_be_sequence():
    with pytest.raises(TypeError):
        build_frequency_change_features(
            target_date=date(2026, 1, 1),
            history=None,
            config=_config(),
        )


def test_config_must_be_feature_config():
    with pytest.raises(TypeError):
        build_frequency_change_features(
            target_date=date(2026, 1, 1),
            history=[],
            config=None,
        )


def test_feature_names_are_deterministic():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 2},
        ),
    ]

    result1 = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(positions=("col1",)),
    )

    result2 = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(positions=("col1",)),
    )

    assert get_frequency_change_feature_names(result1) == (
        get_frequency_change_feature_names(result2)
    )


def test_feature_values_are_numeric():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 2},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(positions=("col1",)),
    )

    for record in result.records:
        assert isinstance(record.value, float)


def test_feature_record_contains_expected_metadata():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 2},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.feature_type == "frequency_change"
    assert record.source == "analytics.frequency_analysis"


def test_get_missing_feature_raises_value_error():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(positions=("col1",)),
    )

    with pytest.raises(ValueError):
        get_frequency_change_feature_value(
            result,
            "does_not_exist",
        )


def test_result_records_are_immutable():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
            {"col1": 1},
        ),
        _observation(
            2,
            date(2026, 1, 2),
            {"col1": 2},
        ),
    ]

    result = build_frequency_change_features(
        target_date=date(2026, 1, 3),
        history=history,
        config=_config(positions=("col1",)),
    )

    with pytest.raises(AttributeError):
        result.records = ()