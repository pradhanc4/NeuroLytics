from __future__ import annotations

from datetime import date

import pytest

from features.feature_config import FeatureConfig
from features.point_in_time import (
    HistoricalFeatureObservation,
    PointInTimeHistory,
)
from features.transition_frequency import (
    TransitionFrequencyRecord,
    TransitionFrequencyResult,
    build_transition_frequency_features,
    get_transition_frequency_feature_names,
    get_transition_frequency_records,
    get_transition_frequency_value,
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
        transition_frequency_features_enabled=enabled,
    )


def test_build_transition_frequency_features_returns_result():
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
        )
    )

    result = build_transition_frequency_features(
        history,
        _config(),
    )

    assert isinstance(
        result,
        TransitionFrequencyResult,
    )

    assert result.target_date == date(2026, 8, 25)


def test_all_configured_positions_generate_frequency_records():
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
        )
    )

    result = build_transition_frequency_features(
        history,
        _config(),
    )

    assert len(result.records) == 16

    assert tuple(
        record.position
        for record in result.records
    ) == (
        "col1",
        "col1",
        "col2",
        "col2",
        "col3",
        "col3",
        "col4",
        "col4",
        "col5",
        "col5",
        "col6",
        "col6",
        "col7",
        "col7",
        "col8",
        "col8",
    )


def test_transition_count_is_calculated():
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    count_records = tuple(
        record
        for record in result.records
        if record.feature_name.endswith(
            "_count_1_to_2"
        )
    )

    assert len(count_records) == 1
    assert count_records[0].count == 2
    assert count_records[0].total_transitions == 3


def test_transition_percentage_is_calculated():
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    percentage_records = tuple(
        record
        for record in result.records
        if record.feature_name.endswith(
            "_percentage_1_to_2"
        )
    )

    assert len(percentage_records) == 1

    assert percentage_records[0].count == 2
    assert percentage_records[0].total_transitions == 3
    assert percentage_records[0].percentage == pytest.approx(
        66.6666666667
    )


def test_each_transition_is_grouped_independently():
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    transitions = {
        record.transition: record.count
        for record in result.records
        if record.feature_name.endswith(
            "_count_" + record.transition
        )
    }

    assert transitions == {
        "1_to_2": 1,
        "2_to_3": 1,
    }


def test_zero_is_preserved_as_valid_transition_value():
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
            _observation(
                date(2026, 8, 22),
                (0, 9, 1, 7, 6, 5, 4, 3),
            ),
        )
    )

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    count_records = {
        record.transition: record.count
        for record in result.records
        if "_count_" in record.feature_name
    }

    assert count_records["0_to_9"] == 1
    assert count_records["9_to_0"] == 1


def test_same_value_transition_is_counted():
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
            _observation(
                date(2026, 8, 22),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    records = tuple(
        record
        for record in result.records
        if record.transition == "1_to_1"
    )

    assert len(records) == 2
    assert all(
        record.count == 2
        for record in records
    )

    assert all(
        record.percentage == pytest.approx(100.0)
        for record in records
    )


def test_multiple_occurrences_are_aggregated():
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    record = next(
        record
        for record in result.records
        if record.feature_name
        == "col1_transition_frequency_count_1_to_2"
    )

    assert record.count == 2


def test_only_consecutive_observations_are_counted():
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    transitions = {
        record.transition
        for record in result.records
        if "_count_" in record.feature_name
    }

    assert transitions == {
        "1_to_2",
        "2_to_3",
    }


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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert len(result.records) == 2

    assert all(
        record.transition == "1_to_2"
        for record in result.records
    )


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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert len(result.records) == 2

    assert all(
        record.transition == "1_to_2"
        for record in result.records
    )


def test_one_observation_produces_no_records():
    history = _history(
        (
            _observation(
                date(2026, 8, 20),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        )
    )

    result = build_transition_frequency_features(
        history,
        _config(),
    )

    assert result.records == ()


def test_empty_history_produces_no_records():
    history = _history(())

    result = build_transition_frequency_features(
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col2", "col5"),
        ),
    )

    assert len(result.records) == 4

    assert tuple(
        record.position
        for record in result.records
    ) == (
        "col2",
        "col2",
        "col5",
        "col5",
    )


def test_disabled_transition_frequency_returns_empty_result():
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

    result = build_transition_frequency_features(
        history,
        _config(enabled=False),
    )

    assert result.records == ()


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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert get_transition_frequency_feature_names(
        result
    ) == (
        "col1_transition_frequency_count_1_to_9",
        "col1_transition_frequency_percentage_1_to_9",
    )


def test_get_transition_frequency_records_returns_records():
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    records = get_transition_frequency_records(
        result
    )

    assert records == result.records

    assert isinstance(
        records[0],
        TransitionFrequencyRecord,
    )


def test_get_transition_frequency_value_returns_record():
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    record = get_transition_frequency_value(
        result,
        "col1_transition_frequency_count_1_to_9",
    )

    assert isinstance(
        record,
        TransitionFrequencyRecord,
    )

    assert record.count == 1
    assert record.percentage == pytest.approx(100.0)


def test_invalid_history_type_raises():
    with pytest.raises(TypeError):
        build_transition_frequency_features(
            history=None,
            config=_config(),
        )


def test_invalid_result_type_for_records_raises():
    with pytest.raises(TypeError):
        get_transition_frequency_records(None)


def test_invalid_result_type_for_names_raises():
    with pytest.raises(TypeError):
        get_transition_frequency_feature_names(None)


def test_invalid_result_type_for_value_raises():
    with pytest.raises(TypeError):
        get_transition_frequency_value(
            None,
            "col1_transition_frequency_count_1_to_9",
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    with pytest.raises(TypeError):
        get_transition_frequency_value(
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    with pytest.raises(ValueError):
        get_transition_frequency_value(
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

    result = build_transition_frequency_features(
        history,
        _config(
            positions=("col1",),
        ),
    )

    assert result.target_date == target_date