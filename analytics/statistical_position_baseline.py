from __future__ import annotations

from dataclasses import dataclass

from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)
from analytics.statistical_descriptive import (
    DescriptiveStatistics,
    StatisticalDescriptiveResult,
    build_statistical_descriptive_result,
    validate_descriptive_statistics,
)
from analytics.statistical_foundation import ANALYSIS_COLUMNS


VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class PositionStatisticalBaseline:
    """Immutable statistical baseline for one historical position."""
    position: str
    statistics: DescriptiveStatistics


@dataclass(frozen=True)
class StatisticalPositionBaseline:
    """Immutable Phase 18.5 position-wise statistical baseline."""

    market_id: int
    analysis_version: str
    baseline_version: str
    positions: tuple[PositionStatisticalBaseline, ...]

    @property
    def position_names(self) -> tuple[str, ...]:
        return tuple(item.position for item in self.positions)

    @property
    def position_count(self) -> int:
        return len(self.positions)


@dataclass(frozen=True)
class StatisticalPositionBaselineValidationIssue:
    """One position-wise baseline validation issue."""
    code: str
    message: str


@dataclass(frozen=True)
class StatisticalPositionBaselineValidationResult:
    """Result of position-wise baseline validation."""

    status: str
    issues: tuple[StatisticalPositionBaselineValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _issue(code: str, message: str):
    return StatisticalPositionBaselineValidationIssue(
        code=code,
        message=message,    )


def build_statistical_position_baseline(
    dataset: StatisticalBaselineDataset,
) -> StatisticalPositionBaseline:
    """
    Build the Phase 18.5 position-wise baseline.

    Phase 18.3 remains the source of truth for descriptive statistics.
    """
    validate_statistical_baseline_dataset(dataset)

    descriptive_result = build_statistical_descriptive_result(dataset)

    positions = tuple(
        PositionStatisticalBaseline(
            position=statistic.column_name,
            statistics=statistic,
        )
        for statistic in descriptive_result.statistics
    )

    return StatisticalPositionBaseline(
        market_id=descriptive_result.market_id,        analysis_version=descriptive_result.analysis_version,
        baseline_version=descriptive_result.baseline_version,
        positions=positions,
    )


def validate_statistical_position_baseline(
    baseline: StatisticalPositionBaseline,
) -> None:
    """Validate a complete Phase 18.5 position-wise baseline."""
    if not isinstance(baseline, StatisticalPositionBaseline):
        raise TypeError(
            "baseline must be a StatisticalPositionBaseline instance."
        )

    if (
        not isinstance(baseline.market_id, int)
        or isinstance(baseline.market_id, bool)
        or baseline.market_id <= 0
    ):
        raise ValueError("market_id must be a positive integer.")

    if (
        not isinstance(baseline.analysis_version, str)
        or not baseline.analysis_version.strip()    ):
        raise ValueError(
            "analysis_version must be a non-empty string."
        )

    if (
        not isinstance(baseline.baseline_version, str)
        or not baseline.baseline_version.strip()
    ):
        raise ValueError(
            "baseline_version must be a non-empty string."
        )

    if not isinstance(baseline.positions, tuple):
        raise TypeError("positions must be a tuple.")

    previous_position = None
    seen_positions: set[str] = set()

    for item in baseline.positions:
        if not isinstance(item, PositionStatisticalBaseline):
            raise TypeError(
                "positions must contain "
                "PositionStatisticalBaseline instances."
            )
        if item.position not in ANALYSIS_COLUMNS:
            raise ValueError(
                "Position baseline contains an unsupported position: "
                f"{item.position}"
            )

        if item.position in seen_positions:
            raise ValueError(
                "Position baseline positions must be unique."
            )

        if (
            previous_position is not None
            and item.position <= previous_position
        ):
            raise ValueError(
                "Position baseline positions must be in deterministic "
                "analysis-column order."
            )

        if item.statistics.column_name != item.position:
            raise ValueError(
                "Position and descriptive-statistics column must match."
            )
        validate_descriptive_statistics(
            StatisticalDescriptiveResult(
                market_id=baseline.market_id,
                analysis_version=baseline.analysis_version,
                baseline_version=baseline.baseline_version,
                statistics=(item.statistics,),
            )
        )

        seen_positions.add(item.position)
        previous_position = item.position


def validate_statistical_position_baseline_result(
    baseline: StatisticalPositionBaseline,
) -> StatisticalPositionBaselineValidationResult:
    """Return a non-raising validation result."""
    if not isinstance(baseline, StatisticalPositionBaseline):
        return StatisticalPositionBaselineValidationResult(
            status=INVALID,
            issues=(
                _issue(
                    "INVALID_BASELINE_TYPE",
                    (                        "baseline must be a "
                        "StatisticalPositionBaseline instance."
                    ),
                ),
            ),
        )

    try:
        validate_statistical_position_baseline(baseline)
    except (TypeError, ValueError) as exc:
        return StatisticalPositionBaselineValidationResult(
            status=INVALID,
            issues=(
                _issue(
                    "INVALID_POSITION_BASELINE",
                    str(exc),
                ),
            ),
        )

    return StatisticalPositionBaselineValidationResult(
        status=VALID,
        issues=(),
    )

def is_statistical_position_baseline_valid(
    baseline: StatisticalPositionBaseline,
) -> bool:
    return validate_statistical_position_baseline_result(
        baseline
    ).is_valid


def get_position_statistical_baseline(
    baseline: StatisticalPositionBaseline,
    position: str,
) -> PositionStatisticalBaseline:
    """Return the baseline statistics for one position."""
    validate_statistical_position_baseline(baseline)

    if position not in ANALYSIS_COLUMNS:
        raise ValueError(f"Unsupported position: {position}")

    for item in baseline.positions:
        if item.position == position:
            return item

    raise ValueError(
        f"Position statistical baseline not found: {position}"    )


def get_position_statistics(
    baseline: StatisticalPositionBaseline,
    position: str,
) -> DescriptiveStatistics:
    """Return descriptive statistics for one position."""
    return get_position_statistical_baseline(
        baseline,
        position,
    ).statistics


def get_position_statistical_baseline_positions(
    baseline: StatisticalPositionBaseline,
) -> tuple[str, ...]:
    """Return baseline positions in deterministic order."""
    validate_statistical_position_baseline(baseline)
    return baseline.position_names
