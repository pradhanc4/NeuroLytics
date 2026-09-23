from __future__ import annotations

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
    *,
    position_count: int = 3,
    stable_position_count: int = 1,
    moderate_position_count: int = 1,
    unstable_position_count: int = 1,
    total_absolute_change: float = 12.0,
    average_mean_absolute_change: float = 4.0,
    minimum_mean_absolute_change: float = 1.0,
    maximum_mean_absolute_change: float = 7.0,
) -> PositionDistributionStabilityComparisonSummary:
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
    summary = make_summary(position_count=8)

    result = build_position_distribution_stability_overview(summary)

    assert result.position_count == 8


def test_stable_position_count_is_preserved():
    summary = make_summary(stable_position_count=4)

    result = build_position_distribution_stability_overview(summary)

    assert result.stable_position_count == 4


def test_moderate_position_count_is_preserved():
    summary = make_summary(moderate_position_count=4)

    result = build_position_distribution_stability_overview(summary)

    assert result.moderate_position_count == 4


def test_unstable_position_count_is_preserved():
    summary = make_summary(unstable_position_count=4)

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


def test_percentages_sum_to_100_for_nonempty_summary():
    summary = make_summary(
        position_count=8,
        stable_position_count=2,
        moderate_position_count=3,
        unstable_position_count=3,
    )

    result = build_position_distribution_stability_overview(summary)

    assert (
        result.stable_percentage
        + result.moderate_percentage
        + result.unstable_percentage
    ) == pytest.approx(100.0)


def test_total_absolute_change_is_preserved():
    summary = make_summary(total_absolute_change=27.5)

    result = build_position_distribution_stability_overview(summary)

    assert result.total_absolute_change == 27.5


def test_average_mean_absolute_change_is_preserved():
    summary = make_summary(average_mean_absolute_change=3.75)

    result = build_position_distribution_stability_overview(summary)

    assert result.average_mean_absolute_change == 3.75


def test_minimum_mean_absolute_change_is_preserved():
    summary = make_summary(minimum_mean_absolute_change=0.75)

    result = build_position_distribution_stability_overview(summary)

    assert result.minimum_mean_absolute_change == 0.75


def test_maximum_mean_absolute_change_is_preserved():
    summary = make_summary(maximum_mean_absolute_change=8.5)

    result = build_position_distribution_stability_overview(summary)

    assert result.maximum_mean_absolute_change == 8.5


def test_overall_stability_is_stable_below_two():
    assert classify_overall_stability(1.99) == STABLE


def test_overall_stability_is_moderate_at_two():
    assert classify_overall_stability(2.0) == MODERATE


def test_overall_stability_is_moderate_below_five():
    assert classify_overall_stability(4.99) == MODERATE


def test_overall_stability_is_unstable_at_five():
    assert classify_overall_stability(5.0) == UNSTABLE


def test_default_thresholds_are_correct():
    assert DEFAULT_STABLE_THRESHOLD == 2.0
    assert DEFAULT_MODERATE_THRESHOLD == 5.0


def test_custom_thresholds_are_supported():
    assert (
        classify_overall_stability(
            3.0,
            stable_threshold=3.0,
            unstable_threshold=6.0,
        )
        == MODERATE
    )

    assert (
        classify_overall_stability(
            2.99,
            stable_threshold=3.0,
            unstable_threshold=6.0,
        )
        == STABLE
    )

    assert (
        classify_overall_stability(
            6.0,
            stable_threshold=3.0,
            unstable_threshold=6.0,
        )
        == UNSTABLE
    )


def test_negative_average_mean_absolute_change_is_rejected():
    with pytest.raises(ValueError):
        classify_overall_stability(-0.1)


def test_negative_stable_threshold_is_rejected():
    with pytest.raises(ValueError):
        classify_overall_stability(
            1.0,
            stable_threshold=-1.0,
            unstable_threshold=5.0,
        )


def test_unstable_threshold_below_stable_threshold_is_rejected():
    with pytest.raises(ValueError):
        classify_overall_stability(
            3.0,
            stable_threshold=5.0,
            unstable_threshold=4.0,
        )


def test_invalid_summary_type_is_rejected():
    with pytest.raises(TypeError):
        build_position_distribution_stability_overview(
            object()  # type: ignore[arg-type]
        )


def test_negative_position_count_is_rejected():
    summary = make_summary(position_count=-1)

    with pytest.raises(ValueError):
        build_position_distribution_stability_overview(summary)


def test_classification_count_mismatch_is_rejected():
    summary = make_summary(
        position_count=5,
        stable_position_count=1,
        moderate_position_count=1,
        unstable_position_count=1,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_overview(summary)


def test_negative_total_absolute_change_is_rejected():
    summary = make_summary(total_absolute_change=-1.0)

    with pytest.raises(ValueError):
        build_position_distribution_stability_overview(summary)


def test_negative_average_mean_absolute_change_is_rejected():
    summary = make_summary(average_mean_absolute_change=-1.0)

    with pytest.raises(ValueError):
        build_position_distribution_stability_overview(summary)


def test_negative_minimum_mean_absolute_change_is_rejected():
    summary = make_summary(minimum_mean_absolute_change=-1.0)

    with pytest.raises(ValueError):
        build_position_distribution_stability_overview(summary)


def test_negative_maximum_mean_absolute_change_is_rejected():
    summary = make_summary(maximum_mean_absolute_change=-1.0)

    with pytest.raises(ValueError):
        build_position_distribution_stability_overview(summary)


def test_minimum_greater_than_maximum_is_rejected():
    summary = make_summary(
        minimum_mean_absolute_change=8.0,
        maximum_mean_absolute_change=3.0,
    )

    with pytest.raises(ValueError):
        build_position_distribution_stability_overview(summary)


def test_result_is_frozen():
    summary = make_summary()

    result = build_position_distribution_stability_overview(summary)

    assert isinstance(result, PositionDistributionStabilityOverview)

    with pytest.raises(AttributeError):
        result.position_count = 10  # type: ignore[misc]


def test_default_overview_classification_uses_average_change():
    summary = make_summary(
        average_mean_absolute_change=1.5,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.overall_stability_level == STABLE


def test_default_overview_classification_is_moderate():
    summary = make_summary(
        average_mean_absolute_change=3.5,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.overall_stability_level == MODERATE


def test_default_overview_classification_is_unstable():
    summary = make_summary(
        average_mean_absolute_change=6.0,
    )

    result = build_position_distribution_stability_overview(summary)

    assert result.overall_stability_level == UNSTABLE