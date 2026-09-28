from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_frequency_features import (
    HistoricalFrequencyFeatureResult,
    build_historical_frequency_features,
    get_historical_frequency_feature_names,
    get_historical_frequency_feature_value,
    get_historical_frequency_feature_values,
)
from features.point_in_time import (
    HistoricalFeatureObservation,
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

    config = FeatureConfig(
        positions=("col1",),
        frequency_windows=(3,),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        config,
    )

    assert isinstance(
        result,
        HistoricalFrequencyFeatureResult,
    )


def test_target_date_is_preserved():
    target_date = date(2026, 1, 5)

    result = build_historical_frequency_features(
        (),
        target_date,
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    assert result.target_date == target_date


def test_one_position_one_window_has_20_features():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    assert len(result.records) == 20


def test_two_positions_one_window_has_40_features():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1", "col2"),
            frequency_windows=(3,),
        ),
    )

    assert len(result.records) == 40


def test_two_windows_one_position_has_40_features():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3, 5),
        ),
    )

    assert len(result.records) == 40


def test_all_digits_are_represented():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    names = get_historical_frequency_feature_names(result)

    for digit in range(10):
        assert (
            f"col1_frequency_count_3_{digit}"
            in names
        )
        assert (
            f"col1_frequency_percentage_3_{digit}"
            in names
        )


def test_zero_is_counted():
    history = (
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
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    values = get_historical_frequency_feature_values(
        result
    )

    assert values[
        "col1_frequency_count_5_0"
    ] == 2

    assert values[
        "col1_frequency_percentage_5_0"
    ] == pytest.approx(100.0)


def test_frequency_count_is_correct():
    history = (
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
        _observation(
            3,
            date(2026, 1, 3),
            (2, 1, 4, 5, 6, 7, 8, 9),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    values = get_historical_frequency_feature_values(
        result
    )

    assert values[
        "col1_frequency_count_3_1"
    ] == 2

    assert values[
        "col1_frequency_count_3_2"
    ] == 1


def test_frequency_percentage_is_correct():
    history = (
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
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    values = get_historical_frequency_feature_values(
        result
    )

    assert values[
        "col1_frequency_percentage_5_1"
    ] == pytest.approx(100.0)


def test_window_limits_observations():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (7, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            3,
            date(2026, 1, 3),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(2,),
        ),
    )

    values = get_historical_frequency_feature_values(
        result
    )

    assert values[
        "col1_frequency_count_2_7"
    ] == 0


def test_target_date_is_never_used():
    history = (
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
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    values = get_historical_frequency_feature_values(
        result
    )

    assert values[
        "col1_frequency_count_5_1"
    ] == 1

    assert values[
        "col1_frequency_count_5_9"
    ] == 0


def test_future_observation_is_never_used():
    history = (
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
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    values = get_historical_frequency_feature_values(
        result
    )

    assert values[
        "col1_frequency_count_5_9"
    ] == 0


def test_insufficient_history_uses_available_observations():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (4, 5, 6, 7, 8, 9, 0, 1),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    values = get_historical_frequency_feature_values(
        result
    )

    assert values[
        "col1_frequency_count_5_4"
    ] == 1

    assert values[
        "col1_frequency_percentage_5_4"
    ] == pytest.approx(100.0)


def test_no_history_still_represents_all_digits():
    result = build_historical_frequency_features(
        (),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(5,),
        ),
    )

    values = get_historical_frequency_feature_values(
        result
    )

    for digit in range(10):
        assert values[
            f"col1_frequency_count_5_{digit}"
        ] == 0

        assert values[
            f"col1_frequency_percentage_5_{digit}"
        ] == 0.0


def test_configured_positions_are_respected():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1", "col3"),
            frequency_windows=(3,),
        ),
    )

    names = get_historical_frequency_feature_names(
        result
    )

    assert any(
        name.startswith("col1_frequency_")
        for name in names
    )

    assert any(
        name.startswith("col3_frequency_")
        for name in names
    )

    assert not any(
        name.startswith("col2_frequency_")
        for name in names
    )


def test_feature_names_are_unique():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1", "col2"),
            frequency_windows=(3, 5),
        ),
    )

    names = get_historical_frequency_feature_names(
        result
    )

    assert len(names) == len(set(names))


def test_feature_values_returns_mapping():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    values = get_historical_frequency_feature_values(
        result
    )

    assert isinstance(values, dict)
    assert len(values) == 20


def test_invalid_target_date_rejected():
    with pytest.raises(TypeError):
        build_historical_frequency_features(
            (),
            "2026-01-02",
            FeatureConfig(
                positions=("col1",),
                frequency_windows=(3,),
            ),
        )


def test_invalid_history_rejected():
    with pytest.raises(TypeError):
        build_historical_frequency_features(
            ["invalid"],
            date(2026, 1, 2),
            FeatureConfig(
                positions=("col1",),
                frequency_windows=(3,),
            ),
        )


def test_invalid_config_rejected():
    with pytest.raises(TypeError):
        build_historical_frequency_features(
            (),
            date(2026, 1, 2),
            "invalid",
        )


def test_invalid_result_type_rejected_by_value():
    with pytest.raises(TypeError):
        get_historical_frequency_feature_value(
            "invalid",
            "col1_frequency_count_3_1",
        )


def test_invalid_result_type_rejected_by_names():
    with pytest.raises(TypeError):
        get_historical_frequency_feature_names(
            "invalid"
        )


def test_invalid_result_type_rejected_by_values():
    with pytest.raises(TypeError):
        get_historical_frequency_feature_values(
            "invalid"
        )


def test_missing_feature_raises_value_error():
    result = build_historical_frequency_features(
        (),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Historical frequency feature not found",
    ):
        get_historical_frequency_feature_value(
            result,
            "col1_frequency_missing",
        )


def test_records_contain_expected_metadata():
    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_historical_frequency_features(
        history,
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            frequency_windows=(3,),
        ),
    )

    for record in result.records:
        assert record.feature_type == "historical_frequency"
        assert record.source == "analytics.frequency_analysis"
        assert record.position == "col1"
        assert record.digit in range(10)
        assert record.window == 3