from datetime import date

import pytest

from analytics.frequency_analysis import (
    FrequencyAnalysisResult,
    FrequencyRecord,
    calculate_all_column_frequencies,
    calculate_frequency,
    get_frequency_record,
)
from analytics.statistical_foundation import StatisticalObservation


def observation(
    column_name: str,
    value: int,
    day: int,
) -> StatisticalObservation:
    return StatisticalObservation(
        record_date=date(2026, 1, day),
        column_name=column_name,
        value=value,
    )


def test_frequency_counts_digits_correctly():
    observations = [
        observation("col1", 1, 1),
        observation("col1", 2, 2),
        observation("col1", 1, 3),
        observation("col1", 5, 4),
        observation("col1", 1, 5),
    ]

    result = calculate_frequency(
        observations,
        "col1",
    )

    assert result.column_name == "col1"
    assert result.total_observations == 5

    assert get_frequency_record(result, 1).count == 3
    assert get_frequency_record(result, 2).count == 1
    assert get_frequency_record(result, 5).count == 1


def test_frequency_percentage_is_calculated():
    observations = [
        observation("col1", 1, 1),
        observation("col1", 1, 2),
        observation("col1", 2, 3),
        observation("col1", 3, 4),
    ]

    result = calculate_frequency(
        observations,
        "col1",
    )

    assert get_frequency_record(result, 1).percentage == pytest.approx(
        50.0
    )

    assert get_frequency_record(result, 2).percentage == pytest.approx(
        25.0
    )


def test_zero_is_counted_as_a_real_observation():
    observations = [
        observation("col1", 0, 1),
        observation("col1", 0, 2),
        observation("col1", 1, 3),
    ]

    result = calculate_frequency(
        observations,
        "col1",
    )

    zero_record = get_frequency_record(result, 0)

    assert zero_record.count == 2
    assert zero_record.percentage == pytest.approx(
        66.6666666667
    )


def test_all_digits_are_present_even_when_unused():
    observations = [
        observation("col1", 2, 1),
    ]

    result = calculate_frequency(
        observations,
        "col1",
    )

    assert len(result.records) == 10

    for digit in range(10):
        assert get_frequency_record(result, digit).digit == digit


def test_unused_digit_has_zero_count():
    observations = [
        observation("col1", 2, 1),
    ]

    result = calculate_frequency(
        observations,
        "col1",
    )

    assert get_frequency_record(result, 0).count == 0
    assert get_frequency_record(result, 9).count == 0


def test_only_requested_column_is_analyzed():
    observations = [
        observation("col1", 1, 1),
        observation("col1", 1, 2),
        observation("col2", 9, 3),
        observation("col2", 9, 4),
    ]

    result = calculate_frequency(
        observations,
        "col1",
    )

    assert result.total_observations == 2
    assert get_frequency_record(result, 1).count == 2
    assert get_frequency_record(result, 9).count == 0


def test_all_column_frequencies_are_calculated():
    observations = [
        observation("col1", 1, 1),
        observation("col2", 2, 2),
        observation("col3", 3, 3),
        observation("col4", 4, 4),
        observation("col5", 5, 5),
        observation("col6", 6, 6),
        observation("col7", 7, 7),
        observation("col8", 8, 8),
    ]

    results = calculate_all_column_frequencies(
        observations
    )

    assert set(results.keys()) == {
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    }

    for column_name, result in results.items():
        assert isinstance(
            result,
            FrequencyAnalysisResult,
        )
        assert result.column_name == column_name
        assert result.total_observations == 1


def test_empty_observations_are_supported():
    result = calculate_frequency(
        [],
        "col1",
    )

    assert result.total_observations == 0
    assert len(result.records) == 10

    for record in result.records:
        assert record.count == 0
        assert record.percentage == 0.0


def test_invalid_column_is_rejected():
    observations = [
        observation("col1", 1, 1),
    ]

    with pytest.raises(ValueError, match="Unsupported"):
        calculate_frequency(
            observations,
            "open_result",
        )


def test_invalid_digit_lookup_is_rejected():
    result = calculate_frequency(
        [],
        "col1",
    )

    with pytest.raises(ValueError, match="between 0 and 9"):
        get_frequency_record(result, 10)


def test_frequency_records_are_immutable():
    record = FrequencyRecord(
        digit=1,
        count=5,
        percentage=50.0,
    )

    with pytest.raises(AttributeError):
        record.count = 10