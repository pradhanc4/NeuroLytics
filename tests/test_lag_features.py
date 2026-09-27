from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.lag_features import (
    LagFeatureRecord,
    LagFeatureResult,
    build_lag_features,
    get_lag_feature_names,
    get_lag_feature_value,
    get_lag_feature_values,
)
from features.point_in_time import (
    build_point_in_time_history,
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


def test_lag_features_use_previous_observations_only():
    observations = (
        _observation(
            1,
            date(2026, 9, 20),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 9, 21),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
        _observation(
            3,
            date(2026, 9, 22),
            (3, 4, 5, 6, 7, 8, 9, 0),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 23),
    )

    config = FeatureConfig(
        positions=("col1",),
        lag_windows=(1, 2, 3),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    assert get_lag_feature_value(
        result,
        "col1_lag_1",
    ) == 3

    assert get_lag_feature_value(
        result,
        "col1_lag_2",
    ) == 2

    assert get_lag_feature_value(
        result,
        "col1_lag_3",
    ) == 1


def test_target_date_is_never_used_as_lag():
    observations = (
        _observation(
            1,
            date(2026, 9, 20),
            (1, 1, 1, 1, 1, 1, 1, 1),
        ),
        _observation(
            2,
            date(2026, 9, 21),
            (2, 2, 2, 2, 2, 2, 2, 2),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 21),
    )

    config = FeatureConfig(
        positions=("col1",),
        lag_windows=(1, 2),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    assert get_lag_feature_value(
        result,
        "col1_lag_1",
    ) == 1

    assert get_lag_feature_value(
        result,
        "col1_lag_2",
    ) is None


def test_insufficient_history_returns_none():
    observations = (
        _observation(
            1,
            date(2026, 9, 20),
            (5, 5, 5, 5, 5, 5, 5, 5),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 21),
    )

    config = FeatureConfig(
        positions=("col1",),
        lag_windows=(1, 2, 3),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    assert get_lag_feature_value(
        result,
        "col1_lag_1",
    ) == 5

    assert get_lag_feature_value(
        result,
        "col1_lag_2",
    ) is None

    assert get_lag_feature_value(
        result,
        "col1_lag_3",
    ) is None


def test_zero_is_preserved():
    observations = (
        _observation(
            1,
            date(2026, 9, 20),
            (0, 0, 0, 0, 0, 0, 0, 0),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 21),
    )

    config = FeatureConfig(
        positions=("col1",),
        lag_windows=(1,),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    assert get_lag_feature_value(
        result,
        "col1_lag_1",
    ) == 0


def test_all_configured_positions_are_generated():
    observations = (
        _observation(
            1,
            date(2026, 9, 20),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 21),
    )

    config = FeatureConfig(
        positions=(
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "col8",
        ),
        lag_windows=(1,),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    assert get_lag_feature_names(result) == (
        "col1_lag_1",
        "col2_lag_1",
        "col3_lag_1",
        "col4_lag_1",
        "col5_lag_1",
        "col6_lag_1",
        "col7_lag_1",
        "col8_lag_1",
    )

    assert get_lag_feature_values(result) == {
        "col1_lag_1": 1,
        "col2_lag_1": 2,
        "col3_lag_1": 3,
        "col4_lag_1": 4,
        "col5_lag_1": 5,
        "col6_lag_1": 6,
        "col7_lag_1": 7,
        "col8_lag_1": 8,
    }


def test_missing_calendar_dates_do_not_create_fake_values():
    observations = (
        _observation(
            1,
            date(2026, 9, 20),
            (1, 1, 1, 1, 1, 1, 1, 1),
        ),
        _observation(
            2,
            date(2026, 9, 22),
            (2, 2, 2, 2, 2, 2, 2, 2),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 25),
    )

    config = FeatureConfig(
        positions=("col1",),
        lag_windows=(1, 2),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    assert get_lag_feature_value(
        result,
        "col1_lag_1",
    ) == 2

    assert get_lag_feature_value(
        result,
        "col1_lag_2",
    ) == 1


def test_empty_history_returns_none_for_lags():
    history = build_point_in_time_history(
        observations=(),
        target_date=date(2026, 9, 21),
    )

    config = FeatureConfig(
        positions=("col1",),
        lag_windows=(1, 2),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    assert get_lag_feature_value(
        result,
        "col1_lag_1",
    ) is None

    assert get_lag_feature_value(
        result,
        "col1_lag_2",
    ) is None


def test_feature_names_are_deterministic():
    history = build_point_in_time_history(
        observations=(
            _observation(
                1,
                date(2026, 9, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        target_date=date(2026, 9, 21),
    )

    config = FeatureConfig(
        positions=("col1", "col2"),
        lag_windows=(1, 2),
    )

    first = build_lag_features(
        history=history,
        config=config,
    )

    second = build_lag_features(
        history=history,
        config=config,
    )

    assert first == second


def test_result_contains_expected_record_objects():
    history = build_point_in_time_history(
        observations=(
            _observation(
                1,
                date(2026, 9, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        target_date=date(2026, 9, 21),
    )

    config = FeatureConfig(
        positions=("col1",),
        lag_windows=(1,),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    assert isinstance(result, LagFeatureResult)
    assert len(result.records) == 1
    assert isinstance(
        result.records[0],
        LagFeatureRecord,
    )


def test_history_type_is_required():
    config = FeatureConfig()

    with pytest.raises(
        TypeError,
        match="PointInTimeHistory",
    ):
        build_lag_features(
            history=object(),
            config=config,
        )


def test_config_type_is_validated():
    history = build_point_in_time_history(
        observations=(),
        target_date=date(2026, 9, 21),
    )

    with pytest.raises(
        TypeError,
        match="FeatureConfig",
    ):
        build_lag_features(
            history=history,
            config=object(),
        )


def test_unknown_feature_name_is_rejected():
    history = build_point_in_time_history(
        observations=(),
        target_date=date(2026, 9, 21),
    )

    config = FeatureConfig(
        positions=("col1",),
        lag_windows=(1,),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    with pytest.raises(
        ValueError,
        match="Lag feature not found",
    ):
        get_lag_feature_value(
            result,
            "unknown_feature",
        )


def test_invalid_feature_name_type_is_rejected():
    history = build_point_in_time_history(
        observations=(),
        target_date=date(2026, 9, 21),
    )

    config = FeatureConfig(
        positions=("col1",),
        lag_windows=(1,),
    )

    result = build_lag_features(
        history=history,
        config=config,
    )

    with pytest.raises(
        TypeError,
        match="string",
    ):
        get_lag_feature_value(
            result,
            123,
        )


def test_getter_requires_lag_result():
    with pytest.raises(
        TypeError,
        match="LagFeatureResult",
    ):
        get_lag_feature_names(object())

    with pytest.raises(
        TypeError,
        match="LagFeatureResult",
    ):
        get_lag_feature_values(object())