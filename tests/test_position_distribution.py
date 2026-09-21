from datetime import date

import pytest

from analytics.position_distribution import (
    PositionDistribution,
    build_position_distribution,
    build_position_distribution_matrix,
    get_digit_percentage,
)
from analytics.position_frequency import (
    PositionFrequencyResult,
    calculate_position_frequency,
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


def test_build_position_distribution_preserves_digit_order():
    observations = [
        make_observation("col1", 0, 1),
        make_observation("col1", 1, 2),
        make_observation("col1", 1, 3),
        make_observation("col1", 2, 4),
        make_observation("col1", 2, 5),
        make_observation("col1", 2, 6),
    ]

    result = calculate_position_frequency(
        observations,
        "col1",
    )

    distribution = build_position_distribution(result)

    assert distribution.position == "col1"
    assert distribution.total_observations == 6
    assert len(distribution.percentages) == 10

    assert distribution.percentages[0] == pytest.approx(16.6666666667)
    assert distribution.percentages[1] == pytest.approx(33.3333333333)
    assert distribution.percentages[2] == pytest.approx(50.0)


def test_unused_digits_have_zero_percentage():
    observations = [
        make_observation("col2", 4, 1),
        make_observation("col2", 4, 2),
    ]

    result = calculate_position_frequency(
        observations,
        "col2",
    )

    distribution = build_position_distribution(result)

    for digit in (0, 1, 2, 3, 5, 6, 7, 8, 9):
        assert get_digit_percentage(
            distribution,
            digit,
        ) == pytest.approx(0.0)


def test_actual_zero_is_preserved():
    observations = [
        make_observation("col3", 0, 1),
        make_observation("col3", 0, 2),
        make_observation("col3", 5, 3),
    ]

    result = calculate_position_frequency(
        observations,
        "col3",
    )

    distribution = build_position_distribution(result)

    assert get_digit_percentage(
        distribution,
        0,
    ) == pytest.approx(66.6666666667)

    assert get_digit_percentage(
        distribution,
        5,
    ) == pytest.approx(33.3333333333)


def test_total_observations_are_preserved():
    observations = [
        make_observation("col4", 1, 1),
        make_observation("col4", 2, 2),
        make_observation("col4", 3, 3),
    ]

    result = calculate_position_frequency(
        observations,
        "col4",
    )

    distribution = build_position_distribution(result)

    assert distribution.total_observations == 3


def test_digit_percentage_lookup_returns_correct_value():
    observations = [
        make_observation("col5", 7, 1),
        make_observation("col5", 7, 2),
        make_observation("col5", 2, 3),
        make_observation("col5", 4, 4),
    ]

    result = calculate_position_frequency(
        observations,
        "col5",
    )

    distribution = build_position_distribution(result)

    assert get_digit_percentage(
        distribution,
        7,
    ) == pytest.approx(50.0)

    assert get_digit_percentage(
        distribution,
        2,
    ) == pytest.approx(25.0)

    assert get_digit_percentage(
        distribution,
        4,
    ) == pytest.approx(25.0)


def test_invalid_digit_is_rejected():
    result = calculate_position_frequency(
        [],
        "col6",
    )

    distribution = build_position_distribution(result)

    with pytest.raises(ValueError):
        get_digit_percentage(distribution, -1)

    with pytest.raises(ValueError):
        get_digit_percentage(distribution, 10)

    with pytest.raises(ValueError):
        get_digit_percentage(distribution, True)


def test_distribution_matrix_contains_all_positions():
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

    results = {
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

    matrix = build_position_distribution_matrix(results)

    assert len(matrix) == 8
    assert [row.position for row in matrix] == [
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    ]

    for row in matrix:
        assert isinstance(row, PositionDistribution)
        assert len(row.percentages) == 10


def test_empty_position_produces_zero_distribution():
    result = calculate_position_frequency(
        [],
        "col7",
    )

    distribution = build_position_distribution(result)

    assert distribution.position == "col7"
    assert distribution.total_observations == 0
    assert distribution.percentages == (0.0,) * 10


def test_incomplete_frequency_result_is_rejected():
    result = PositionFrequencyResult(
        position="col8",
        total_observations=1,
        records=(),
    )

    with pytest.raises(ValueError):
        build_position_distribution(result)


def test_duplicate_digit_records_are_rejected():
    result = PositionFrequencyResult(
        position="col8",
        total_observations=2,
        records=(
            *calculate_position_frequency(
                [
                    make_observation("col8", 1, 1),
                    make_observation("col8", 2, 2),
                ],
                "col8",
            ).records[:-1],
            calculate_position_frequency(
                [
                    make_observation("col8", 1, 1),
                ],
                "col8",
            ).records[1],
        ),
    )

    with pytest.raises(ValueError):
        build_position_distribution(result)


def test_position_distribution_is_immutable():
    result = calculate_position_frequency(
        [
            make_observation("col1", 5, 1),
        ],
        "col1",
    )

    distribution = build_position_distribution(result)

    with pytest.raises(AttributeError):
        distribution.position = "col2"
