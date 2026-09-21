from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution_volatility import (
    PositionDistributionVolatility,
)
from analytics.position_distribution_volatility_summary import (
    PositionDistributionVolatilitySummary,
    summarize_all_position_distribution_volatility,
    summarize_position_distribution_volatility,
)


def make_result(
    position: str,
    digit: int,
    total_absolute_change: float,
    mean_absolute_change: float,
    volatility_level: str,
) -> PositionDistributionVolatility:
    return PositionDistributionVolatility(
        position=position,
        digit=digit,
        window_count=3,
        change_count=2,
        total_absolute_change=total_absolute_change,
        mean_absolute_change=mean_absolute_change,
        maximum_absolute_change=mean_absolute_change,
        minimum_absolute_change=mean_absolute_change,
        volatility_level=volatility_level,
    )


def test_empty_results_return_zero_summary():
    result = summarize_position_distribution_volatility(
        position="col1",
        results=(),
    )

    assert result.position == "col1"
    assert result.digit_count == 0
    assert result.low_count == 0
    assert result.medium_count == 0
    assert result.high_count == 0
    assert result.total_absolute_change == 0.0
    assert result.average_mean_absolute_change == 0.0
    assert result.volatility_results == ()


def test_low_medium_high_counts():
    results = (
        make_result("col1", 0, 1.0, 0.5, "LOW"),
        make_result("col1", 1, 3.0, 3.0, "MEDIUM"),
        make_result("col1", 2, 6.0, 6.0, "HIGH"),
    )

    result = summarize_position_distribution_volatility(
        position="col1",
        results=results,
    )

    assert result.digit_count == 3
    assert result.low_count == 1
    assert result.medium_count == 1
    assert result.high_count == 1


def test_total_absolute_change_is_summed():
    results = (
        make_result("col1", 0, 2.0, 1.0, "LOW"),
        make_result("col1", 1, 5.0, 2.5, "MEDIUM"),
        make_result("col1", 2, 8.0, 4.0, "MEDIUM"),
    )

    result = summarize_position_distribution_volatility(
        position="col1",
        results=results,
    )

    assert result.total_absolute_change == 15.0


def test_average_mean_absolute_change_is_calculated():
    results = (
        make_result("col1", 0, 2.0, 1.0, "LOW"),
        make_result("col1", 1, 6.0, 3.0, "MEDIUM"),
        make_result("col1", 2, 12.0, 6.0, "HIGH"),
    )

    result = summarize_position_distribution_volatility(
        position="col1",
        results=results,
    )

    assert result.average_mean_absolute_change == 10 / 3


def test_all_low_results_are_counted():
    results = tuple(
        make_result(
            "col1",
            digit,
            1.0,
            1.0,
            "LOW",
        )
        for digit in range(10)
    )

    result = summarize_position_distribution_volatility(
        position="col1",
        results=results,
    )

    assert result.digit_count == 10
    assert result.low_count == 10
    assert result.medium_count == 0
    assert result.high_count == 0


def test_all_medium_results_are_counted():
    results = tuple(
        make_result(
            "col1",
            digit,
            3.0,
            3.0,
            "MEDIUM",
        )
        for digit in range(10)
    )

    result = summarize_position_distribution_volatility(
        position="col1",
        results=results,
    )

    assert result.digit_count == 10
    assert result.low_count == 0
    assert result.medium_count == 10
    assert result.high_count == 0


def test_all_high_results_are_counted():
    results = tuple(
        make_result(
            "col1",
            digit,
            6.0,
            6.0,
            "HIGH",
        )
        for digit in range(10)
    )

    result = summarize_position_distribution_volatility(
        position="col1",
        results=results,
    )

    assert result.digit_count == 10
    assert result.low_count == 0
    assert result.medium_count == 0
    assert result.high_count == 10


def test_all_digits_are_preserved():
    results = tuple(
        make_result(
            "col1",
            digit,
            float(digit),
            float(digit),
            "LOW",
        )
        for digit in range(10)
    )

    result = summarize_position_distribution_volatility(
        position="col1",
        results=results,
    )

    assert tuple(
        item.digit
        for item in result.volatility_results
    ) == tuple(range(10))


def test_individual_results_are_preserved():
    results = (
        make_result("col1", 0, 2.0, 1.0, "LOW"),
        make_result("col1", 1, 4.0, 4.0, "MEDIUM"),
    )

    result = summarize_position_distribution_volatility(
        position="col1",
        results=results,
    )

    assert result.volatility_results == results


def test_position_is_preserved():
    results = (
        make_result("col7", 0, 2.0, 1.0, "LOW"),
    )

    result = summarize_position_distribution_volatility(
        position="col7",
        results=results,
    )

    assert result.position == "col7"


def test_position_mismatch_is_rejected():
    results = (
        make_result("col2", 0, 2.0, 1.0, "LOW"),
    )

    with pytest.raises(ValueError, match="does not match"):
        summarize_position_distribution_volatility(
            position="col1",
            results=results,
        )


def test_invalid_digit_is_rejected():
    results = (
        make_result("col1", 10, 2.0, 1.0, "LOW"),
    )

    with pytest.raises(ValueError, match="between 0 and 9"):
        summarize_position_distribution_volatility(
            position="col1",
            results=results,
        )


def test_negative_digit_is_rejected():
    results = (
        make_result("col1", -1, 2.0, 1.0, "LOW"),
    )

    with pytest.raises(ValueError, match="between 0 and 9"):
        summarize_position_distribution_volatility(
            position="col1",
            results=results,
        )


def test_multiple_positions_are_rejected_by_all_position_summary():
    results = (
        make_result("col1", 0, 2.0, 1.0, "LOW"),
        make_result("col2", 1, 4.0, 4.0, "MEDIUM"),
    )

    with pytest.raises(
        ValueError,
        match="same position",
    ):
        summarize_all_position_distribution_volatility(
            results,
        )


def test_all_position_summary_detects_position():
    results = (
        make_result("col4", 0, 2.0, 1.0, "LOW"),
        make_result("col4", 1, 6.0, 6.0, "HIGH"),
    )

    result = summarize_all_position_distribution_volatility(
        results,
    )

    assert result.position == "col4"
    assert result.digit_count == 2
    assert result.low_count == 1
    assert result.high_count == 1


def test_all_position_summary_empty_results():
    result = summarize_all_position_distribution_volatility(
        (),
    )

    assert result.position == ""
    assert result.digit_count == 0
    assert result.low_count == 0
    assert result.medium_count == 0
    assert result.high_count == 0
    assert result.total_absolute_change == 0.0
    assert result.average_mean_absolute_change == 0.0
    assert result.volatility_results == ()


def test_all_position_summary_preserves_results():
    results = (
        make_result("col3", 0, 2.0, 1.0, "LOW"),
        make_result("col3", 1, 6.0, 6.0, "HIGH"),
    )

    result = summarize_all_position_distribution_volatility(
        results,
    )

    assert result.volatility_results == results


def test_summary_is_frozen():
    result = PositionDistributionVolatilitySummary(
        position="col1",
        digit_count=1,
        low_count=1,
        medium_count=0,
        high_count=0,
        total_absolute_change=1.0,
        average_mean_absolute_change=1.0,
        volatility_results=(),
    )

    with pytest.raises(FrozenInstanceError):
        result.position = "col2"


def test_counts_sum_to_digit_count():
    results = (
        make_result("col1", 0, 1.0, 1.0, "LOW"),
        make_result("col1", 1, 3.0, 3.0, "MEDIUM"),
        make_result("col1", 2, 6.0, 6.0, "HIGH"),
        make_result("col1", 3, 1.0, 1.0, "LOW"),
    )

    result = summarize_position_distribution_volatility(
        position="col1",
        results=results,
    )

    assert (
        result.low_count
        + result.medium_count
        + result.high_count
        == result.digit_count
    )