from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation
from features.point_in_time import build_point_in_time_history
from features.position_features import (
    PositionFeatureResult,
    build_position_features,
    get_position_feature_names,
    get_position_feature_value,
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


def test_latest_value_uses_most_recent_historical_observation():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (4, 5, 6, 7, 8, 9, 0, 1),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 3),
    )

    config = FeatureConfig(
        positions=("col1",),
    )

    result = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_value(
            result,
            "col1_latest_value",
        )
        == 4
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
        positions=("col1",),
    )

    result = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_value(
            result,
            "col1_latest_value",
        )
        == 1
    )


def test_future_observation_is_never_used():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (2, 3, 4, 5, 6, 7, 8, 9),
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
        positions=("col1",),
    )

    result = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_value(
            result,
            "col1_latest_value",
        )
        == 2
    )


def test_even_and_odd_are_classified_correctly():
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
        positions=("col1", "col2"),
    )

    result = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_value(
            result,
            "col1_latest_is_even",
        )
        == 1
    )

    assert (
        get_position_feature_value(
            result,
            "col2_latest_is_even",
        )
        == 0
    )


def test_zero_is_preserved_as_valid_value():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (0, 1, 2, 3, 4, 5, 6, 7),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 2),
    )

    config = FeatureConfig(
        positions=("col1",),
    )

    result = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_value(
            result,
            "col1_latest_value",
        )
        == 0
    )

    assert (
        get_position_feature_value(
            result,
            "col1_latest_is_zero",
        )
        == 1
    )


def test_high_and_low_are_classified_correctly():
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
        positions=("col1", "col2"),
    )

    result = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_value(
            result,
            "col1_latest_is_high",
        )
        == 0
    )

    assert (
        get_position_feature_value(
            result,
            "col2_latest_is_high",
        )
        == 1
    )


def test_historical_mean_is_calculated():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (4, 5, 6, 7, 8, 9, 0, 1),
        ),
        _observation(
            3,
            date(2026, 1, 3),
            (6, 7, 8, 9, 0, 1, 2, 3),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    config = FeatureConfig(
        positions=("col1",),
    )

    result = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_value(
            result,
            "col1_historical_mean",
        )
        == 4.0
    )


def test_historical_minimum_and_maximum_are_calculated():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (8, 7, 6, 5, 4, 3, 2, 1),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 3),
    )

    config = FeatureConfig(
        positions=("col1",),
    )

    result = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_value(
            result,
            "col1_historical_min",
        )
        == 2
    )

    assert (
        get_position_feature_value(
            result,
            "col1_historical_max",
        )
        == 8
    )


def test_empty_history_returns_unavailable_features():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        positions=("col1",),
    )

    result = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_value(
            result,
            "col1_latest_value",
        )
        is None
    )

    assert (
        get_position_feature_value(
            result,
            "col1_latest_is_even",
        )
        is None
    )

    assert (
        get_position_feature_value(
            result,
            "col1_historical_mean",
        )
        is None
    )


def test_all_position_features_are_generated():
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

    config = FeatureConfig()

    result = build_position_features(
        history,
        config,
    )

    names = get_position_feature_names(result)

    assert len(names) == 56

    expected_features = (
        "latest_value",
        "latest_is_even",
        "latest_is_zero",
        "latest_is_high",
        "historical_mean",
        "historical_min",
        "historical_max",
    )

    for position in config.positions:
        for feature in expected_features:
            assert (
                f"{position}_{feature}"
                in names
            )


def test_configured_positions_are_respected():
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
        positions=("col1", "col3"),
    )

    result = build_position_features(
        history,
        config,
    )

    names = get_position_feature_names(result)

    assert len(names) == 14

    assert "col1_latest_value" in names
    assert "col3_latest_value" in names
    assert "col2_latest_value" not in names


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
    )

    first = build_position_features(
        history,
        config,
    )

    second = build_position_features(
        history,
        config,
    )

    assert (
        get_position_feature_names(first)
        == get_position_feature_names(second)
    )


def test_result_type_is_correct():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        positions=("col1",),
    )

    result = build_position_features(
        history,
        config,
    )

    assert isinstance(
        result,
        PositionFeatureResult,
    )


def test_history_type_is_required():
    config = FeatureConfig()

    with pytest.raises(TypeError):
        build_position_features(
            "invalid",
            config,
        )


def test_config_type_is_required():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    with pytest.raises(TypeError):
        build_position_features(
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
    )

    result = build_position_features(
        history,
        config,
    )

    with pytest.raises(ValueError):
        get_position_feature_value(
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
    )

    result = build_position_features(
        history,
        config,
    )

    with pytest.raises(TypeError):
        get_position_feature_value(
            result,
            123,
        )


def test_names_getter_requires_correct_result_type():
    with pytest.raises(TypeError):
        get_position_feature_names(
            "invalid",
        )