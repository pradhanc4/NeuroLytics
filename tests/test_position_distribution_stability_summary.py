from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution_stability_summary import (
    PositionDistributionStabilitySummary,
    summarize_all_position_distribution_stability,
    summarize_position_distribution_stability,
)
from analytics.position_distribution_volatility import (
    PositionDistributionVolatility,
)


def make_result(
    position="col1",
    digit=0,
    mean_absolute_change=1.0,
    total_absolute_change=3.0,
):
    return PositionDistributionVolatility(
        position=position,
        digit=digit,
        window_count=4,
        change_count=3,
        total_absolute_change=total_absolute_change,
        mean_absolute_change=mean_absolute_change,
        maximum_absolute_change=2.0,
        minimum_absolute_change=0.5,
        volatility_level="LOW",
    )


def test_empty_results_return_empty_summary():
    result = summarize_position_distribution_stability(
        position="col1",
        results=(),
    )

    assert result.position == "col1"
    assert result.digit_count == 0
    assert result.stable_digit_count == 0
    assert result.moderate_digit_count == 0
    assert result.unstable_digit_count == 0
    assert result.total_absolute_change == 0.0
    assert result.average_mean_absolute_change == 0.0
    assert result.stability_results == ()


def test_stable_digit_is_classified_below_low_threshold():
    result = summarize_position_distribution_stability(
        position="col1",
        results=(
            make_result(
                digit=0,
                mean_absolute_change=1.99,
            ),
        ),
    )

    assert result.stable_digit_count == 1
    assert result.moderate_digit_count == 0
    assert result.unstable_digit_count == 0


def test_low_threshold_boundary_is_moderate():
    result = summarize_position_distribution_stability(
        position="col1",
        results=(
            make_result(
                digit=0,
                mean_absolute_change=2.0,
            ),
        ),
    )

    assert result.stable_digit_count == 0
    assert result.moderate_digit_count == 1
    assert result.unstable_digit_count == 0


def test_moderate_digit_is_below_high_threshold():
    result = summarize_position_distribution_stability(
        position="col1",
        results=(
            make_result(
                digit=0,
                mean_absolute_change=4.99,
            ),
        ),
    )

    assert result.stable_digit_count == 0
    assert result.moderate_digit_count == 1
    assert result.unstable_digit_count == 0


def test_high_threshold_boundary_is_unstable():
    result = summarize_position_distribution_stability(
        position="col1",
        results=(
            make_result(
                digit=0,
                mean_absolute_change=5.0,
            ),
        ),
    )

    assert result.stable_digit_count == 0
    assert result.moderate_digit_count == 0
    assert result.unstable_digit_count == 1


def test_counts_multiple_stability_categories():
    results = (
        make_result(digit=0, mean_absolute_change=1.0),
        make_result(digit=1, mean_absolute_change=2.5),
        make_result(digit=2, mean_absolute_change=6.0),
    )

    result = summarize_position_distribution_stability(
        position="col1",
        results=results,
    )

    assert result.digit_count == 3
    assert result.stable_digit_count == 1
    assert result.moderate_digit_count == 1
    assert result.unstable_digit_count == 1


def test_stability_counts_sum_to_digit_count():
    results = (
        make_result(digit=0, mean_absolute_change=1.0),
        make_result(digit=1, mean_absolute_change=2.0),
        make_result(digit=2, mean_absolute_change=5.0),
        make_result(digit=3, mean_absolute_change=1.5),
    )

    result = summarize_position_distribution_stability(
        position="col1",
        results=results,
    )

    total_classified = (
        result.stable_digit_count
        + result.moderate_digit_count
        + result.unstable_digit_count
    )

    assert total_classified == result.digit_count


def test_total_absolute_change_is_summed():
    results = (
        make_result(
            digit=0,
            total_absolute_change=5.0,
        ),
        make_result(
            digit=1,
            total_absolute_change=7.5,
        ),
        make_result(
            digit=2,
            total_absolute_change=2.5,
        ),
    )

    result = summarize_position_distribution_stability(
        position="col1",
        results=results,
    )

    assert result.total_absolute_change == 15.0


def test_average_mean_absolute_change_is_calculated():
    results = (
        make_result(
            digit=0,
            mean_absolute_change=1.0,
        ),
        make_result(
            digit=1,
            mean_absolute_change=3.0,
        ),
        make_result(
            digit=2,
            mean_absolute_change=5.0,
        ),
    )

    result = summarize_position_distribution_stability(
        position="col1",
        results=results,
    )

    assert result.average_mean_absolute_change == 3.0


def test_decimal_average_mean_absolute_change():
    results = (
        make_result(
            digit=0,
            mean_absolute_change=1.0,
        ),
        make_result(
            digit=1,
            mean_absolute_change=2.0,
        ),
        make_result(
            digit=2,
            mean_absolute_change=4.0,
        ),
    )

    result = summarize_position_distribution_stability(
        position="col1",
        results=results,
    )

    assert result.average_mean_absolute_change == pytest.approx(7 / 3)


def test_all_digits_zero_to_nine_are_supported():
    results = tuple(
        make_result(
            digit=digit,
            mean_absolute_change=1.0,
        )
        for digit in range(10)
    )

    result = summarize_position_distribution_stability(
        position="col1",
        results=results,
    )

    assert result.digit_count == 10
    assert result.stable_digit_count == 10
    assert result.moderate_digit_count == 0
    assert result.unstable_digit_count == 0


def test_results_are_preserved_in_original_order():
    results = (
        make_result(digit=7),
        make_result(digit=2),
        make_result(digit=9),
    )

    result = summarize_position_distribution_stability(
        position="col1",
        results=results,
    )

    assert result.stability_results == results


def test_position_is_preserved():
    result = summarize_position_distribution_stability(
        position="col5",
        results=(
            make_result(
                position="col5",
                digit=3,
            ),
        ),
    )

    assert result.position == "col5"


def test_mismatched_position_is_rejected():
    results = (
        make_result(
            position="col2",
            digit=0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Volatility result position does not match",
    ):
        summarize_position_distribution_stability(
            position="col1",
            results=results,
        )


def test_negative_digit_is_rejected():
    results = (
        make_result(
            digit=-1,
        ),
    )

    with pytest.raises(
        ValueError,
        match="digit must be between 0 and 9",
    ):
        summarize_position_distribution_stability(
            position="col1",
            results=results,
        )


def test_digit_above_nine_is_rejected():
    results = (
        make_result(
            digit=10,
        ),
    )

    with pytest.raises(
        ValueError,
        match="digit must be between 0 and 9",
    ):
        summarize_position_distribution_stability(
            position="col1",
            results=results,
        )


def test_negative_low_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="Low threshold must be greater than or equal to zero",
    ):
        summarize_position_distribution_stability(
            position="col1",
            results=(),
            low_threshold=-1.0,
        )


def test_high_threshold_below_low_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="High threshold must be greater than or equal to",
    ):
        summarize_position_distribution_stability(
            position="col1",
            results=(),
            low_threshold=5.0,
            high_threshold=2.0,
        )


def test_custom_thresholds_are_supported():
    result = summarize_position_distribution_stability(
        position="col1",
        results=(
            make_result(
                digit=0,
                mean_absolute_change=3.0,
            ),
            make_result(
                digit=1,
                mean_absolute_change=6.0,
            ),
            make_result(
                digit=2,
                mean_absolute_change=9.0,
            ),
        ),
        low_threshold=4.0,
        high_threshold=8.0,
    )

    assert result.stable_digit_count == 1
    assert result.moderate_digit_count == 1
    assert result.unstable_digit_count == 1


def test_all_position_stability_returns_summary():
    results = (
        make_result(
            position="col3",
            digit=0,
            mean_absolute_change=1.0,
        ),
        make_result(
            position="col3",
            digit=1,
            mean_absolute_change=6.0,
        ),
    )

    result = summarize_all_position_distribution_stability(
        results=results,
    )

    assert result.position == "col3"
    assert result.digit_count == 2
    assert result.stable_digit_count == 1
    assert result.unstable_digit_count == 1


def test_all_position_stability_detects_single_position():
    results = (
        make_result(
            position="col7",
            digit=0,
        ),
    )

    result = summarize_all_position_distribution_stability(
        results=results,
    )

    assert result.position == "col7"


def test_all_position_stability_rejects_multiple_positions():
    results = (
        make_result(
            position="col1",
            digit=0,
        ),
        make_result(
            position="col2",
            digit=1,
        ),
    )

    with pytest.raises(
        ValueError,
        match="same position",
    ):
        summarize_all_position_distribution_stability(
            results=results,
        )


def test_all_position_stability_empty_results():
    result = summarize_all_position_distribution_stability(
        results=(),
    )

    assert result.position == ""
    assert result.digit_count == 0
    assert result.stable_digit_count == 0
    assert result.moderate_digit_count == 0
    assert result.unstable_digit_count == 0
    assert result.total_absolute_change == 0.0
    assert result.average_mean_absolute_change == 0.0
    assert result.stability_results == ()


def test_all_position_stability_preserves_results():
    results = (
        make_result(
            position="col4",
            digit=2,
        ),
        make_result(
            position="col4",
            digit=8,
        ),
    )

    result = summarize_all_position_distribution_stability(
        results=results,
    )

    assert result.stability_results == results


def test_summary_is_frozen():
    result = summarize_position_distribution_stability(
        position="col1",
        results=(
            make_result(
                digit=0,
            ),
        ),
    )

    with pytest.raises(FrozenInstanceError):
        result.position = "col2"


def test_digit_count_matches_input_length():
    results = tuple(
        make_result(digit=digit)
        for digit in range(6)
    )

    result = summarize_position_distribution_stability(
        position="col1",
        results=results,
    )

    assert result.digit_count == len(results)