from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation
from features.rolling_frequency_features import (
    RollingFrequencyFeatureResult,
    build_rolling_frequency_features,
    get_rolling_frequency_feature_names,
    get_rolling_frequency_feature_value,
    get_rolling_frequency_feature_values,
)


def _observation(
    result_id: int,
    result_date: date,
    positions: tuple[int, ...],
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=positions,
    )


def test_build_returns_result():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_rolling_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    assert isinstance(result, RollingFrequencyFeatureResult)


def test_target_date_is_preserved():
    target_date = date(2026, 1, 5)

    result = build_rolling_frequency_features(
        (),
        target_date,
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    assert result.target_date == target_date


def test_one_position_one_window_has_ten_features():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    assert len(result.records) == 10


def test_two_positions_one_window_has_twenty_features():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1", "col2"),
            frequency_windows=(3,),
        ),
    )

    assert len(result.records) == 20


def test_two_windows_one_position_has_twenty_features():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3, 5),
        ),
    )

    assert len(result.records) == 20


def test_all_digits_are_represented():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (4, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    digits = {record.digit for record in result.records}

    assert digits == set(range(10))


def test_zero_is_counted_as_valid_digit():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (0, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                2,
                date(2026, 1, 2),
                (0, 3, 4, 5, 6, 7, 8, 9),
            ),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    value = get_rolling_frequency_feature_value(
        result,
        "col1_rolling_frequency_5_0",
    )

    assert value == 100.0


def test_frequency_percentage_is_correct():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                2,
                date(2026, 1, 2),
                (1, 3, 4, 5, 6, 7, 8, 9),
            ),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    value = get_rolling_frequency_feature_value(
        result,
        "col1_rolling_frequency_5_1",
    )

    assert value == 100.0


def test_window_uses_only_most_recent_observations():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                2,
                date(2026, 1, 2),
                (2, 3, 4, 5, 6, 7, 8, 9),
            ),
            _observation(
                3,
                date(2026, 1, 3),
                (3, 4, 5, 6, 7, 8, 9, 0),
            ),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(2,),
        ),
    )

    digit_one = get_rolling_frequency_feature_value(
        result,
        "col1_rolling_frequency_2_1",
    )

    digit_three = get_rolling_frequency_feature_value(
        result,
        "col1_rolling_frequency_2_3",
    )

    assert digit_one == 0.0
    assert digit_three == 50.0


def test_target_date_is_never_used():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                2,
                date(2026, 1, 2),
                (9, 9, 9, 9, 9, 9, 9, 9),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    digit_one = get_rolling_frequency_feature_value(
        result,
        "col1_rolling_frequency_5_1",
    )

    digit_nine = get_rolling_frequency_feature_value(
        result,
        "col1_rolling_frequency_5_9",
    )

    assert digit_one == 100.0
    assert digit_nine == 0.0


def test_future_observation_is_never_used():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                2,
                date(2026, 1, 3),
                (9, 9, 9, 9, 9, 9, 9, 9),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    digit_one = get_rolling_frequency_feature_value(
        result,
        "col1_rolling_frequency_5_1",
    )

    digit_nine = get_rolling_frequency_feature_value(
        result,
        "col1_rolling_frequency_5_9",
    )

    assert digit_one == 100.0
    assert digit_nine == 0.0


def test_insufficient_history_uses_available_observations():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (4, 5, 6, 7, 8, 9, 0, 1),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    value = get_rolling_frequency_feature_value(
        result,
        "col1_rolling_frequency_5_4",
    )

    assert value == 100.0


def test_no_history_still_represents_all_digits():
    result = build_rolling_frequency_features(
        (),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    assert len(result.records) == 10

    assert {
        record.digit
        for record in result.records
    } == set(range(10))


def test_no_history_values_are_zero():
    result = build_rolling_frequency_features(
        (),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    assert all(
        record.value == 0.0
        for record in result.records
    )


def test_configured_positions_are_respected():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1", "col3"),
            frequency_windows=(3,),
        ),
    )

    positions = {
        record.position
        for record in result.records
    }

    assert positions == {"col1", "col3"}


def test_feature_names_are_unique():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1", "col2"),
            frequency_windows=(3, 5),
        ),
    )

    names = get_rolling_frequency_feature_names(result)

    assert len(names) == len(set(names))


def test_feature_values_returns_mapping():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    values = get_rolling_frequency_feature_values(result)

    assert isinstance(values, dict)
    assert len(values) == 10


def test_missing_feature_raises_value_error():
    result = build_rolling_frequency_features(
        (),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    with pytest.raises(ValueError, match="not found"):
        get_rolling_frequency_feature_value(
            result,
            "missing_feature",
        )


def test_records_contain_expected_metadata():
    result = build_rolling_frequency_features(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    record = result.records[0]

    assert record.position == "col1"
    assert record.window == 5
    assert record.digit in range(10)
    assert record.feature_type == "rolling_frequency_percentage"
    assert record.source == "analytics.frequency_analysis"


def test_feature_names_have_expected_prefix():
    result = build_rolling_frequency_features(
        (),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    names = get_rolling_frequency_feature_names(result)

    assert all(
        name.startswith("col1_rolling_frequency_5_")
        for name in names
    )


def test_invalid_target_date_type_raises():
    with pytest.raises(TypeError, match="target_date"):
        build_rolling_frequency_features(
            (),
            "2026-01-02",
            FeatureConfig(
                positions=("col1",),
                frequency_windows=(5,),
            ),
        )


def test_invalid_config_type_raises():
    with pytest.raises(TypeError, match="config"):
        build_rolling_frequency_features(
            (),
            date(2026, 1, 2),
            None,
        )


def test_invalid_history_value_raises():
    with pytest.raises(
        TypeError,
        match="HistoricalFeatureObservation",
    ):
        build_rolling_frequency_features(
            ("invalid",),
            date(2026, 1, 2),
            FeatureConfig(
                positions=("col1",),
                frequency_windows=(5,),
            ),
        )