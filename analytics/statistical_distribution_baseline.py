from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution import (
    PositionDistribution,
    build_position_distribution,
)
from analytics.position_frequency import (
    calculate_position_frequency,
)
from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)
from analytics.statistical_foundation import ANALYSIS_COLUMNS


VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class StatisticalDistributionBaseline:
    """Immutable Phase 18.6 distribution baseline."""

    market_id: int
    analysis_version: str
    baseline_version: str
    distributions: tuple[PositionDistribution, ...]

    @property
    def positions(self) -> tuple[str, ...]:
        return tuple(item.position for item in self.distributions)

    @property
    def position_count(self) -> int:
        return len(self.distributions)


@dataclass(frozen=True)
class StatisticalDistributionBaselineValidationIssue:
    """One distribution-baseline validation issue."""

    code: str
    message: str


@dataclass(frozen=True)
class StatisticalDistributionBaselineValidationResult:
    """Result of distribution-baseline validation."""

    status: str
    issues: tuple[
        StatisticalDistributionBaselineValidationIssue,
        ...,
    ]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _issue(
    code: str,
    message: str,
) -> StatisticalDistributionBaselineValidationIssue:
    return StatisticalDistributionBaselineValidationIssue(
        code=code,
        message=message,
    )


def build_statistical_distribution_baseline(
    dataset: StatisticalBaselineDataset,
) -> StatisticalDistributionBaseline:
    """Build a distribution baseline from the validated baseline dataset."""
    validate_statistical_baseline_dataset(dataset)

    distributions = tuple(
        build_position_distribution(
            calculate_position_frequency(
                dataset.observations,
                position,
            )
        )
        for position in dataset.columns
    )

    return StatisticalDistributionBaseline(
        market_id=dataset.contract.market_id,
        analysis_version=dataset.contract.analysis_version,
        baseline_version=dataset.contract.baseline_version,
        distributions=distributions,
    )


def validate_statistical_distribution_baseline(
    baseline: StatisticalDistributionBaseline,
) -> None:
    """Validate the complete distribution baseline."""
    if not isinstance(baseline, StatisticalDistributionBaseline):
        raise TypeError(
            "baseline must be a StatisticalDistributionBaseline instance."
        )

    if (
        not isinstance(baseline.market_id, int)
        or isinstance(baseline.market_id, bool)
        or baseline.market_id <= 0
    ):
        raise ValueError("market_id must be a positive integer.")

    if (
        not isinstance(baseline.analysis_version, str)
        or not baseline.analysis_version.strip()
    ):
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

    if not isinstance(baseline.distributions, tuple):
        raise TypeError("distributions must be a tuple.")

    for distribution in baseline.distributions:
        if not isinstance(distribution, PositionDistribution):
            raise TypeError(
                "distributions must contain PositionDistribution instances."
            )

    positions = tuple(
        distribution.position
        for distribution in baseline.distributions
    )

    if len(positions) != len(set(positions)):
        raise ValueError(
            "Distribution baseline positions must be unique."
        )

    if positions != tuple(sorted(positions)):
        raise ValueError(
            "Distribution baseline positions must be in deterministic order."
        )

    for distribution in baseline.distributions:
        if not isinstance(distribution, PositionDistribution):
            raise TypeError(
                "distributions must contain PositionDistribution instances."
            )

        if distribution.position not in ANALYSIS_COLUMNS:
            raise ValueError(
                "Distribution baseline contains an unsupported position: "
                f"{distribution.position}"
            )

        if not isinstance(distribution.total_observations, int):
            raise TypeError(
                "total_observations must be an integer."
            )

        if (
            isinstance(distribution.total_observations, bool)
            or distribution.total_observations < 0
        ):
            raise ValueError(
                "total_observations cannot be negative."
            )

        if not isinstance(distribution.percentages, tuple):
            raise TypeError("percentages must be a tuple.")

        if len(distribution.percentages) != 10:
            raise ValueError(
                "Each distribution must contain exactly 10 percentages."
            )

        for percentage in distribution.percentages:
            if not isinstance(percentage, (int, float)):
                raise TypeError(
                    "Distribution percentages must be numeric."
                )

            if percentage < 0 or percentage > 100:
                raise ValueError(
                    "Distribution percentages must be between 0 and 100."
                )

        percentage_total = sum(distribution.percentages)

        if distribution.total_observations == 0:
            if percentage_total != 0.0:
                raise ValueError(
                    "Empty distributions must have zero percentages."
                )
        elif abs(percentage_total - 100.0) > 1e-10:
            raise ValueError(
                "Distribution percentages must sum to 100."
            )


def validate_statistical_distribution_baseline_result(
    baseline: StatisticalDistributionBaseline,
) -> StatisticalDistributionBaselineValidationResult:
    """Return a non-raising validation result."""
    if not isinstance(baseline, StatisticalDistributionBaseline):
        return StatisticalDistributionBaselineValidationResult(
            status=INVALID,
            issues=(
                _issue(
                    "INVALID_BASELINE_TYPE",
                    (
                        "baseline must be a "
                        "StatisticalDistributionBaseline instance."
                    ),
                ),
            ),
        )

    try:
        validate_statistical_distribution_baseline(baseline)
    except (TypeError, ValueError) as exc:
        return StatisticalDistributionBaselineValidationResult(
            status=INVALID,
            issues=(
                _issue(
                    "INVALID_DISTRIBUTION_BASELINE",
                    str(exc),
                ),
            ),
        )

    return StatisticalDistributionBaselineValidationResult(
        status=VALID,
        issues=(),
    )


def is_statistical_distribution_baseline_valid(
    baseline: StatisticalDistributionBaseline,
) -> bool:
    return validate_statistical_distribution_baseline_result(
        baseline
    ).is_valid


def get_distribution_baseline(
    baseline: StatisticalDistributionBaseline,
    position: str,
) -> PositionDistribution:
    """Return the distribution for one historical position."""
    validate_statistical_distribution_baseline(baseline)

    for distribution in baseline.distributions:
        if distribution.position == position:
            return distribution

    raise ValueError(
        "Distribution baseline not found for position: "
        f"{position}"
    )


def get_distribution_baseline_positions(
    baseline: StatisticalDistributionBaseline,
) -> tuple[str, ...]:
    """Return distribution positions in deterministic order."""
    validate_statistical_distribution_baseline(baseline)
    return baseline.positions


def get_distribution_baseline_percentage(
    baseline: StatisticalDistributionBaseline,
    position: str,
    digit: int,
) -> float:
    """Return one digit percentage from the distribution baseline."""
    distribution = get_distribution_baseline(
        baseline,
        position,
    )

    if not isinstance(digit, int) or isinstance(digit, bool):
        raise ValueError(
            "digit must be an integer between 0 and 9."
        )

    if digit < 0 or digit > 9:
        raise ValueError(
            "digit must be between 0 and 9."
        )

    return distribution.percentages[digit]
