from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.distribution_regime_detection import (
    DistributionRegimeDetection,
    DistributionRegimeDetectionResult,
)
from analytics.distribution_regime_transition_analysis import (
    DistributionRegimeTransitionAnalysis,
    DistributionRegimeTransitionAnalysisResult,
)


STABILITY_LEVELS = (
    "HIGH",
    "MEDIUM",
    "LOW",
    "INSUFFICIENT_DATA",
)


@dataclass(frozen=True)
class DistributionRegimeStability:
    """Descriptive stability analysis for one position."""

    position: str

    window_count: int
    valid_window_count: int
    insufficient_window_count: int

    transition_count: int
    unchanged_count: int
    missing_count: int

    comparable_transition_count: int

    regime_consistency_percentage: float
    stability_percentage: float
    stability_level: str


@dataclass(frozen=True)
class DistributionRegimeStabilityResult:
    """Collection of distribution-regime stability analyses."""

    position_count: int
    positions: tuple[str, ...]
    stability_results: tuple[DistributionRegimeStability, ...]


def _percentage(value: int, total: int) -> float:
    """Return percentage safely when the denominator is zero."""

    if total <= 0:
        return 0.0

    return (value / total) * 100.0


def _classify_stability(
    consistency_percentage: float,
    comparable_transition_count: int,
) -> str:
    """Classify descriptive regime stability."""

    if comparable_transition_count <= 0:
        return "INSUFFICIENT_DATA"

    if consistency_percentage >= 80.0:
        return "HIGH"

    if consistency_percentage >= 50.0:
        return "MEDIUM"

    return "LOW"


def _build_stability(
    detection: DistributionRegimeDetection,
    transition_analysis: DistributionRegimeTransitionAnalysis,
) -> DistributionRegimeStability:
    """Build stability analysis for one position."""

    if detection.position != transition_analysis.position:
        raise ValueError(
            "Detection position and transition-analysis position "
            "must match"
        )

    windows = tuple(detection.windows)
    transitions = tuple(transition_analysis.transitions)

    window_count = len(windows)

    valid_window_count = sum(
        window.regime != "INSUFFICIENT_DATA"
        for window in windows
    )

    insufficient_window_count = (
        window_count - valid_window_count
    )

    transition_count = sum(
        transition.transition == "TRANSITION"
        for transition in transitions
    )

    unchanged_count = sum(
        transition.transition == "UNCHANGED"
        for transition in transitions
    )

    missing_count = sum(
        transition.transition == "MISSING"
        for transition in transitions
    )

    comparable_transition_count = (
        transition_count + unchanged_count
    )

    regime_consistency_percentage = _percentage(
        unchanged_count,
        comparable_transition_count,
    )

    stability_percentage = regime_consistency_percentage

    stability_level = _classify_stability(
        regime_consistency_percentage,
        comparable_transition_count,
    )

    return DistributionRegimeStability(
        position=detection.position,
        window_count=window_count,
        valid_window_count=valid_window_count,
        insufficient_window_count=insufficient_window_count,
        transition_count=transition_count,
        unchanged_count=unchanged_count,
        missing_count=missing_count,
        comparable_transition_count=comparable_transition_count,
        regime_consistency_percentage=regime_consistency_percentage,
        stability_percentage=stability_percentage,
        stability_level=stability_level,
    )


def build_distribution_regime_stability(
    detection: DistributionRegimeDetection,
    transition_analysis: DistributionRegimeTransitionAnalysis,
) -> DistributionRegimeStability:
    """
    Build descriptive regime stability for one position.

    Missing transitions are excluded from the comparable-transition
    denominator.
    """

    if not isinstance(
        detection,
        DistributionRegimeDetection,
    ):
        raise TypeError(
            "detection must be a DistributionRegimeDetection"
        )

    if not isinstance(
        transition_analysis,
        DistributionRegimeTransitionAnalysis,
    ):
        raise TypeError(
            "transition_analysis must be a "
            "DistributionRegimeTransitionAnalysis"
        )

    return _build_stability(
        detection,
        transition_analysis,
    )


def build_distribution_regime_stability_result(
    detection_result: DistributionRegimeDetectionResult,
    transition_analysis_result: DistributionRegimeTransitionAnalysisResult,
) -> DistributionRegimeStabilityResult:
    """
    Build stability analysis for all positions.

    Position order follows detection_result.positions.
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

    detection_by_position = {
        detection.position: detection
        for detection in detection_result.detections
    }

    transition_by_position = {
        analysis.position: analysis
        for analysis in transition_analysis_result.analyses
    }

    if set(detection_by_position) != set(transition_by_position):
        raise ValueError(
            "Detection and transition-analysis results must contain "
            "the same positions"
        )

    positions = tuple(detection_result.positions)

    stability_results = tuple(
        _build_stability(
            detection_by_position[position],
            transition_by_position[position],
        )
        for position in positions
    )

    return DistributionRegimeStabilityResult(
        position_count=len(positions),
        positions=positions,
        stability_results=stability_results,
    )


def get_distribution_regime_stability(
    result: DistributionRegimeStabilityResult,
    position: str,
) -> DistributionRegimeStability:
    """Return stability analysis for a specific position."""

    if not isinstance(
        result,
        DistributionRegimeStabilityResult,
    ):
        raise TypeError(
            "result must be a DistributionRegimeStabilityResult"
        )

    for stability in result.stability_results:
        if stability.position == position:
            return stability

    raise KeyError(f"Unknown position: {position}")


def iter_distribution_regime_stabilities(
    result: DistributionRegimeStabilityResult,
) -> tuple[DistributionRegimeStability, ...]:
    """Return stability results in caller order."""

    if not isinstance(
        result,
        DistributionRegimeStabilityResult,
    ):
        raise TypeError(
            "result must be a DistributionRegimeStabilityResult"
        )

    return result.stability_results


def get_distribution_regime_stability_level(
    result: DistributionRegimeStabilityResult,
    position: str,
) -> str:
    """Return the stability level for a specific position."""

    stability = get_distribution_regime_stability(
        result,
        position,
    )

    return stability.stability_level


def get_distribution_regime_stability_percentage(
    result: DistributionRegimeStabilityResult,
    position: str,
) -> float:
    """Return the stability percentage for a specific position."""

    stability = get_distribution_regime_stability(
        result,
        position,
    )

    return stability.stability_percentage