from __future__ import annotations

from dataclasses import dataclass
from typing import Any


QUALITY_STATUSES = (
    "VALID",
    "WARNING",
    "INVALID",
)


@dataclass(frozen=True)
class PositionAnalyticsQualityIssue:
    """One descriptive quality issue."""

    position: str | None
    component: str
    issue_type: str
    message: str
    severity: str


@dataclass(frozen=True)
class PositionAnalyticsQualityReport:
    """Descriptive quality report for position analytics."""

    position_count: int
    positions: tuple[str, ...]

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

    issues: tuple[PositionAnalyticsQualityIssue, ...]


COMPONENTS = (
    "position_frequency",
    "position_frequency_summary",
    "position_distribution",
    "position_stability",
    "position_behavior_profile",
    "temporal_position_analysis",
    "cross_position_relationship_overview",
    "distribution_regime_overview",
)


def _component_value(
    consolidation: Any,
    component: str,
) -> Any:
    """Return a component from the consolidation object."""

    return getattr(
        consolidation,
        component,
        None,
    )


def _is_empty_component(
    component: Any,
) -> bool:
    """
    Determine whether a component is structurally empty.

    None is always considered missing. Empty containers are also
    considered unavailable for quality-report purposes.
    """

    if component is None:
        return True

    if isinstance(
        component,
        (tuple, list, dict, set, frozenset),
    ):
        return len(component) == 0

    return False


def _build_component_issues(
    consolidation: Any,
) -> tuple[
    PositionAnalyticsQualityIssue,
    ...,
]:
    """Build descriptive component-level quality issues."""

    issues: list[
        PositionAnalyticsQualityIssue
    ] = []

    for component_name in COMPONENTS:
        component = _component_value(
            consolidation,
            component_name,
        )

        if _is_empty_component(component):
            issues.append(
                PositionAnalyticsQualityIssue(
                    position=None,
                    component=component_name,
                    issue_type="MISSING_COMPONENT",
                    message=(
                        f"Analytics component "
                        f"'{component_name}' is missing "
                        f"or empty."
                    ),
                    severity="INVALID",
                )
            )

    return tuple(issues)


def _build_position_issues(
    positions: tuple[str, ...],
    expected_position_count: int,
    positions_attribute_missing: bool = False,
) -> tuple[
    PositionAnalyticsQualityIssue,
    ...,
]:
    """Build descriptive position-list quality issues."""

    issues: list[
        PositionAnalyticsQualityIssue
    ] = []

    if positions_attribute_missing:
        issues.append(
            PositionAnalyticsQualityIssue(
                position=None,
                component="positions",
                issue_type="MISSING_POSITIONS",
                message=(
                    "The consolidated analytics object "
                    "does not expose positions."
                ),
                severity="INVALID",
            )
        )

    if len(positions) != expected_position_count:
        issues.append(
            PositionAnalyticsQualityIssue(
                position=None,
                component="positions",
                issue_type="POSITION_COUNT_MISMATCH",
                message=(
                    "Actual position count does not match "
                    "the expected position count."
                ),
                severity="INVALID",
            )
        )

    if len(set(positions)) != len(positions):
        issues.append(
            PositionAnalyticsQualityIssue(
                position=None,
                component="positions",
                issue_type="DUPLICATE_POSITION",
                message=(
                    "Duplicate position names were detected."
                ),
                severity="INVALID",
            )
        )

    for position in positions:
        if not isinstance(position, str):
            issues.append(
                PositionAnalyticsQualityIssue(
                    position=None,
                    component="positions",
                    issue_type="INVALID_POSITION_NAME",
                    message=(
                        "A position name is not a string."
                    ),
                    severity="INVALID",
                )
            )
            continue

        if not position:
            issues.append(
                PositionAnalyticsQualityIssue(
                    position=position,
                    component="positions",
                    issue_type="EMPTY_POSITION_NAME",
                    message=(
                        "An empty position name was detected."
                    ),
                    severity="INVALID",
                )
            )

    return tuple(issues)


def _build_summary_issues(
    consolidation: Any,
) -> tuple[
    PositionAnalyticsQualityIssue,
    ...,
]:
    """Build descriptive summary-level quality issues."""

    issues: list[
        PositionAnalyticsQualityIssue
    ] = []

    position_count = getattr(
        consolidation,
        "position_count",
        None,
    )

    positions_attribute_missing = not hasattr(
        consolidation,
        "positions",
    )

    positions = getattr(
        consolidation,
        "positions",
        None,
    )

    if position_count is None:
        issues.append(
            PositionAnalyticsQualityIssue(
                position=None,
                component="position_count",
                issue_type="MISSING_POSITION_COUNT",
                message=(
                    "The consolidated analytics object "
                    "does not expose position_count."
                ),
                severity="INVALID",
            )
        )

    elif not isinstance(
        position_count,
        int,
    ):
        issues.append(
            PositionAnalyticsQualityIssue(
                position=None,
                component="position_count",
                issue_type="INVALID_POSITION_COUNT",
                message=(
                    "position_count must be an integer."
                ),
                severity="INVALID",
            )
        )

    if positions_attribute_missing or positions is None:
        issues.append(
            PositionAnalyticsQualityIssue(
                position=None,
                component="positions",
                issue_type="MISSING_POSITIONS",
                message=(
                    "The consolidated analytics object "
                    "does not expose positions."
                ),
                severity="INVALID",
            )
        )

    return tuple(issues)


def _validate_expected_position_count(
    expected_position_count: int,
) -> None:
    """Validate expected position count."""

    if isinstance(
        expected_position_count,
        bool,
    ):
        raise TypeError(
            "expected_position_count must be an integer"
        )

    if not isinstance(
        expected_position_count,
        int,
    ):
        raise TypeError(
            "expected_position_count must be an integer"
        )

    if expected_position_count < 0:
        raise ValueError(
            "expected_position_count must be non-negative"
        )


def _determine_quality_status(
    issues: tuple[
        PositionAnalyticsQualityIssue,
        ...,
    ],
) -> str:
    """Determine the overall descriptive quality status."""

    if any(
        issue.severity == "INVALID"
        for issue in issues
    ):
        return "INVALID"

    if any(
        issue.severity == "WARNING"
        for issue in issues
    ):
        return "WARNING"

    return "VALID"


def _count_severity(
    issues: tuple[
        PositionAnalyticsQualityIssue,
        ...,
    ],
    severity: str,
) -> int:
    """Count issues of one severity."""

    return sum(
        issue.severity == severity
        for issue in issues
    )


def _available_component_count(
    consolidation: Any,
) -> int:
    """Count available analytics components."""

    return sum(
        not _is_empty_component(
            _component_value(
                consolidation,
                component,
            )
        )
        for component in COMPONENTS
    )


def build_position_analytics_quality_report(
    consolidation: Any,
    expected_position_count: int = 8,
) -> PositionAnalyticsQualityReport:
    """
    Build a descriptive quality report for consolidated position
    analytics.

    The report only audits availability and structural consistency.
    It does not alter source analytics.
    """

    if consolidation is None:
        raise TypeError(
            "consolidation must not be None"
        )

    _validate_expected_position_count(
        expected_position_count
    )

    positions_attribute_missing = not hasattr(
        consolidation,
        "positions",
    )

    raw_positions = getattr(
        consolidation,
        "positions",
        (),
    )

    if raw_positions is None:
        positions = ()
        positions_attribute_missing = True
    else:
        positions = tuple(raw_positions)

    position_issues = _build_position_issues(
        positions,
        expected_position_count,
        positions_attribute_missing,
    )

    summary_issues = _build_summary_issues(
        consolidation
    )

    component_issues = _build_component_issues(
        consolidation
    )

    issues = (
        position_issues
        + summary_issues
        + component_issues
    )

    quality_status = _determine_quality_status(
        issues
    )

    available_component_count = (
        _available_component_count(
            consolidation
        )
    )

    missing_component_count = (
        len(COMPONENTS)
        - available_component_count
    )

    issue_count = len(issues)

    warning_issue_count = _count_severity(
        issues,
        "WARNING",
    )

    invalid_issue_count = _count_severity(
        issues,
        "INVALID",
    )

    valid_position_count = (
        len(positions)
        if not any(
            issue.severity == "INVALID"
            and issue.component == "positions"
            for issue in issues
        )
        else 0
    )

    warning_position_count = 0

    invalid_position_count = (
        len(positions)
        if any(
            issue.severity == "INVALID"
            and issue.component == "positions"
            for issue in issues
        )
        else 0
    )

    return PositionAnalyticsQualityReport(
        position_count=len(positions),
        positions=positions,
        expected_position_count=expected_position_count,
        valid_position_count=valid_position_count,
        warning_position_count=warning_position_count,
        invalid_position_count=invalid_position_count,
        component_count=len(COMPONENTS),
        available_component_count=available_component_count,
        missing_component_count=missing_component_count,
        issue_count=issue_count,
        warning_issue_count=warning_issue_count,
        invalid_issue_count=invalid_issue_count,
        quality_status=quality_status,
        issues=issues,
    )


def get_position_analytics_quality_issues(
    report: PositionAnalyticsQualityReport,
) -> tuple[
    PositionAnalyticsQualityIssue,
    ...,
]:
    """Return all quality issues."""

    if not isinstance(
        report,
        PositionAnalyticsQualityReport,
    ):
        raise TypeError(
            "report must be a PositionAnalyticsQualityReport"
        )

    return report.issues


def get_position_analytics_quality_status(
    report: PositionAnalyticsQualityReport,
) -> str:
    """Return the overall quality status."""

    if not isinstance(
        report,
        PositionAnalyticsQualityReport,
    ):
        raise TypeError(
            "report must be a PositionAnalyticsQualityReport"
        )

    return report.quality_status


def iter_position_analytics_quality_issues(
    report: PositionAnalyticsQualityReport,
) -> tuple[
    PositionAnalyticsQualityIssue,
    ...,
]:
    """Return quality issues in stable order."""

    if not isinstance(
        report,
        PositionAnalyticsQualityReport,
    ):
        raise TypeError(
            "report must be a PositionAnalyticsQualityReport"
        )

    return report.issues


def get_position_analytics_quality_issue_count(
    report: PositionAnalyticsQualityReport,
) -> int:
    """Return total issue count."""

    if not isinstance(
        report,
        PositionAnalyticsQualityReport,
    ):
        raise TypeError(
            "report must be a PositionAnalyticsQualityReport"
        )

    return report.issue_count


def get_position_analytics_quality_component_count(
    report: PositionAnalyticsQualityReport,
) -> tuple[int, int, int]:
    """
    Return component counts as:

    (total, available, missing)
    """

    if not isinstance(
        report,
        PositionAnalyticsQualityReport,
    ):
        raise TypeError(
            "report must be a PositionAnalyticsQualityReport"
        )

    return (
        report.component_count,
        report.available_component_count,
        report.missing_component_count,
    )