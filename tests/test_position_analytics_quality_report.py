from __future__ import annotations

from dataclasses import dataclass

import pytest

from analytics.position_analytics_quality_report import (
    COMPONENTS,
    PositionAnalyticsQualityReport,
    build_position_analytics_quality_report,
    get_position_analytics_quality_component_count,
    get_position_analytics_quality_issue_count,
    get_position_analytics_quality_issues,
    get_position_analytics_quality_status,
    iter_position_analytics_quality_issues,
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
    """Create a structurally complete consolidation object."""

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


def make_consolidation_with_positions(positions):
    """Create a consolidation with custom positions."""

    consolidation = make_complete_consolidation()

    return type(
        "CustomPositionConsolidation",
        (),
        {
            **{
                name: getattr(consolidation, name)
                for name in COMPONENTS
            },
            "position_count": len(positions),
            "positions": positions,
        },
    )()


def test_complete_consolidation_is_valid():
    consolidation = make_complete_consolidation()

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert isinstance(
        report,
        PositionAnalyticsQualityReport,
    )

    assert report.quality_status == "VALID"
    assert report.position_count == 8
    assert report.positions == POSITIONS
    assert report.expected_position_count == 8

    assert report.valid_position_count == 8
    assert report.warning_position_count == 0
    assert report.invalid_position_count == 0

    assert report.component_count == 8
    assert report.available_component_count == 8
    assert report.missing_component_count == 0

    assert report.issue_count == 0
    assert report.warning_issue_count == 0
    assert report.invalid_issue_count == 0
    assert report.issues == ()


def test_custom_expected_position_count_is_supported():
    consolidation = make_complete_consolidation()

    report = build_position_analytics_quality_report(
        consolidation,
        expected_position_count=8,
    )

    assert report.expected_position_count == 8
    assert report.quality_status == "VALID"


def test_expected_position_count_mismatch_is_invalid():
    consolidation = make_complete_consolidation()

    report = build_position_analytics_quality_report(
        consolidation,
        expected_position_count=7,
    )

    assert report.quality_status == "INVALID"
    assert report.position_count == 8

    assert any(
        issue.issue_type == "POSITION_COUNT_MISMATCH"
        for issue in report.issues
    )


def test_missing_component_is_invalid():
    consolidation = make_complete_consolidation()

    consolidation.position_frequency = None

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"
    assert report.available_component_count == 7
    assert report.missing_component_count == 1

    assert any(
        issue.issue_type == "MISSING_COMPONENT"
        and issue.component == "position_frequency"
        for issue in report.issues
    )


def test_empty_component_is_invalid():
    consolidation = make_complete_consolidation()

    consolidation.position_frequency = ()

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"
    assert report.available_component_count == 7
    assert report.missing_component_count == 1

    assert any(
        issue.issue_type == "MISSING_COMPONENT"
        and issue.component == "position_frequency"
        for issue in report.issues
    )


def test_multiple_missing_components_are_reported():
    consolidation = make_complete_consolidation()

    consolidation.position_frequency = None
    consolidation.position_distribution = None
    consolidation.position_stability = None

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"
    assert report.available_component_count == 5
    assert report.missing_component_count == 3

    missing_components = {
        issue.component
        for issue in report.issues
        if issue.issue_type == "MISSING_COMPONENT"
    }

    assert missing_components == {
        "position_frequency",
        "position_distribution",
        "position_stability",
    }


def test_all_components_missing_are_invalid():
    consolidation = make_complete_consolidation()

    for component in COMPONENTS:
        setattr(
            consolidation,
            component,
            None,
        )

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"
    assert report.available_component_count == 0
    assert report.missing_component_count == 8

    missing_components = {
        issue.component
        for issue in report.issues
        if issue.issue_type == "MISSING_COMPONENT"
    }

    assert missing_components == set(COMPONENTS)


def test_duplicate_positions_are_invalid():
    consolidation = make_consolidation_with_positions(
        (
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "col7",
        )
    )

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"

    assert any(
        issue.issue_type == "DUPLICATE_POSITION"
        for issue in report.issues
    )


def test_empty_position_name_is_invalid():
    consolidation = make_consolidation_with_positions(
        (
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "",
        )
    )

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"

    assert any(
        issue.issue_type == "EMPTY_POSITION_NAME"
        for issue in report.issues
    )


def test_non_string_position_name_is_invalid():
    consolidation = make_consolidation_with_positions(
        (
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            8,
        )
    )

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"

    assert any(
        issue.issue_type == "INVALID_POSITION_NAME"
        for issue in report.issues
    )


def test_missing_positions_are_invalid():
    consolidation = make_complete_consolidation()

    class MissingPositions:
        position_count = 8

        position_frequency = consolidation.position_frequency
        position_frequency_summary = (
            consolidation.position_frequency_summary
        )
        position_distribution = consolidation.position_distribution
        position_stability = consolidation.position_stability
        position_behavior_profile = (
            consolidation.position_behavior_profile
        )
        temporal_position_analysis = (
            consolidation.temporal_position_analysis
        )
        cross_position_relationship_overview = (
            consolidation.cross_position_relationship_overview
        )
        distribution_regime_overview = (
            consolidation.distribution_regime_overview
        )

    report = build_position_analytics_quality_report(
        MissingPositions()
    )

    assert report.quality_status == "INVALID"
    assert report.position_count == 0

    assert any(
        issue.issue_type == "MISSING_POSITIONS"
        for issue in report.issues
    )


def test_none_positions_are_invalid():
    consolidation = make_complete_consolidation()

    consolidation.positions = None

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"
    assert report.position_count == 0

    assert any(
        issue.issue_type == "MISSING_POSITIONS"
        for issue in report.issues
    )


def test_missing_position_count_is_invalid():
    consolidation = make_complete_consolidation()

    class MissingPositionCount:
        positions = POSITIONS

        position_frequency = consolidation.position_frequency
        position_frequency_summary = (
            consolidation.position_frequency_summary
        )
        position_distribution = consolidation.position_distribution
        position_stability = consolidation.position_stability
        position_behavior_profile = (
            consolidation.position_behavior_profile
        )
        temporal_position_analysis = (
            consolidation.temporal_position_analysis
        )
        cross_position_relationship_overview = (
            consolidation.cross_position_relationship_overview
        )
        distribution_regime_overview = (
            consolidation.distribution_regime_overview
        )

    report = build_position_analytics_quality_report(
        MissingPositionCount()
    )

    assert report.quality_status == "INVALID"

    assert any(
        issue.issue_type == "MISSING_POSITION_COUNT"
        for issue in report.issues
    )


def test_invalid_position_count_type_is_invalid():
    consolidation = make_complete_consolidation()

    consolidation.position_count = "8"

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"

    assert any(
        issue.issue_type == "INVALID_POSITION_COUNT"
        for issue in report.issues
    )


def test_none_consolidation_raises_type_error():
    with pytest.raises(TypeError):
        build_position_analytics_quality_report(
            None
        )


def test_boolean_expected_position_count_raises_type_error():
    consolidation = make_complete_consolidation()

    with pytest.raises(TypeError):
        build_position_analytics_quality_report(
            consolidation,
            expected_position_count=True,
        )


def test_non_integer_expected_position_count_raises_type_error():
    consolidation = make_complete_consolidation()

    with pytest.raises(TypeError):
        build_position_analytics_quality_report(
            consolidation,
            expected_position_count="8",
        )


def test_negative_expected_position_count_raises_value_error():
    consolidation = make_complete_consolidation()

    with pytest.raises(ValueError):
        build_position_analytics_quality_report(
            consolidation,
            expected_position_count=-1,
        )


def test_issue_getter_returns_all_issues():
    consolidation = make_complete_consolidation()

    consolidation.position_frequency = None
    consolidation.position_distribution = None

    report = build_position_analytics_quality_report(
        consolidation
    )

    issues = get_position_analytics_quality_issues(
        report
    )

    assert issues == report.issues
    assert len(issues) == 2


def test_quality_status_getter_returns_status():
    consolidation = make_complete_consolidation()

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert (
        get_position_analytics_quality_status(report)
        == "VALID"
    )


def test_issue_count_getter_returns_count():
    consolidation = make_complete_consolidation()

    consolidation.position_frequency = None

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert (
        get_position_analytics_quality_issue_count(report)
        == report.issue_count
    )


def test_component_count_getter_returns_counts():
    consolidation = make_complete_consolidation()

    consolidation.position_frequency = None
    consolidation.position_distribution = None

    report = build_position_analytics_quality_report(
        consolidation
    )

    counts = get_position_analytics_quality_component_count(
        report
    )

    assert counts == (8, 6, 2)


def test_issue_iterator_returns_stable_issue_order():
    consolidation = make_complete_consolidation()

    consolidation.position_frequency = None
    consolidation.position_distribution = None

    report = build_position_analytics_quality_report(
        consolidation
    )

    issues = tuple(
        iter_position_analytics_quality_issues(report)
    )

    assert issues == report.issues

    assert issues[0].component == "position_frequency"
    assert issues[1].component == "position_distribution"


def test_empty_tuple_component_is_missing():
    consolidation = make_complete_consolidation()

    consolidation.position_frequency_summary = ()

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"

    assert any(
        issue.issue_type == "MISSING_COMPONENT"
        and issue.component == "position_frequency_summary"
        for issue in report.issues
    )


def test_empty_dict_component_is_missing():
    consolidation = make_complete_consolidation()

    consolidation.position_distribution = {}

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"

    assert any(
        issue.issue_type == "MISSING_COMPONENT"
        and issue.component == "position_distribution"
        for issue in report.issues
    )


def test_empty_list_component_is_missing():
    consolidation = make_complete_consolidation()

    consolidation.position_stability = []

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.quality_status == "INVALID"

    assert any(
        issue.issue_type == "MISSING_COMPONENT"
        and issue.component == "position_stability"
        for issue in report.issues
    )


def test_non_empty_container_component_is_available():
    consolidation = make_complete_consolidation()

    consolidation.position_frequency = ("available",)

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.available_component_count == 8
    assert report.missing_component_count == 0
    assert report.quality_status == "VALID"


def test_report_preserves_positions():
    consolidation = make_complete_consolidation()

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.positions == POSITIONS
    assert report.position_count == len(POSITIONS)


def test_report_preserves_expected_position_count():
    consolidation = make_complete_consolidation()

    report = build_position_analytics_quality_report(
        consolidation,
        expected_position_count=8,
    )

    assert report.expected_position_count == 8


def test_report_dataclass_fields_are_populated():
    consolidation = make_complete_consolidation()

    report = build_position_analytics_quality_report(
        consolidation
    )

    assert report.position_count == 8
    assert report.positions == POSITIONS
    assert report.expected_position_count == 8

    assert report.valid_position_count == 8
    assert report.warning_position_count == 0
    assert report.invalid_position_count == 0

    assert report.component_count == 8
    assert report.available_component_count == 8
    assert report.missing_component_count == 0

    assert report.issue_count == 0
    assert report.warning_issue_count == 0
    assert report.invalid_issue_count == 0

    assert report.quality_status == "VALID"
    assert report.issues == ()