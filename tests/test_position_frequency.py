from datetime import date

import pytest

from analytics.position_frequency import (
    PositionFrequencyResult,
    calculate_all_position_frequencies,
    calculate_position_frequency,
    get_position_frequency_record,
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


def test_calculate_position_frequency_counts_digits():
    observations = [
        make_observation("col3", 5, 1),
        make_observation("col3", 5, 2),
        make_observation("col3", 2, 3),
        make_observation("col3", 0, 4),
    ]

    result = calculate_position_frequency(
        observations,
        "col3",
    )

    assert result.position == "col3"
    assert result.total_observations == 4

    assert get_position_frequency_record(result, 5).count == 2
    assert get_position_frequency_record(result, 2).count == 1
    assert get_position_frequency_record(result, 0).count == 1


def test_percentage_is_calculated_for_each_digit():
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

    assert get_position_frequency_record(
        result,
        5,
    ).percentage == pytest.approx(50.0)

    assert get_position_frequency_record(
        result,
        2,
    ).percentage == pytest.approx(25.0)

    assert get_position_frequency_record(
        result,
        0,
    ).percentage == pytest.approx(25.0)


def test_actual_zero_is_counted_as_a_valid_observation():
    observations = [
        make_observation("col4", 0, 1),
        make_observation("col4", 3, 2),
        make_observation("col4", 0, 3),
    ]

    result = calculate_position_frequency(
        observations,
        "col4",
    )

    zero_record = get_position_frequency_record(result, 0)

    assert result.total_observations == 3
    assert zero_record.count == 2
    assert zero_record.percentage == pytest.approx(66.6666666667)


def test_all_digits_zero_to_nine_are_present():
    observations = [
        make_observation("col1", digit, digit + 1)
        for digit in range(10)
    ]

    result = calculate_position_frequency(
        observations,
        "col1",
    )

    assert len(result.records) == 10

    for digit in range(10):
        record = get_position_frequency_record(result, digit)

        assert record.digit == digit
        assert record.count == 1
        assert record.percentage == pytest.approx(10.0)


def test_unused_digits_have_zero_frequency():
    observations = [
        make_observation("col5", 2, 1),
        make_observation("col5", 2, 2),
        make_observation("col5", 7, 3),
    ]

    result = calculate_position_frequency(
        observations,
        "col5",
    )

    for digit in (0, 1, 3, 4, 5, 6, 8, 9):
        record = get_position_frequency_record(result, digit)

        assert record.count == 0
        assert record.percentage == 0.0


def test_position_frequency_isolated_to_requested_position():
    observations = [
        make_observation("col1", 5, 1),
        make_observation("col2", 5, 2),
        make_observation("col3", 7, 3),
        make_observation("col3", 7, 4),
    ]

    result = calculate_position_frequency(
        observations,
        "col3",
    )

    assert result.total_observations == 2
    assert get_position_frequency_record(result, 7).count == 2
    assert get_position_frequency_record(result, 5).count == 0


def test_all_position_frequencies_returns_all_eight_positions():
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

    results = calculate_all_position_frequencies(observations)

    assert list(results.keys()) == [
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    ]

    for position in results:
        assert isinstance(
            results[position],
            PositionFrequencyResult,
        )


def test_empty_observations_return_zero_frequency_distribution():
    result = calculate_position_frequency(
        [],
        "col6",
    )

    assert result.position == "col6"
    assert result.total_observations == 0
    assert len(result.records) == 10

    for record in result.records:
        assert record.count == 0
        assert record.percentage == 0.0


def test_invalid_position_is_rejected():
    with pytest.raises(ValueError):
        calculate_position_frequency(
            [],
            "invalid_column",
        )


def test_invalid_digit_lookup_is_rejected():
    result = calculate_position_frequency(
        [],
        "col7",
    )

    with pytest.raises(ValueError):
        get_position_frequency_record(result, -1)

    with pytest.raises(ValueError):
        get_position_frequency_record(result, 10)

    with pytest.raises(ValueError):
        get_position_frequency_record(result, True)


def test_position_frequency_result_is_immutable():
    result = calculate_position_frequency(
        [
            make_observation("col8", 4, 1),
        ],
        "col8",
    )

    with pytest.raises(AttributeError):
        result.position = "col1"