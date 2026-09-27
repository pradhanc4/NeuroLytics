from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from analytics.position_analytics_quality_report import (
    PositionAnalyticsQualityReport,
)


@dataclass(frozen=True)
class PositionAnalyticsQualitySummary:
    """Descriptive summary of position analytics quality."""

    position_count: int
    expected_position_count: int

    valid_position_count: int
    warning_position_count: int
    invalid_position_count: int

    component_count: int
    available_component_count: int
    missing_component_count: int

    issue_count: int
    warning_issue_count: int
    invalid_issue_count: int

    quality_status: str

    issue_percentage: float
    component_availability_percentage: float
    component_missing_percentage: float

    source_quality_report: PositionAnalyticsQualityReport


def _validate_report(
    report: Any,
) -> None:
    """Validate the source quality report."""

    if not isinstance(
        report,
        PositionAnalyticsQualityReport,
    ):
        raise TypeError(
            "report must be a PositionAnalyticsQualityReport"
        )


def _percentage(
    numerator: int,
    denominator: int,
) -> float:
    """Calculate a percentage safely."""

    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
        * 100.0
    )


def build_position_analytics_quality_summary(
    report: PositionAnalyticsQualityReport,
) -> PositionAnalyticsQualitySummary:
    """
    Build a descriptive summary from a position analytics
    quality report.

    The source quality report is preserved and is not modified.
    """

    _validate_report(report)

    issue_percentage = _percentage(
        report.issue_count,
        report.position_count,
    )

    component_availability_percentage = _percentage(
        report.available_component_count,
        report.component_count,
    )

    component_missing_percentage = _percentage(
        report.missing_component_count,
        report.component_count,
    )

    return PositionAnalyticsQualitySummary(
        position_count=report.position_count,
        expected_position_count=(
            report.expected_position_count
        ),
        valid_position_count=(
            report.valid_position_count
        ),
        warning_position_count=(
            report.warning_position_count
        ),
        invalid_position_count=(
            report.invalid_position_count
        ),
        component_count=report.component_count,
        available_component_count=(
            report.available_component_count
        ),
        missing_component_count=(
            report.missing_component_count
        ),
        issue_count=report.issue_count,
        warning_issue_count=(
            report.warning_issue_count
        ),
        invalid_issue_count=(
            report.invalid_issue_count
        ),
        quality_status=report.quality_status,
        issue_percentage=issue_percentage,
        component_availability_percentage=(
            component_availability_percentage
        ),
        component_missing_percentage=(
            component_missing_percentage
        ),
        source_quality_report=report,
    )


def get_position_analytics_quality_summary_status(
    summary: PositionAnalyticsQualitySummary,
) -> str:
    """Return the quality status from the summary."""

    if not isinstance(
        summary,
        PositionAnalyticsQualitySummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionAnalyticsQualitySummary"
        )

    return summary.quality_status


def get_position_analytics_quality_summary_issue_percentage(
    summary: PositionAnalyticsQualitySummary,
) -> float:
    """Return the issue percentage."""

    if not isinstance(
        summary,
        PositionAnalyticsQualitySummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionAnalyticsQualitySummary"
        )

    return summary.issue_percentage


def get_position_analytics_quality_summary_component_percentages(
    summary: PositionAnalyticsQualitySummary,
) -> tuple[float, float]:
    """
    Return component percentages as:

    (available_percentage, missing_percentage)
    """

    if not isinstance(
        summary,
        PositionAnalyticsQualitySummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionAnalyticsQualitySummary"
        )

    return (
        summary.component_availability_percentage,
        summary.component_missing_percentage,
    )


def get_position_analytics_quality_summary_source(
    summary: PositionAnalyticsQualitySummary,
) -> PositionAnalyticsQualityReport:
    """Return the source quality report."""

    if not isinstance(
        summary,
        PositionAnalyticsQualitySummary,
    ):
        raise TypeError(
            "summary must be a "
            "PositionAnalyticsQualitySummary"
        )

    return summary.source_quality_report