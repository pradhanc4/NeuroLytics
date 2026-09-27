from dataclasses import FrozenInstanceError

import pytest

from analytics.position_distribution_stability_comparison_summary import (
    PositionDistributionStabilityComparisonSummary,
)
from analytics.position_distribution_stability_overview import (
    DEFAULT_MODERATE_THRESHOLD,
    DEFAULT_STABLE_THRESHOLD,
    MODERATE,
    STABLE,
    UNSTABLE,
    PositionDistributionStabilityOverview,
    build_position_distribution_stability_overview,
    classify_overall_stability,
)


def make_summary(
    position_count=3,
    stable_position_count=1,
    moderate_position_count=1,
    unstable_position_count=1,
    total_absolute_change=12.0,
    average_mean_absolute_change=4.0,
    minimum_mean_absolute_change=1.0,
    maximum_mean_absolute_change=7.0,
):
    return PositionDistributionStabilityComparisonSummary(
        position_count=position_count,
        stable_position_count=stable_position_count,
        moderate_position_count=moderate_position_count,
        unstable_position_count=unstable_position_count,
        total_absolute_change=total_absolute_change,
        average_mean_absolute_change=average_mean_absolute_change,
        minimum_mean_absolute_change=minimum_mean_absolute_change,
        maximum_mean_absolute_change=maximum_mean_absolute_change,
        comparisons=(),
    )


def test_empty_summary_returns_zero_overview():
    summary = make_summary(
        position_count=0,
        stable_position_count=0,
        moderate_position_count=0,
        unstable_position_count=0,
        total_absolute_change=0.0,
        average_mean_absolute_change=0.0,
        minimum_mean_absolute_change=0.0,
        maximum_mean_absolute_change=0.0,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.position_count == 0
    assert result.stable_position_count == 0
    assert result.moderate_position_count == 0
    assert result.unstable_position_count == 0

    assert result.stable_percentage == 0.0
    assert result.moderate_percentage == 0.0
    assert result.unstable_percentage == 0.0

    assert result.total_absolute_change == 0.0
    assert result.average_mean_absolute_change == 0.0
    assert result.minimum_mean_absolute_change == 0.0
    assert result.maximum_mean_absolute_change == 0.0

    assert result.overall_stability_level == STABLE


def test_position_count_is_preserved():
    summary = make_summary(
        position_count=8,
        stable_position_count=3,
        moderate_position_count=3,
        unstable_position_count=2,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.position_count == 8


def test_stable_position_count_is_preserved():
    summary = make_summary(
        position_count=6,
        stable_position_count=4,
        moderate_position_count=1,
        unstable_position_count=1,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.stable_position_count == 4


def test_moderate_position_count_is_preserved():
    summary = make_summary(
        position_count=6,
        stable_position_count=1,
        moderate_position_count=4,
        unstable_position_count=1,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.moderate_position_count == 4


def test_unstable_position_count_is_preserved():
    summary = make_summary(
        position_count=6,
        stable_position_count=1,
        moderate_position_count=1,
        unstable_position_count=4,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.unstable_position_count == 4


def test_stable_percentage_is_calculated():
    summary = make_summary(
        position_count=4,
        stable_position_count=2,
        moderate_position_count=1,
        unstable_position_count=1,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.stable_percentage == 50.0


def test_moderate_percentage_is_calculated():
    summary = make_summary(
        position_count=4,
        stable_position_count=1,
        moderate_position_count=2,
        unstable_position_count=1,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.moderate_percentage == 50.0


def test_unstable_percentage_is_calculated():
    summary = make_summary(
        position_count=4,
        stable_position_count=1,
        moderate_position_count=1,
        unstable_position_count=2,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.unstable_percentage == 50.0


def test_percentages_sum_to_100():
    summary = make_summary()

    result = build_position_distribution_stability_overview(summary)

    total = (
        result.stable_percentage
        + result.moderate_percentage
        + result.unstable_percentage
    )

    assert total == pytest.approx(100.0)


def test_total_absolute_change_is_preserved():
    summary = make_summary(total_absolute_change=25.5)

    result = build_position_distribution_stability_overview(summary)

    assert result.total_absolute_change == 25.5


def test_average_mean_absolute_change_is_preserved():
    summary = make_summary(average_mean_absolute_change=3.75)

    result = build_position_distribution_stability_overview(summary)

    assert result.average_mean_absolute_change == 3.75


def test_minimum_mean_absolute_change_is_preserved():
    summary = make_summary(minimum_mean_absolute_change=0.5)

    result = build_position_distribution_stability_overview(summary)

    assert result.minimum_mean_absolute_change == 0.5


def test_maximum_mean_absolute_change_is_preserved():
    summary = make_summary(maximum_mean_absolute_change=8.5)

    result = build_position_distribution_stability_overview(summary)

    assert result.maximum_mean_absolute_change == 8.5


def test_stable_overall_classification():
    summary = make_summary(average_mean_absolute_change=1.99)

    result = build_position_distribution_stability_overview(summary)

    assert result.overall_stability_level == STABLE


def test_moderate_overall_classification():
    summary = make_summary(average_mean_absolute_change=2.0)

    result = build_position_distribution_stability_overview(summary)

    assert result.overall_stability_level == MODERATE


def test_moderate_upper_boundary():
    summary = make_summary(average_mean_absolute_change=4.99)

    result = build_position_distribution_stability_overview(summary)

    assert result.overall_stability_level == MODERATE


def test_unstable_overall_classification():
    summary = make_summary(average_mean_absolute_change=5.0)

    result = build_position_distribution_stability_overview(summary)

    assert result.overall_stability_level == UNSTABLE


def test_stable_threshold_constant():
    assert DEFAULT_STABLE_THRESHOLD == 2.0


def test_moderate_threshold_constant():
    assert DEFAULT_MODERATE_THRESHOLD == 5.0


def test_classify_stable():
    assert classify_overall_stability(0.0) == STABLE
    assert classify_overall_stability(1.99) == STABLE


def test_classify_moderate():
    assert classify_overall_stability(2.0) == MODERATE
    assert classify_overall_stability(4.99) == MODERATE


def test_classify_unstable():
    assert classify_overall_stability(5.0) == UNSTABLE
    assert classify_overall_stability(10.0) == UNSTABLE


def test_negative_position_count_is_rejected():
    summary = make_summary(
        position_count=-1,
        stable_position_count=0,
        moderate_position_count=0,
        unstable_position_count=0,
    )

    with pytest.raises(ValueError, match="position_count cannot be negative"):
        build_position_distribution_stability_overview(summary)


def test_negative_stable_position_count_is_rejected():
    summary = make_summary(
        position_count=2,
        stable_position_count=-1,
        moderate_position_count=2,
        unstable_position_count=1,
    )

    with pytest.raises(
        ValueError,
        match="stable_position_count cannot be negative",
    ):
        build_position_distribution_stability_overview(summary)


def test_negative_moderate_position_count_is_rejected():
    summary = make_summary(
        position_count=2,
        stable_position_count=2,
        moderate_position_count=-1,
        unstable_position_count=1,
    )

    with pytest.raises(
        ValueError,
        match="moderate_position_count cannot be negative",
    ):
        build_position_distribution_stability_overview(summary)


def test_negative_unstable_position_count_is_rejected():
    summary = make_summary(
        position_count=2,
        stable_position_count=2,
        moderate_position_count=1,
        unstable_position_count=-1,
    )

    with pytest.raises(
        ValueError,
        match="unstable_position_count cannot be negative",
    ):
        build_position_distribution_stability_overview(summary)


def test_classification_counts_must_equal_position_count():
    summary = make_summary(
        position_count=5,
        stable_position_count=1,
        moderate_position_count=1,
        unstable_position_count=1,
    )

    with pytest.raises(
        ValueError,
        match="Stability classification counts must equal position_count",
    ):
        build_position_distribution_stability_overview(summary)


def test_negative_total_absolute_change_is_rejected():
    summary = make_summary(total_absolute_change=-1.0)

    with pytest.raises(
        ValueError,
        match="total_absolute_change cannot be negative",
    ):
        build_position_distribution_stability_overview(summary)


def test_negative_average_mean_absolute_change_is_rejected():
    summary = make_summary(average_mean_absolute_change=-1.0)

    with pytest.raises(
        ValueError,
        match="average_mean_absolute_change cannot be negative",
    ):
        build_position_distribution_stability_overview(summary)


def test_negative_minimum_mean_absolute_change_is_rejected():
    summary = make_summary(minimum_mean_absolute_change=-1.0)

    with pytest.raises(
        ValueError,
        match="minimum_mean_absolute_change cannot be negative",
    ):
        build_position_distribution_stability_overview(summary)


def test_negative_maximum_mean_absolute_change_is_rejected():
    summary = make_summary(maximum_mean_absolute_change=-1.0)

    with pytest.raises(
        ValueError,
        match="maximum_mean_absolute_change cannot be negative",
    ):
        build_position_distribution_stability_overview(summary)


def test_minimum_greater_than_maximum_is_rejected():
    summary = make_summary(
        minimum_mean_absolute_change=8.0,
        maximum_mean_absolute_change=5.0,
    )

    with pytest.raises(
        ValueError,
        match="minimum_mean_absolute_change cannot exceed maximum",
    ):
        build_position_distribution_stability_overview(summary)


def test_invalid_summary_type_is_rejected():
    with pytest.raises(
        TypeError,
        match="summary must be a PositionDistributionStabilityComparisonSummary",
    ):
        build_position_distribution_stability_overview(object())


def test_overview_is_frozen():
    summary = make_summary()

    result = build_position_distribution_stability_overview(summary)

    with pytest.raises(FrozenInstanceError):
        result.position_count = 10


def test_result_is_correct_dataclass_type():
    summary = make_summary()

    result = build_position_distribution_stability_overview(summary)

    assert isinstance(result, PositionDistributionStabilityOverview)