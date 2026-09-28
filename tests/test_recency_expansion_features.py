from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.point_in_time import (
    build_point_in_time_history,
)
from features.recency_expansion_features import (
    RecencyExpansionFeatureResult,
    build_recency_expansion_features,
    get_recency_expansion_feature_names,
    get_recency_expansion_feature_value,
    get_recency_expansion_feature_values,
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
    observations: tuple[
        HistoricalFeatureObservation,
        ...,
    ],
    target_date: date,
):
    return build_point_in_time_history(
        observations,
        target_date,
    )


def _config(
    lookbacks: tuple[int, ...] = (3, 5),
    positions: tuple[str, ...] = ("col1",),
) -> FeatureConfig:
    return FeatureConfig(
        positions=positions,
        recency_lookbacks=lookbacks,
    )


def test_result_type_is_correct():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    result = build_recency_expansion_features(
        history,
        _config(),
    )

    assert isinstance(
        result,
        RecencyExpansionFeatureResult,
    )


def test_target_date_is_preserved():
    target_date = date(2026, 1, 10)

    history = _history(
        (),
        target_date,
    )

    result = build_recency_expansion_features(
        history,
        _config(),
    )

    assert result.target_date == target_date


def test_expected_number_of_records_is_generated():
    history = _history(
        (),
        date(2026, 1, 10),
    )

    config = _config(
        lookbacks=(3, 5),
        positions=("col1",),
    )

    result = build_recency_expansion_features(
        history,
        config,
    )

    # position × digit × lookback × metric
    # 1 × 10 × 2 × 4 = 80
    assert len(result.records) == 80


def test_all_positions_digits_lookbacks_and_metrics_are_generated():
    history = _history(
        (),
        date(2026, 1, 10),
    )

    config = _config(
        lookbacks=(3, 5),
        positions=("col1", "col3"),
    )

    result = build_recency_expansion_features(
        history,
        config,
    )

    names = get_recency_expansion_feature_names(
        result
    )

    # 2 × 10 × 2 × 4 = 160
    assert len(names) == 160

    metrics = (
        "count",
        "rate",
        "last_distance",
        "seen",
    )

    for position in config.positions:
        for digit in range(10):
            for lookback in config.recency_lookbacks:
                for metric in metrics:
                    assert (
                        f"{position}_digit_{digit}_"
                        f"recency_{metric}_{lookback}"
                        in names
                    )


def test_occurrence_count_is_correct():
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
            (7, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_7_recency_count_3",
    ) == 2


def test_occurrence_rate_uses_configured_lookback():
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
            (7, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_7_recency_rate_3",
    ) == pytest.approx(2 / 3)


def test_last_distance_matches_phase_13_semantics():
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
            (7, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 4),
    )

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_7_recency_last_distance_3",
    ) == 0


def test_unseen_digit_has_zero_count_and_rate():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 3),
    )

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_9_recency_count_3",
    ) == 0

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_9_recency_rate_3",
    ) == 0.0

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_9_recency_last_distance_3",
    ) is None


def test_zero_is_valid_digit():
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

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_0_recency_count_3",
    ) == 1

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_0_recency_rate_3",
    ) == pytest.approx(1 / 3)

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_0_recency_last_distance_3",
    ) == 0


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

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_9_recency_count_3",
    ) == 0


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

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_9_recency_count_3",
    ) == 0


def test_lookback_limits_history():
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

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(2,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_7_recency_count_2",
    ) == 0

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_7_recency_last_distance_2",
    ) is None


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

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(5,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_7_recency_last_distance_5",
    ) == 1


def test_empty_history_returns_zero_count_and_none_distance():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_0_recency_count_3",
    ) == 0

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_0_recency_rate_3",
    ) == 0.0

    assert get_recency_expansion_feature_value(
        result,
        "col1_digit_0_recency_last_distance_3",
    ) is None


def test_seen_is_true_when_digit_exists():
    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (5, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 2),
    )

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    record = next(
        record
        for record in result.records
        if record.position == "col1"
        and record.digit == 5
        and record.lookback == 3
        and record.metric == "count"
    )

    assert record.seen_within_lookback is True


def test_seen_is_false_when_digit_does_not_exist():
    history = _history(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (5, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
    )

    result = build_recency_expansion_features(
        history,
        _config(lookbacks=(3,)),
    )

    record = next(
        record
        for record in result.records
        if record.position == "col1"
        and record.digit == 9
        and record.lookback == 3
        and record.metric == "count"
    )

    assert record.seen_within_lookback is False


def test_configured_positions_are_respected():
    history = _history(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
    )

    config = _config(
        lookbacks=(3,),
        positions=("col1", "col3"),
    )

    result = build_recency_expansion_features(
        history,
        config,
    )

    # 2 positions × 10 digits × 1 lookback × 4 metrics
    assert len(result.records) == 80

    names = get_recency_expansion_feature_names(
        result
    )

    assert (
        "col1_digit_1_recency_count_3"
        in names
    )

    assert (
        "col3_digit_3_recency_count_3"
        in names
    )

    assert (
        "col2_digit_2_recency_count_3"
        not in names
    )


def test_feature_names_are_deterministic():
    history = _history(
        (
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        date(2026, 1, 2),
    )

    config = _config(
        lookbacks=(3, 5),
        positions=("col1",),
    )

    first = build_recency_expansion_features(
        history,
        config,
    )

    second = build_recency_expansion_features(
        history,
        config,
    )

    assert (
        get_recency_expansion_feature_names(first)
        == get_recency_expansion_feature_names(second)
    )


def test_values_getter_returns_mapping():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    result = build_recency_expansion_features(
        history,
        _config(
            lookbacks=(3,),
            positions=("col1",),
        ),
    )

    values = get_recency_expansion_feature_values(
        result
    )

    # 10 digits × 4 metrics
    assert len(values) == 40


def test_unknown_feature_name_is_rejected():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    result = build_recency_expansion_features(
        history,
        _config(
            lookbacks=(3,),
            positions=("col1",),
        ),
    )

    with pytest.raises(ValueError):
        get_recency_expansion_feature_value(
            result,
            "unknown_feature",
        )


def test_feature_name_type_is_validated():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    result = build_recency_expansion_features(
        history,
        _config(
            lookbacks=(3,),
            positions=("col1",),
        ),
    )

    with pytest.raises(TypeError):
        get_recency_expansion_feature_value(
            result,
            123,
        )


def test_result_type_is_validated_by_getter():
    with pytest.raises(TypeError):
        get_recency_expansion_feature_value(
            "invalid",
            "col1_digit_0_recency_count_3",
        )


def test_history_type_is_required():
    with pytest.raises(TypeError):
        build_recency_expansion_features(
            "invalid",
            _config(),
        )


def test_config_type_is_required():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    with pytest.raises(TypeError):
        build_recency_expansion_features(
            history,
            "invalid",
        )


def test_records_are_immutable():
    history = _history(
        (),
        date(2026, 1, 1),
    )

    result = build_recency_expansion_features(
        history,
        _config(
            lookbacks=(3,),
            positions=("col1",),
        ),
    )

    with pytest.raises(AttributeError):
        result.records = ()