from __future__ import annotations

from dataclasses import dataclass
from typing import Any


COMPARISON_METRICS = (
    "total_frequency",
    "total_observations",
    "average_distribution_mean",
    "average_distribution_std",
    "average_stability_percentage",
    "total_change_count",
    "total_increase_count",
    "total_decrease_count",
    "total_unchanged_count",
    "average_change_magnitude",
    "average_trend_strength",
    "average_trend_consistency",
    "average_volatility",
    "total_transition_count",
    "temporal_total_observation_count",
    "temporal_total_change_count",
    "temporal_total_increase_count",
    "temporal_total_decrease_count",
    "temporal_total_unchanged_count",
    "relationship_count",
    "relationship_positive_count",
    "relationship_negative_count",
    "relationship_neutral_count",
    "relationship_insufficient_data_count",
    "regime_window_count",
    "regime_valid_window_count",
    "regime_insufficient_window_count",
    "regime_transition_count",
    "regime_unchanged_count",
    "regime_missing_count",
    "high_regime_stability_count",
    "medium_regime_stability_count",
    "low_regime_stability_count",
    "insufficient_regime_stability_count",
)


@dataclass(frozen=True)
class PositionAnalyticsComparison:
    """Descriptive pairwise comparison between two positions."""

    position_a: str
    position_b: str

    metric_differences: tuple[tuple[str, float], ...]

    position_a_values: tuple[tuple[str, float], ...]
    position_b_values: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class PositionAnalyticsComparisonResult:
    """Collection of descriptive position comparisons."""

    position_count: int
    positions: tuple[str, ...]
    comparison_count: int
    comparisons: tuple[PositionAnalyticsComparison, ...]


def _read_numeric(
    summary: Any,
    metric_name: str,
) -> float:
    """Read one numeric metric from a position summary."""

    value = getattr(
        summary,
        metric_name,
        0.0,
    )

    if value is None:
        return 0.0

    if isinstance(value, bool):
        raise TypeError(
            f"Metric {metric_name} must be numeric"
        )

    if not isinstance(
        value,
        (int, float),
    ):
        raise TypeError(
            f"Metric {metric_name} must be numeric"
        )

    return float(value)


def _extract_summary_values(
    summary: Any,
) -> tuple[tuple[str, float], ...]:
    """Extract all supported numeric comparison metrics."""

    return tuple(
        (
            metric_name,
            _read_numeric(
                summary,
                metric_name,
            ),
        )
        for metric_name in COMPARISON_METRICS
    )


def _build_comparison(
    position_a: str,
    position_b: str,
    summary_a: Any,
    summary_b: Any,
) -> PositionAnalyticsComparison:
    """Build one descriptive pairwise comparison."""

    values_a = _extract_summary_values(summary_a)
    values_b = _extract_summary_values(summary_b)

    values_a_dict = dict(values_a)
    values_b_dict = dict(values_b)

    metric_differences = tuple(
        (
            metric_name,
            values_a_dict[metric_name]
            - values_b_dict[metric_name],
        )
        for metric_name in COMPARISON_METRICS
    )

    return PositionAnalyticsComparison(
        position_a=position_a,
        position_b=position_b,
        metric_differences=metric_differences,
        position_a_values=values_a,
        position_b_values=values_b,
    )


def build_position_analytics_comparison(
    position_a: str,
    position_b: str,
    summary_a: Any,
    summary_b: Any,
) -> PositionAnalyticsComparison:
    """
    Build a descriptive comparison between two positions.

    The comparison preserves caller order and reports numeric
    differences as position_a minus position_b.
    """

    if not isinstance(position_a, str):
        raise TypeError(
            "position_a must be a string"
        )

    if not isinstance(position_b, str):
        raise TypeError(
            "position_b must be a string"
        )

    if not position_a:
        raise ValueError(
            "position_a must not be empty"
        )

    if not position_b:
        raise ValueError(
            "position_b must not be empty"
        )

    if position_a == position_b:
        raise ValueError(
            "position_a and position_b must be different"
        )

    if summary_a is None:
        raise TypeError(
            "summary_a must not be None"
        )

    if summary_b is None:
        raise TypeError(
            "summary_b must not be None"
        )

    return _build_comparison(
        position_a,
        position_b,
        summary_a,
        summary_b,
    )


def build_position_analytics_comparison_result(
    summaries: tuple[tuple[str, Any], ...],
) -> PositionAnalyticsComparisonResult:
    """
    Build all unique pairwise position comparisons.

    Position order follows the caller-provided order.
    """

    if not isinstance(
        summaries,
        tuple,
    ):
        summaries = tuple(summaries)

    positions = tuple(
        position
        for position, _ in summaries
    )

    if len(set(positions)) != len(positions):
        raise ValueError(
            "positions must not contain duplicates"
        )

    for position in positions:
        if not isinstance(position, str):
            raise TypeError(
                "each position must be a string"
            )

        if not position:
            raise ValueError(
                "position names must not be empty"
            )

    comparisons: list[
        PositionAnalyticsComparison
    ] = []

    for index, (
        position_a,
        summary_a,
    ) in enumerate(summaries):
        for (
            position_b,
            summary_b,
        ) in summaries[index + 1:]:
            comparisons.append(
                _build_comparison(
                    position_a,
                    position_b,
                    summary_a,
                    summary_b,
                )
            )

    return PositionAnalyticsComparisonResult(
        position_count=len(positions),
        positions=positions,
        comparison_count=len(comparisons),
        comparisons=tuple(comparisons),
    )


def get_position_analytics_comparison(
    result: PositionAnalyticsComparisonResult,
    position_a: str,
    position_b: str,
) -> PositionAnalyticsComparison:
    """Return a comparison using the exact caller pair order."""

    if not isinstance(
        result,
        PositionAnalyticsComparisonResult,
    ):
        raise TypeError(
            "result must be a "
            "PositionAnalyticsComparisonResult"
        )

    for comparison in result.comparisons:
        if (
            comparison.position_a == position_a
            and comparison.position_b == position_b
        ):
            return comparison

    raise KeyError(
        f"Comparison not found: {position_a} vs {position_b}"
    )


def iter_position_analytics_comparisons(
    result: PositionAnalyticsComparisonResult,
) -> tuple[PositionAnalyticsComparison, ...]:
    """Return comparisons in stable caller order."""

    if not isinstance(
        result,
        PositionAnalyticsComparisonResult,
    ):
        raise TypeError(
            "result must be a "
            "PositionAnalyticsComparisonResult"
        )

    return result.comparisons


def get_position_analytics_metric_difference(
    comparison: PositionAnalyticsComparison,
    metric_name: str,
) -> float:
    """Return one numeric metric difference."""

    if not isinstance(
        comparison,
        PositionAnalyticsComparison,
    ):
        raise TypeError(
            "comparison must be a PositionAnalyticsComparison"
        )

    if metric_name not in COMPARISON_METRICS:
        raise KeyError(
            f"Unknown comparison metric: {metric_name}"
        )

    differences = dict(
        comparison.metric_differences
    )

    return differences[metric_name]