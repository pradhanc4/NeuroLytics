from __future__ import annotations

import pytest

from analytics.position_distribution import PositionDistribution
from analytics.position_distribution_change import (
    PositionDistributionChangeSummary,
    PositionDistributionDigitChange,
    calculate_position_distribution_digit_changes,
    summarize_position_distribution_change,
)


def make_distribution(
    position: str,
    percentages: tuple[float, ...],
    total_observations: int = 100,
) -> PositionDistribution:
    return PositionDistribution(
        position=position,
        total_observations=total_observations,
        percentages=percentages,
    )


def test_identical_distributions_have_no_changes() -> None:
    distribution = make_distribution(
        position="col1",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    result = calculate_position_distribution_digit_changes(
        position="col1",
        distribution_a=distribution,
        distribution_b=distribution,
    )

    assert len(result) == 10
    assert all(change.direction == "unchanged" for change in result)
    assert all(change.absolute_change == 0.0 for change in result)


def test_increased_digit_is_detected() -> None:
    distribution_a = make_distribution(
        position="col1",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col1",
        percentages=(
            20.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            0.0,
        ),
    )

    result = calculate_position_distribution_digit_changes(
        position="col1",
        distribution_a=distribution_a,
        distribution_b=distribution_b,
    )

    assert result[0].digit == 0
    assert result[0].percentage_a == 10.0
    assert result[0].percentage_b == 20.0
    assert result[0].absolute_change == 10.0
    assert result[0].direction == "increased"


def test_decreased_digit_is_detected() -> None:
    distribution_a = make_distribution(
        position="col2",
        percentages=(
            20.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            0.0,
        ),
    )

    distribution_b = make_distribution(
        position="col2",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    result = calculate_position_distribution_digit_changes(
        position="col2",
        distribution_a=distribution_a,
        distribution_b=distribution_b,
    )

    assert result[0].digit == 0
    assert result[0].percentage_a == 20.0
    assert result[0].percentage_b == 10.0
    assert result[0].absolute_change == 10.0
    assert result[0].direction == "decreased"


def test_all_ten_digits_are_returned_in_order() -> None:
    distribution_a = make_distribution(
        position="col3",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col3",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    result = calculate_position_distribution_digit_changes(
        position="col3",
        distribution_a=distribution_a,
        distribution_b=distribution_b,
    )

    assert tuple(change.digit for change in result) == tuple(range(10))


def test_position_name_is_preserved() -> None:
    distribution_a = make_distribution(
        position="col4",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col4",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    result = calculate_position_distribution_digit_changes(
        position="col4",
        distribution_a=distribution_a,
        distribution_b=distribution_b,
    )

    assert all(change.position == "col4" for change in result)


def test_summary_counts_increased_decreased_and_unchanged_digits() -> None:
    distribution_a = make_distribution(
        position="col5",
        percentages=(
            10.0,
            20.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            0.0,
            0.0,
        ),
    )

    distribution_b = make_distribution(
        position="col5",
        percentages=(
            20.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            5.0,
            5.0,
        ),
    )

    result = summarize_position_distribution_change(
        position="col5",
        distribution_a=distribution_a,
        distribution_b=distribution_b,
    )

    assert isinstance(result, PositionDistributionChangeSummary)
    assert result.position == "col5"
    assert result.increased_digits == 3
    assert result.decreased_digits == 1
    assert result.unchanged_digits == 6


def test_summary_calculates_total_and_mean_absolute_change() -> None:
    distribution_a = make_distribution(
        position="col6",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col6",
        percentages=(
            20.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            0.0,
        ),
    )

    result = summarize_position_distribution_change(
        position="col6",
        distribution_a=distribution_a,
        distribution_b=distribution_b,
    )

    assert result.total_absolute_change == pytest.approx(20.0)
    assert result.mean_absolute_change == pytest.approx(2.0)


def test_summary_contains_all_digit_changes() -> None:
    distribution_a = make_distribution(
        position="col7",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col7",
        percentages=(
            20.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            0.0,
        ),
    )

    result = summarize_position_distribution_change(
        position="col7",
        distribution_a=distribution_a,
        distribution_b=distribution_b,
    )

    assert len(result.changes) == 10
    assert all(
        isinstance(change, PositionDistributionDigitChange)
        for change in result.changes
    )


def test_first_distribution_position_mismatch_is_rejected() -> None:
    distribution_a = make_distribution(
        position="col2",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col1",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    with pytest.raises(ValueError, match="Distribution position"):
        calculate_position_distribution_digit_changes(
            position="col1",
            distribution_a=distribution_a,
            distribution_b=distribution_b,
        )


def test_second_distribution_position_mismatch_is_rejected() -> None:
    distribution_a = make_distribution(
        position="col1",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    distribution_b = make_distribution(
        position="col2",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    with pytest.raises(ValueError, match="Distribution position"):
        summarize_position_distribution_change(
            position="col1",
            distribution_a=distribution_a,
            distribution_b=distribution_b,
        )


def test_invalid_percentage_length_is_rejected() -> None:
    distribution_a = PositionDistribution(
        position="col1",
        total_observations=100,
        percentages=(10.0, 10.0, 10.0),
    )

    distribution_b = make_distribution(
        position="col1",
        percentages=(
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
            10.0,
        ),
    )

    with pytest.raises(ValueError, match="exactly 10"):
        calculate_position_distribution_digit_changes(
            position="col1",
            distribution_a=distribution_a,
            distribution_b=distribution_b,
        )