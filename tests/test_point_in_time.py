from datetime import date

import pytest

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.point_in_time import (
    PointInTimeHistory,
    build_point_in_time_history,
    get_point_in_time_observation_count,
    get_point_in_time_observations,
)


def _observation(
    result_id: int,
    result_date: date,
    value_offset: int = 0,
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=(
            value_offset,
            value_offset,
            value_offset,
            value_offset,
            value_offset,
            value_offset,
            value_offset,
            value_offset,
        ),
    )


def test_target_date_is_excluded():
    observations = (
        _observation(
            result_id=1,
            result_date=date(2026, 9, 20),
            value_offset=1,
        ),
        _observation(
            result_id=2,
            result_date=date(2026, 9, 21),
            value_offset=2,
        ),
        _observation(
            result_id=3,
            result_date=date(2026, 9, 22),
            value_offset=3,
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 21),
    )

    assert [
        observation.result_date
        for observation in history.observations
    ] == [
        date(2026, 9, 20),
    ]


def test_future_dates_are_excluded():
    observations = (
        _observation(
            result_id=1,
            result_date=date(2026, 9, 20),
        ),
        _observation(
            result_id=2,
            result_date=date(2026, 9, 21),
        ),
        _observation(
            result_id=3,
            result_date=date(2026, 9, 22),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 21),
    )

    assert all(
        observation.result_date < history.target_date
        for observation in history.observations
    )


def test_observations_are_sorted_chronologically():
    observations = (
        _observation(
            result_id=3,
            result_date=date(2026, 9, 22),
        ),
        _observation(
            result_id=1,
            result_date=date(2026, 9, 20),
        ),
        _observation(
            result_id=2,
            result_date=date(2026, 9, 21),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 23),
    )

    assert [
        observation.result_date
        for observation in history.observations
    ] == [
        date(2026, 9, 20),
        date(2026, 9, 21),
        date(2026, 9, 22),
    ]


def test_duplicate_dates_are_rejected():
    observations = (
        _observation(
            result_id=1,
            result_date=date(2026, 9, 20),
        ),
        _observation(
            result_id=2,
            result_date=date(2026, 9, 20),
        ),
    )

    with pytest.raises(
        ValueError,
        match="duplicate dates",
    ):
        build_point_in_time_history(
            observations=observations,
            target_date=date(2026, 9, 21),
        )


def test_empty_history_is_explicit():
    history = build_point_in_time_history(
        observations=(),
        target_date=date(2026, 9, 21),
    )

    assert isinstance(
        history,
        PointInTimeHistory,
    )

    assert history.observations == ()
    assert history.observation_count == 0


def test_observation_on_target_date_is_not_available():
    observations = (
        _observation(
            result_id=1,
            result_date=date(2026, 9, 20),
        ),
        _observation(
            result_id=2,
            result_date=date(2026, 9, 21),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 21),
    )

    assert history.observation_count == 1
    assert history.observations[0].result_date == date(2026, 9, 20)


def test_target_date_must_be_a_date():
    with pytest.raises(
        TypeError,
        match="target_date",
    ):
        build_point_in_time_history(
            observations=(),
            target_date="2026-09-21",
        )


def test_observations_must_contain_expected_type():
    with pytest.raises(
        TypeError,
        match="HistoricalFeatureObservation",
    ):
        build_point_in_time_history(
            observations=(object(),),
            target_date=date(2026, 9, 21),
        )


def test_string_observations_are_rejected():
    with pytest.raises(
        TypeError,
        match="iterable",
    ):
        build_point_in_time_history(
            observations="invalid",
            target_date=date(2026, 9, 21),
        )


def test_get_observations_requires_history_instance():
    with pytest.raises(
        TypeError,
        match="PointInTimeHistory",
    ):
        get_point_in_time_observations(object())


def test_get_observation_count_requires_history_instance():
    with pytest.raises(
        TypeError,
        match="PointInTimeHistory",
    ):
        get_point_in_time_observation_count(object())


def test_getters_return_expected_values():
    observations = (
        _observation(
            result_id=1,
            result_date=date(2026, 9, 20),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 21),
    )

    assert get_point_in_time_observations(history) == observations
    assert get_point_in_time_observation_count(history) == 1


def test_zero_is_preserved_as_valid_value():
    observations = (
        HistoricalFeatureObservation(
            result_id=1,
            market_id=1,
            result_date=date(2026, 9, 20),
            positions=(0, 0, 0, 0, 0, 0, 0, 0),
        ),
    )

    history = build_point_in_time_history(
        observations=observations,
        target_date=date(2026, 9, 21),
    )

    assert history.observations[0].positions == (
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )