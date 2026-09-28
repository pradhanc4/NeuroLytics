from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.historical_interval_features import (
    HistoricalIntervalFeatureResult,
    build_historical_interval_features,
    get_historical_interval_feature_names,
    get_historical_interval_feature_value,
    get_historical_interval_feature_values,
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
        historical_interval_features_enabled=enabled,
    )


def test_build_returns_expected_result_type():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
        ),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 2),
        history=history,
        config=_config(),
    )

    assert isinstance(
        result,
        HistoricalIntervalFeatureResult,
    )


def test_target_date_is_preserved():
    target_date = date(2026, 1, 10)

    result = build_historical_interval_features(
        target_date=target_date,
        history=[],
        config=_config(),
    )

    assert result.target_date == target_date


def test_all_expected_features_are_generated():
    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    assert len(result.records) == 7

    expected = (
        "historical_interval_days_since_last",
        "historical_interval_days_since_first",
        "historical_interval_span_days",
        "historical_interval_mean_days",
        "historical_interval_min_days",
        "historical_interval_max_days",
        "historical_interval_std_days",
    )

    assert get_historical_interval_feature_names(
        result
    ) == expected


def test_days_since_last_observation():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 5)),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_days_since_last",
    ) == 5.0


def test_days_since_first_observation():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 5)),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_days_since_first",
    ) == 9.0


def test_historical_span_is_correct():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 5)),
        _observation(3, date(2026, 1, 8)),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_span_days",
    ) == 7.0


def test_interval_statistics_are_correct():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 3)),
        _observation(3, date(2026, 1, 8)),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_mean_days",
    ) == pytest.approx(3.5)

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_min_days",
    ) == 2.0

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_max_days",
    ) == 5.0

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_std_days",
    ) == pytest.approx(1.5)


def test_single_observation_has_no_between_observation_interval():
    history = [
        _observation(
            1,
            date(2026, 1, 5),
        ),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_days_since_last",
    ) == 5.0

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_days_since_first",
    ) == 5.0

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_span_days",
    ) == 0.0

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_mean_days",
    ) is None

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_min_days",
    ) is None

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_max_days",
    ) is None

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_std_days",
    ) is None


def test_empty_history_returns_none_for_all_features():
    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=[],
        config=_config(),
    )

    values = get_historical_interval_feature_values(
        result
    )

    assert len(values) == 7

    for value in values.values():
        assert value is None


def test_no_history_before_target_returns_none():
    history = [
        _observation(
            1,
            date(2026, 1, 11),
        ),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    values = get_historical_interval_feature_values(
        result
    )

    for value in values.values():
        assert value is None


def test_target_date_is_excluded():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
        ),
        _observation(
            2,
            date(2026, 1, 10),
        ),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_days_since_last",
    ) == 9.0

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_span_days",
    ) == 0.0


def test_future_observation_is_excluded():
    history = [
        _observation(
            1,
            date(2026, 1, 1),
        ),
        _observation(
            2,
            date(2026, 1, 20),
        ),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_days_since_last",
    ) == 9.0


def test_unsorted_history_is_handled_chronologically():
    history = [
        _observation(3, date(2026, 1, 8)),
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 3)),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_days_since_last",
    ) == 2.0

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_mean_days",
    ) == pytest.approx(3.5)


def test_duplicate_observation_dates_are_not_double_counted():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 1)),
        _observation(3, date(2026, 1, 5)),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 10),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_days_since_last",
    ) == 5.0

    assert get_historical_interval_feature_value(
        result,
        "historical_interval_span_days",
    ) == 4.0


def test_feature_values_are_numeric_or_none():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 3)),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 5),
        history=history,
        config=_config(),
    )

    for record in result.records:
        assert (
            record.value is None
            or isinstance(record.value, float)
        )


def test_feature_names_are_deterministic():
    history = [
        _observation(1, date(2026, 1, 1)),
        _observation(2, date(2026, 1, 3)),
    ]

    result1 = build_historical_interval_features(
        target_date=date(2026, 1, 5),
        history=history,
        config=_config(),
    )

    result2 = build_historical_interval_features(
        target_date=date(2026, 1, 5),
        history=history,
        config=_config(),
    )

    assert get_historical_interval_feature_names(
        result1
    ) == get_historical_interval_feature_names(
        result2
    )


def test_feature_metadata_is_correct():
    history = [
        _observation(1, date(2026, 1, 1)),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 5),
        history=history,
        config=_config(),
    )

    for record in result.records:
        assert record.feature_type == "historical_interval"
        assert record.source == "historical_observations"


def test_disabled_feature_family_returns_empty_result():
    history = [
        _observation(1, date(2026, 1, 1)),
    ]

    result = build_historical_interval_features(
        target_date=date(2026, 1, 5),
        history=history,
        config=_config(enabled=False),
    )

    assert result.records == ()


def test_invalid_target_date_is_rejected():
    with pytest.raises(TypeError):
        build_historical_interval_features(
            target_date="2026-01-01",
            history=[],
            config=_config(),
        )


def test_invalid_history_is_rejected():
    with pytest.raises(TypeError):
        build_historical_interval_features(
            target_date=date(2026, 1, 1),
            history=None,
            config=_config(),
        )


def test_invalid_history_item_is_rejected():
    with pytest.raises(TypeError):
        build_historical_interval_features(
            target_date=date(2026, 1, 1),
            history=[None],
            config=_config(),
        )


def test_invalid_config_is_rejected():
    with pytest.raises(TypeError):
        build_historical_interval_features(
            target_date=date(2026, 1, 1),
            history=[],
            config=None,
        )


def test_missing_feature_raises_value_error():
    result = build_historical_interval_features(
        target_date=date(2026, 1, 1),
        history=[],
        config=_config(),
    )

    with pytest.raises(ValueError):
        get_historical_interval_feature_value(
            result,
            "does_not_exist",
        )


def test_invalid_result_is_rejected_by_getter():
    with pytest.raises(TypeError):
        get_historical_interval_feature_value(
            None,
            "historical_interval_span_days",
        )


def test_invalid_feature_name_is_rejected():
    result = build_historical_interval_features(
        target_date=date(2026, 1, 1),
        history=[],
        config=_config(),
    )

    with pytest.raises(TypeError):
        get_historical_interval_feature_value(
            result,
            None,
        )


def test_get_values_returns_mapping():
    result = build_historical_interval_features(
        target_date=date(2026, 1, 1),
        history=[],
        config=_config(),
    )

    values = get_historical_interval_feature_values(
        result
    )

    assert isinstance(values, dict)
    assert len(values) == 7


def test_records_are_immutable():
    result = build_historical_interval_features(
        target_date=date(2026, 1, 1),
        history=[],
        config=_config(),
    )

    with pytest.raises(AttributeError):
        result.records = ()