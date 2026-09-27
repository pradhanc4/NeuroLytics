from __future__ import annotations

from datetime import date

import pytest

from analytics.distribution_regime_detection import (
    DistributionRegimeDetection,
    DistributionRegimeDetectionResult,
    DistributionRegimeWindow,
)
from analytics.distribution_regime_transition_analysis import (
    DistributionRegimeTransition,
    DistributionRegimeTransitionAnalysis,
    DistributionRegimeTransitionAnalysisResult,
)
from analytics.distribution_regime_overview import (
    DistributionRegimeOverview,
    build_distribution_regime_overview,
    get_distribution_regime_overview_stability,
    get_distribution_regime_overview_summary,
    iter_distribution_regime_overview_stabilities,
)


def make_window(
    position: str,
    window_index: int,
    regime: str,
) -> DistributionRegimeWindow:
    return DistributionRegimeWindow(
        position=position,
        window_index=window_index,
        start_date=date(2026, 1, window_index),
        end_date=date(2026, 1, window_index + 1),
        observation_count=5,
        frequency_total=5,
        dominant_digit=1,
        dominant_digit_percentage=60.0,
        distribution_mean=1.0,
        distribution_std=0.0,
        entropy=2.0,
        regime=regime,
    )


def make_detection(
    position: str,
    regimes: tuple[str, ...],
) -> DistributionRegimeDetection:
    windows = tuple(
        make_window(
            position,
            index + 1,
            regime,
        )
        for index, regime in enumerate(regimes)
    )

    return DistributionRegimeDetection(
        position=position,
        window_size=5,
        window_count=len(windows),
        valid_window_count=sum(
            regime != "INSUFFICIENT_DATA"
            for regime in regimes
        ),
        windows=windows,
    )


def make_transition(
    position: str,
    previous_window_index: int,
    current_window_index: int,
    previous_regime: str,
    current_regime: str,
    transition: str,
) -> DistributionRegimeTransition:
    return DistributionRegimeTransition(
        position=position,
        previous_window_index=previous_window_index,
        current_window_index=current_window_index,
        previous_regime=previous_regime,
        current_regime=current_regime,
        transition=transition,
    )


def make_transition_analysis(
    position: str,
    transitions: tuple[DistributionRegimeTransition, ...],
) -> DistributionRegimeTransitionAnalysis:
    return DistributionRegimeTransitionAnalysis(
        position=position,
        window_count=4,
        transition_count=len(transitions),
        transitions=transitions,
    )


def test_build_overview_combines_summary_and_stability():
    detection_result = DistributionRegimeDetectionResult(
        position_count=2,
        positions=("col1", "col2"),
        detections=(
            make_detection(
                "col1",
                (
                    "BALANCED",
                    "BALANCED",
                    "DIVERSE",
                ),
            ),
            make_detection(
                "col2",
                (
                    "DIVERSE",
                    "DIVERSE",
                    "CONCENTRATED",
                ),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=2,
        positions=("col1", "col2"),
        analyses=(
            make_transition_analysis(
                "col1",
                (
                    make_transition(
                        "col1",
                        1,
                        2,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                    make_transition(
                        "col1",
                        2,
                        3,
                        "BALANCED",
                        "DIVERSE",
                        "TRANSITION",
                    ),
                ),
            ),
            make_transition_analysis(
                "col2",
                (
                    make_transition(
                        "col2",
                        1,
                        2,
                        "DIVERSE",
                        "DIVERSE",
                        "UNCHANGED",
                    ),
                    make_transition(
                        "col2",
                        2,
                        3,
                        "DIVERSE",
                        "CONCENTRATED",
                        "TRANSITION",
                    ),
                ),
            ),
        ),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    assert isinstance(
        overview,
        DistributionRegimeOverview,
    )

    assert overview.position_count == 2
    assert overview.positions == ("col1", "col2")

    assert overview.total_window_count == 6
    assert overview.total_valid_window_count == 6
    assert overview.total_insufficient_window_count == 0

    assert overview.total_transition_count == 2
    assert overview.total_unchanged_count == 2
    assert overview.total_missing_count == 0

    assert overview.concentrated_count == 1
    assert overview.balanced_count == 2
    assert overview.diverse_count == 3


def test_overview_contains_stability_counts():
    detection_result = DistributionRegimeDetectionResult(
        position_count=3,
        positions=("col1", "col2", "col3"),
        detections=(
            make_detection(
                "col1",
                (
                    "BALANCED",
                    "BALANCED",
                    "BALANCED",
                    "BALANCED",
                ),
            ),
            make_detection(
                "col2",
                (
                    "BALANCED",
                    "BALANCED",
                    "DIVERSE",
                    "DIVERSE",
                ),
            ),
            make_detection(
                "col3",
                (
                    "BALANCED",
                    "DIVERSE",
                    "CONCENTRATED",
                    "DIVERSE",
                ),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=3,
        positions=("col1", "col2", "col3"),
        analyses=(
            make_transition_analysis(
                "col1",
                (
                    make_transition(
                        "col1",
                        1,
                        2,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                    make_transition(
                        "col1",
                        2,
                        3,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                    make_transition(
                        "col1",
                        3,
                        4,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                ),
            ),
            make_transition_analysis(
                "col2",
                (
                    make_transition(
                        "col2",
                        1,
                        2,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                    make_transition(
                        "col2",
                        2,
                        3,
                        "BALANCED",
                        "DIVERSE",
                        "TRANSITION",
                    ),
                    make_transition(
                        "col2",
                        3,
                        4,
                        "DIVERSE",
                        "DIVERSE",
                        "UNCHANGED",
                    ),
                ),
            ),
            make_transition_analysis(
                "col3",
                (
                    make_transition(
                        "col3",
                        1,
                        2,
                        "BALANCED",
                        "DIVERSE",
                        "TRANSITION",
                    ),
                    make_transition(
                        "col3",
                        2,
                        3,
                        "DIVERSE",
                        "CONCENTRATED",
                        "TRANSITION",
                    ),
                    make_transition(
                        "col3",
                        3,
                        4,
                        "CONCENTRATED",
                        "DIVERSE",
                        "TRANSITION",
                    ),
                ),
            ),
        ),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    assert overview.high_stability_count == 1
    assert overview.medium_stability_count == 1
    assert overview.low_stability_count == 1
    assert overview.insufficient_stability_count == 0


def test_overview_calculates_average_stability():
    detection_result = DistributionRegimeDetectionResult(
        position_count=2,
        positions=("col1", "col2"),
        detections=(
            make_detection(
                "col1",
                (
                    "BALANCED",
                    "BALANCED",
                    "BALANCED",
                ),
            ),
            make_detection(
                "col2",
                (
                    "BALANCED",
                    "DIVERSE",
                    "DIVERSE",
                ),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=2,
        positions=("col1", "col2"),
        analyses=(
            make_transition_analysis(
                "col1",
                (
                    make_transition(
                        "col1",
                        1,
                        2,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                    make_transition(
                        "col1",
                        2,
                        3,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                ),
            ),
            make_transition_analysis(
                "col2",
                (
                    make_transition(
                        "col2",
                        1,
                        2,
                        "BALANCED",
                        "DIVERSE",
                        "TRANSITION",
                    ),
                    make_transition(
                        "col2",
                        2,
                        3,
                        "DIVERSE",
                        "DIVERSE",
                        "UNCHANGED",
                    ),
                ),
            ),
        ),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    assert overview.minimum_stability_percentage == 50.0
    assert overview.maximum_stability_percentage == 100.0
    assert overview.average_stability_percentage == 75.0


def test_insufficient_stability_is_excluded_from_average():
    detection_result = DistributionRegimeDetectionResult(
        position_count=2,
        positions=("col1", "col2"),
        detections=(
            make_detection(
                "col1",
                (
                    "BALANCED",
                    "BALANCED",
                    "BALANCED",
                ),
            ),
            make_detection(
                "col2",
                (
                    "INSUFFICIENT_DATA",
                    "INSUFFICIENT_DATA",
                    "INSUFFICIENT_DATA",
                ),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=2,
        positions=("col1", "col2"),
        analyses=(
            make_transition_analysis(
                "col1",
                (
                    make_transition(
                        "col1",
                        1,
                        2,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                    make_transition(
                        "col1",
                        2,
                        3,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                ),
            ),
            make_transition_analysis(
                "col2",
                (
                    make_transition(
                        "col2",
                        1,
                        2,
                        "INSUFFICIENT_DATA",
                        "INSUFFICIENT_DATA",
                        "MISSING",
                    ),
                    make_transition(
                        "col2",
                        2,
                        3,
                        "INSUFFICIENT_DATA",
                        "INSUFFICIENT_DATA",
                        "MISSING",
                    ),
                ),
            ),
        ),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    assert overview.high_stability_count == 1
    assert overview.insufficient_stability_count == 1

    assert overview.average_stability_percentage == 100.0
    assert overview.minimum_stability_percentage == 100.0
    assert overview.maximum_stability_percentage == 100.0


def test_all_insufficient_stability_returns_zero_average_and_none_min_max():
    detection_result = DistributionRegimeDetectionResult(
        position_count=1,
        positions=("col1",),
        detections=(
            make_detection(
                "col1",
                (
                    "INSUFFICIENT_DATA",
                    "INSUFFICIENT_DATA",
                ),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=1,
        positions=("col1",),
        analyses=(
            make_transition_analysis(
                "col1",
                (
                    make_transition(
                        "col1",
                        1,
                        2,
                        "INSUFFICIENT_DATA",
                        "INSUFFICIENT_DATA",
                        "MISSING",
                    ),
                ),
            ),
        ),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    assert overview.average_stability_percentage == 0.0
    assert overview.minimum_stability_percentage is None
    assert overview.maximum_stability_percentage is None
    assert overview.insufficient_stability_count == 1


def test_get_position_stability():
    detection_result = DistributionRegimeDetectionResult(
        position_count=1,
        positions=("col1",),
        detections=(
            make_detection(
                "col1",
                (
                    "BALANCED",
                    "BALANCED",
                ),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=1,
        positions=("col1",),
        analyses=(
            make_transition_analysis(
                "col1",
                (
                    make_transition(
                        "col1",
                        1,
                        2,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                ),
            ),
        ),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    stability = get_distribution_regime_overview_stability(
        overview,
        "col1",
    )

    assert stability.position == "col1"
    assert stability.stability_level == "HIGH"


def test_get_unknown_position_stability_raises():
    detection_result = DistributionRegimeDetectionResult(
        position_count=1,
        positions=("col1",),
        detections=(
            make_detection(
                "col1",
                ("BALANCED",),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=1,
        positions=("col1",),
        analyses=(
            make_transition_analysis(
                "col1",
                (),
            ),
        ),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    with pytest.raises(KeyError):
        get_distribution_regime_overview_stability(
            overview,
            "col2",
        )


def test_iter_stabilities_returns_caller_order():
    detection_result = DistributionRegimeDetectionResult(
        position_count=2,
        positions=("col2", "col1"),
        detections=(
            make_detection(
                "col2",
                ("BALANCED", "BALANCED"),
            ),
            make_detection(
                "col1",
                ("DIVERSE", "BALANCED"),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=2,
        positions=("col2", "col1"),
        analyses=(
            make_transition_analysis(
                "col2",
                (
                    make_transition(
                        "col2",
                        1,
                        2,
                        "BALANCED",
                        "BALANCED",
                        "UNCHANGED",
                    ),
                ),
            ),
            make_transition_analysis(
                "col1",
                (
                    make_transition(
                        "col1",
                        1,
                        2,
                        "DIVERSE",
                        "BALANCED",
                        "TRANSITION",
                    ),
                ),
            ),
        ),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    values = iter_distribution_regime_overview_stabilities(
        overview,
    )

    assert isinstance(values, tuple)

    assert tuple(
        item.position
        for item in values
    ) == ("col2", "col1")


def test_get_summary_returns_underlying_summary():
    detection_result = DistributionRegimeDetectionResult(
        position_count=1,
        positions=("col1",),
        detections=(
            make_detection(
                "col1",
                (
                    "BALANCED",
                    "DIVERSE",
                ),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=1,
        positions=("col1",),
        analyses=(
            make_transition_analysis(
                "col1",
                (
                    make_transition(
                        "col1",
                        1,
                        2,
                        "BALANCED",
                        "DIVERSE",
                        "TRANSITION",
                    ),
                ),
            ),
        ),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    summary = get_distribution_regime_overview_summary(
        overview,
    )

    assert summary is overview.summary
    assert summary.position_count == 1


def test_invalid_detection_type_raises():
    with pytest.raises(TypeError):
        build_distribution_regime_overview(
            "invalid",
            "invalid",
        )


def test_invalid_transition_result_type_raises():
    detection_result = DistributionRegimeDetectionResult(
        position_count=0,
        positions=(),
        detections=(),
    )

    with pytest.raises(TypeError):
        build_distribution_regime_overview(
            detection_result,
            "invalid",
        )


def test_invalid_overview_type_for_stability_getter_raises():
    with pytest.raises(TypeError):
        get_distribution_regime_overview_stability(
            "invalid",
            "col1",
        )


def test_invalid_overview_type_for_iterator_raises():
    with pytest.raises(TypeError):
        iter_distribution_regime_overview_stabilities(
            "invalid",
        )


def test_invalid_overview_type_for_summary_getter_raises():
    with pytest.raises(TypeError):
        get_distribution_regime_overview_summary(
            "invalid",
        )


def test_empty_results_produce_empty_overview():
    detection_result = DistributionRegimeDetectionResult(
        position_count=0,
        positions=(),
        detections=(),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=0,
        positions=(),
        analyses=(),
    )

    overview = build_distribution_regime_overview(
        detection_result,
        transition_result,
    )

    assert overview.position_count == 0
    assert overview.positions == ()

    assert overview.total_window_count == 0
    assert overview.total_valid_window_count == 0
    assert overview.total_insufficient_window_count == 0

    assert overview.total_transition_count == 0
    assert overview.total_unchanged_count == 0
    assert overview.total_missing_count == 0

    assert overview.average_stability_percentage == 0.0
    assert overview.minimum_stability_percentage is None
    assert overview.maximum_stability_percentage is None

    assert overview.high_stability_count == 0
    assert overview.medium_stability_count == 0
    assert overview.low_stability_count == 0
    assert overview.insufficient_stability_count == 0

    assert overview.stability_results == ()