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
    build_distribution_regime_transition_analysis,
    build_distribution_regime_transition_analysis_result,
    get_distribution_regime_transition,
    get_distribution_regime_transition_analysis,
    iter_distribution_regime_transition_analyses,
    iter_distribution_regime_transitions,
)


def make_window(
    window_index: int,
    regime: str,
) -> DistributionRegimeWindow:
    return DistributionRegimeWindow(
        position="col1",
        window_index=window_index,
        start_date=date(2026, 1, window_index),
        end_date=date(2026, 1, window_index),
        observation_count=5,
        frequency_total=5,
        dominant_digit=1,
        dominant_digit_percentage=100.0,
        distribution_mean=1.0,
        distribution_std=0.0,
        entropy=0.0,
        regime=regime,
    )


def make_detection(
    windows,
) -> DistributionRegimeDetection:
    return DistributionRegimeDetection(
        position="col1",
        window_size=5,
        window_count=len(windows),
        valid_window_count=sum(
            1
            for window in windows
            if window.regime != "INSUFFICIENT_DATA"
        ),
        windows=tuple(windows),
    )


def make_detection_result():
    detection_col1 = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
            make_window(3, "DIVERSE"),
            make_window(4, "DIVERSE"),
        )
    )

    detection_col2 = DistributionRegimeDetection(
        position="col2",
        window_size=5,
        window_count=3,
        valid_window_count=2,
        windows=(
            DistributionRegimeWindow(
                position="col2",
                window_index=1,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 5),
                observation_count=5,
                frequency_total=5,
                dominant_digit=2,
                dominant_digit_percentage=80.0,
                distribution_mean=2.0,
                distribution_std=0.0,
                entropy=0.0,
                regime="CONCENTRATED",
            ),
            DistributionRegimeWindow(
                position="col2",
                window_index=2,
                start_date=date(2026, 1, 6),
                end_date=date(2026, 1, 10),
                observation_count=5,
                frequency_total=5,
                dominant_digit=None,
                dominant_digit_percentage=None,
                distribution_mean=None,
                distribution_std=None,
                entropy=None,
                regime="INSUFFICIENT_DATA",
            ),
            DistributionRegimeWindow(
                position="col2",
                window_index=3,
                start_date=date(2026, 1, 11),
                end_date=date(2026, 1, 15),
                observation_count=5,
                frequency_total=5,
                dominant_digit=3,
                dominant_digit_percentage=100.0,
                distribution_mean=3.0,
                distribution_std=0.0,
                entropy=0.0,
                regime="CONCENTRATED",
            ),
        ),
    )

    return DistributionRegimeDetectionResult(
        position_count=2,
        positions=("col1", "col2"),
        detections=(
            detection_col1,
            detection_col2,
        ),
    )


def test_build_returns_expected_type():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert isinstance(
        result,
        DistributionRegimeTransitionAnalysis,
    )


def test_position_is_preserved():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.position == "col1"


def test_window_count_is_preserved():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
            make_window(3, "DIVERSE"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.window_count == 3


def test_transition_count_is_window_count_minus_one():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
            make_window(3, "DIVERSE"),
            make_window(4, "DIVERSE"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.transition_count == 3


def test_consecutive_windows_are_compared():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
            make_window(3, "DIVERSE"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert (
        result.transitions[0].previous_window_index
        == 1
    )
    assert (
        result.transitions[0].current_window_index
        == 2
    )
    assert (
        result.transitions[1].previous_window_index
        == 2
    )
    assert (
        result.transitions[1].current_window_index
        == 3
    )


def test_concentrated_to_balanced_is_transition():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    transition = result.transitions[0]

    assert transition.previous_regime == "CONCENTRATED"
    assert transition.current_regime == "BALANCED"
    assert transition.transition == "TRANSITION"


def test_balanced_to_diverse_is_transition():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "DIVERSE"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.transitions[0].transition == "TRANSITION"


def test_diverse_to_concentrated_is_transition():
    detection = make_detection(
        (
            make_window(1, "DIVERSE"),
            make_window(2, "CONCENTRATED"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.transitions[0].transition == "TRANSITION"


def test_same_regime_is_unchanged():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "BALANCED"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.transitions[0].transition == "UNCHANGED"


def test_missing_previous_regime_is_missing_transition():
    detection = make_detection(
        (
            make_window(1, "INSUFFICIENT_DATA"),
            make_window(2, "BALANCED"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.transitions[0].transition == "MISSING"


def test_missing_current_regime_is_missing_transition():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "INSUFFICIENT_DATA"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.transitions[0].transition == "MISSING"


def test_both_missing_regimes_are_missing_transition():
    detection = make_detection(
        (
            make_window(1, "INSUFFICIENT_DATA"),
            make_window(2, "INSUFFICIENT_DATA"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.transitions[0].transition == "MISSING"


def test_transition_fields_are_preserved():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "DIVERSE"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    transition = result.transitions[0]

    assert transition.position == "col1"
    assert transition.previous_window_index == 1
    assert transition.current_window_index == 2
    assert transition.previous_regime == "CONCENTRATED"
    assert transition.current_regime == "DIVERSE"
    assert transition.transition == "TRANSITION"


def test_single_window_produces_no_transitions():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.window_count == 1
    assert result.transition_count == 0
    assert result.transitions == ()


def test_empty_windows_produce_no_transitions():
    detection = make_detection(())

    result = build_distribution_regime_transition_analysis(
        detection
    )

    assert result.window_count == 0
    assert result.transition_count == 0
    assert result.transitions == ()


def test_result_builder_returns_expected_type():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    assert isinstance(
        result,
        DistributionRegimeTransitionAnalysisResult,
    )


def test_result_builder_preserves_position_count():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    assert result.position_count == 2


def test_result_builder_preserves_positions():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    assert result.positions == (
        "col1",
        "col2",
    )


def test_result_builder_creates_analysis_for_each_position():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    assert len(result.analyses) == 2
    assert result.analyses[0].position == "col1"
    assert result.analyses[1].position == "col2"


def test_col1_transitions_are_detected():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    analysis = result.analyses[0]

    assert analysis.transition_count == 3
    assert (
        analysis.transitions[0].transition
        == "TRANSITION"
    )
    assert (
        analysis.transitions[1].transition
        == "TRANSITION"
    )
    assert (
        analysis.transitions[2].transition
        == "UNCHANGED"
    )


def test_col2_missing_transition_is_detected():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    analysis = result.analyses[1]

    assert analysis.transition_count == 2
    assert (
        analysis.transitions[0].transition
        == "MISSING"
    )
    assert (
        analysis.transitions[1].transition
        == "MISSING"
    )


def test_get_analysis_returns_requested_position():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    analysis = (
        get_distribution_regime_transition_analysis(
            result,
            "col2",
        )
    )

    assert analysis.position == "col2"


def test_iter_analyses_returns_all_analyses():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    analyses = (
        iter_distribution_regime_transition_analyses(
            result
        )
    )

    assert analyses == result.analyses
    assert len(analyses) == 2


def test_get_transition_returns_one_based_transition():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
            make_window(3, "DIVERSE"),
        )
    )

    analysis = build_distribution_regime_transition_analysis(
        detection
    )

    transition = get_distribution_regime_transition(
        analysis,
        1,
    )

    assert transition.previous_window_index == 1
    assert transition.current_window_index == 2


def test_get_second_transition_returns_correct_transition():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
            make_window(3, "DIVERSE"),
        )
    )

    analysis = build_distribution_regime_transition_analysis(
        detection
    )

    transition = get_distribution_regime_transition(
        analysis,
        2,
    )

    assert transition.previous_window_index == 2
    assert transition.current_window_index == 3


def test_iter_transitions_returns_all_transitions():
    detection = make_detection(
        (
            make_window(1, "CONCENTRATED"),
            make_window(2, "BALANCED"),
            make_window(3, "DIVERSE"),
        )
    )

    analysis = build_distribution_regime_transition_analysis(
        detection
    )

    transitions = iter_distribution_regime_transitions(
        analysis
    )

    assert transitions == analysis.transitions
    assert len(transitions) == 2


def test_detection_type_validation():
    with pytest.raises(
        TypeError,
        match="detection must be a DistributionRegimeDetection",
    ):
        build_distribution_regime_transition_analysis(
            None
        )


def test_detection_result_type_validation():
    with pytest.raises(
        TypeError,
        match="detection_result must be a",
    ):
        build_distribution_regime_transition_analysis_result(
            None
        )


def test_result_accessor_type_validation():
    with pytest.raises(
        TypeError,
        match="result must be a",
    ):
        get_distribution_regime_transition_analysis(
            None,
            "col1",
        )


def test_result_accessor_requires_string_position():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    with pytest.raises(
        TypeError,
        match="position must be a string",
    ):
        get_distribution_regime_transition_analysis(
            result,
            1,
        )


def test_missing_position_raises():
    result = (
        build_distribution_regime_transition_analysis_result(
            make_detection_result()
        )
    )

    with pytest.raises(
        ValueError,
        match="not found for col3",
    ):
        get_distribution_regime_transition_analysis(
            result,
            "col3",
        )


def test_analysis_accessor_type_validation():
    with pytest.raises(
        TypeError,
        match="analysis must be a",
    ):
        get_distribution_regime_transition(
            None,
            1,
        )


def test_boolean_transition_index_is_rejected():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "DIVERSE"),
        )
    )

    analysis = build_distribution_regime_transition_analysis(
        detection
    )

    with pytest.raises(
        TypeError,
        match="transition_index must be an integer",
    ):
        get_distribution_regime_transition(
            analysis,
            True,
        )


def test_non_integer_transition_index_is_rejected():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "DIVERSE"),
        )
    )

    analysis = build_distribution_regime_transition_analysis(
        detection
    )

    with pytest.raises(
        TypeError,
        match="transition_index must be an integer",
    ):
        get_distribution_regime_transition(
            analysis,
            1.5,
        )


def test_zero_transition_index_is_rejected():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "DIVERSE"),
        )
    )

    analysis = build_distribution_regime_transition_analysis(
        detection
    )

    with pytest.raises(
        ValueError,
        match="transition_index must be greater than zero",
    ):
        get_distribution_regime_transition(
            analysis,
            0,
        )


def test_negative_transition_index_is_rejected():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "DIVERSE"),
        )
    )

    analysis = build_distribution_regime_transition_analysis(
        detection
    )

    with pytest.raises(
        ValueError,
        match="transition_index must be greater than zero",
    ):
        get_distribution_regime_transition(
            analysis,
            -1,
        )


def test_missing_transition_raises():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "DIVERSE"),
        )
    )

    analysis = build_distribution_regime_transition_analysis(
        detection
    )

    with pytest.raises(
        ValueError,
        match="Distribution regime transition not found",
    ):
        get_distribution_regime_transition(
            analysis,
            99,
        )


def test_transition_iterator_type_validation():
    with pytest.raises(
        TypeError,
        match="analysis must be a",
    ):
        iter_distribution_regime_transitions(None)


def test_string_windows_are_rejected():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "DIVERSE"),
        )
    )

    detection = DistributionRegimeDetection(
        position=detection.position,
        window_size=detection.window_size,
        window_count=detection.window_count,
        valid_window_count=detection.valid_window_count,
        windows=(
            "invalid",
        ),
    )

    with pytest.raises(
        TypeError,
        match="each window must be a DistributionRegimeWindow",
    ):
        build_distribution_regime_transition_analysis(
            detection
        )


def test_transition_analysis_objects_are_immutable():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "DIVERSE"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    with pytest.raises(AttributeError):
        result.position = "col2"


def test_transition_objects_are_immutable():
    detection = make_detection(
        (
            make_window(1, "BALANCED"),
            make_window(2, "DIVERSE"),
        )
    )

    result = build_distribution_regime_transition_analysis(
        detection
    )

    with pytest.raises(AttributeError):
        result.transitions[0].position = "col2"


def test_original_detection_is_not_mutated():
    windows = (
        make_window(1, "CONCENTRATED"),
        make_window(2, "BALANCED"),
    )

    detection = make_detection(windows)

    original_windows = detection.windows

    build_distribution_regime_transition_analysis(
        detection
    )

    assert detection.windows == original_windows