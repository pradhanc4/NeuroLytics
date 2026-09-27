from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation
from features.point_in_time import build_point_in_time_history
from features.recency_features import (
    RecencyFeatureResult,
    build_recency_features,
    get_recency_feature_names,
    get_recency_feature_seen,
    get_recency_feature_value,
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


def test_recency_returns_zero_for_latest_observation():
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
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert (
        get_recency_feature_value(
            result,
            "col1_digit_4_recency",
        )
        == 0
    )

    assert get_recency_feature_seen(
        result,
        "col1_digit_4_recency",
    )


def test_recency_counts_previous_observations():
    observations = (
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
            (2, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    config = FeatureConfig(
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert (
        get_recency_feature_value(
            result,
            "col1_digit_7_recency",
        )
        == 2
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
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert not get_recency_feature_seen(
        result,
        "col1_digit_9_recency",
    )

    assert (
        get_recency_feature_value(
            result,
            "col1_digit_9_recency",
        )
        is None
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
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert not get_recency_feature_seen(
        result,
        "col1_digit_9_recency",
    )


def test_zero_is_treated_as_a_valid_digit():
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
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert (
        get_recency_feature_value(
            result,
            "col1_digit_0_recency",
        )
        == 0
    )

    assert get_recency_feature_seen(
        result,
        "col1_digit_0_recency",
    )


def test_unseen_digit_returns_none_and_false():
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
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert (
        get_recency_feature_value(
            result,
            "col1_digit_9_recency",
        )
        is None
    )

    assert not get_recency_feature_seen(
        result,
        "col1_digit_9_recency",
    )


def test_lookback_limits_search():
    observations = (
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
            (2, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    config = FeatureConfig(
        recency_lookback=2,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert (
        get_recency_feature_value(
            result,
            "col1_digit_7_recency",
        )
        is None
    )

    assert not get_recency_feature_seen(
        result,
        "col1_digit_7_recency",
    )


def test_missing_calendar_dates_do_not_change_observation_distance():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (7, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 5),
            (1, 2, 3, 4, 5, 6, 7, 8),
    ),
    )

    history = _history(
        observations,
        date(2026, 1, 6),
    )

    config = FeatureConfig(
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert (
        get_recency_feature_value(
            result,
            "col1_digit_7_recency",
        )
        == 1
    )


def test_empty_history_returns_unavailable_recency():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert (
        get_recency_feature_value(
            result,
            "col1_digit_0_recency",
        )
        is None
    )

    assert not get_recency_feature_seen(
        result,
        "col1_digit_0_recency",
    )


def test_all_positions_and_digits_are_generated():
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
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    names = get_recency_feature_names(result)

    assert len(names) == 80

    for position in config.positions:
        for digit in range(10):
            assert (
                f"{position}_digit_{digit}_recency"
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
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    names = get_recency_feature_names(result)

    assert len(names) == 20

    assert "col1_digit_1_recency" in names
    assert "col3_digit_3_recency" in names
    assert "col2_digit_2_recency" not in names


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
        recency_lookback=5,
    )

    first = build_recency_features(
        history,
        config,
    )

    second = build_recency_features(
        history,
        config,
    )

    assert (
        get_recency_feature_names(first)
        == get_recency_feature_names(second)
    )


def test_result_type_is_correct():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        positions=("col1",),
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    assert isinstance(
        result,
        RecencyFeatureResult,
    )


def test_history_type_is_required():
    config = FeatureConfig()

    with pytest.raises(TypeError):
        build_recency_features(
            "invalid",
            config,
        )


def test_config_type_is_required():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    with pytest.raises(TypeError):
        build_recency_features(
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
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    with pytest.raises(ValueError):
        get_recency_feature_value(
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
        recency_lookback=5,
    )

    result = build_recency_features(
        history,
        config,
    )

    with pytest.raises(TypeError):
        get_recency_feature_value(
            result,
            123,
        )


def test_seen_getter_requires_correct_result_type():
    with pytest.raises(TypeError):
        get_recency_feature_seen(
            "invalid",
            "col1_digit_0_recency",
        )


def test_names_getter_requires_correct_result_type():
    with pytest.raises(TypeError):
        get_recency_feature_names(
            "invalid",
        )