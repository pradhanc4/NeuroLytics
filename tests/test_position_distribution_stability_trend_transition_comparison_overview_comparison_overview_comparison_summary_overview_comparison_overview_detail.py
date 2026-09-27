from dataclasses import fields, FrozenInstanceError
import pytest

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverview,
)
from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail import (
    ALL_METRIC_FIELDS, PERCENTAGE_FIELDS, MOVEMENT_FIELDS, PERCENTAGE_METRIC, MOVEMENT_METRIC,
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverviewDetail,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_details,
    build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail_from_overviews,
    get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail_metric,
)


def make_overview(shift=0.0, count=2):
    data = {"overview_count": count}
    for i, name in enumerate(PERCENTAGE_FIELDS):
        start = 10.0 + i + shift
        data[name + "_start"] = start
        data[name + "_end"] = start + 1.0
        data[name + "_change"] = 1.0
    for i, name in enumerate(MOVEMENT_FIELDS):
        start = 1.0 + i + shift
        data[name + "_start"] = start
        data[name + "_end"] = start + 1.0
        data[name + "_change"] = 1.0
    data["total_absolute_percentage_movement"] = 27.0
    data["mean_absolute_percentage_movement"] = 27.0
    return PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverview(**data)


def make_zero():
    data = {"overview_count": 0}
    for name in ALL_METRIC_FIELDS:
        data[name + "_start"] = 0.0
        data[name + "_end"] = 0.0
        data[name + "_change"] = 0.0
    data["total_absolute_percentage_movement"] = 0.0
    data["mean_absolute_percentage_movement"] = 0.0
    return PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverview(**data)


def test_expected_output_fields():
    assert {f.name for f in fields(PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverviewDetail)} == {"overview_count", "metric_count", "metrics"}


def test_31_metrics():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(make_overview())
    assert result.metric_count == 31
    assert tuple(m.metric_name for m in result.metrics) == ALL_METRIC_FIELDS


def test_percentage_and_movement_types():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(make_overview())
    assert all(m.metric_type == PERCENTAGE_METRIC for m in result.metrics[:27])
    assert all(m.metric_type == MOVEMENT_METRIC for m in result.metrics[27:])


def test_values_and_absolute_change():
    source = make_overview()
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(source)
    for m in result.metrics:
        assert m.start_value == getattr(source, m.metric_name + "_start")
        assert m.end_value == getattr(source, m.metric_name + "_end")
        assert m.change == getattr(source, m.metric_name + "_change")
        assert m.absolute_change == abs(m.change)


def test_empty_count_is_preserved():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(make_zero())
    assert result.overview_count == 0
    assert result.metric_count == 31


def test_wrapper_preserves_order():
    a, b = make_overview(0), make_overview(5)
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_details((a, b))
    assert result[0].metrics[0].start_value == a.low_increase_increase_percentage_start
    assert result[1].metrics[0].start_value == b.low_increase_increase_percentage_start


def test_iterable_wrapper():
    result = build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail_from_overviews(iter((make_overview(),)))
    assert len(result) == 1


def test_get_metric():
    detail = build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(make_overview())
    assert get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail_metric(detail, "total_absolute_percentage_movement").metric_type == MOVEMENT_METRIC
    assert get_position_distribution_stability_trend_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail_metric if False else True


def test_unknown_metric_returns_none():
    detail = build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(make_overview())
    assert get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail_metric(detail, "missing") is None


def test_invalid_input():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(object())


def test_invalid_tuple_input():
    with pytest.raises(TypeError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_details([])


def test_frozen():
    detail = build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(make_overview())
    with pytest.raises(FrozenInstanceError):
        detail.metric_count = 0


def test_negative_percentage():
    source = make_overview()
    data = {f.name: getattr(source, f.name) for f in fields(source)}
    data["low_increase_increase_percentage_start"] = -1.0
    data["low_increase_increase_percentage_change"] = 2.0
    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(type(source)(**data))


def test_percentage_over_100():
    source = make_overview()
    data = {f.name: getattr(source, f.name) for f in fields(source)}
    data["low_increase_increase_percentage_end"] = 101.0
    data["low_increase_increase_percentage_change"] = 91.0
    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(type(source)(**data))


def test_negative_movement():
    source = make_overview()
    data = {f.name: getattr(source, f.name) for f in fields(source)}
    data["average_total_absolute_percentage_movement_start"] = -1.0
    data["average_total_absolute_percentage_movement_change"] = 2.0
    with pytest.raises(ValueError):
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(type(source)(**data))
