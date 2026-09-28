from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.point_in_time import (
    HistoricalFeatureObservation,
    PointInTimeHistory,
)
from features.relationship_change_trend import (
    RelationshipChangeTrendRecord,
    RelationshipChangeTrendResult,
    build_relationship_change_trend_features,
    get_relationship_change_trend_feature_names,
    get_relationship_change_trend_records,
    get_relationship_change_trend_value,
)


def _positions(
    col1: int,
    col2: int,
    col3: int = 3,
    col4: int = 4,
    col5: int = 5,
    col6: int = 6,
    col7: int = 7,
    col8: int = 8,
) -> tuple[int, ...]:
    return (
        col1,
        col2,
        col3,
        col4,
        col5,
        col6,
        col7,
        col8,
    )


def _observation(
    result_date: date,
    positions: tuple[int, ...],
    result_id: int = 1,
    market_id: int = 1,
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_date=result_date,
        positions=positions,
        result_id=result_id,
        market_id=market_id,
    )


def _history(
    observations: tuple[HistoricalFeatureObservation, ...],
    target_date: date = date(2026, 8, 30),
) -> PointInTimeHistory:
    return PointInTimeHistory(
        target_date=target_date,
        observations=observations,
        observation_count=len(observations),
    )


def _config(
    *,
    positions: tuple[str, ...] = (
        "col1",
        "col2",
    ),
    trend_windows: tuple[int, ...] = (2,),
    enabled: bool = True,
) -> FeatureConfig:
    config = FeatureConfig()

    return replace(
        config,
        positions=positions,
        trend_windows=trend_windows,
        relationship_change_trend_features_enabled=enabled,
    )


def test_result_type():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(),
    )

    assert isinstance(
        result,
        RelationshipChangeTrendResult,
    )


def test_record_type():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(),
    )

    assert result.records
    assert isinstance(
        result.records[0],
        RelationshipChangeTrendRecord,
    )


def test_configured_position_pair_is_processed():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(),
    )

    assert all(
        record.position_a == "col1"
        for record in result.records
    )

    assert all(
        record.position_b == "col2"
        for record in result.records
    )


def test_increasing_relationship_trend():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
            _observation(
                date(2026, 8, 24),
                _positions(5, 5),
                result_id=5,
            ),
            _observation(
                date(2026, 8, 25),
                _positions(6, 6),
                result_id=6,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert result.records

    assert any(
        record.trend_direction == "STABLE"
        or record.trend_direction == "INCREASING"
        for record in result.records
    )


def test_decreasing_relationship_trend():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 6),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 5),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 4),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 3),
                result_id=4,
            ),
            _observation(
                date(2026, 8, 24),
                _positions(5, 2),
                result_id=5,
            ),
            _observation(
                date(2026, 8, 25),
                _positions(6, 1),
                result_id=6,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert result.records

    assert any(
        record.trend_direction == "STABLE"
        or record.trend_direction == "DECREASING"
        for record in result.records
    )


def test_stable_relationship_trend():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert result.records

    assert all(
        record.trend_direction == "STABLE"
        for record in result.records
    )


def test_correlation_change_is_exposed():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 1),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert result.records

    for record in result.records:
        if (
            record.previous_correlation is not None
            and record.current_correlation is not None
        ):
            assert (
                record.correlation_change
                == pytest.approx(
                    record.current_correlation
                    - record.previous_correlation
                )
            )


def test_absolute_correlation_change_is_exposed():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 1),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    for record in result.records:
        if (
            record.previous_correlation is not None
            and record.current_correlation is not None
        ):
            assert (
                record.absolute_correlation_change
                == pytest.approx(
                    abs(record.current_correlation)
                    - abs(record.previous_correlation)
                )
            )


def test_direction_change_is_preserved():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 6),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 5),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 4),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 3),
                result_id=4,
            ),
            _observation(
                date(2026, 8, 24),
                _positions(5, 5),
                result_id=5,
            ),
            _observation(
                date(2026, 8, 25),
                _positions(6, 6),
                result_id=6,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert all(
        isinstance(
            record.direction_changed,
            bool,
        )
        for record in result.records
    )


def test_strength_change_is_preserved():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 1),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert all(
        isinstance(
            record.strength_changed,
            bool,
        )
        for record in result.records
    )


def test_relationship_change_is_preserved():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 1),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert all(
        isinstance(
            record.relationship_changed,
            bool,
        )
        for record in result.records
    )


def test_zero_values_are_valid():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(0, 0),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(1, 1),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(2, 2),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(3, 3),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert result.records


def test_target_date_observation_is_excluded():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 30),
                _positions(9, 0),
                result_id=3,
            ),
        ),
        target_date=date(2026, 8, 30),
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert all(
        record.previous_window_index >= 1
        for record in result.records
    )

    assert all(
        record.current_window_index >= 2
        for record in result.records
    )


def test_future_observation_is_excluded():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 31),
                _positions(9, 0),
                result_id=3,
            ),
        ),
        target_date=date(2026, 8, 30),
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2,),
        ),
    )

    assert result.records == ()


def test_empty_history_produces_no_records():
    result = build_relationship_change_trend_features(
        _history(()),
        _config(),
    )

    assert result.records == ()


def test_one_observation_produces_no_records():
    result = build_relationship_change_trend_features(
        _history(
            (
                _observation(
                    date(2026, 8, 20),
                    _positions(1, 1),
                    result_id=1,
                ),
            )
        ),
        _config(),
    )

    assert result.records == ()


def test_multiple_trend_windows_are_supported():
    history = _history(
        tuple(
            _observation(
                date(2026, 8, 20 + index),
                _positions(index, index),
                result_id=index + 1,
            )
            for index in range(1, 10)
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            trend_windows=(2, 3),
        ),
    )

    assert result.records

    assert {
        record.window_size
        for record in result.records
    } == {2, 3}


def test_disabled_feature_returns_empty_result():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(
            enabled=False,
        ),
    )

    assert result.records == ()
    assert result.target_date == date(2026, 8, 30)


def test_feature_names_are_deterministic():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(),
    )

    assert result.records

    assert (
        result.records[0].feature_name
        == (
            "col1_col2_relationship_trend_"
            "window_2_1_to_2"
        )
    )


def test_get_records_accessor():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(),
    )

    assert (
        get_relationship_change_trend_records(result)
        == result.records
    )


def test_get_feature_names_accessor():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(),
    )

    names = get_relationship_change_trend_feature_names(
        result
    )

    assert names == tuple(
        record.feature_name
        for record in result.records
    )


def test_get_value_accessor():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(),
    )

    record = result.records[0]

    value = get_relationship_change_trend_value(
        result,
        record.feature_name,
    )

    assert value == record


def test_missing_feature_raises_value_error():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        )
    )

    result = build_relationship_change_trend_features(
        history,
        _config(),
    )

    with pytest.raises(
        ValueError,
        match="Relationship change/trend feature not found",
    ):
        get_relationship_change_trend_value(
            result,
            "does_not_exist",
        )


def test_invalid_history_type_raises_type_error():
    with pytest.raises(TypeError):
        build_relationship_change_trend_features(
            object(),
            _config(),
        )


def test_invalid_config_type_raises_type_error():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
        )
    )

    with pytest.raises(TypeError):
        build_relationship_change_trend_features(
            history,
            object(),
        )


def test_target_date_is_preserved():
    target_date = date(2026, 9, 1)

    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
            _observation(
                date(2026, 8, 23),
                _positions(4, 4),
                result_id=4,
            ),
        ),
        target_date=target_date,
    )

    result = build_relationship_change_trend_features(
        history,
        _config(),
    )

    assert result.target_date == target_date


def test_invalid_trend_window_is_rejected():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, 1),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, 2),
                result_id=2,
            ),
            _observation(
                date(2026, 8, 22),
                _positions(3, 3),
                result_id=3,
            ),
        )
    )

    config = _config(
        trend_windows=(1,),
    )

    with pytest.raises(ValueError):
        build_relationship_change_trend_features(
            history,
            config,
        )