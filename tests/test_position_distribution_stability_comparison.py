from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution_stability_comparison import (
    PositionDistributionStabilityComparison,
    compare_all_position_distribution_stability,
    compare_position_distribution_stability,
    get_position_distribution_stability_comparison,
)
from analytics.position_distribution_stability_summary import (
    PositionDistributionStabilitySummary,
)
from analytics.position_distribution_volatility import (
    PositionDistributionVolatility,
)


def make_volatility_result(
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


def make_summary(
    position="col1",
    stable_digit_count=6,
    moderate_digit_count=3,
    unstable_digit_count=1,
    total_absolute_change=20.0,
    average_mean_absolute_change=1.8,
    results=None,
):
    if results is None:
        results = tuple(
            make_volatility_result(
                position=position,
                digit=digit,
                mean_absolute_change=1.0,
            )
            for digit in range(
                stable_digit_count
                + moderate_digit_count
                + unstable_digit_count
            )
        )

    return PositionDistributionStabilitySummary(
        position=position,
        digit_count=len(results),
        stable_digit_count=stable_digit_count,
        moderate_digit_count=moderate_digit_count,
        unstable_digit_count=unstable_digit_count,
        total_absolute_change=total_absolute_change,
        average_mean_absolute_change=average_mean_absolute_change,
        stability_results=results,
    )


def test_stable_position_is_classified_correctly():
    summary = make_summary(
        average_mean_absolute_change=1.5,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.position == "col1"
    assert result.stability_level == "STABLE"


def test_low_threshold_boundary_is_moderate():
    summary = make_summary(
        average_mean_absolute_change=2.0,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.stability_level == "MODERATE"


def test_moderate_position_is_classified_correctly():
    summary = make_summary(
        average_mean_absolute_change=3.5,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.stability_level == "MODERATE"


def test_high_threshold_boundary_is_unstable():
    summary = make_summary(
        average_mean_absolute_change=5.0,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.stability_level == "UNSTABLE"


def test_unstable_position_is_classified_correctly():
    summary = make_summary(
        average_mean_absolute_change=8.0,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.stability_level == "UNSTABLE"


def test_summary_counts_are_preserved():
    summary = make_summary(
        stable_digit_count=5,
        moderate_digit_count=3,
        unstable_digit_count=2,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.digit_count == 10
    assert result.stable_digit_count == 5
    assert result.moderate_digit_count == 3
    assert result.unstable_digit_count == 2


def test_total_absolute_change_is_preserved():
    summary = make_summary(
        total_absolute_change=37.5,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.total_absolute_change == 37.5


def test_average_mean_absolute_change_is_preserved():
    summary = make_summary(
        average_mean_absolute_change=3.75,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.average_mean_absolute_change == 3.75


def test_minimum_mean_absolute_change_is_calculated():
    results = (
        make_volatility_result(
            digit=0,
            mean_absolute_change=1.2,
        ),
        make_volatility_result(
            digit=1,
            mean_absolute_change=3.5,
        ),
        make_volatility_result(
            digit=2,
            mean_absolute_change=0.8,
        ),
    )

    summary = make_summary(
        stable_digit_count=2,
        moderate_digit_count=1,
        unstable_digit_count=0,
        average_mean_absolute_change=1.8333333333,
        results=results,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.minimum_mean_absolute_change == 0.8


def test_maximum_mean_absolute_change_is_calculated():
    results = (
        make_volatility_result(
            digit=0,
            mean_absolute_change=1.2,
        ),
        make_volatility_result(
            digit=1,
            mean_absolute_change=3.5,
        ),
        make_volatility_result(
            digit=2,
            mean_absolute_change=6.8,
        ),
    )

    summary = make_summary(
        stable_digit_count=1,
        moderate_digit_count=1,
        unstable_digit_count=1,
        average_mean_absolute_change=3.8333333333,
        results=results,
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.maximum_mean_absolute_change == 6.8


def test_minimum_and_maximum_are_zero_for_empty_results():
    summary = PositionDistributionStabilitySummary(
        position="col1",
        digit_count=0,
        stable_digit_count=0,
        moderate_digit_count=0,
        unstable_digit_count=0,
        total_absolute_change=0.0,
        average_mean_absolute_change=0.0,
        stability_results=(),
    )

    result = compare_position_distribution_stability(
        summary=summary,
    )

    assert result.minimum_mean_absolute_change == 0.0
    assert result.maximum_mean_absolute_change == 0.0
    assert result.stability_level == "STABLE"


def test_empty_position_is_rejected():
    summary = make_summary(
        position="",
    )

    with pytest.raises(
        ValueError,
        match="Position must not be empty",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_negative_digit_count_is_rejected():
    summary = make_summary()
    summary = PositionDistributionStabilitySummary(
        position=summary.position,
        digit_count=-1,
        stable_digit_count=0,
        moderate_digit_count=0,
        unstable_digit_count=0,
        total_absolute_change=0.0,
        average_mean_absolute_change=0.0,
        stability_results=(),
    )

    with pytest.raises(
        ValueError,
        match="Digit count must be greater than or equal to zero",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_negative_stable_digit_count_is_rejected():
    summary = PositionDistributionStabilitySummary(
        position="col1",
        digit_count=0,
        stable_digit_count=-1,
        moderate_digit_count=1,
        unstable_digit_count=0,
        total_absolute_change=0.0,
        average_mean_absolute_change=0.0,
        stability_results=(),
    )

    with pytest.raises(
        ValueError,
        match="Stable digit count must be greater than or equal to zero",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_negative_moderate_digit_count_is_rejected():
    summary = PositionDistributionStabilitySummary(
        position="col1",
        digit_count=0,
        stable_digit_count=0,
        moderate_digit_count=-1,
        unstable_digit_count=1,
        total_absolute_change=0.0,
        average_mean_absolute_change=0.0,
        stability_results=(),
    )

    with pytest.raises(
        ValueError,
        match="Moderate digit count must be greater than or equal to zero",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_negative_unstable_digit_count_is_rejected():
    summary = PositionDistributionStabilitySummary(
        position="col1",
        digit_count=0,
        stable_digit_count=0,
        moderate_digit_count=0,
        unstable_digit_count=-1,
        total_absolute_change=0.0,
        average_mean_absolute_change=0.0,
        stability_results=(),
    )

    with pytest.raises(
        ValueError,
        match="Unstable digit count must be greater than or equal to zero",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_classification_counts_must_equal_digit_count():
    summary = PositionDistributionStabilitySummary(
        position="col1",
        digit_count=10,
        stable_digit_count=5,
        moderate_digit_count=2,
        unstable_digit_count=2,
        total_absolute_change=10.0,
        average_mean_absolute_change=1.0,
        stability_results=(),
    )

    with pytest.raises(
        ValueError,
        match="Stability classification counts must equal digit count",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_negative_total_absolute_change_is_rejected():
    summary = PositionDistributionStabilitySummary(
        position="col1",
        digit_count=0,
        stable_digit_count=0,
        moderate_digit_count=0,
        unstable_digit_count=0,
        total_absolute_change=-1.0,
        average_mean_absolute_change=0.0,
        stability_results=(),
    )

    with pytest.raises(
        ValueError,
        match="Total absolute change must be greater than or equal to zero",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_negative_average_mean_absolute_change_is_rejected():
    summary = PositionDistributionStabilitySummary(
        position="col1",
        digit_count=0,
        stable_digit_count=0,
        moderate_digit_count=0,
        unstable_digit_count=0,
        total_absolute_change=0.0,
        average_mean_absolute_change=-1.0,
        stability_results=(),
    )

    with pytest.raises(
        ValueError,
        match="Average mean absolute change must be greater than or equal to zero",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_invalid_stability_result_digit_is_rejected():
    results = (
        make_volatility_result(
            digit=10,
        ),
    )

    summary = make_summary(
        stable_digit_count=1,
        moderate_digit_count=0,
        unstable_digit_count=0,
        results=results,
    )

    with pytest.raises(
        ValueError,
        match="Stability result digit must be between 0 and 9",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_stability_result_position_mismatch_is_rejected():
    results = (
        make_volatility_result(
            position="col2",
            digit=0,
        ),
    )

    summary = make_summary(
        position="col1",
        stable_digit_count=1,
        moderate_digit_count=0,
        unstable_digit_count=0,
        results=results,
    )

    with pytest.raises(
        ValueError,
        match="Stability result position does not match",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_negative_stability_result_mean_change_is_rejected():
    results = (
        make_volatility_result(
            digit=0,
            mean_absolute_change=-1.0,
        ),
    )

    summary = make_summary(
        stable_digit_count=1,
        moderate_digit_count=0,
        unstable_digit_count=0,
        results=results,
    )

    with pytest.raises(
        ValueError,
        match="Mean absolute change must be greater than or equal to zero",
    ):
        compare_position_distribution_stability(
            summary=summary,
        )


def test_negative_low_threshold_is_rejected():
    summary = make_summary()

    with pytest.raises(
        ValueError,
        match="Low threshold must be greater than or equal to zero",
    ):
        compare_position_distribution_stability(
            summary=summary,
            low_threshold=-1.0,
        )


def test_high_threshold_below_low_threshold_is_rejected():
    summary = make_summary()

    with pytest.raises(
        ValueError,
        match="High threshold must be greater than or equal to",
    ):
        compare_position_distribution_stability(
            summary=summary,
            low_threshold=5.0,
            high_threshold=2.0,
        )


def test_custom_thresholds_are_supported():
    summary = make_summary(
        average_mean_absolute_change=6.0,
    )

    result = compare_position_distribution_stability(
        summary=summary,
        low_threshold=4.0,
        high_threshold=7.0,
    )

    assert result.stability_level == "MODERATE"


def test_multiple_positions_are_compared():
    summaries = (
        make_summary(
            position="col1",
            stable_digit_count=8,
            moderate_digit_count=2,
            unstable_digit_count=0,
            average_mean_absolute_change=1.5,
        ),
        make_summary(
            position="col2",
            stable_digit_count=3,
            moderate_digit_count=4,
            unstable_digit_count=3,
            average_mean_absolute_change=4.0,
        ),
        make_summary(
            position="col3",
            stable_digit_count=1,
            moderate_digit_count=2,
            unstable_digit_count=7,
            average_mean_absolute_change=6.5,
        ),
    )

    results = compare_all_position_distribution_stability(
        summaries=summaries,
    )

    assert len(results) == 3
    assert [result.position for result in results] == [
        "col1",
        "col2",
        "col3",
    ]
    assert [result.stability_level for result in results] == [
        "STABLE",
        "MODERATE",
        "UNSTABLE",
    ]


def test_multiple_position_input_order_is_preserved():
    summaries = (
        make_summary(
            position="col7",
        ),
        make_summary(
            position="col2",
        ),
        make_summary(
            position="col9",
        ),
    )

    results = compare_all_position_distribution_stability(
        summaries=summaries,
    )

    assert [result.position for result in results] == [
        "col7",
        "col2",
        "col9",
    ]


def test_duplicate_positions_are_rejected():
    summaries = (
        make_summary(
            position="col1",
        ),
        make_summary(
            position="col1",
        ),
    )

    with pytest.raises(
        ValueError,
        match="Duplicate position summaries are not allowed",
    ):
        compare_all_position_distribution_stability(
            summaries=summaries,
        )


def test_empty_multiple_position_input_returns_empty_tuple():
    result = compare_all_position_distribution_stability(
        summaries=(),
    )

    assert result == ()


def test_multiple_position_custom_thresholds_are_supported():
    summaries = (
        make_summary(
            position="col1",
            average_mean_absolute_change=3.0,
        ),
        make_summary(
            position="col2",
            average_mean_absolute_change=7.0,
        ),
    )

    results = compare_all_position_distribution_stability(
        summaries=summaries,
        low_threshold=4.0,
        high_threshold=8.0,
    )

    assert results[0].stability_level == "STABLE"
    assert results[1].stability_level == "MODERATE"


def test_get_comparison_returns_matching_position():
    comparisons = (
        compare_position_distribution_stability(
            summary=make_summary(
                position="col1",
            ),
        ),
        compare_position_distribution_stability(
            summary=make_summary(
                position="col2",
            ),
        ),
    )

    result = get_position_distribution_stability_comparison(
        comparisons=comparisons,
        position="col2",
    )

    assert result is not None
    assert result.position == "col2"


def test_get_comparison_returns_none_for_missing_position():
    comparisons = (
        compare_position_distribution_stability(
            summary=make_summary(
                position="col1",
            ),
        ),
    )

    result = get_position_distribution_stability_comparison(
        comparisons=comparisons,
        position="col9",
    )

    assert result is None


def test_get_comparison_rejects_empty_position():
    with pytest.raises(
        ValueError,
        match="Position must not be empty",
    ):
        get_position_distribution_stability_comparison(
            comparisons=(),
            position="",
        )


def test_comparison_dataclass_is_frozen():
    result = compare_position_distribution_stability(
        summary=make_summary(),
    )

    with pytest.raises(FrozenInstanceError):
        result.position = "col2"


def test_comparison_result_type_is_correct():
    result = compare_position_distribution_stability(
        summary=make_summary(),
    )

    assert isinstance(
        result,
        PositionDistributionStabilityComparison,
    )


def test_all_comparison_results_have_correct_type():
    summaries = (
        make_summary(position="col1"),
        make_summary(position="col2"),
        make_summary(position="col3"),
    )

    results = compare_all_position_distribution_stability(
        summaries=summaries,
    )

    assert all(
        isinstance(
            result,
            PositionDistributionStabilityComparison,
        )
        for result in results
    )