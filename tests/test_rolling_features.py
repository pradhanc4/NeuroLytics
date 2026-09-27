from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation
from features.point_in_time import build_point_in_time_history
from features.rolling_features import (
    RollingFeatureResult,
    build_rolling_features,
    get_rolling_feature_names,
    get_rolling_feature_value,
)


def _observation(
    result_id: int,
    result_date: date,
    values: tuple[int, ...],
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=values,
    )


def _history(
    observations: tuple[HistoricalFeatureObservation, ...],
    target_date: date,
):
    return build_point_in_time_history(
        observations,
        target_date,
    )


def test_rolling_features_use_only_previous_observations():
    observations = (
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
    )

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    config = FeatureConfig(
        rolling_windows=(2,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_2_mean",
        )
        == 2.5
    )


def test_target_date_is_never_used():
    observations = (
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

    history = _history(
        observations,
        date(2026, 1, 2),
    )

    config = FeatureConfig(
        rolling_windows=(2,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_2_mean",
        )
        == 1.0
    )


def test_future_observation_is_never_used():
    observations = (
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

    history = _history(
        observations,
        date(2026, 1, 2),
    )

    config = FeatureConfig(
        rolling_windows=(2,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_2_mean",
        )
        == 1.0
    )


def test_insufficient_history_uses_available_history():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (4, 5, 6, 7, 8, 9, 0, 1),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 2),
    )

    config = FeatureConfig(
        rolling_windows=(5,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_5_mean",
        )
        == 4.0
    )


def test_empty_history_returns_empty_statistics():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        rolling_windows=(3,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_3_mean",
        )
        is None
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_3_min",
        )
        is None
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_3_max",
        )
        is None
    )


def test_zero_is_preserved_as_valid_value():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (0, 1, 2, 3, 4, 5, 6, 7),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 3),
    )

    config = FeatureConfig(
        rolling_windows=(2,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_2_mean",
        )
        == 1.0
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_2_min",
        )
        == 0
    )


def test_missing_calendar_dates_do_not_create_fake_values():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 5),
            (5, 6, 7, 8, 9, 0, 1, 2),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 6),
    )

    config = FeatureConfig(
        rolling_windows=(3,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_3_mean",
        )
        == 3.0
    )


def test_all_configured_positions_are_generated():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 2),
    )

    config = FeatureConfig(
        rolling_windows=(3,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    names = get_rolling_feature_names(result)

    for position in config.positions:
        assert f"{position}_rolling_3_mean" in names
        assert f"{position}_rolling_3_min" in names
        assert f"{position}_rolling_3_max" in names


def test_minimum_and_maximum_are_calculated():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (2, 8, 1, 4, 5, 6, 7, 9),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (7, 3, 9, 4, 1, 8, 2, 6),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 3),
    )

    config = FeatureConfig(
        rolling_windows=(2,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_2_min",
        )
        == 2
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_2_max",
        )
        == 7
    )


def test_multiple_windows_are_generated():
    observations = (
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
    )

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    config = FeatureConfig(
        rolling_windows=(2, 3),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_2_mean",
        )
        == 2.5
    )

    assert (
        get_rolling_feature_value(
            result,
            "col1_rolling_3_mean",
        )
        == 2.0
    )


def test_feature_names_are_deterministic():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 2),
    )

    config = FeatureConfig(
        positions=("col1",),
        rolling_windows=(3,),
    )

    first = build_rolling_features(
        history,
        config,
    )

    second = build_rolling_features(
        history,
        config,
    )

    assert (
        get_rolling_feature_names(first)
        == get_rolling_feature_names(second)
    )


def test_result_contains_rolling_feature_records():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 2),
    )

    config = FeatureConfig(
        positions=("col1",),
        rolling_windows=(3,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    assert isinstance(
        result,
        RollingFeatureResult,
    )

    assert len(result.records) == 3


def test_history_type_is_required():
    config = FeatureConfig()

    with pytest.raises(TypeError):
        build_rolling_features(
            "invalid",
            config,
        )


def test_config_type_is_required():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    with pytest.raises(TypeError):
        build_rolling_features(
            history,
            "invalid",
        )


def test_unknown_feature_name_is_rejected():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        positions=("col1",),
        rolling_windows=(3,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    with pytest.raises(ValueError):
        get_rolling_feature_value(
            result,
            "unknown_feature",
        )


def test_feature_name_type_is_validated():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        positions=("col1",),
        rolling_windows=(3,),
    )

    result = build_rolling_features(
        history,
        config,
    )

    with pytest.raises(TypeError):
        get_rolling_feature_value(
            result,
            123,
        )


def test_getter_requires_rolling_feature_result():
    with pytest.raises(TypeError):
        get_rolling_feature_names(
            "invalid",
        )