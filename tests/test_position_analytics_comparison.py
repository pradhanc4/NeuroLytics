from __future__ import annotations

from dataclasses import dataclass

import pytest

from analytics.position_analytics_comparison import (
    COMPARISON_METRICS,
    PositionAnalyticsComparison,
    PositionAnalyticsComparisonResult,
    build_position_analytics_comparison,
    build_position_analytics_comparison_result,
    get_position_analytics_comparison,
    get_position_analytics_metric_difference,
    iter_position_analytics_comparisons,
)


@dataclass(frozen=True)
class FakeSummary:
    total_frequency: int = 100
    total_observations: int = 50
    average_distribution_mean: float = 4.0
    average_distribution_std: float = 2.0
    average_stability_percentage: float = 80.0

    total_change_count: int = 20
    total_increase_count: int = 8
    total_decrease_count: int = 7
    total_unchanged_count: int = 5

    average_change_magnitude: float = 3.0
    average_trend_strength: float = 0.6
    average_trend_consistency: float = 70.0
    average_volatility: float = 2.5

    total_transition_count: int = 10

    temporal_total_observation_count: int = 45
    temporal_total_change_count: int = 30
    temporal_total_increase_count: int = 12
    temporal_total_decrease_count: int = 10
    temporal_total_unchanged_count: int = 8

    relationship_count: int = 7
    relationship_positive_count: int = 3
    relationship_negative_count: int = 2
    relationship_neutral_count: int = 1
    relationship_insufficient_data_count: int = 1

    regime_window_count: int = 20
    regime_valid_window_count: int = 18
    regime_insufficient_window_count: int = 2
    regime_transition_count: int = 6
    regime_unchanged_count: int = 10
    regime_missing_count: int = 2

    high_regime_stability_count: int = 1
    medium_regime_stability_count: int = 1
    low_regime_stability_count: int = 1
    insufficient_regime_stability_count: int = 0


def test_comparison_metrics_are_defined():
    assert "total_frequency" in COMPARISON_METRICS
    assert "average_stability_percentage" in COMPARISON_METRICS
    assert "average_volatility" in COMPARISON_METRICS
    assert "regime_transition_count" in COMPARISON_METRICS


def test_build_comparison_returns_expected_type():
    result = build_position_analytics_comparison(
        "col1",
        "col2",
        FakeSummary(),
        FakeSummary(),
    )

    assert isinstance(
        result,
        PositionAnalyticsComparison,
    )


def test_build_comparison_preserves_position_order():
    result = build_position_analytics_comparison(
        "col1",
        "col2",
        FakeSummary(),
        FakeSummary(),
    )

    assert result.position_a == "col1"
    assert result.position_b == "col2"


def test_comparison_contains_all_supported_metrics():
    result = build_position_analytics_comparison(
        "col1",
        "col2",
        FakeSummary(),
        FakeSummary(),
    )

    assert tuple(
        name
        for name, _ in result.metric_differences
    ) == COMPARISON_METRICS

    assert tuple(
        name
        for name, _ in result.position_a_values
    ) == COMPARISON_METRICS

    assert tuple(
        name
        for name, _ in result.position_b_values
    ) == COMPARISON_METRICS


def test_equal_summaries_have_zero_differences():
    result = build_position_analytics_comparison(
        "col1",
        "col2",
        FakeSummary(),
        FakeSummary(),
    )

    assert all(
        value == 0.0
        for _, value in result.metric_differences
    )


def test_comparison_calculates_a_minus_b_difference():
    summary_a = FakeSummary(
        total_frequency=120,
        average_stability_percentage=90.0,
        average_volatility=4.0,
    )

    summary_b = FakeSummary(
        total_frequency=100,
        average_stability_percentage=70.0,
        average_volatility=1.5,
    )

    result = build_position_analytics_comparison(
        "col1",
        "col2",
        summary_a,
        summary_b,
    )

    differences = dict(
        result.metric_differences
    )

    assert differences["total_frequency"] == 20.0
    assert differences[
        "average_stability_percentage"
    ] == 20.0
    assert differences["average_volatility"] == 2.5


def test_position_values_are_preserved():
    summary_a = FakeSummary(
        total_frequency=125,
    )

    summary_b = FakeSummary(
        total_frequency=75,
    )

    result = build_position_analytics_comparison(
        "col1",
        "col2",
        summary_a,
        summary_b,
    )

    values_a = dict(
        result.position_a_values
    )

    values_b = dict(
        result.position_b_values
    )

    assert values_a["total_frequency"] == 125.0
    assert values_b["total_frequency"] == 75.0


def test_negative_difference_is_preserved():
    summary_a = FakeSummary(
        total_frequency=50,
    )

    summary_b = FakeSummary(
        total_frequency=100,
    )

    result = build_position_analytics_comparison(
        "col1",
        "col2",
        summary_a,
        summary_b,
    )

    differences = dict(
        result.metric_differences
    )

    assert differences["total_frequency"] == -50.0


def test_metric_difference_getter():
    summary_a = FakeSummary(
        total_frequency=120,
    )

    summary_b = FakeSummary(
        total_frequency=100,
    )

    comparison = build_position_analytics_comparison(
        "col1",
        "col2",
        summary_a,
        summary_b,
    )

    assert (
        get_position_analytics_metric_difference(
            comparison,
            "total_frequency",
        )
        == 20.0
    )


def test_unknown_metric_raises():
    comparison = build_position_analytics_comparison(
        "col1",
        "col2",
        FakeSummary(),
        FakeSummary(),
    )

    with pytest.raises(KeyError):
        get_position_analytics_metric_difference(
            comparison,
            "unknown_metric",
        )


def test_same_position_raises():
    with pytest.raises(ValueError):
        build_position_analytics_comparison(
            "col1",
            "col1",
            FakeSummary(),
            FakeSummary(),
        )


def test_empty_position_a_raises():
    with pytest.raises(ValueError):
        build_position_analytics_comparison(
            "",
            "col2",
            FakeSummary(),
            FakeSummary(),
        )


def test_empty_position_b_raises():
    with pytest.raises(ValueError):
        build_position_analytics_comparison(
            "col1",
            "",
            FakeSummary(),
            FakeSummary(),
        )


def test_non_string_position_a_raises():
    with pytest.raises(TypeError):
        build_position_analytics_comparison(
            1,
            "col2",
            FakeSummary(),
            FakeSummary(),
        )


def test_non_string_position_b_raises():
    with pytest.raises(TypeError):
        build_position_analytics_comparison(
            "col1",
            2,
            FakeSummary(),
            FakeSummary(),
        )


def test_none_summary_a_raises():
    with pytest.raises(TypeError):
        build_position_analytics_comparison(
            "col1",
            "col2",
            None,
            FakeSummary(),
        )


def test_none_summary_b_raises():
    with pytest.raises(TypeError):
        build_position_analytics_comparison(
            "col1",
            "col2",
            FakeSummary(),
            None,
        )


def test_boolean_metric_is_rejected():
    summary = FakeSummary()
    invalid_summary = type(
        "InvalidSummary",
        (),
        {
            "total_frequency": True,
        },
    )()

    with pytest.raises(TypeError):
        build_position_analytics_comparison(
            "col1",
            "col2",
            invalid_summary,
            summary,
        )


def test_non_numeric_metric_is_rejected():
    invalid_summary = type(
        "InvalidSummary",
        (),
        {
            "total_frequency": "invalid",
        },
    )()

    with pytest.raises(TypeError):
        build_position_analytics_comparison(
            "col1",
            "col2",
            invalid_summary,
            FakeSummary(),
        )


def test_none_numeric_metric_defaults_to_zero():
    summary_a = type(
        "SummaryWithNone",
        (),
        {
            "total_frequency": None,
        },
    )()

    summary_b = FakeSummary(
        total_frequency=10,
    )

    result = build_position_analytics_comparison(
        "col1",
        "col2",
        summary_a,
        summary_b,
    )

    differences = dict(
        result.metric_differences
    )

    assert differences["total_frequency"] == -10.0


def test_build_result_creates_unique_pairs():
    summaries = (
        ("col1", FakeSummary()),
        ("col2", FakeSummary()),
        ("col3", FakeSummary()),
    )

    result = build_position_analytics_comparison_result(
        summaries
    )

    assert isinstance(
        result,
        PositionAnalyticsComparisonResult,
    )

    assert result.position_count == 3
    assert result.positions == (
        "col1",
        "col2",
        "col3",
    )

    assert result.comparison_count == 3


def test_build_result_preserves_pair_order():
    summaries = (
        ("col1", FakeSummary()),
        ("col2", FakeSummary()),
        ("col3", FakeSummary()),
    )

    result = build_position_analytics_comparison_result(
        summaries
    )

    assert tuple(
        (
            comparison.position_a,
            comparison.position_b,
        )
        for comparison in result.comparisons
    ) == (
        ("col1", "col2"),
        ("col1", "col3"),
        ("col2", "col3"),
    )


def test_build_result_with_two_positions():
    result = build_position_analytics_comparison_result(
        (
            ("col1", FakeSummary()),
            ("col2", FakeSummary()),
        )
    )

    assert result.position_count == 2
    assert result.comparison_count == 1

    assert (
        result.comparisons[0].position_a
        == "col1"
    )

    assert (
        result.comparisons[0].position_b
        == "col2"
    )


def test_build_result_with_one_position_has_no_pairs():
    result = build_position_analytics_comparison_result(
        (
            ("col1", FakeSummary()),
        )
    )

    assert result.position_count == 1
    assert result.comparison_count == 0
    assert result.comparisons == ()


def test_build_result_with_no_positions():
    result = build_position_analytics_comparison_result(
        ()
    )

    assert result.position_count == 0
    assert result.positions == ()
    assert result.comparison_count == 0
    assert result.comparisons == ()


def test_duplicate_positions_raise():
    with pytest.raises(ValueError):
        build_position_analytics_comparison_result(
            (
                ("col1", FakeSummary()),
                ("col1", FakeSummary()),
            )
        )


def test_empty_position_in_result_raises():
    with pytest.raises(ValueError):
        build_position_analytics_comparison_result(
            (
                ("col1", FakeSummary()),
                ("", FakeSummary()),
            )
        )


def test_non_string_position_in_result_raises():
    with pytest.raises(TypeError):
        build_position_analytics_comparison_result(
            (
                ("col1", FakeSummary()),
                (2, FakeSummary()),
            )
        )


def test_list_input_is_normalized_to_tuple():
    result = build_position_analytics_comparison_result(
        [
            ("col1", FakeSummary()),
            ("col2", FakeSummary()),
        ]
    )

    assert isinstance(
        result.positions,
        tuple,
    )

    assert isinstance(
        result.comparisons,
        tuple,
    )


def test_get_comparison_by_exact_pair():
    result = build_position_analytics_comparison_result(
        (
            ("col1", FakeSummary()),
            ("col2", FakeSummary()),
            ("col3", FakeSummary()),
        )
    )

    comparison = get_position_analytics_comparison(
        result,
        "col1",
        "col3",
    )

    assert comparison.position_a == "col1"
    assert comparison.position_b == "col3"


def test_reverse_pair_is_not_implicitly_reordered():
    result = build_position_analytics_comparison_result(
        (
            ("col1", FakeSummary()),
            ("col2", FakeSummary()),
        )
    )

    with pytest.raises(KeyError):
        get_position_analytics_comparison(
            result,
            "col2",
            "col1",
        )


def test_unknown_pair_raises():
    result = build_position_analytics_comparison_result(
        (
            ("col1", FakeSummary()),
            ("col2", FakeSummary()),
        )
    )

    with pytest.raises(KeyError):
        get_position_analytics_comparison(
            result,
            "col1",
            "col3",
        )


def test_iterator_returns_comparisons():
    result = build_position_analytics_comparison_result(
        (
            ("col1", FakeSummary()),
            ("col2", FakeSummary()),
            ("col3", FakeSummary()),
        )
    )

    comparisons = iter_position_analytics_comparisons(
        result
    )

    assert isinstance(
        comparisons,
        tuple,
    )

    assert len(comparisons) == 3


def test_invalid_result_type_for_getter_raises():
    with pytest.raises(TypeError):
        get_position_analytics_comparison(
            "invalid",
            "col1",
            "col2",
        )


def test_invalid_result_type_for_iterator_raises():
    with pytest.raises(TypeError):
        iter_position_analytics_comparisons(
            "invalid",
        )


def test_invalid_comparison_type_for_metric_getter_raises():
    with pytest.raises(TypeError):
        get_position_analytics_metric_difference(
            "invalid",
            "total_frequency",
        )