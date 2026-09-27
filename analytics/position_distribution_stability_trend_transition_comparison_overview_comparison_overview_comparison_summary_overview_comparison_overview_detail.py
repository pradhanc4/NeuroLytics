"""Phase 9.3.50: field-level detail for the Phase 9.3.49 overview comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview import (
    PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverview,
)

PERCENTAGE_FIELDS = (
    "low_increase_increase_percentage", "low_increase_decrease_percentage",
    "low_increase_unchanged_percentage", "low_decrease_increase_percentage",
    "low_decrease_decrease_percentage", "low_decrease_unchanged_percentage",
    "low_unchanged_increase_percentage", "low_unchanged_decrease_percentage",
    "low_unchanged_unchanged_percentage", "medium_increase_increase_percentage",
    "medium_increase_decrease_percentage", "medium_increase_unchanged_percentage",
    "medium_decrease_increase_percentage", "medium_decrease_decrease_percentage",
    "medium_decrease_unchanged_percentage", "medium_unchanged_increase_percentage",
    "medium_unchanged_decrease_percentage", "medium_unchanged_unchanged_percentage",
    "high_increase_increase_percentage", "high_increase_decrease_percentage",
    "high_increase_unchanged_percentage", "high_decrease_increase_percentage",
    "high_decrease_decrease_percentage", "high_decrease_unchanged_percentage",
    "high_unchanged_increase_percentage", "high_unchanged_decrease_percentage",
    "high_unchanged_unchanged_percentage",
)
MOVEMENT_FIELDS = (
    "average_total_absolute_percentage_movement",
    "minimum_total_absolute_percentage_movement",
    "maximum_total_absolute_percentage_movement",
    "total_absolute_percentage_movement",
)
ALL_METRIC_FIELDS = PERCENTAGE_FIELDS + MOVEMENT_FIELDS
PERCENTAGE_METRIC = "PERCENTAGE"
MOVEMENT_METRIC = "MOVEMENT"
VALID_METRIC_TYPES = (PERCENTAGE_METRIC, MOVEMENT_METRIC)


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverviewDetailMetric:
    metric_name: str
    metric_type: str
    start_value: float
    end_value: float
    change: float
    absolute_change: float


@dataclass(frozen=True)
class PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverviewDetail:
    overview_count: int
    metric_count: int
    metrics: tuple[
        PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverviewDetailMetric,
        ...,
    ]


def _validate_overview(overview) -> None:
    if not isinstance(overview, PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverview):
        raise TypeError("overview must be a Phase 9.3.49 comparison-overview result.")
    if isinstance(overview.overview_count, bool) or not isinstance(overview.overview_count, int):
        raise TypeError("overview_count must be an integer.")
    if overview.overview_count < 0:
        raise ValueError("overview_count must be non-negative.")
    for name in PERCENTAGE_FIELDS:
        value = getattr(overview, name + "_start")
        end = getattr(overview, name + "_end")
        if not 0 <= value <= 100 or not 0 <= end <= 100:
            raise ValueError(f"{name} values must be between 0 and 100.")
        if getattr(overview, name + "_change") != end - value:
            raise ValueError(f"{name}_change must equal end minus start.")
    for name in MOVEMENT_FIELDS:
        value = getattr(overview, name + "_start")
        end = getattr(overview, name + "_end")
        if value < 0 or end < 0:
            raise ValueError(f"{name} values must be non-negative.")
        if getattr(overview, name + "_change") != end - value:
            raise ValueError(f"{name}_change must equal end minus start.")
    if overview.minimum_total_absolute_percentage_movement_start > overview.maximum_total_absolute_percentage_movement_start:
        raise ValueError("minimum start movement must not exceed maximum start movement.")
    if overview.minimum_total_absolute_percentage_movement_end > overview.maximum_total_absolute_percentage_movement_end:
        raise ValueError("minimum end movement must not exceed maximum end movement.")
    if overview.overview_count == 0:
        for name in ALL_METRIC_FIELDS:
            for suffix in ("_start", "_end", "_change"):
                if getattr(overview, name + suffix) != 0:
                    raise ValueError("overview_count of 0 requires zero metric values.")
        if overview.total_absolute_percentage_movement != 0 or overview.mean_absolute_percentage_movement != 0:
            raise ValueError("overview_count of 0 requires zero aggregate movement.")


def _validate_metric(metric) -> None:
    if not isinstance(metric, PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverviewDetailMetric):
        raise TypeError("metric must be a Phase 9.3.50 detail metric.")
    if not isinstance(metric.metric_name, str) or not metric.metric_name:
        raise ValueError("metric_name must be a non-empty string.")
    if metric.metric_type not in VALID_METRIC_TYPES:
        raise ValueError("metric_type is invalid.")
    if metric.metric_name in PERCENTAGE_FIELDS:
        if not 0 <= metric.start_value <= 100 or not 0 <= metric.end_value <= 100:
            raise ValueError("percentage values must be between 0 and 100.")
    elif metric.metric_name in MOVEMENT_FIELDS:
        if metric.start_value < 0 or metric.end_value < 0:
            raise ValueError("movement values must be non-negative.")
    else:
        raise ValueError("metric_name is not a supported Phase 9.3.50 metric.")
    if metric.change != metric.end_value - metric.start_value:
        raise ValueError("change must equal end minus start.")
    if metric.absolute_change != abs(metric.change):
        raise ValueError("absolute_change must equal abs(change).")


def _build_metric(overview, name):
    start = float(getattr(overview, name + "_start"))
    end = float(getattr(overview, name + "_end"))
    change = float(getattr(overview, name + "_change"))
    metric = PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverviewDetailMetric(
        name,
        PERCENTAGE_METRIC if name in PERCENTAGE_FIELDS else MOVEMENT_METRIC,
        start,
        end,
        change,
        abs(change),
    )
    _validate_metric(metric)
    return metric


def build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(overview):
    _validate_overview(overview)
    metrics = tuple(_build_metric(overview, name) for name in ALL_METRIC_FIELDS)
    return PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverviewDetail(
        overview_count=overview.overview_count,
        metric_count=len(metrics),
        metrics=metrics,
    )


def build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_details(overviews):
    if not isinstance(overviews, tuple):
        raise TypeError("overviews must be a tuple.")
    return tuple(
        build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail(item)
        for item in overviews
    )


def build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail_from_overviews(overviews: Iterable):
    return build_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_details(tuple(overviews))


def get_position_distribution_stability_trend_transition_comparison_overview_comparison_overview_comparison_summary_overview_comparison_overview_detail_metric(detail, metric_name):
    if not isinstance(detail, PositionDistributionStabilityTrendTransitionComparisonOverviewComparisonOverviewComparisonSummaryOverviewComparisonOverviewDetail):
        raise TypeError("detail must be a Phase 9.3.50 detail result.")
    if not isinstance(metric_name, str):
        raise TypeError("metric_name must be a string.")
    for metric in detail.metrics:
        if metric.metric_name == metric_name:
            return metric
    return None
