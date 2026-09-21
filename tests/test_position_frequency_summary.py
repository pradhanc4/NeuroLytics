from datetime import date

import pytest

from analytics.position_frequency import (
    PositionFrequencyResult,
    calculate_position_frequency,
)
from analytics.position_frequency_summary import (
    PositionFrequencySummary,
    summarize_all_position_frequencies,
    summarize_position_frequency,
)
from analytics.statistical_foundation import StatisticalObservation


def make_observation(
    column_name: str,
    value: int,
    day: int = 1,
) -> StatisticalObservation:
    return StatisticalObservation(
        record_date=date(2026, 1, day),
        column_name=column_name,
        value=value,
    )


def test_summarize_position_frequency_returns_basic_summary():
    observations = [
        make_observation("col1", 5, 1),
        make_observation("col1", 5, 2),
        make_observation("col1", 5, 3),
        make_observation("col1", 2, 4),
        make_observation("col1", 2, 5),
        make_observation("col1", 0, 6),
    ]

    result = calculate_position_frequency(
        observations,
        "col1",
    )

    summary = summarize_position_frequency(result)

    assert summary.position == "col1"
    assert summary.total_observations == 6

    assert summary.most_frequent_digits == (5,)
    assert summary.highest_count == 3
    assert summary.highest_percentage == pytest.approx(50.0)


def test_least_frequent_digit_is_identified():
    observations = [
        make_observation("col2", 5, 1),
        make_observation("col2", 5, 2),
        make_observation("col2", 2, 3),
        make_observation("col2", 0, 4),
    ]

    result = calculate_position_frequency(
        observations,
        "col2",
    )

    summary = summarize_position_frequency(result)

    assert summary.least_frequent_digits == (
        1,
        3,
        4,
        6,
        7,
        8,
        9,
    )

    assert summary.lowest_count == 0
    assert summary.lowest_percentage == pytest.approx(0.0)


def test_most_frequent_ties_are_preserved():
    observations = [
        make_observation("col3", 2, 1),
        make_observation("col3", 2, 2),
        make_observation("col3", 7, 3),
        make_observation("col3", 7, 4),
        make_observation("col3", 5, 5),
    ]

    result = calculate_position_frequency(
        observations,
        "col3",
    )

    summary = summarize_position_frequency(result)

    assert summary.most_frequent_digits == (2, 7)
    assert summary.highest_count == 2
    assert summary.highest_percentage == pytest.approx(40.0)


def test_least_frequent_ties_are_preserved():
    observations = [
        make_observation("col4", 2, 1),
        make_observation("col4", 2, 2),
        make_observation("col4", 7, 3),
        make_observation("col4", 7, 4),
        make_observation("col4", 5, 5),
    ]

    result = calculate_position_frequency(
        observations,
        "col4",
    )

    summary = summarize_position_frequency(result)

    assert summary.least_frequent_digits == (
        0,
        1,
        3,
        4,
        6,
        8,
        9,
    )

    assert summary.lowest_count == 0
    assert summary.lowest_percentage == pytest.approx(0.0)


def test_actual_zero_is_preserved_in_summary():
    observations = [
        make_observation("col5", 0, 1),
        make_observation("col5", 0, 2),
        make_observation("col5", 3, 3),
    ]

    result = calculate_position_frequency(
        observations,
        "col5",
    )

    summary = summarize_position_frequency(result)

    assert summary.most_frequent_digits == (0,)
    assert summary.highest_count == 2
    assert summary.highest_percentage == pytest.approx(
        66.6666666667
    )


def test_empty_position_preserves_all_zero_frequency_ties():
    result = calculate_position_frequency(
        [],
        "col6",
    )

    summary = summarize_position_frequency(result)

    assert summary.position == "col6"
    assert summary.total_observations == 0

    assert summary.most_frequent_digits == tuple(range(10))
    assert summary.highest_count == 0
    assert summary.highest_percentage == 0.0

    assert summary.least_frequent_digits == tuple(range(10))
    assert summary.lowest_count == 0
    assert summary.lowest_percentage == 0.0


def test_total_observation_count_is_preserved():
    observations = [
        make_observation("col7", 1, 1),
        make_observation("col7", 1, 2),
        make_observation("col7", 4, 3),
        make_observation("col7", 8, 4),
    ]

    result = calculate_position_frequency(
        observations,
        "col7",
    )

    summary = summarize_position_frequency(result)

    assert summary.total_observations == result.total_observations


def test_all_position_summaries_are_created():
    observations = [
        make_observation("col1", 1, 1),
        make_observation("col2", 2, 2),
        make_observation("col3", 3, 3),
        make_observation("col4", 4, 4),
        make_observation("col5", 5, 5),
        make_observation("col6", 6, 6),
        make_observation("col7", 7, 7),
        make_observation("col8", 8, 8),
    ]

    position_results = {
        position: calculate_position_frequency(
            observations,
            position,
        )
        for position in (
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "col8",
        )
    }

    summaries = summarize_all_position_frequencies(
        position_results
    )

    assert list(summaries.keys()) == [
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    ]

    for position, summary in summaries.items():
        assert isinstance(
            summary,
            PositionFrequencySummary,
        )
        assert summary.position == position


def test_summary_does_not_change_frequency_result():
    observations = [
        make_observation("col8", 4, 1),
        make_observation("col8", 4, 2),
        make_observation("col8", 9, 3),
    ]

    result = calculate_position_frequency(
        observations,
        "col8",
    )

    original_records = result.records

    summarize_position_frequency(result)

    assert result.records == original_records
    assert result.total_observations == 3


def test_empty_frequency_records_are_rejected():
    empty_result = PositionFrequencyResult(
        position="col1",
        total_observations=0,
        records=(),
    )

    with pytest.raises(ValueError):
        summarize_position_frequency(empty_result)


def test_position_frequency_summary_is_immutable():
    observations = [
        make_observation("col1", 5, 1),
    ]

    result = calculate_position_frequency(
        observations,
        "col1",
    )

    summary = summarize_position_frequency(result)

    with pytest.raises(AttributeError):
        summary.position = "col2"