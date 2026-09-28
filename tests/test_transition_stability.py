from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.point_in_time import (
    HistoricalFeatureObservation,
    PointInTimeHistory,
)
from features.transition_stability import (
    TransitionStabilityRecord,
    TransitionStabilityResult,
    build_transition_stability_features,
    get_transition_stability_feature_names,
    get_transition_stability_records,
    get_transition_stability_value,
)


def _positions(
    value: int,
    *,
    col2: int = 2,
    col3: int = 3,
    col4: int = 4,
    col5: int = 5,
    col6: int = 6,
    col7: int = 7,
    col8: int = 8,
) -> tuple[int, ...]:
    return (
        value,
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
    target_date: date = date(2026, 8, 26),
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
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    ),
    enabled: bool = True,
) -> FeatureConfig:
    config = FeatureConfig()

    return replace(
        config,
        positions=positions,
        transition_stability_features_enabled=enabled,
    )


def test_result_type():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    assert isinstance(result, TransitionStabilityResult)


def test_record_type():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    assert len(result.records) == 1
    assert isinstance(result.records[0], TransitionStabilityRecord)


def test_all_configured_positions_are_processed():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(),
    )

    assert {record.position for record in result.records} == {
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    }


def test_dominant_transition_is_identified():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
            _observation(date(2026, 8, 22), _positions(1), result_id=3),
            _observation(date(2026, 8, 23), _positions(2), result_id=4),
            _observation(date(2026, 8, 24), _positions(1), result_id=5),
            _observation(date(2026, 8, 25), _positions(2), result_id=6),
        ),
        target_date=date(2026, 8, 26),
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_from_value == 1
    assert record.dominant_to_value == 2
    assert record.dominant_transition == "1_to_2"
    assert record.dominant_transition_count == 3
    assert record.total_transitions == 5


def test_dominant_transition_percentage_is_correct():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
            _observation(date(2026, 8, 22), _positions(3), result_id=3),
            _observation(date(2026, 8, 23), _positions(2), result_id=4),
            _observation(date(2026, 8, 24), _positions(3), result_id=5),
            _observation(date(2026, 8, 25), _positions(2), result_id=6),
        ),
        target_date=date(2026, 8, 26),
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_transition == "2_to_3"
    assert record.dominant_transition_count == 2
    assert record.total_transitions == 5
    assert record.stability_percentage == pytest.approx(40.0)


def test_all_transitions_identical_have_full_stability():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
            _observation(date(2026, 8, 22), _positions(2), result_id=3),
            _observation(date(2026, 8, 23), _positions(2), result_id=4),
            _observation(date(2026, 8, 24), _positions(2), result_id=5),
        ),
        target_date=date(2026, 8, 25),
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_transition == "2_to_2"
    assert record.dominant_transition_count == 3
    assert record.total_transitions == 4
    assert record.stability_percentage == pytest.approx(75.0)


def test_single_transition_has_100_percent_stability():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_transition == "1_to_2"
    assert record.dominant_transition_count == 1
    assert record.total_transitions == 1
    assert record.transition_change_count == 0
    assert record.stability_percentage == pytest.approx(100.0)


def test_zero_values_are_valid():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(0), result_id=1),
            _observation(date(2026, 8, 21), _positions(1), result_id=2),
            _observation(date(2026, 8, 22), _positions(0), result_id=3),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_transition == "0_to_1"
    assert record.dominant_transition_count == 1
    assert record.total_transitions == 2
    assert record.stability_percentage == pytest.approx(50.0)


def test_same_value_transition_is_valid():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(5), result_id=1),
            _observation(date(2026, 8, 21), _positions(5), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_from_value == 5
    assert record.dominant_to_value == 5
    assert record.dominant_transition == "5_to_5"
    assert record.dominant_transition_count == 1
    assert record.stability_percentage == pytest.approx(100.0)


def test_transition_change_count_is_total_minus_dominant():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
            _observation(date(2026, 8, 22), _positions(1), result_id=3),
            _observation(date(2026, 8, 23), _positions(2), result_id=4),
            _observation(date(2026, 8, 24), _positions(3), result_id=5),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_transition_count == 2
    assert record.total_transitions == 4
    assert record.transition_change_count == 2


def test_only_consecutive_observations_are_used():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 22), _positions(2), result_id=2),
            _observation(date(2026, 8, 24), _positions(1), result_id=3),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.total_transitions == 2
    assert record.dominant_transition_count == 1
    assert record.stability_percentage == pytest.approx(50.0)


def test_target_date_observation_is_excluded():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
            _observation(date(2026, 8, 26), _positions(3), result_id=3),
        ),
        target_date=date(2026, 8, 26),
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_transition == "1_to_2"
    assert record.total_transitions == 1
    assert record.stability_percentage == pytest.approx(100.0)


def test_future_observation_is_excluded():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
            _observation(date(2026, 8, 27), _positions(9), result_id=3),
        ),
        target_date=date(2026, 8, 26),
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_transition == "1_to_2"
    assert record.total_transitions == 1
    assert record.stability_percentage == pytest.approx(100.0)


def test_one_observation_produces_no_records():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    assert result.records == ()


def test_empty_history_produces_no_records():
    history = _history(())

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    assert result.records == ()


def test_configured_position_subset_is_respected():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                _positions(1, col2=8),
                result_id=1,
            ),
            _observation(
                date(2026, 8, 21),
                _positions(2, col2=9),
                result_id=2,
            ),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col2",)),
    )

    assert len(result.records) == 1
    assert result.records[0].position == "col2"
    assert result.records[0].dominant_transition == "8_to_9"


def test_disabled_feature_returns_empty_result():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(
            positions=("col1",),
            enabled=False,
        ),
    )

    assert isinstance(result, TransitionStabilityResult)
    assert result.records == ()
    assert result.target_date == date(2026, 8, 26)


def test_feature_name_is_deterministic():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    assert (
        result.records[0].feature_name
        == "col1_transition_stability_percentage"
    )


def test_get_records_accessor():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    assert get_transition_stability_records(result) == result.records


def test_get_feature_names_accessor():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    assert get_transition_stability_feature_names(result) == (
        "col1_transition_stability_percentage",
    )


def test_get_value_accessor():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    value = get_transition_stability_value(
        result,
        "col1_transition_stability_percentage",
    )

    assert isinstance(value, TransitionStabilityRecord)
    assert value.feature_name == "col1_transition_stability_percentage"
    assert value.stability_percentage == pytest.approx(100.0)
    assert value.dominant_transition == "1_to_2"


def test_missing_feature_raises_value_error():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    with pytest.raises(ValueError, match="Transition stability feature not found"):
        get_transition_stability_value(
            result,
            "does_not_exist",
        )


def test_invalid_history_type_raises_type_error():
    with pytest.raises(TypeError):
        build_transition_stability_features(
            object(),
            _config(positions=("col1",)),
        )


def test_invalid_config_type_raises_type_error():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        )
    )

    with pytest.raises(TypeError):
        build_transition_stability_features(
            history,
            object(),
        )


def test_target_date_is_preserved():
    target_date = date(2026, 9, 1)

    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
        ),
        target_date=target_date,
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    assert result.target_date == target_date


def test_tie_breaking_is_deterministic():
    history = _history(
        (
            _observation(date(2026, 8, 20), _positions(1), result_id=1),
            _observation(date(2026, 8, 21), _positions(2), result_id=2),
            _observation(date(2026, 8, 22), _positions(1), result_id=3),
        )
    )

    result = build_transition_stability_features(
        history,
        _config(positions=("col1",)),
    )

    record = result.records[0]

    assert record.dominant_transition == "1_to_2"
    assert record.dominant_transition_count == 1
    assert record.total_transitions == 2
    assert record.stability_percentage == pytest.approx(50.0)