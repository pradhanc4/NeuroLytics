from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.observation_density_features import (
    ObservationDensityFeatureResult,
    build_observation_density_features,
    get_observation_density_feature_names,
    get_observation_density_feature_value,
    get_observation_density_feature_values,
)


def _observation(
    result_id: int,
    result_date: date,
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=(
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
        ),
    )


def _config(
    enabled: bool = True,
) -> FeatureConfig:
    return FeatureConfig(
        observation_density_features_enabled=enabled,
        observation_density_windows=(
            7,
            14,
            30,
        ),
    )


def test_build_returns_expected_result_type():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    assert isinstance(
        result,
        ObservationDensityFeatureResult,
    )


def test_target_date_is_preserved():
    target_date = date(2026, 1, 10)

    result = build_observation_density_features(
        target_date=target_date,
        history=[],
        config=_config(),
    )

    assert result.target_date == target_date


def test_expected_window_features_are_generated():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    names = get_observation_density_feature_names(
        result
    )

    assert (
        "observation_density_count_7"
        in names
    )

    assert (
        "observation_density_rate_7"
        in names
    )

    assert (
        "observation_density_count_14"
        in names
    )

    assert (
        "observation_density_rate_14"
        in names
    )

    assert (
        "observation_density_count_30"
        in names
    )

    assert (
        "observation_density_rate_30"
        in names
    )


def test_overall_features_are_generated():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    names = get_observation_density_feature_names(
        result
    )

    expected = (
        "observation_density_total_count",
        "observation_density_span_days",
        "observation_density_rate",
        "observation_density_average_interval",
        "observation_density_interval_std",
    )

    for name in expected:
        assert name in names


def test_window_count_uses_calendar_days():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 5)),
        _observation(3, date(2026, 1, 8)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_count_7",
    ) == 2.0

    assert get_observation_density_feature_value(
        result,
        "observation_density_count_14",
    ) == 3.0


def test_window_rate_is_count_divided_by_window_days():
    history = [
        _observation(1, date(2026, 1, 5)),
        _observation(2, date(2026, 1, 8)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_rate_7",
    ) == pytest.approx(2 / 7)


def test_target_date_is_excluded():
    history = [
        _observation(1, date(2026, 1, 5)),
        _observation(2, date(2026, 1, 10)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_count_7",
    ) == 1.0


def test_future_dates_are_excluded():
    history = [
        _observation(1, date(2026, 1, 5)),
        _observation(2, date(2026, 1, 20)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_count_14",
    ) == 1.0


def test_duplicate_dates_are_counted_once():
    history = [
        _observation(1, date(2026, 1, 5)),
        _observation(2, date(2026, 1, 5)),
        _observation(3, date(2026, 1, 8)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_count_7",
    ) == 2.0


def test_overall_count_uses_unique_historical_dates():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 1)),
        _observation(3, date(2026, 1, 5)),
        _observation(4, date(2026, 1, 8)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_total_count",
    ) == 3.0


def test_overall_span_is_correct():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 5)),
        _observation(3, date(2026, 1, 8)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_span_days",
    ) == 7.0


def test_overall_rate_is_count_divided_by_span():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 5)),
        _observation(3, date(2026, 1, 8)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_rate",
    ) == pytest.approx(3 / 7)


def test_average_interval_is_correct():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 3)),
        _observation(3, date(2026, 1, 8)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_average_interval",
    ) == pytest.approx(3.5)


def test_interval_std_is_correct():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 3)),
        _observation(3, date(2026, 1, 8)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_interval_std",
    ) == pytest.approx(1.5)


def test_single_observation_has_no_overall_rate():
    history = [
        _observation(
            1,
            date(2026, 1, 5),
        ),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_total_count",
    ) == 1.0

    assert get_observation_density_feature_value(
        result,
        "observation_density_span_days",
    ) == 0.0

    assert get_observation_density_feature_value(
        result,
        "observation_density_rate",
    ) is None

    assert get_observation_density_feature_value(
        result,
        "observation_density_average_interval",
    ) is None

    assert get_observation_density_feature_value(
        result,
        "observation_density_interval_std",
    ) is None


def test_empty_history_returns_none_for_overall_features():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    for name in (
        "observation_density_total_count",
        "observation_density_span_days",
        "observation_density_rate",
        "observation_density_average_interval",
        "observation_density_interval_std",
    ):
        assert get_observation_density_feature_value(
            result,
            name,
        ) is None


def test_empty_history_has_zero_window_counts():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_count_7",
    ) == 0.0

    assert get_observation_density_feature_value(
        result,
        "observation_density_count_14",
    ) == 0.0

    assert get_observation_density_feature_value(
        result,
        "observation_density_count_30",
    ) == 0.0


def test_empty_history_has_zero_window_rates():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_rate_7",
    ) == 0.0


def test_unsorted_history_is_handled_chronologically():
    history = [
        _observation(3, date(2026, 1, 8)),
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 3)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_value(
        result,
        "observation_density_average_interval",
    ) == pytest.approx(3.5)


def test_features_are_numeric_or_none():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 5)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    for record in result.records:
        assert (
            record.value is None
            or isinstance(record.value, float)
        )


def test_metadata_is_correct():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    for record in result.records:
        assert record.feature_type == "observation_density"
        assert record.source == "historical_observations"


def test_disabled_feature_family_returns_empty_result():
    history = [
        _observation(
            1,
            date(2026, 1, 5),
        ),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(enabled=False),
    )

    assert result.records == ()


def test_invalid_target_date_is_rejected():
    with pytest.raises(TypeError):
        build_observation_density_features(
            target_date="2026-01-10",
            history=[],
            config=_config(),
        )


def test_invalid_history_is_rejected():
    with pytest.raises(TypeError):
        build_observation_density_features(
            target_date=date(2026, 1, 10),
            history=None,
            config=_config(),
        )


def test_invalid_history_item_is_rejected():
    with pytest.raises(TypeError):
        build_observation_density_features(
            target_date=date(2026, 1, 10),
            history=[None],
            config=_config(),
        )


def test_invalid_config_is_rejected():
    with pytest.raises(TypeError):
        build_observation_density_features(
            target_date=date(2026, 1, 10),
            history=[],
            config=None,
        )


def test_missing_feature_raises_value_error():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    with pytest.raises(ValueError):
        get_observation_density_feature_value(
            result,
            "does_not_exist",
        )


def test_invalid_result_is_rejected_by_getter():
    with pytest.raises(TypeError):
        get_observation_density_feature_value(
            None,
            "observation_density_count_7",
        )


def test_invalid_feature_name_is_rejected():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    with pytest.raises(TypeError):
        get_observation_density_feature_value(
            result,
            None,
        )


def test_values_getter_returns_mapping():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    values = get_observation_density_feature_values(
        result
    )

    assert isinstance(values, dict)
    assert len(values) == 11


def test_names_are_deterministic():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 5)),
    ]

    result1 = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    result2 = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_observation_density_feature_names(
        result1
    ) == get_observation_density_feature_names(
        result2
    )


def test_custom_windows_are_respected():
    config = FeatureConfig(
        observation_density_windows=(
            2,
            5,
        )
    )

    history = [
        _observation(1, date(2026, 1, 5)),
        _observation(2, date(2026, 1, 8)),
    ]

    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=config,
    )

    names = get_observation_density_feature_names(
        result
    )

    assert "observation_density_count_2" in names
    assert "observation_density_count_5" in names
    assert "observation_density_count_7" not in names


def test_records_are_immutable():
    result = build_observation_density_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    with pytest.raises(AttributeError):
        result.records = ()