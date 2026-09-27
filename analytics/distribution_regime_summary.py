from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.distribution_regime_detection import (
    DistributionRegimeDetection,
    DistributionRegimeDetectionResult,
    DistributionRegimeWindow,
)
from analytics.distribution_regime_transition_analysis import (
    DistributionRegimeTransitionAnalysis,
    DistributionRegimeTransitionAnalysisResult,
    DistributionRegimeTransition,
)


REGIMES = (
    "CONCENTRATED",
    "BALANCED",
    "DIVERSE",
    "INSUFFICIENT_DATA",
)

TRANSITION_TYPES = (
    "TRANSITION",
    "UNCHANGED",
    "MISSING",
)

POSITIONS = (
    "col1",
    "col2",
    "col3",
    "col4",
    "col5",
    "col6",
    "col7",
    "col8",
)


@dataclass(frozen=True)
class DistributionRegimePositionSummary:
    """Descriptive regime summary for one position."""

    position: str

    window_count: int
    valid_window_count: int
    insufficient_window_count: int

    transition_count: int
    unchanged_count: int
    missing_count: int

    regime_transition_percentage: float
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

    transition_type_counts: tuple[tuple[str, int], ...]
    regime_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class DistributionRegimeSummary:
    """Aggregate descriptive summary of distribution regimes."""

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

    transition_type_counts: tuple[tuple[str, int], ...]
    regime_counts: tuple[tuple[str, int], ...]

    position_summaries: tuple[DistributionRegimePositionSummary, ...]


def _percentage(value: int, total: int) -> float:
    """Return percentage while safely handling zero denominators."""

    if total <= 0:
        return 0.0

    return (value / total) * 100.0


def _count_regimes(
    windows: Iterable[DistributionRegimeWindow],
) -> dict[str, int]:
    """Count each supported regime."""

    counts = {regime: 0 for regime in REGIMES}

    for window in windows:
        regime = window.regime

        if regime not in counts:
            raise ValueError(f"Unsupported distribution regime: {regime}")

        counts[regime] += 1

    return counts


def _count_transitions(
    transitions: Iterable[DistributionRegimeTransition],
) -> dict[str, int]:
    """Count each supported transition type."""

    counts = {transition_type: 0 for transition_type in TRANSITION_TYPES}

    for transition in transitions:
        transition_type = transition.transition

        if transition_type not in counts:
            raise ValueError(
                f"Unsupported distribution regime transition type: "
                f"{transition_type}"
            )

        counts[transition_type] += 1

    return counts


def _build_position_summary(
    detection: DistributionRegimeDetection,
    transition_analysis: DistributionRegimeTransitionAnalysis,
) -> DistributionRegimePositionSummary:
    """Build a descriptive summary for one position."""

    if detection.position != transition_analysis.position:
        raise ValueError(
            "Detection position and transition-analysis position must match"
        )

    windows = tuple(detection.windows)
    transitions = tuple(transition_analysis.transitions)

    window_count = len(windows)

    regime_counts = _count_regimes(windows)

    valid_window_count = (
        regime_counts["CONCENTRATED"]
        + regime_counts["BALANCED"]
        + regime_counts["DIVERSE"]
    )

    insufficient_window_count = regime_counts["INSUFFICIENT_DATA"]

    transition_counts = _count_transitions(transitions)

    transition_count = transition_counts["TRANSITION"]
    unchanged_count = transition_counts["UNCHANGED"]
    missing_count = transition_counts["MISSING"]

    transition_type_total = len(transitions)

    return DistributionRegimePositionSummary(
        position=detection.position,
        window_count=window_count,
        valid_window_count=valid_window_count,
        insufficient_window_count=insufficient_window_count,
        transition_count=transition_count,
        unchanged_count=unchanged_count,
        missing_count=missing_count,
        regime_transition_percentage=_percentage(
            transition_count,
            transition_type_total,
        ),
        unchanged_percentage=_percentage(
            unchanged_count,
            transition_type_total,
        ),
        missing_percentage=_percentage(
            missing_count,
            transition_type_total,
        ),
        concentrated_count=regime_counts["CONCENTRATED"],
        balanced_count=regime_counts["BALANCED"],
        diverse_count=regime_counts["DIVERSE"],
        insufficient_data_count=regime_counts["INSUFFICIENT_DATA"],
        concentrated_percentage=_percentage(
            regime_counts["CONCENTRATED"],
            window_count,
        ),
        balanced_percentage=_percentage(
            regime_counts["BALANCED"],
            window_count,
        ),
        diverse_percentage=_percentage(
            regime_counts["DIVERSE"],
            window_count,
        ),
        insufficient_data_percentage=_percentage(
            regime_counts["INSUFFICIENT_DATA"],
            window_count,
        ),
        transition_type_counts=tuple(
            (transition_type, transition_counts[transition_type])
            for transition_type in TRANSITION_TYPES
        ),
        regime_counts=tuple(
            (regime, regime_counts[regime])
            for regime in REGIMES
        ),
    )


def build_distribution_regime_summary(
    detection: DistributionRegimeDetection,
    transition_analysis: DistributionRegimeTransitionAnalysis,
) -> DistributionRegimePositionSummary:
    """
    Build a descriptive distribution-regime summary for one position.

    The detection and transition-analysis objects must belong to the
    same position.
    """

    if not isinstance(detection, DistributionRegimeDetection):
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

    return _build_position_summary(
        detection,
        transition_analysis,
    )


def build_distribution_regime_summary_result(
    detection_result: DistributionRegimeDetectionResult,
    transition_analysis_result: DistributionRegimeTransitionAnalysisResult,
) -> DistributionRegimeSummary:
    """
    Build the complete distribution-regime summary.

    Position order follows the caller-provided detection result order.
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

    position_summaries = tuple(
        _build_position_summary(
            detection_by_position[position],
            transition_by_position[position],
        )
        for position in positions
    )

    total_window_count = sum(
        summary.window_count
        for summary in position_summaries
    )

    total_valid_window_count = sum(
        summary.valid_window_count
        for summary in position_summaries
    )

    total_insufficient_window_count = sum(
        summary.insufficient_window_count
        for summary in position_summaries
    )

    total_transition_count = sum(
        summary.transition_count
        for summary in position_summaries
    )

    total_unchanged_count = sum(
        summary.unchanged_count
        for summary in position_summaries
    )

    total_missing_count = sum(
        summary.missing_count
        for summary in position_summaries
    )

    concentrated_count = sum(
        summary.concentrated_count
        for summary in position_summaries
    )

    balanced_count = sum(
        summary.balanced_count
        for summary in position_summaries
    )

    diverse_count = sum(
        summary.diverse_count
        for summary in position_summaries
    )

    insufficient_data_count = sum(
        summary.insufficient_data_count
        for summary in position_summaries
    )

    transition_type_counts = tuple(
        (
            transition_type,
            sum(
                dict(summary.transition_type_counts).get(
                    transition_type,
                    0,
                )
                for summary in position_summaries
            ),
        )
        for transition_type in TRANSITION_TYPES
    )

    regime_counts = tuple(
        (
            regime,
            sum(
                dict(summary.regime_counts).get(regime, 0)
                for summary in position_summaries
            ),
        )
        for regime in REGIMES
    )

    total_transition_observations = (
        total_transition_count
        + total_unchanged_count
        + total_missing_count
    )

    return DistributionRegimeSummary(
        position_count=len(positions),
        positions=positions,
        total_window_count=total_window_count,
        total_valid_window_count=total_valid_window_count,
        total_insufficient_window_count=total_insufficient_window_count,
        total_transition_count=total_transition_count,
        total_unchanged_count=total_unchanged_count,
        total_missing_count=total_missing_count,
        transition_percentage=_percentage(
            total_transition_count,
            total_transition_observations,
        ),
        unchanged_percentage=_percentage(
            total_unchanged_count,
            total_transition_observations,
        ),
        missing_percentage=_percentage(
            total_missing_count,
            total_transition_observations,
        ),
        concentrated_count=concentrated_count,
        balanced_count=balanced_count,
        diverse_count=diverse_count,
        insufficient_data_count=insufficient_data_count,
        concentrated_percentage=_percentage(
            concentrated_count,
            total_window_count,
        ),
        balanced_percentage=_percentage(
            balanced_count,
            total_window_count,
        ),
        diverse_percentage=_percentage(
            diverse_count,
            total_window_count,
        ),
        insufficient_data_percentage=_percentage(
            insufficient_data_count,
            total_window_count,
        ),
        transition_type_counts=transition_type_counts,
        regime_counts=regime_counts,
        position_summaries=position_summaries,
    )


def get_distribution_regime_summary(
    summary: DistributionRegimeSummary,
    position: str,
) -> DistributionRegimePositionSummary:
    """Return the summary for a specific position."""

    if not isinstance(summary, DistributionRegimeSummary):
        raise TypeError(
            "summary must be a DistributionRegimeSummary"
        )

    for position_summary in summary.position_summaries:
        if position_summary.position == position:
            return position_summary

    raise KeyError(f"Unknown position: {position}")


def iter_distribution_regime_position_summaries(
    summary: DistributionRegimeSummary,
) -> tuple[DistributionRegimePositionSummary, ...]:
    """Return position summaries in caller order."""

    if not isinstance(summary, DistributionRegimeSummary):
        raise TypeError(
            "summary must be a DistributionRegimeSummary"
        )

    return summary.position_summaries


def get_distribution_regime_transition_count(
    summary: DistributionRegimeSummary,
    transition_type: str,
) -> int:
    """Return the aggregate count for one transition type."""

    if not isinstance(summary, DistributionRegimeSummary):
        raise TypeError(
            "summary must be a DistributionRegimeSummary"
        )

    if transition_type not in TRANSITION_TYPES:
        raise ValueError(
            f"Unsupported transition type: {transition_type}"
        )

    return dict(summary.transition_type_counts).get(
        transition_type,
        0,
    )


def get_distribution_regime_count(
    summary: DistributionRegimeSummary,
    regime: str,
) -> int:
    """Return the aggregate count for one regime."""

    if not isinstance(summary, DistributionRegimeSummary):
        raise TypeError(
            "summary must be a DistributionRegimeSummary"
        )

    if regime not in REGIMES:
        raise ValueError(
            f"Unsupported regime: {regime}"
        )

    return dict(summary.regime_counts).get(regime, 0)