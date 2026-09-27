from __future__ import annotations

from datetime import date
from dataclasses import dataclass

import pytest

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
from analytics.distribution_regime_summary import (
    REGIMES,
    TRANSITION_TYPES,
    DistributionRegimePositionSummary,
    DistributionRegimeSummary,
    build_distribution_regime_summary,
    build_distribution_regime_summary_result,
    get_distribution_regime_count,
    get_distribution_regime_summary,
    get_distribution_regime_transition_count,
    iter_distribution_regime_position_summaries,
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


def make_detection(
    position: str,
    regimes: tuple[str, ...],
) -> DistributionRegimeDetection:
    windows = tuple(
        make_window(position, index + 1, regime)
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


def test_constants_are_defined():
    assert REGIMES == (
        "CONCENTRATED",
        "BALANCED",
        "DIVERSE",
        "INSUFFICIENT_DATA",
    )

    assert TRANSITION_TYPES == (
        "TRANSITION",
        "UNCHANGED",
        "MISSING",
    )


def test_build_position_summary_counts_windows_and_regimes():
    detection = make_detection(
        "col1",
        (
            "CONCENTRATED",
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
            "CONCENTRATED",
            "BALANCED",
            "TRANSITION",
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

    analysis = make_transition_analysis(
        "col1",
        transitions,
    )

    summary = build_distribution_regime_summary(
        detection,
        analysis,
    )

    assert isinstance(summary, DistributionRegimePositionSummary)

    assert summary.position == "col1"
    assert summary.window_count == 4
    assert summary.valid_window_count == 3
    assert summary.insufficient_window_count == 1

    assert summary.concentrated_count == 1
    assert summary.balanced_count == 1
    assert summary.diverse_count == 1
    assert summary.insufficient_data_count == 1


def test_build_position_summary_counts_transition_types():
    detection = make_detection(
        "col1",
        (
            "CONCENTRATED",
            "BALANCED",
            "BALANCED",
            "INSUFFICIENT_DATA",
        ),
    )

    transitions = (
        make_transition(
            "col1",
            1,
            2,
            "CONCENTRATED",
            "BALANCED",
            "TRANSITION",
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
            "INSUFFICIENT_DATA",
            "MISSING",
        ),
    )

    analysis = make_transition_analysis(
        "col1",
        transitions,
    )

    summary = build_distribution_regime_summary(
        detection,
        analysis,
    )

    assert summary.transition_count == 1
    assert summary.unchanged_count == 1
    assert summary.missing_count == 1

    assert dict(summary.transition_type_counts) == {
        "TRANSITION": 1,
        "UNCHANGED": 1,
        "MISSING": 1,
    }


def test_build_position_summary_percentages():
    detection = make_detection(
        "col1",
        (
            "CONCENTRATED",
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
            "CONCENTRATED",
            "BALANCED",
            "TRANSITION",
        ),
        make_transition(
            "col1",
            2,
            3,
            "BALANCED",
            "DIVERSE",
            "UNCHANGED",
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

    analysis = make_transition_analysis(
        "col1",
        transitions,
    )

    summary = build_distribution_regime_summary(
        detection,
        analysis,
    )

    assert summary.concentrated_percentage == 25.0
    assert summary.balanced_percentage == 25.0
    assert summary.diverse_percentage == 25.0
    assert summary.insufficient_data_percentage == 25.0

    assert summary.regime_transition_percentage == pytest.approx(
        100 / 3
    )
    assert summary.unchanged_percentage == pytest.approx(
        100 / 3
    )
    assert summary.missing_percentage == pytest.approx(
        100 / 3
    )


def test_position_summary_requires_matching_position():
    detection = make_detection(
        "col1",
        ("BALANCED",),
    )

    analysis = make_transition_analysis(
        "col2",
        (),
    )

    with pytest.raises(ValueError):
        build_distribution_regime_summary(
            detection,
            analysis,
        )


def test_build_complete_summary_for_multiple_positions():
    detection_result = DistributionRegimeDetectionResult(
        position_count=2,
        positions=("col1", "col2"),
        detections=(
            make_detection(
                "col1",
                (
                    "CONCENTRATED",
                    "BALANCED",
                ),
            ),
            make_detection(
                "col2",
                (
                    "DIVERSE",
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
                        "CONCENTRATED",
                        "BALANCED",
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
                        "INSUFFICIENT_DATA",
                        "MISSING",
                    ),
                ),
            ),
        ),
    )

    summary = build_distribution_regime_summary_result(
        detection_result,
        transition_result,
    )

    assert isinstance(summary, DistributionRegimeSummary)

    assert summary.position_count == 2
    assert summary.positions == ("col1", "col2")

    assert summary.total_window_count == 4
    assert summary.total_valid_window_count == 3
    assert summary.total_insufficient_window_count == 1

    assert summary.total_transition_count == 1
    assert summary.total_unchanged_count == 0
    assert summary.total_missing_count == 1

    assert summary.concentrated_count == 1
    assert summary.balanced_count == 1
    assert summary.diverse_count == 1
    assert summary.insufficient_data_count == 1


def test_complete_summary_aggregates_transition_counts():
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
                    "CONCENTRATED",
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
                        "CONCENTRATED",
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

    summary = build_distribution_regime_summary_result(
        detection_result,
        transition_result,
    )

    assert dict(summary.transition_type_counts) == {
        "TRANSITION": 2,
        "UNCHANGED": 2,
        "MISSING": 0,
    }


def test_complete_summary_aggregates_regime_counts():
    detection_result = DistributionRegimeDetectionResult(
        position_count=2,
        positions=("col1", "col2"),
        detections=(
            make_detection(
                "col1",
                (
                    "CONCENTRATED",
                    "BALANCED",
                    "DIVERSE",
                ),
            ),
            make_detection(
                "col2",
                (
                    "CONCENTRATED",
                    "DIVERSE",
                    "INSUFFICIENT_DATA",
                ),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=2,
        positions=("col1", "col2"),
        analyses=(
            make_transition_analysis("col1", ()),
            make_transition_analysis("col2", ()),
        ),
    )

    summary = build_distribution_regime_summary_result(
        detection_result,
        transition_result,
    )

    assert dict(summary.regime_counts) == {
        "CONCENTRATED": 2,
        "BALANCED": 1,
        "DIVERSE": 2,
        "INSUFFICIENT_DATA": 1,
    }


def test_position_order_is_preserved():
    detection_result = DistributionRegimeDetectionResult(
        position_count=2,
        positions=("col2", "col1"),
        detections=(
            make_detection("col2", ("BALANCED",)),
            make_detection("col1", ("DIVERSE",)),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=2,
        positions=("col2", "col1"),
        analyses=(
            make_transition_analysis("col2", ()),
            make_transition_analysis("col1", ()),
        ),
    )

    summary = build_distribution_regime_summary_result(
        detection_result,
        transition_result,
    )

    assert summary.positions == ("col2", "col1")

    assert tuple(
        item.position
        for item in summary.position_summaries
    ) == ("col2", "col1")


def test_get_position_summary():
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
            make_transition_analysis("col1", ()),
        ),
    )

    summary = build_distribution_regime_summary_result(
        detection_result,
        transition_result,
    )

    result = get_distribution_regime_summary(
        summary,
        "col1",
    )

    assert result.position == "col1"


def test_get_position_summary_unknown_position():
    summary = DistributionRegimeSummary(
        position_count=0,
        positions=(),
        total_window_count=0,
        total_valid_window_count=0,
        total_insufficient_window_count=0,
        total_transition_count=0,
        total_unchanged_count=0,
        total_missing_count=0,
        transition_percentage=0.0,
        unchanged_percentage=0.0,
        missing_percentage=0.0,
        concentrated_count=0,
        balanced_count=0,
        diverse_count=0,
        insufficient_data_count=0,
        concentrated_percentage=0.0,
        balanced_percentage=0.0,
        diverse_percentage=0.0,
        insufficient_data_percentage=0.0,
        transition_type_counts=tuple(
            (item, 0)
            for item in TRANSITION_TYPES
        ),
        regime_counts=tuple(
            (item, 0)
            for item in REGIMES
        ),
        position_summaries=(),
    )

    with pytest.raises(KeyError):
        get_distribution_regime_summary(
            summary,
            "col1",
        )


def test_iter_position_summaries():
    detection_result = DistributionRegimeDetectionResult(
        position_count=2,
        positions=("col1", "col2"),
        detections=(
            make_detection("col1", ("BALANCED",)),
            make_detection("col2", ("DIVERSE",)),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=2,
        positions=("col1", "col2"),
        analyses=(
            make_transition_analysis("col1", ()),
            make_transition_analysis("col2", ()),
        ),
    )

    summary = build_distribution_regime_summary_result(
        detection_result,
        transition_result,
    )

    summaries = iter_distribution_regime_position_summaries(
        summary
    )

    assert isinstance(summaries, tuple)
    assert tuple(
        item.position
        for item in summaries
    ) == ("col1", "col2")


def test_get_transition_count():
    summary = DistributionRegimeSummary(
        position_count=0,
        positions=(),
        total_window_count=0,
        total_valid_window_count=0,
        total_insufficient_window_count=0,
        total_transition_count=3,
        total_unchanged_count=2,
        total_missing_count=1,
        transition_percentage=50.0,
        unchanged_percentage=33.3333333333,
        missing_percentage=16.6666666667,
        concentrated_count=0,
        balanced_count=0,
        diverse_count=0,
        insufficient_data_count=0,
        concentrated_percentage=0.0,
        balanced_percentage=0.0,
        diverse_percentage=0.0,
        insufficient_data_percentage=0.0,
        transition_type_counts=(
            ("TRANSITION", 3),
            ("UNCHANGED", 2),
            ("MISSING", 1),
        ),
        regime_counts=tuple(
            (item, 0)
            for item in REGIMES
        ),
        position_summaries=(),
    )

    assert (
        get_distribution_regime_transition_count(
            summary,
            "TRANSITION",
        )
        == 3
    )

    assert (
        get_distribution_regime_transition_count(
            summary,
            "UNCHANGED",
        )
        == 2
    )

    assert (
        get_distribution_regime_transition_count(
            summary,
            "MISSING",
        )
        == 1
    )


def test_get_regime_count():
    summary = DistributionRegimeSummary(
        position_count=0,
        positions=(),
        total_window_count=0,
        total_valid_window_count=0,
        total_insufficient_window_count=0,
        total_transition_count=0,
        total_unchanged_count=0,
        total_missing_count=0,
        transition_percentage=0.0,
        unchanged_percentage=0.0,
        missing_percentage=0.0,
        concentrated_count=4,
        balanced_count=3,
        diverse_count=2,
        insufficient_data_count=1,
        concentrated_percentage=40.0,
        balanced_percentage=30.0,
        diverse_percentage=20.0,
        insufficient_data_percentage=10.0,
        transition_type_counts=tuple(
            (item, 0)
            for item in TRANSITION_TYPES
        ),
        regime_counts=(
            ("CONCENTRATED", 4),
            ("BALANCED", 3),
            ("DIVERSE", 2),
            ("INSUFFICIENT_DATA", 1),
        ),
        position_summaries=(),
    )

    assert get_distribution_regime_count(
        summary,
        "CONCENTRATED",
    ) == 4

    assert get_distribution_regime_count(
        summary,
        "BALANCED",
    ) == 3

    assert get_distribution_regime_count(
        summary,
        "DIVERSE",
    ) == 2

    assert get_distribution_regime_count(
        summary,
        "INSUFFICIENT_DATA",
    ) == 1


def test_invalid_transition_type_raises():
    summary = DistributionRegimeSummary(
        position_count=0,
        positions=(),
        total_window_count=0,
        total_valid_window_count=0,
        total_insufficient_window_count=0,
        total_transition_count=0,
        total_unchanged_count=0,
        total_missing_count=0,
        transition_percentage=0.0,
        unchanged_percentage=0.0,
        missing_percentage=0.0,
        concentrated_count=0,
        balanced_count=0,
        diverse_count=0,
        insufficient_data_count=0,
        concentrated_percentage=0.0,
        balanced_percentage=0.0,
        diverse_percentage=0.0,
        insufficient_data_percentage=0.0,
        transition_type_counts=tuple(
            (item, 0)
            for item in TRANSITION_TYPES
        ),
        regime_counts=tuple(
            (item, 0)
            for item in REGIMES
        ),
        position_summaries=(),
    )

    with pytest.raises(ValueError):
        get_distribution_regime_transition_count(
            summary,
            "INVALID",
        )


def test_invalid_regime_raises():
    summary = DistributionRegimeSummary(
        position_count=0,
        positions=(),
        total_window_count=0,
        total_valid_window_count=0,
        total_insufficient_window_count=0,
        total_transition_count=0,
        total_unchanged_count=0,
        total_missing_count=0,
        transition_percentage=0.0,
        unchanged_percentage=0.0,
        missing_percentage=0.0,
        concentrated_count=0,
        balanced_count=0,
        diverse_count=0,
        insufficient_data_count=0,
        concentrated_percentage=0.0,
        balanced_percentage=0.0,
        diverse_percentage=0.0,
        insufficient_data_percentage=0.0,
        transition_type_counts=tuple(
            (item, 0)
            for item in TRANSITION_TYPES
        ),
        regime_counts=tuple(
            (item, 0)
            for item in REGIMES
        ),
        position_summaries=(),
    )

    with pytest.raises(ValueError):
        get_distribution_regime_count(
            summary,
            "INVALID",
        )


def test_invalid_detection_type_raises():
    with pytest.raises(TypeError):
        build_distribution_regime_summary(
            "invalid",
            "invalid",
        )


def test_invalid_result_types_raise():
    with pytest.raises(TypeError):
        build_distribution_regime_summary_result(
            "invalid",
            "invalid",
        )


def test_mismatched_result_positions_raise():
    detection_result = DistributionRegimeDetectionResult(
        position_count=1,
        positions=("col1",),
        detections=(
            make_detection("col1", ("BALANCED",)),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=1,
        positions=("col2",),
        analyses=(
            make_transition_analysis("col2", ()),
        ),
    )

    with pytest.raises(ValueError):
        build_distribution_regime_summary_result(
            detection_result,
            transition_result,
        )


def test_empty_position_summary_has_zero_percentages():
    detection = make_detection(
        "col1",
        (),
    )

    analysis = make_transition_analysis(
        "col1",
        (),
    )

    summary = build_distribution_regime_summary(
        detection,
        analysis,
    )

    assert summary.window_count == 0
    assert summary.valid_window_count == 0
    assert summary.insufficient_window_count == 0

    assert summary.transition_count == 0
    assert summary.unchanged_count == 0
    assert summary.missing_count == 0

    assert summary.concentrated_percentage == 0.0
    assert summary.balanced_percentage == 0.0
    assert summary.diverse_percentage == 0.0
    assert summary.insufficient_data_percentage == 0.0

    assert summary.regime_transition_percentage == 0.0
    assert summary.unchanged_percentage == 0.0
    assert summary.missing_percentage == 0.0


def test_summary_contains_all_supported_regime_keys():
    detection_result = DistributionRegimeDetectionResult(
        position_count=1,
        positions=("col1",),
        detections=(
            make_detection(
                "col1",
                (
                    "CONCENTRATED",
                    "BALANCED",
                    "DIVERSE",
                    "INSUFFICIENT_DATA",
                ),
            ),
        ),
    )

    transition_result = DistributionRegimeTransitionAnalysisResult(
        position_count=1,
        positions=("col1",),
        analyses=(
            make_transition_analysis("col1", ()),
        ),
    )

    summary = build_distribution_regime_summary_result(
        detection_result,
        transition_result,
    )

    assert tuple(
        key for key, _ in summary.regime_counts
    ) == REGIMES


def test_summary_contains_all_supported_transition_keys():
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
            make_transition_analysis("col1", ()),
        ),
    )

    summary = build_distribution_regime_summary_result(
        detection_result,
        transition_result,
    )

    assert tuple(
        key for key, _ in summary.transition_type_counts
    ) == TRANSITION_TYPES