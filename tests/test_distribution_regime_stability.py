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
from analytics.distribution_regime_stability import (
    STABILITY_LEVELS,
    DistributionRegimeStability,
    DistributionRegimeStabilityResult,
    build_distribution_regime_stability,
    build_distribution_regime_stability_result,
    get_distribution_regime_stability,
    get_distribution_regime_stability_level,
    get_distribution_regime_stability_percentage,
    iter_distribution_regime_stabilities,
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

    valid_window_count = sum(
        regime != "INSUFFICIENT_DATA"
        for regime in regimes
    )

    return DistributionRegimeDetection(
        position=position,
        window_size=5,
        window_count=len(windows),
        valid_window_count=valid_window_count,
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


def test_stability_levels_are_defined():
    assert STABILITY_LEVELS == (
        "HIGH",
        "MEDIUM",
        "LOW",
        "INSUFFICIENT_DATA",
    )


def test_high_stability():
    detection = make_detection(
        "col1",
        (
            "BALANCED",
            "BALANCED",
            "BALANCED",
            "BALANCED",
        ),
    )

    analysis = make_transition_analysis(
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
    )

    result = build_distribution_regime_stability(
        detection,
        analysis,
    )

    assert isinstance(result, DistributionRegimeStability)

    assert result.position == "col1"
    assert result.window_count == 4
    assert result.valid_window_count == 4
    assert result.insufficient_window_count == 0

    assert result.transition_count == 0
    assert result.unchanged_count == 3
    assert result.missing_count == 0

    assert result.comparable_transition_count == 3
    assert result.regime_consistency_percentage == 100.0
    assert result.stability_percentage == 100.0
    assert result.stability_level == "HIGH"


def test_medium_stability():
    detection = make_detection(
        "col1",
        (
            "BALANCED",
            "BALANCED",
            "DIVERSE",
            "DIVERSE",
            "DIVERSE",
        ),
    )

    analysis = make_transition_analysis(
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
            make_transition(
                "col1",
                3,
                4,
                "DIVERSE",
                "DIVERSE",
                "UNCHANGED",
            ),
            make_transition(
                "col1",
                4,
                5,
                "DIVERSE",
                "DIVERSE",
                "UNCHANGED",
            ),
        ),
    )

    result = build_distribution_regime_stability(
        detection,
        analysis,
    )

    assert result.comparable_transition_count == 4
    assert result.unchanged_count == 3
    assert result.transition_count == 1

    assert result.regime_consistency_percentage == 75.0
    assert result.stability_percentage == 75.0
    assert result.stability_level == "MEDIUM"


def test_low_stability():
    detection = make_detection(
        "col1",
        (
            "BALANCED",
            "DIVERSE",
            "CONCENTRATED",
            "DIVERSE",
        ),
    )

    analysis = make_transition_analysis(
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
            make_transition(
                "col1",
                2,
                3,
                "DIVERSE",
                "CONCENTRATED",
                "TRANSITION",
            ),
            make_transition(
                "col1",
                3,
                4,
                "CONCENTRATED",
                "DIVERSE",
                "TRANSITION",
            ),
        ),
    )

    result = build_distribution_regime_stability(
        detection,
        analysis,
    )

    assert result.comparable_transition_count == 3
    assert result.transition_count == 3
    assert result.unchanged_count == 0

    assert result.regime_consistency_percentage == 0.0
    assert result.stability_percentage == 0.0
    assert result.stability_level == "LOW"


def test_exact_80_percent_is_high():
    detection = make_detection(
        "col1",
        (
            "BALANCED",
            "BALANCED",
            "BALANCED",
            "BALANCED",
            "DIVERSE",
            "DIVERSE",
            "DIVERSE",
            "DIVERSE",
            "DIVERSE",
            "DIVERSE",
        ),
    )

    transitions = (
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
        make_transition(
            "col1",
            4,
            5,
            "BALANCED",
            "DIVERSE",
            "TRANSITION",
        ),
        make_transition(
            "col1",
            5,
            6,
            "DIVERSE",
            "DIVERSE",
            "UNCHANGED",
        ),
    )

    result = build_distribution_regime_stability(
        detection,
        make_transition_analysis(
            "col1",
            transitions,
        ),
    )

    assert result.regime_consistency_percentage == 80.0
    assert result.stability_level == "HIGH"


def test_exact_50_percent_is_medium():
    detection = make_detection(
        "col1",
        (
            "BALANCED",
            "BALANCED",
            "DIVERSE",
            "DIVERSE",
        ),
    )

    transitions = (
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
    )

    result = build_distribution_regime_stability(
        detection,
        make_transition_analysis(
            "col1",
            transitions,
        ),
    )

    assert result.regime_consistency_percentage == 50.0
    assert result.stability_level == "MEDIUM"


def test_missing_transitions_are_excluded_from_consistency():
    detection = make_detection(
        "col1",
        (
            "BALANCED",
            "BALANCED",
            "DIVERSE",
            "INSUFFICIENT_DATA",
        ),
    )

    transitions = (
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
        make_transition(
            "col1",
            3,
            4,
            "DIVERSE",
            "INSUFFICIENT_DATA",
            "MISSING",
        ),
    )

    result = build_distribution_regime_stability(
        detection,
        make_transition_analysis(
            "col1",
            transitions,
        ),
    )

    assert result.missing_count == 1
    assert result.comparable_transition_count == 2

    assert result.regime_consistency_percentage == 50.0
    assert result.stability_percentage == 50.0
    assert result.stability_level == "MEDIUM"


def test_all_missing_is_insufficient_data():
    detection = make_detection(
        "col1",
        (
            "INSUFFICIENT_DATA",
            "INSUFFICIENT_DATA",
            "INSUFFICIENT_DATA",
        ),
    )

    transitions = (
        make_transition(
            "col1",
            1,
            2,
            "INSUFFICIENT_DATA",
            "INSUFFICIENT_DATA",
            "MISSING",
        ),
        make_transition(
            "col1",
            2,
            3,
            "INSUFFICIENT_DATA",
            "INSUFFICIENT_DATA",
            "MISSING",
        ),
    )

    result = build_distribution_regime_stability(
        detection,
        make_transition_analysis(
            "col1",
            transitions,
        ),
    )

    assert result.window_count == 3
    assert result.valid_window_count == 0
    assert result.insufficient_window_count == 3

    assert result.transition_count == 0
    assert result.unchanged_count == 0
    assert result.missing_count == 2

    assert result.comparable_transition_count == 0
    assert result.regime_consistency_percentage == 0.0
    assert result.stability_percentage == 0.0
    assert result.stability_level == "INSUFFICIENT_DATA"


def test_no_transitions_is_insufficient_data():
    detection = make_detection(
        "col1",
        (
            "BALANCED",
            "BALANCED",
        ),
    )

    analysis = make_transition_analysis(
        "col1",
        (),
    )

    result = build_distribution_regime_stability(
        detection,
        analysis,
    )

    assert result.comparable_transition_count == 0
    assert result.stability_level == "INSUFFICIENT_DATA"


def test_position_mismatch_raises():
    detection = make_detection(
        "col1",
        ("BALANCED",),
    )

    analysis = make_transition_analysis(
        "col2",
        (),
    )

    with pytest.raises(ValueError):
        build_distribution_regime_stability(
            detection,
            analysis,
        )


def test_invalid_detection_type_raises():
    with pytest.raises(TypeError):
        build_distribution_regime_stability(
            "invalid",
            "invalid",
        )


def test_invalid_transition_analysis_type_raises():
    detection = make_detection(
        "col1",
        ("BALANCED",),
    )

    with pytest.raises(TypeError):
        build_distribution_regime_stability(
            detection,
            "invalid",
        )


def test_build_result_for_multiple_positions():
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
                        "DIVERSE",
                        "UNCHANGED",
                    ),
                ),
            ),
        ),
    )

    result = build_distribution_regime_stability_result(
        detection_result,
        transition_result,
    )

    assert isinstance(
        result,
        DistributionRegimeStabilityResult,
    )

    assert result.position_count == 2
    assert result.positions == ("col1", "col2")

    assert len(result.stability_results) == 2

    assert result.stability_results[0].position == "col1"
    assert result.stability_results[1].position == "col2"

    assert result.stability_results[0].stability_level == "MEDIUM"
    assert result.stability_results[1].stability_level == "HIGH"


def test_result_position_order_is_preserved():
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

    result = build_distribution_regime_stability_result(
        detection_result,
        transition_result,
    )

    assert result.positions == ("col2", "col1")

    assert tuple(
        item.position
        for item in result.stability_results
    ) == ("col2", "col1")


def test_mismatched_result_positions_raise():
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
        positions=("col2",),
        analyses=(
            make_transition_analysis(
                "col2",
                (),
            ),
        ),
    )

    with pytest.raises(ValueError):
        build_distribution_regime_stability_result(
            detection_result,
            transition_result,
        )


def test_invalid_result_types_raise():
    with pytest.raises(TypeError):
        build_distribution_regime_stability_result(
            "invalid",
            "invalid",
        )


def test_get_stability_for_position():
    detection_result = DistributionRegimeDetectionResult(
        position_count=1,
        positions=("col1",),
        detections=(
            make_detection(
                "col1",
                ("BALANCED", "BALANCED"),
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

    result = build_distribution_regime_stability_result(
        detection_result,
        transition_result,
    )

    stability = get_distribution_regime_stability(
        result,
        "col1",
    )

    assert stability.position == "col1"
    assert stability.stability_level == "HIGH"


def test_get_unknown_position_raises():
    result = DistributionRegimeStabilityResult(
        position_count=0,
        positions=(),
        stability_results=(),
    )

    with pytest.raises(KeyError):
        get_distribution_regime_stability(
            result,
            "col1",
        )


def test_iter_stabilities_returns_tuple():
    stability = DistributionRegimeStability(
        position="col1",
        window_count=2,
        valid_window_count=2,
        insufficient_window_count=0,
        transition_count=0,
        unchanged_count=1,
        missing_count=0,
        comparable_transition_count=1,
        regime_consistency_percentage=100.0,
        stability_percentage=100.0,
        stability_level="HIGH",
    )

    result = DistributionRegimeStabilityResult(
        position_count=1,
        positions=("col1",),
        stability_results=(stability,),
    )

    values = iter_distribution_regime_stabilities(result)

    assert isinstance(values, tuple)
    assert values == (stability,)


def test_get_stability_level():
    stability = DistributionRegimeStability(
        position="col1",
        window_count=2,
        valid_window_count=2,
        insufficient_window_count=0,
        transition_count=0,
        unchanged_count=1,
        missing_count=0,
        comparable_transition_count=1,
        regime_consistency_percentage=100.0,
        stability_percentage=100.0,
        stability_level="HIGH",
    )

    result = DistributionRegimeStabilityResult(
        position_count=1,
        positions=("col1",),
        stability_results=(stability,),
    )

    assert (
        get_distribution_regime_stability_level(
            result,
            "col1",
        )
        == "HIGH"
    )


def test_get_stability_percentage():
    stability = DistributionRegimeStability(
        position="col1",
        window_count=2,
        valid_window_count=2,
        insufficient_window_count=0,
        transition_count=0,
        unchanged_count=1,
        missing_count=0,
        comparable_transition_count=1,
        regime_consistency_percentage=100.0,
        stability_percentage=100.0,
        stability_level="HIGH",
    )

    result = DistributionRegimeStabilityResult(
        position_count=1,
        positions=("col1",),
        stability_results=(stability,),
    )

    assert (
        get_distribution_regime_stability_percentage(
            result,
            "col1",
        )
        == 100.0
    )


def test_invalid_result_type_for_getter_raises():
    with pytest.raises(TypeError):
        get_distribution_regime_stability(
            "invalid",
            "col1",
        )


def test_invalid_result_type_for_iterator_raises():
    with pytest.raises(TypeError):
        iter_distribution_regime_stabilities(
            "invalid",
        )


def test_invalid_result_type_for_level_getter_raises():
    with pytest.raises(TypeError):
        get_distribution_regime_stability_level(
            "invalid",
            "col1",
        )


def test_invalid_result_type_for_percentage_getter_raises():
    with pytest.raises(TypeError):
        get_distribution_regime_stability_percentage(
            "invalid",
            "col1",
        )


def test_empty_detection_and_analysis_return_insufficient_data():
    detection = make_detection(
        "col1",
        (),
    )

    analysis = make_transition_analysis(
        "col1",
        (),
    )

    result = build_distribution_regime_stability(
        detection,
        analysis,
    )

    assert result.window_count == 0
    assert result.valid_window_count == 0
    assert result.insufficient_window_count == 0
    assert result.comparable_transition_count == 0
    assert result.stability_percentage == 0.0
    assert result.stability_level == "INSUFFICIENT_DATA"