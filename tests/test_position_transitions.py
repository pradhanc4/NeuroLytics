from __future__ import annotations

from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.point_in_time import (
    HistoricalFeatureObservation,
    PointInTimeHistory,
)
from features.position_transitions import (
    PositionTransitionRecord,
    PositionTransitionResult,
    build_position_transition_features,
    get_position_transition_feature_names,
    get_position_transition_records,
    get_position_transition_value,
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
    target_date: date = date(2026, 8, 25),
) -> PointInTimeHistory:
    return PointInTimeHistory(
        target_date=target_date,
        observations=observations,
        observation_count=len(observations),
    )


def _config(
    positions: tuple[str, ...] = (
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    ),
    enabled: bool = True,
) -> FeatureConfig:
    return FeatureConfig(
        positions=positions,
        position_transition_features_enabled=enabled,
    )


def test_build_position_transition_features_returns_result():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(),
    )

    assert isinstance(
        result,
        PositionTransitionResult,
    )
    assert result.target_date == date(2026, 8, 25)


def test_all_configured_positions_generate_transitions():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(),
    )

    assert len(result.records) == 8

    assert tuple(
        record.position
        for record in result.records
    ) == (
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    )


def test_transition_values_are_exact():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(),
    )

    col1 = result.records[0]

    assert col1.position == "col1"
    assert col1.from_value == 1
    assert col1.to_value == 9
    assert col1.transition == "1_to_9"
    assert (
        col1.feature_name
        == "col1_position_transition_1_to_9"
    )


def test_zero_is_preserved_as_valid_value():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (0, 1, 2, 3, 4, 5, 6, 7),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 0, 0, 8, 7, 6, 5, 4),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(),
    )

    assert result.records[0].from_value == 0
    assert result.records[0].to_value == 9
    assert result.records[0].transition == "0_to_9"

    assert result.records[1].from_value == 1
    assert result.records[1].to_value == 0
    assert result.records[1].transition == "1_to_0"

    assert result.records[2].from_value == 2
    assert result.records[2].to_value == 0
    assert result.records[2].transition == "2_to_0"


def test_same_value_transition_is_preserved():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(),
    )

    assert all(
        record.from_value == record.to_value
        for record in result.records
    )

    assert result.records[0].transition == "1_to_1"


def test_multiple_consecutive_transitions_are_retained():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (2, 3, 4, 5, 6, 7, 8, 9),
            ),
            _observation(
                date(2026, 8, 22),
                (3, 4, 5, 6, 7, 8, 9, 0),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert len(result.records) == 2

    assert result.records[0].from_value == 1
    assert result.records[0].to_value == 2
    assert result.records[0].transition == "1_to_2"

    assert result.records[1].from_value == 2
    assert result.records[1].to_value == 3
    assert result.records[1].transition == "2_to_3"


def test_transition_order_is_historical_order():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (2, 3, 4, 5, 6, 7, 8, 9),
            ),
            _observation(
                date(2026, 8, 22),
                (3, 4, 5, 6, 7, 8, 9, 0),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert [
        record.transition
        for record in result.records
    ] == [
        "1_to_2",
        "2_to_3",
    ]


def test_target_date_observation_is_excluded():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (2, 3, 4, 5, 6, 7, 8, 9),
            ),
            _observation(
                date(2026, 8, 25),
                (9, 9, 9, 9, 9, 9, 9, 9),
            ),
        ),
        target_date=date(2026, 8, 25),
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert len(result.records) == 1

    assert result.records[0].from_value == 1
    assert result.records[0].to_value == 2


def test_future_observations_are_excluded():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (2, 3, 4, 5, 6, 7, 8, 9),
            ),
            _observation(
                date(2026, 8, 26),
                (9, 9, 9, 9, 9, 9, 9, 9),
            ),
        ),
        target_date=date(2026, 8, 25),
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert len(result.records) == 1

    assert result.records[0].transition == "1_to_2"


def test_one_observation_produces_no_transitions():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(),
    )

    assert result.records == ()


def test_empty_history_produces_no_transitions():
    history = _history(())

    result = build_position_transition_features(
        history,
        _config(),
    )

    assert result.records == ()


def test_configured_position_subset_is_respected():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col2", "col5"),
        ),
    )

    assert len(result.records) == 2

    assert [
        record.position
        for record in result.records
    ] == [
        "col2",
        "col5",
    ]


def test_disabled_position_transition_features_return_empty_result():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(enabled=False),
    )

    assert result.records == ()


def test_duplicate_transition_values_are_retained_as_separate_events():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (2, 3, 4, 5, 6, 7, 8, 9),
            ),
            _observation(
                date(2026, 8, 22),
                (1, 4, 5, 6, 7, 8, 9, 0),
            ),
            _observation(
                date(2026, 8, 23),
                (2, 5, 6, 7, 8, 9, 0, 1),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert len(result.records) == 3

    assert [
        record.transition
        for record in result.records
    ] == [
        "1_to_2",
        "2_to_1",
        "1_to_2",
    ]


def test_feature_names_are_deterministic():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert get_position_transition_feature_names(
        result
    ) == (
        "col1_position_transition_1_to_9",
    )


def test_get_position_transition_records_returns_records():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    records = get_position_transition_records(
        result
    )

    assert records == result.records

    assert isinstance(
        records[0],
        PositionTransitionRecord,
    )


def test_get_position_transition_value_returns_record():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    record = get_position_transition_value(
        result,
        "col1_position_transition_1_to_9",
    )

    assert isinstance(
        record,
        PositionTransitionRecord,
    )

    assert record.from_value == 1
    assert record.to_value == 9


def test_invalid_history_type_raises():
    with pytest.raises(TypeError):
        build_position_transition_features(
            history=None,
            config=_config(),
        )


def test_invalid_result_type_for_records_raises():
    with pytest.raises(TypeError):
        get_position_transition_records(None)


def test_invalid_result_type_for_names_raises():
    with pytest.raises(TypeError):
        get_position_transition_feature_names(None)


def test_invalid_result_type_for_value_raises():
    with pytest.raises(TypeError):
        get_position_transition_value(
            None,
            "col1_position_transition_1_to_9",
        )


def test_invalid_feature_name_type_raises():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    with pytest.raises(TypeError):
        get_position_transition_value(
            result,
            None,
        )


def test_missing_feature_name_raises():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        )
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    with pytest.raises(ValueError):
        get_position_transition_value(
            result,
            "does_not_exist",
        )


def test_target_date_is_preserved():
    target_date = date(2026, 9, 1)

    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
            _observation(
                date(2026, 8, 21),
                (9, 8, 7, 6, 5, 4, 3, 2),
            ),
        ),
        target_date=target_date,
    )

    result = build_position_transition_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert result.target_date == target_date