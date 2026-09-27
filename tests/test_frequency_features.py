from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.frequency_features import (
    FrequencyFeatureResult,
    build_frequency_features,
    get_frequency_feature_count,
    get_frequency_feature_names,
    get_frequency_feature_percentage,
)
from features.historical_data_loader import HistoricalFeatureObservation
from features.point_in_time import build_point_in_time_history


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


def test_frequency_counts_digits_in_configured_window():
    observations = (
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

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    config = FeatureConfig(
        positions=("col1",),
        frequency_window=3,
    )

    result = build_frequency_features(
        history,
        config,
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_1_frequency_count",
        )
        == 2
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_2_frequency_count",
        )
        == 1
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
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_1_frequency_count",
        )
        == 1
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_9_frequency_count",
        )
        == 0
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
        positions=("col1",),
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_9_frequency_count",
        )
        == 0
    )


def test_zero_is_counted_as_a_valid_digit():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (0, 1, 2, 3, 4, 5, 6, 7),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (0, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 3),
    )

    config = FeatureConfig(
        positions=("col1",),
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_0_frequency_count",
        )
        == 2
    )


def test_all_digits_are_always_represented():
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
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    names = get_frequency_feature_names(result)

    assert len(names) == 20

    for digit in range(10):
        assert (
            f"col1_digit_{digit}_frequency_count"
            in names
        )
        assert (
            f"col1_digit_{digit}_frequency_percentage"
            in names
        )


def test_percentage_is_calculated_from_window_observations():
    observations = (
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

    history = _history(
        observations,
        date(2026, 1, 3),
    )

    config = FeatureConfig(
        positions=("col1",),
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    assert (
        get_frequency_feature_percentage(
            result,
            "col1_digit_1_frequency_percentage",
        )
        == 100.0
    )


def test_frequency_window_limits_historical_observations():
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
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    config = FeatureConfig(
        positions=("col1",),
        frequency_window=2,
    )

    result = build_frequency_features(
        history,
        config,
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_7_frequency_count",
        )
        == 0
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_1_frequency_count",
        )
        == 1
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_2_frequency_count",
        )
        == 1
    )


def test_insufficient_history_uses_available_observations():
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
        positions=("col1",),
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_4_frequency_count",
        )
        == 1
    )

    assert (
        get_frequency_feature_percentage(
            result,
            "col1_digit_4_frequency_percentage",
        )
        == 100.0
    )


def test_empty_history_returns_zero_counts():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        positions=("col1",),
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    for digit in range(10):
        assert (
            get_frequency_feature_count(
                result,
                f"col1_digit_{digit}_frequency_count",
            )
            == 0
        )

        assert (
            get_frequency_feature_percentage(
                result,
                f"col1_digit_{digit}_frequency_percentage",
            )
            == 0.0
        )


def test_missing_calendar_dates_do_not_create_observations():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 5),
            (2, 3, 4, 5, 6, 7, 8, 9),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 6),
    )

    config = FeatureConfig(
        positions=("col1",),
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_1_frequency_count",
        )
        == 1
    )

    assert (
        get_frequency_feature_count(
            result,
            "col1_digit_2_frequency_count",
        )
        == 1
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
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    names = get_frequency_feature_names(result)

    assert len(names) == 40

    assert (
        "col1_digit_1_frequency_count"
        in names
    )

    assert (
        "col3_digit_3_frequency_count"
        in names
    )

    assert (
        "col2_digit_2_frequency_count"
        not in names
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
        frequency_window=5,
    )

    first = build_frequency_features(
        history,
        config,
    )

    second = build_frequency_features(
        history,
        config,
    )

    assert (
        get_frequency_feature_names(first)
        == get_frequency_feature_names(second)
    )


def test_result_type_is_correct():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        positions=("col1",),
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    assert isinstance(
        result,
        FrequencyFeatureResult,
    )


def test_history_type_is_required():
    config = FeatureConfig()

    with pytest.raises(TypeError):
        build_frequency_features(
            "invalid",
            config,
        )


def test_config_type_is_required():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    with pytest.raises(TypeError):
        build_frequency_features(
            history,
            "invalid",
        )


def test_unknown_count_feature_name_is_rejected():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        positions=("col1",),
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    with pytest.raises(ValueError):
        get_frequency_feature_count(
            result,
            "unknown_feature",
        )


def test_unknown_percentage_feature_name_is_rejected():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    config = FeatureConfig(
        positions=("col1",),
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    with pytest.raises(ValueError):
        get_frequency_feature_percentage(
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
        frequency_window=5,
    )

    result = build_frequency_features(
        history,
        config,
    )

    with pytest.raises(TypeError):
        get_frequency_feature_count(
            result,
            123,
        )


def test_names_getter_requires_correct_result_type():
    with pytest.raises(TypeError):
        get_frequency_feature_names(
            "invalid",
        )