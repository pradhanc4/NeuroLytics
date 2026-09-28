from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation
from features.recency_bucket_features import (
    RecencyBucketFeatureResult,
    build_recency_bucket_features,
    get_recency_bucket_feature_names,
    get_recency_bucket_feature_value,
    get_recency_bucket_feature_values,
)


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
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(),
    )

    assert isinstance(result, RecencyBucketFeatureResult)


def test_recent_bucket_zero_to_three():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_5_recency_bucket_label_3",
        )
        == "RECENT_0_3"
    )


def test_second_bucket_four_to_seven():
    observations = [
        _observation(1, date(2026, 1, 1), 9),
        _observation(2, date(2026, 1, 2), 5),
        _observation(3, date(2026, 1, 3), 5),
        _observation(4, date(2026, 1, 4), 5),
        _observation(5, date(2026, 1, 5), 5),
    ]

    result = build_recency_bucket_features(
        _history(*observations),
        date(2026, 1, 6),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(5,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_9_recency_bucket_label_5",
        )
        == "RECENT_4_7"
    )


def test_third_bucket_eight_to_fourteen():
    observations = [
        _observation(i, date(2026, 1, i), 5)
        for i in range(1, 10)
    ]

    observations[0] = _observation(
        1,
        date(2026, 1, 1),
        9,
    )

    result = build_recency_bucket_features(
        _history(*observations),
        date(2026, 1, 11),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(10,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_9_recency_bucket_label_10",
        )
        == "RECENT_8_14"
    )


def test_stale_bucket():
    observations = [
        _observation(i, date(2026, 1, i), 5)
        for i in range(1, 17)
    ]

    observations[0] = _observation(
        1,
        date(2026, 1, 1),
        9,
    )

    result = build_recency_bucket_features(
        _history(*observations),
        date(2026, 1, 18),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(20,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_9_recency_bucket_label_20",
        )
        == "STALE_15_PLUS"
    )


def test_unseen_bucket():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_9_recency_bucket_label_3",
        )
        == "UNSEEN"
    )


def test_unseen_has_unseen_indicator():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_9_recency_bucket_is_unseen_3",
        )
        == 1
    )


def test_seen_has_no_unseen_indicator():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_5_recency_bucket_is_unseen_3",
        )
        == 0
    )


def test_recent_bucket_index():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_5_recency_bucket_index_3",
        )
        == 0
    )


def test_unseen_bucket_index():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_9_recency_bucket_index_3",
        )
        == 3
    )


def test_point_in_time_future_observation_excluded():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
            _observation(2, date(2026, 1, 3), 9),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_9_recency_bucket_label_3",
        )
        == "UNSEEN"
    )


def test_target_date_observation_excluded():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
            _observation(2, date(2026, 1, 2), 9),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_9_recency_bucket_label_3",
        )
        == "UNSEEN"
    )


def test_zero_is_valid_digit():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 0),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_0_recency_bucket_label_3",
        )
        == "RECENT_0_3"
    )


def test_configured_positions_respected():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col2",),
            recency_lookbacks=(3,),
        ),
    )

    names = get_recency_bucket_feature_names(result)

    assert names
    assert all(name.startswith("col2_") for name in names)


def test_multiple_lookbacks_generate_separate_features():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3, 5),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_5_recency_bucket_label_3",
        )
        == "RECENT_0_3"
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_5_recency_bucket_label_5",
        )
        == "RECENT_0_3"
    )


def test_custom_boundaries():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
            recency_bucket_boundaries=(1, 2, 5),
        ),
    )

    assert (
        get_recency_bucket_feature_value(
            result,
            "col1_digit_5_recency_bucket_label_3",
        )
        == "RECENT_0_1"
    )


def test_disabled_feature_returns_empty_result():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
            recency_buckets_enabled=False,
        ),
    )

    assert result.records == ()


def test_deterministic_feature_names():
    history = _history(
        _observation(1, date(2026, 1, 1), 5),
    )

    config = FeatureConfig(
        positions=("col1",),
        recency_lookbacks=(3,),
    )

    result1 = build_recency_bucket_features(
        history,
        date(2026, 1, 2),
        config,
    )

    result2 = build_recency_bucket_features(
        history,
        date(2026, 1, 2),
        config,
    )

    assert (
        get_recency_bucket_feature_names(result1)
        == get_recency_bucket_feature_names(result2)
    )


def test_feature_values_mapping():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    values = get_recency_bucket_feature_values(result)

    assert (
        values[
            "col1_digit_5_recency_bucket_label_3"
        ]
        == "RECENT_0_3"
    )


def test_invalid_history_type():
    with pytest.raises(TypeError):
        build_recency_bucket_features(
            [],
            date(2026, 1, 2),
            FeatureConfig(),
        )


def test_invalid_history_observation_type():
    with pytest.raises(TypeError):
        build_recency_bucket_features(
            (object(),),
            date(2026, 1, 2),
            FeatureConfig(),
        )


def test_invalid_target_date():
    with pytest.raises(TypeError):
        build_recency_bucket_features(
            _history(
                _observation(1, date(2026, 1, 1), 5),
            ),
            "2026-01-02",
            FeatureConfig(),
        )


def test_invalid_config():
    with pytest.raises(TypeError):
        build_recency_bucket_features(
            _history(
                _observation(1, date(2026, 1, 1), 5),
            ),
            date(2026, 1, 2),
            object(),
        )


def test_missing_feature_raises():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    with pytest.raises(ValueError):
        get_recency_bucket_feature_value(
            result,
            "does_not_exist",
        )


def test_result_is_immutable():
    result = build_recency_bucket_features(
        _history(
            _observation(1, date(2026, 1, 1), 5),
        ),
        date(2026, 1, 2),
        FeatureConfig(
            positions=("col1",),
            recency_lookbacks=(3,),
        ),
    )

    with pytest.raises(Exception):
        result.records = ()