from __future__ import annotations

from dataclasses import dataclass

import pytest

from analytics.position_analytics_quality_report import (
    COMPONENTS,
    PositionAnalyticsQualityReport,
    build_position_analytics_quality_report,
)

from analytics.position_analytics_quality_summary import (
    PositionAnalyticsQualitySummary,
    build_position_analytics_quality_summary,
    get_position_analytics_quality_summary_component_percentages,
    get_position_analytics_quality_summary_issue_percentage,
    get_position_analytics_quality_summary_source,
    get_position_analytics_quality_summary_status,
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
class DummyComponent:
    name: str


def make_complete_consolidation():
    """Create a complete consolidation object."""

    return type(
        "CompleteConsolidation",
        (),
        {
            "position_count": 8,
            "positions": POSITIONS,
            "position_frequency": DummyComponent(
                "position_frequency"
            ),
            "position_frequency_summary": DummyComponent(
                "position_frequency_summary"
            ),
            "position_distribution": DummyComponent(
                "position_distribution"
            ),
            "position_stability": DummyComponent(
                "position_stability"
            ),
            "position_behavior_profile": DummyComponent(
                "position_behavior_profile"
            ),
            "temporal_position_analysis": DummyComponent(
                "temporal_position_analysis"
            ),
            "cross_position_relationship_overview": DummyComponent(
                "cross_position_relationship_overview"
            ),
            "distribution_regime_overview": DummyComponent(
                "distribution_regime_overview"
            ),
        },
    )()


def make_quality_report():
    """Create a valid source quality report."""

    consolidation = make_complete_consolidation()

    return build_position_analytics_quality_report(
        consolidation
    )


def make_quality_report_with_missing_components():
    """Create a quality report with missing components."""

    consolidation = make_complete_consolidation()

    consolidation.position_frequency = None
    consolidation.position_distribution = None

    return build_position_analytics_quality_report(
        consolidation
    )


def test_valid_quality_report_produces_valid_summary():
    report = make_quality_report()

    summary = build_position_analytics_quality_summary(
        report
    )

    assert isinstance(
        summary,
        PositionAnalyticsQualitySummary,
    )

    assert summary.position_count == 8
    assert summary.expected_position_count == 8

    assert summary.valid_position_count == 8
    assert summary.warning_position_count == 0
    assert summary.invalid_position_count == 0

    assert summary.component_count == 8
    assert summary.available_component_count == 8
    assert summary.missing_component_count == 0

    assert summary.issue_count == 0
    assert summary.warning_issue_count == 0
    assert summary.invalid_issue_count == 0

    assert summary.quality_status == "VALID"


def test_valid_quality_report_has_zero_issue_percentage():
    report = make_quality_report()

    summary = build_position_analytics_quality_summary(
        report
    )

    assert summary.issue_percentage == 0.0


def test_complete_components_have_full_availability():
    report = make_quality_report()

    summary = build_position_analytics_quality_summary(
        report
    )

    assert (
        summary.component_availability_percentage
        == 100.0
    )

    assert (
        summary.component_missing_percentage
        == 0.0
    )


def test_missing_components_are_reflected_in_summary():
    report = (
        make_quality_report_with_missing_components()
    )

    summary = build_position_analytics_quality_summary(
        report
    )

    assert summary.quality_status == "INVALID"

    assert summary.component_count == 8
    assert summary.available_component_count == 6
    assert summary.missing_component_count == 2

    assert (
        summary.component_availability_percentage
        == 75.0
    )

    assert (
        summary.component_missing_percentage
        == 25.0
    )


def test_issue_percentage_is_based_on_position_count():
    report = (
        make_quality_report_with_missing_components()
    )

    summary = build_position_analytics_quality_summary(
        report
    )

    assert summary.issue_count == 2
    assert summary.position_count == 8

    assert summary.issue_percentage == 25.0


def test_summary_preserves_quality_status():
    report = (
        make_quality_report_with_missing_components()
    )

    summary = build_position_analytics_quality_summary(
        report
    )

    assert summary.quality_status == (
        report.quality_status
    )


def test_summary_preserves_position_counts():
    report = make_quality_report()

    summary = build_position_analytics_quality_summary(
        report
    )

    assert summary.position_count == (
        report.position_count
    )

    assert summary.expected_position_count == (
        report.expected_position_count
    )

    assert summary.valid_position_count == (
        report.valid_position_count
    )

    assert summary.warning_position_count == (
        report.warning_position_count
    )

    assert summary.invalid_position_count == (
        report.invalid_position_count
    )


def test_summary_preserves_component_counts():
    report = (
        make_quality_report_with_missing_components()
    )

    summary = build_position_analytics_quality_summary(
        report
    )

    assert summary.component_count == (
        report.component_count
    )

    assert summary.available_component_count == (
        report.available_component_count
    )

    assert summary.missing_component_count == (
        report.missing_component_count
    )


def test_summary_preserves_issue_counts():
    report = (
        make_quality_report_with_missing_components()
    )

    summary = build_position_analytics_quality_summary(
        report
    )

    assert summary.issue_count == (
        report.issue_count
    )

    assert summary.warning_issue_count == (
        report.warning_issue_count
    )

    assert summary.invalid_issue_count == (
        report.invalid_issue_count
    )


def test_source_quality_report_is_preserved():
    report = make_quality_report()

    summary = build_position_analytics_quality_summary(
        report
    )

    assert summary.source_quality_report is report


def test_status_getter_returns_summary_status():
    report = make_quality_report()

    summary = build_position_analytics_quality_summary(
        report
    )

    assert (
        get_position_analytics_quality_summary_status(
            summary
        )
        == "VALID"
    )


def test_issue_percentage_getter_returns_value():
    report = (
        make_quality_report_with_missing_components()
    )

    summary = build_position_analytics_quality_summary(
        report
    )

    assert (
        get_position_analytics_quality_summary_issue_percentage(
            summary
        )
        == 25.0
    )


def test_component_percentage_getter_returns_values():
    report = (
        make_quality_report_with_missing_components()
    )

    summary = build_position_analytics_quality_summary(
        report
    )

    percentages = (
        get_position_analytics_quality_summary_component_percentages(
            summary
        )
    )

    assert percentages == (
        75.0,
        25.0,
    )


def test_source_getter_returns_original_report():
    report = make_quality_report()

    summary = build_position_analytics_quality_summary(
        report
    )

    assert (
        get_position_analytics_quality_summary_source(
            summary
        )
        is report
    )


def test_invalid_report_type_raises_type_error():
    with pytest.raises(TypeError):
        build_position_analytics_quality_summary(
            object()
        )


def test_status_getter_rejects_invalid_summary_type():
    with pytest.raises(TypeError):
        get_position_analytics_quality_summary_status(
            object()
        )


def test_issue_percentage_getter_rejects_invalid_summary_type():
    with pytest.raises(TypeError):
        get_position_analytics_quality_summary_issue_percentage(
            object()
        )


def test_component_percentage_getter_rejects_invalid_summary_type():
    with pytest.raises(TypeError):
        get_position_analytics_quality_summary_component_percentages(
            object()
        )


def test_source_getter_rejects_invalid_summary_type():
    with pytest.raises(TypeError):
        get_position_analytics_quality_summary_source(
            object()
        )


def test_summary_does_not_modify_source_report():
    report = (
        make_quality_report_with_missing_components()
    )

    original_issue_count = report.issue_count
    original_component_count = (
        report.component_count
    )
    original_quality_status = (
        report.quality_status
    )

    build_position_analytics_quality_summary(
        report
    )

    assert report.issue_count == (
        original_issue_count
    )

    assert report.component_count == (
        original_component_count
    )

    assert report.quality_status == (
        original_quality_status
    )


def test_summary_dataclass_contains_source_report():
    report = make_quality_report()

    summary = build_position_analytics_quality_summary(
        report
    )

    assert isinstance(
        summary.source_quality_report,
        PositionAnalyticsQualityReport,
    )


def test_all_expected_components_are_available_in_valid_summary():
    report = make_quality_report()

    assert len(COMPONENTS) == 8

    summary = build_position_analytics_quality_summary(
        report
    )

    assert summary.available_component_count == (
        len(COMPONENTS)
    )


def test_zero_component_count_is_handled_safely():
    report = make_quality_report()

    modified_report = PositionAnalyticsQualityReport(
        position_count=0,
        positions=(),
        expected_position_count=0,
        valid_position_count=0,
        warning_position_count=0,
        invalid_position_count=0,
        component_count=0,
        available_component_count=0,
        missing_component_count=0,
        issue_count=0,
        warning_issue_count=0,
        invalid_issue_count=0,
        quality_status="VALID",
        issues=(),
    )

    summary = build_position_analytics_quality_summary(
        modified_report
    )

    assert summary.issue_percentage == 0.0
    assert (
        summary.component_availability_percentage
        == 0.0
    )
    assert (
        summary.component_missing_percentage
        == 0.0
    )


def test_summary_is_frozen():
    report = make_quality_report()

    summary = build_position_analytics_quality_summary(
        report
    )

    with pytest.raises(AttributeError):
        summary.quality_status = "INVALID"