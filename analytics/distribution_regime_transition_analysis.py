from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.distribution_regime_detection import (
    DistributionRegimeDetection,
    DistributionRegimeDetectionResult,
    DistributionRegimeWindow,
)


TRANSITION_TYPES = (
    "TRANSITION",
    "UNCHANGED",
    "MISSING",
)

MISSING_REGIME = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class DistributionRegimeTransition:
    position: str
    previous_window_index: int
    current_window_index: int
    previous_regime: str
    current_regime: str
    transition: str


@dataclass(frozen=True)
class DistributionRegimeTransitionAnalysis:
    position: str
    window_count: int
    transition_count: int
    transitions: tuple[
        DistributionRegimeTransition,
        ...,
    ]


@dataclass(frozen=True)
class DistributionRegimeTransitionAnalysisResult:
    position_count: int
    positions: tuple[str, ...]
    analyses: tuple[
        DistributionRegimeTransitionAnalysis,
        ...,
    ]


def _validate_window(
    window: DistributionRegimeWindow,
) -> None:
    if not isinstance(
        window,
        DistributionRegimeWindow,
    ):
        raise TypeError(
            "each window must be a DistributionRegimeWindow"
        )


def _validate_windows(
    windows: Iterable[DistributionRegimeWindow],
) -> tuple[DistributionRegimeWindow, ...]:
    if isinstance(windows, (str, bytes)):
        raise TypeError(
            "windows must be an iterable of DistributionRegimeWindow"
        )

    validated = []

    for window in windows:
        _validate_window(window)
        validated.append(window)

    return tuple(validated)


def _classify_transition(
    previous_regime: str,
    current_regime: str,
) -> str:
    if (
        previous_regime == MISSING_REGIME
        or current_regime == MISSING_REGIME
    ):
        return "MISSING"

    if previous_regime == current_regime:
        return "UNCHANGED"

    return "TRANSITION"


def build_distribution_regime_transition_analysis(
    detection: DistributionRegimeDetection,
) -> DistributionRegimeTransitionAnalysis:
    if not isinstance(
        detection,
        DistributionRegimeDetection,
    ):
        raise TypeError(
            "detection must be a DistributionRegimeDetection"
        )

    windows = _validate_windows(
        detection.windows
    )

    transitions = []

    for previous_window, current_window in zip(
        windows,
        windows[1:],
    ):
        transitions.append(
            DistributionRegimeTransition(
                position=detection.position,
                previous_window_index=(
                    previous_window.window_index
                ),
                current_window_index=(
                    current_window.window_index
                ),
                previous_regime=(
                    previous_window.regime
                ),
                current_regime=(
                    current_window.regime
                ),
                transition=_classify_transition(
                    previous_window.regime,
                    current_window.regime,
                ),
            )
        )

    return DistributionRegimeTransitionAnalysis(
        position=detection.position,
        window_count=len(windows),
        transition_count=len(transitions),
        transitions=tuple(transitions),
    )


def build_distribution_regime_transition_analysis_result(
    detection_result: DistributionRegimeDetectionResult,
) -> DistributionRegimeTransitionAnalysisResult:
    if not isinstance(
        detection_result,
        DistributionRegimeDetectionResult,
    ):
        raise TypeError(
            "detection_result must be a "
            "DistributionRegimeDetectionResult"
        )

    analyses = tuple(
        build_distribution_regime_transition_analysis(
            detection
        )
        for detection in detection_result.detections
    )

    return DistributionRegimeTransitionAnalysisResult(
        position_count=len(analyses),
        positions=tuple(
            analysis.position
            for analysis in analyses
        ),
        analyses=analyses,
    )


def get_distribution_regime_transition_analysis(
    result: DistributionRegimeTransitionAnalysisResult,
    position: str,
) -> DistributionRegimeTransitionAnalysis:
    if not isinstance(
        result,
        DistributionRegimeTransitionAnalysisResult,
    ):
        raise TypeError(
            "result must be a "
            "DistributionRegimeTransitionAnalysisResult"
        )

    if not isinstance(position, str):
        raise TypeError(
            "position must be a string"
        )

    for analysis in result.analyses:
        if analysis.position == position:
            return analysis

    raise ValueError(
        f"Distribution regime transition analysis "
        f"not found for {position}"
    )


def iter_distribution_regime_transition_analyses(
    result: DistributionRegimeTransitionAnalysisResult,
) -> tuple[
    DistributionRegimeTransitionAnalysis,
    ...,
]:
    if not isinstance(
        result,
        DistributionRegimeTransitionAnalysisResult,
    ):
        raise TypeError(
            "result must be a "
            "DistributionRegimeTransitionAnalysisResult"
        )

    return result.analyses


def get_distribution_regime_transition(
    analysis: DistributionRegimeTransitionAnalysis,
    transition_index: int,
) -> DistributionRegimeTransition:
    if not isinstance(
        analysis,
        DistributionRegimeTransitionAnalysis,
    ):
        raise TypeError(
            "analysis must be a "
            "DistributionRegimeTransitionAnalysis"
        )

    if isinstance(transition_index, bool):
        raise TypeError(
            "transition_index must be an integer"
        )

    if not isinstance(
        transition_index,
        int,
    ):
        raise TypeError(
            "transition_index must be an integer"
        )

    if transition_index < 1:
        raise ValueError(
            "transition_index must be greater than zero"
        )

    try:
        return analysis.transitions[
            transition_index - 1
        ]
    except IndexError as exc:
        raise ValueError(
            f"Distribution regime transition "
            f"not found: {transition_index}"
        ) from exc


def iter_distribution_regime_transitions(
    analysis: DistributionRegimeTransitionAnalysis,
) -> tuple[
    DistributionRegimeTransition,
    ...,
]:
    if not isinstance(
        analysis,
        DistributionRegimeTransitionAnalysis,
    ):
        raise TypeError(
            "analysis must be a "
            "DistributionRegimeTransitionAnalysis"
        )

    return analysis.transitions