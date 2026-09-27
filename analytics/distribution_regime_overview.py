from __future__ import annotations

from dataclasses import dataclass

from analytics.distribution_regime_detection import (
    DistributionRegimeDetectionResult,
)
from analytics.distribution_regime_transition_analysis import (
    DistributionRegimeTransitionAnalysisResult,
)
from analytics.distribution_regime_summary import (
    DistributionRegimeSummary,
    build_distribution_regime_summary_result,
)
from analytics.distribution_regime_stability import (
    DistributionRegimeStability,
    DistributionRegimeStabilityResult,
    build_distribution_regime_stability_result,
)


@dataclass(frozen=True)
class DistributionRegimeOverview:
    """Descriptive consolidated overview of distribution regimes."""

    position_count: int
    positions: tuple[str, ...]

    total_window_count: int
    total_valid_window_count: int
    total_insufficient_window_count: int

    total_transition_count: int
    total_unchanged_count: int
    total_missing_count: int

    transition_percentage: float
    unchanged_percentage: float
    missing_percentage: float

    concentrated_count: int
    balanced_count: int
    diverse_count: int
    insufficient_data_count: int

    concentrated_percentage: float
    balanced_percentage: float
    diverse_percentage: float
    insufficient_data_percentage: float

    high_stability_count: int
    medium_stability_count: int
    low_stability_count: int
    insufficient_stability_count: int

    average_stability_percentage: float
    minimum_stability_percentage: float | None
    maximum_stability_percentage: float | None

    summary: DistributionRegimeSummary
    stability_results: tuple[DistributionRegimeStability, ...]


def _calculate_average(values: list[float]) -> float:
    """Return the arithmetic mean, or zero for an empty collection."""

    if not values:
        return 0.0

    return sum(values) / len(values)


def _calculate_minimum(values: list[float]) -> float | None:
    """Return minimum value, or None when no values exist."""

    if not values:
        return None

    return min(values)


def _calculate_maximum(values: list[float]) -> float | None:
    """Return maximum value, or None when no values exist."""

    if not values:
        return None

    return max(values)


def build_distribution_regime_overview(
    detection_result: DistributionRegimeDetectionResult,
    transition_analysis_result: DistributionRegimeTransitionAnalysisResult,
) -> DistributionRegimeOverview:
    """
    Build a consolidated descriptive distribution-regime overview.

    The overview combines regime summary and regime stability results.
    """

    if not isinstance(
        detection_result,
        DistributionRegimeDetectionResult,
    ):
        raise TypeError(
            "detection_result must be a "
            "DistributionRegimeDetectionResult"
        )

    if not isinstance(
        transition_analysis_result,
        DistributionRegimeTransitionAnalysisResult,
    ):
        raise TypeError(
            "transition_analysis_result must be a "
            "DistributionRegimeTransitionAnalysisResult"
        )

    summary = build_distribution_regime_summary_result(
        detection_result,
        transition_analysis_result,
    )

    stability_result = build_distribution_regime_stability_result(
        detection_result,
        transition_analysis_result,
    )

    positions = tuple(detection_result.positions)

    if positions != stability_result.positions:
        raise ValueError(
            "Detection and stability positions must match"
        )

    stability_results = tuple(
        stability_result.stability_results
    )

    stability_percentages = [
        stability.stability_percentage
        for stability in stability_results
        if stability.stability_level != "INSUFFICIENT_DATA"
    ]

    high_stability_count = sum(
        stability.stability_level == "HIGH"
        for stability in stability_results
    )

    medium_stability_count = sum(
        stability.stability_level == "MEDIUM"
        for stability in stability_results
    )

    low_stability_count = sum(
        stability.stability_level == "LOW"
        for stability in stability_results
    )

    insufficient_stability_count = sum(
        stability.stability_level == "INSUFFICIENT_DATA"
        for stability in stability_results
    )

    return DistributionRegimeOverview(
        position_count=summary.position_count,
        positions=summary.positions,
        total_window_count=summary.total_window_count,
        total_valid_window_count=summary.total_valid_window_count,
        total_insufficient_window_count=(
            summary.total_insufficient_window_count
        ),
        total_transition_count=summary.total_transition_count,
        total_unchanged_count=summary.total_unchanged_count,
        total_missing_count=summary.total_missing_count,
        transition_percentage=summary.transition_percentage,
        unchanged_percentage=summary.unchanged_percentage,
        missing_percentage=summary.missing_percentage,
        concentrated_count=summary.concentrated_count,
        balanced_count=summary.balanced_count,
        diverse_count=summary.diverse_count,
        insufficient_data_count=summary.insufficient_data_count,
        concentrated_percentage=summary.concentrated_percentage,
        balanced_percentage=summary.balanced_percentage,
        diverse_percentage=summary.diverse_percentage,
        insufficient_data_percentage=(
            summary.insufficient_data_percentage
        ),
        high_stability_count=high_stability_count,
        medium_stability_count=medium_stability_count,
        low_stability_count=low_stability_count,
        insufficient_stability_count=insufficient_stability_count,
        average_stability_percentage=_calculate_average(
            stability_percentages
        ),
        minimum_stability_percentage=_calculate_minimum(
            stability_percentages
        ),
        maximum_stability_percentage=_calculate_maximum(
            stability_percentages
        ),
        summary=summary,
        stability_results=stability_results,
    )


def get_distribution_regime_overview_stability(
    overview: DistributionRegimeOverview,
    position: str,
) -> DistributionRegimeStability:
    """Return stability information for a specific position."""

    if not isinstance(
        overview,
        DistributionRegimeOverview,
    ):
        raise TypeError(
            "overview must be a DistributionRegimeOverview"
        )

    for stability in overview.stability_results:
        if stability.position == position:
            return stability

    raise KeyError(f"Unknown position: {position}")


def iter_distribution_regime_overview_stabilities(
    overview: DistributionRegimeOverview,
) -> tuple[DistributionRegimeStability, ...]:
    """Return all stability results in caller order."""

    if not isinstance(
        overview,
        DistributionRegimeOverview,
    ):
        raise TypeError(
            "overview must be a DistributionRegimeOverview"
        )

    return overview.stability_results


def get_distribution_regime_overview_summary(
    overview: DistributionRegimeOverview,
) -> DistributionRegimeSummary:
    """Return the underlying distribution-regime summary."""

    if not isinstance(
        overview,
        DistributionRegimeOverview,
    ):
        raise TypeError(
            "overview must be a DistributionRegimeOverview"
        )

    return overview.summary