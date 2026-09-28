from datetime import date

import pytest

from features.change_trend_features import (
    ChangeTrendFeatureResult,
    build_change_trend_features,
    get_change_trend_feature_names,
    get_change_trend_feature_value,
    get_change_trend_feature_values,
)
from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation


def _observation(
    result_id: int,
    result_date: date,
    value: int,
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=(value,) * 8,
    )


def _history(
    *observations: HistoricalFeatureObservation,
) -> tuple[HistoricalFeatureObservation, ...]:
    return tuple(observations)


def test_result_type():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
        ),
        date(2026, 1, 2),
        FeatureConfig(),
    )

    assert isinstance(
        result,
        ChangeTrendFeatureResult,
    )


def test_latest_change():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 7),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_change",
        )
        == 5
    )


def test_absolute_change():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 7),
            _observation(2, date(2026, 1, 2), 2),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_absolute_change",
        )
        == 5
    )


def test_increase_direction():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 7),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_change_direction",
        )
        == "INCREASE"
    )


def test_decrease_direction():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 7),
            _observation(2, date(2026, 1, 2), 2),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_change_direction",
        )
        == "DECREASE"
    )


def test_unchanged_direction():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
            _observation(2, date(2026, 1, 2), 5),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_change_direction",
        )
        == "UNCHANGED"
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_changed",
        )
        == 0
    )


def test_changed_indicator_for_change():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 1),
            _observation(2, date(2026, 1, 2), 9),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_changed",
        )
        == 1
    )


def test_change_requires_two_observations():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_change",
        )
        is None
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_absolute_change",
        )
        is None
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_change_direction",
        )
        is None
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_changed",
        )
        is None
    )


def test_trend_mean():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 4),
            _observation(3, date(2026, 1, 3), 7),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_mean_3",
        )
        == pytest.approx(13 / 3)
    )


def test_trend_minimum():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 4),
            _observation(3, date(2026, 1, 3), 7),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_min_3",
        )
        == 2
    )


def test_trend_maximum():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 4),
            _observation(3, date(2026, 1, 3), 7),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_max_3",
        )
        == 7
    )


def test_trend_range():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 4),
            _observation(3, date(2026, 1, 3), 7),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_range_3",
        )
        == 5
    )


def test_trend_standard_deviation():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 4),
            _observation(3, date(2026, 1, 3), 7),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    expected = (
        (
            (2 - 13 / 3) ** 2
            + (4 - 13 / 3) ** 2
            + (7 - 13 / 3) ** 2
        )
        / 3
    ) ** 0.5

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_std_3",
        )
        == pytest.approx(expected)
    )


def test_trend_first_to_last_change():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 4),
            _observation(3, date(2026, 1, 3), 7),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_change_3",
        )
        == 5
    )


def test_linear_slope():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 4),
            _observation(3, date(2026, 1, 3), 6),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_slope_3",
        )
        == pytest.approx(2.0)
    )


def test_flat_series_has_zero_slope():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
            _observation(2, date(2026, 1, 2), 5),
            _observation(3, date(2026, 1, 3), 5),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_slope_3",
        )
        == pytest.approx(0.0)
    )


def test_trend_window_limits_observations():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 1),
            _observation(2, date(2026, 1, 2), 2),
            _observation(3, date(2026, 1, 3), 9),
        ),
        date(2026, 1, 4),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(2,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_mean_2",
        )
        == pytest.approx(5.5)
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_change_2",
        )
        == 7
    )


def test_target_date_is_excluded():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 9),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_change",
        )
        is None
    )


def test_future_observation_is_excluded():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 3), 9),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_change",
        )
        is None
    )


def test_zero_is_valid():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 0),
            _observation(2, date(2026, 1, 2), 5),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_change",
        )
        == 5
    )


def test_missing_calendar_dates_do_not_change_observation_count():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 10), 7),
        ),
        date(2026, 1, 11),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(2,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_change_2",
        )
        == 5
    )


def test_single_observation_has_no_trend_change_or_slope():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_change_3",
        )
        is None
    )

    assert (
        get_change_trend_feature_value(
            result,
            "col1_trend_slope_3",
        )
        is None
    )


def test_all_configured_positions_generate_features():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 5),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=(
                "col1",
                "col2",
                "col3",
            ),
            trend_windows=(3,),
        ),
    )

    names = get_change_trend_feature_names(result)

    assert any(
        name.startswith("col1_")
        for name in names
    )

    assert any(
        name.startswith("col2_")
        for name in names
    )

    assert any(
        name.startswith("col3_")
        for name in names
    )


def test_change_features_can_be_disabled():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 5),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
            change_features_enabled=False,
            trend_features_enabled=True,
        ),
    )

    names = get_change_trend_feature_names(result)

    assert not any(
        name == "col1_change"
        for name in names
    )

    assert "col1_trend_mean_3" in names


def test_trend_features_can_be_disabled():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 5),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
            change_features_enabled=True,
            trend_features_enabled=False,
        ),
    )

    names = get_change_trend_feature_names(result)

    assert "col1_change" in names

    assert not any(
        name.startswith("col1_trend_")
        for name in names
    )


def test_feature_values_mapping():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 2),
            _observation(2, date(2026, 1, 2), 7),
        ),
        date(2026, 1, 3),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    values = get_change_trend_feature_values(result)

    assert values["col1_change"] == 5
    assert values["col1_trend_max_3"] == 7


def test_deterministic_feature_names():
    history = _history(
        _observation(1, date(2026, 1, 1), 2),
        _observation(2, date(2026, 1, 2), 7),
    )

    config = FeatureConfig(
        positions=("col1",),
        trend_windows=(3,),
    )

    result1 = build_change_trend_features(
        history,
        date(2026, 1, 3),
        config,
    )

    result2 = build_change_trend_features(
        history,
        date(2026, 1, 3),
        config,
    )

    assert (
        get_change_trend_feature_names(result1)
        == get_change_trend_feature_names(result2)
    )


def test_invalid_history_type():
    with pytest.raises(TypeError):
        build_change_trend_features(
            [],
            date(2026, 1, 2),
            FeatureConfig(),
        )


def test_invalid_history_observation_type():
    with pytest.raises(TypeError):
        build_change_trend_features(
            (object(),),
            date(2026, 1, 2),
            FeatureConfig(),
        )


def test_invalid_target_date():
    with pytest.raises(TypeError):
        build_change_trend_features(
            _history(
                _observation(1, date(2026, 1, 1), 5),
            ),
            "2026-01-02",
            FeatureConfig(),
        )


def test_invalid_config():
    with pytest.raises(TypeError):
        build_change_trend_features(
            _history(
                _observation(1, date(2026, 1, 1), 5),
            ),
            date(2026, 1, 2),
            object(),
        )


def test_missing_feature_raises():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    with pytest.raises(ValueError):
        get_change_trend_feature_value(
            result,
            "does_not_exist",
        )


def test_result_is_immutable():
    result = build_change_trend_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            trend_windows=(3,),
        ),
    )

    with pytest.raises(Exception):
        result.records = ()