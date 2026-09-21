from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution_trend_strength import (
    PositionDistributionTrendStrength,
)
from analytics.position_distribution_trend_strength_summary import (
    PositionDistributionTrendStrengthSummary,
    summarize_all_position_distribution_trend_strength,
    summarize_position_distribution_trend_strength,
)


def make_result(
    position: str,
    digit: int,
    strength: str,
    trend_direction: str,
    absolute_total_change: float,
    mean_absolute_change: float,
) -> PositionDistributionTrendStrength:
    return PositionDistributionTrendStrength(
        position=position,
        digit=digit,
        window_count=4,
        change_count=3,
        total_change=absolute_total_change,
        mean_change=mean_absolute_change,
        absolute_total_change=absolute_total_change,
        mean_absolute_change=mean_absolute_change,
        trend_direction=trend_direction,
        strength=strength,
    )


def test_empty_results_return_zero_summary() -> None:
    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=(),
    )

    assert result.position == "col1"
    assert result.digit_count == 0
    assert result.low_count == 0
    assert result.medium_count == 0
    assert result.high_count == 0
    assert result.increasing_count == 0
    assert result.decreasing_count == 0
    assert result.mixed_count == 0
    assert result.unchanged_count == 0
    assert result.total_absolute_change == 0.0
    assert result.average_mean_absolute_change == 0.0
    assert result.strength_results == ()


def test_strength_counts_are_calculated() -> None:
    results = (
        make_result(
            "col1",
            0,
            "LOW",
            "INCREASING",
            1.0,
            0.5,
        ),
        make_result(
            "col1",
            1,
            "MEDIUM",
            "DECREASING",
            6.0,
            3.0,
        ),
        make_result(
            "col1",
            2,
            "HIGH",
            "MIXED",
            15.0,
            7.5,
        ),
        make_result(
            "col1",
            3,
            "HIGH",
            "UNCHANGED",
            0.0,
            0.0,
        ),
    )

    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=results,
    )

    assert result.low_count == 1
    assert result.medium_count == 1
    assert result.high_count == 2


def test_direction_counts_are_calculated() -> None:
    results = (
        make_result(
            "col1",
            0,
            "LOW",
            "INCREASING",
            2.0,
            1.0,
        ),
        make_result(
            "col1",
            1,
            "MEDIUM",
            "INCREASING",
            4.0,
            2.0,
        ),
        make_result(
            "col1",
            2,
            "HIGH",
            "DECREASING",
            8.0,
            4.0,
        ),
        make_result(
            "col1",
            3,
            "HIGH",
            "MIXED",
            10.0,
            5.0,
        ),
        make_result(
            "col1",
            4,
            "LOW",
            "UNCHANGED",
            0.0,
            0.0,
        ),
    )

    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=results,
    )

    assert result.increasing_count == 2
    assert result.decreasing_count == 1
    assert result.mixed_count == 1
    assert result.unchanged_count == 1


def test_total_absolute_change_is_calculated() -> None:
    results = (
        make_result(
            "col1",
            0,
            "LOW",
            "INCREASING",
            2.0,
            1.0,
        ),
        make_result(
            "col1",
            1,
            "MEDIUM",
            "DECREASING",
            6.0,
            3.0,
        ),
        make_result(
            "col1",
            2,
            "HIGH",
            "MIXED",
            12.0,
            6.0,
        ),
    )

    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=results,
    )

    assert result.total_absolute_change == 20.0


def test_average_mean_absolute_change_is_calculated() -> None:
    results = (
        make_result(
            "col1",
            0,
            "LOW",
            "INCREASING",
            2.0,
            1.0,
        ),
        make_result(
            "col1",
            1,
            "MEDIUM",
            "DECREASING",
            6.0,
            3.0,
        ),
        make_result(
            "col1",
            2,
            "HIGH",
            "MIXED",
            12.0,
            6.0,
        ),
    )

    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=results,
    )

    assert result.average_mean_absolute_change == pytest.approx(
        10.0 / 3.0
    )


def test_digit_count_matches_input() -> None:
    results = (
        make_result(
            "col1",
            0,
            "LOW",
            "INCREASING",
            2.0,
            1.0,
        ),
        make_result(
            "col1",
            1,
            "MEDIUM",
            "DECREASING",
            4.0,
            2.0,
        ),
    )

    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=results,
    )

    assert result.digit_count == 2


def test_original_strength_results_are_preserved() -> None:
    results = (
        make_result(
            "col1",
            0,
            "LOW",
            "INCREASING",
            2.0,
            1.0,
        ),
        make_result(
            "col1",
            1,
            "HIGH",
            "DECREASING",
            8.0,
            4.0,
        ),
    )

    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=results,
    )

    assert result.strength_results == results


def test_position_is_preserved() -> None:
    results = (
        make_result(
            "col8",
            0,
            "HIGH",
            "INCREASING",
            10.0,
            5.0,
        ),
    )

    result = summarize_position_distribution_trend_strength(
        position="col8",
        results=results,
    )

    assert result.position == "col8"


def test_zero_digit_is_valid() -> None:
    results = (
        make_result(
            "col1",
            0,
            "LOW",
            "UNCHANGED",
            0.0,
            0.0,
        ),
    )

    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=results,
    )

    assert result.digit_count == 1
    assert result.strength_results[0].digit == 0


def test_digit_nine_is_valid() -> None:
    results = (
        make_result(
            "col1",
            9,
            "HIGH",
            "INCREASING",
            10.0,
            5.0,
        ),
    )

    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=results,
    )

    assert result.strength_results[0].digit == 9
    assert result.high_count == 1


def test_position_mismatch_is_rejected() -> None:
    results = (
        make_result(
            "col2",
            0,
            "LOW",
            "INCREASING",
            2.0,
            1.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="All trend strength results must belong",
    ):
        summarize_position_distribution_trend_strength(
            position="col1",
            results=results,
        )


def test_invalid_digit_is_rejected() -> None:
    results = (
        make_result(
            "col1",
            10,
            "LOW",
            "INCREASING",
            2.0,
            1.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        summarize_position_distribution_trend_strength(
            position="col1",
            results=results,
        )


def test_negative_digit_is_rejected() -> None:
    results = (
        make_result(
            "col1",
            -1,
            "LOW",
            "INCREASING",
            2.0,
            1.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Digit must be between 0 and 9",
    ):
        summarize_position_distribution_trend_strength(
            position="col1",
            results=results,
        )


def test_all_position_results_are_supported() -> None:
    results = tuple(
        make_result(
            "col1",
            digit,
            "LOW",
            "UNCHANGED",
            0.0,
            0.0,
        )
        for digit in range(10)
    )

    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=results,
    )

    assert result.digit_count == 10
    assert result.low_count == 10
    assert result.unchanged_count == 10


def test_all_position_summary_detects_position() -> None:
    results = (
        make_result(
            "col5",
            0,
            "MEDIUM",
            "INCREASING",
            4.0,
            2.0,
        ),
        make_result(
            "col5",
            1,
            "HIGH",
            "DECREASING",
            8.0,
            4.0,
        ),
    )

    result = summarize_all_position_distribution_trend_strength(
        results=results,
    )

    assert result.position == "col5"
    assert result.digit_count == 2
    assert result.medium_count == 1
    assert result.high_count == 1


def test_all_position_summary_empty_input() -> None:
    result = summarize_all_position_distribution_trend_strength(
        results=(),
    )

    assert result.position == ""
    assert result.digit_count == 0
    assert result.strength_results == ()


def test_all_position_summary_rejects_multiple_positions() -> None:
    results = (
        make_result(
            "col1",
            0,
            "LOW",
            "INCREASING",
            2.0,
            1.0,
        ),
        make_result(
            "col2",
            1,
            "HIGH",
            "DECREASING",
            8.0,
            4.0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="All trend strength results must belong",
    ):
        summarize_all_position_distribution_trend_strength(
            results=results,
        )


def test_result_has_correct_dataclass_type() -> None:
    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=(),
    )

    assert isinstance(
        result,
        PositionDistributionTrendStrengthSummary,
    )


def test_summary_dataclass_is_frozen() -> None:
    result = summarize_position_distribution_trend_strength(
        position="col1",
        results=(),
    )

    with pytest.raises(FrozenInstanceError):
        result.position = "col2"