from __future__ import annotations

from dataclasses import dataclass

from analytics.frequency_analysis import (
    FrequencyAnalysisResult,
    calculate_frequency,
)
from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)
from analytics.statistical_foundation import (
    ANALYSIS_COLUMNS,
)


VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class StatisticalFrequencyBaseline:
    """Immutable Phase 18.4 frequency baseline."""

    market_id: int
    analysis_version: str
    baseline_version: str
    frequencies: tuple[FrequencyAnalysisResult, ...]
    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(result.column_name for result in self.frequencies)

    @property
    def column_count(self) -> int:
        return len(self.frequencies)


@dataclass(frozen=True)
class StatisticalFrequencyBaselineValidationIssue:
    """One frequency-baseline validation issue."""

    code: str
    message: str


@dataclass(frozen=True)
class StatisticalFrequencyBaselineValidationResult:
    """Result of frequency-baseline validation."""

    status: str
    issues: tuple[StatisticalFrequencyBaselineValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def issue_count(self) -> int:        return len(self.issues)


def _issue(
    code: str,
    message: str,
) -> StatisticalFrequencyBaselineValidationIssue:
    return StatisticalFrequencyBaselineValidationIssue(
        code=code,
        message=message,
    )


def build_statistical_frequency_baseline(
    dataset: StatisticalBaselineDataset,
) -> StatisticalFrequencyBaseline:
    """
    Build a frequency baseline from the validated Phase 18.2 dataset.

    The existing frequency_analysis engine is the source of truth for
    digit counts and percentages. This layer only scopes those results
    to the Phase 18 baseline dataset and preserves deterministic order.
    """
    validate_statistical_baseline_dataset(dataset)

    results = tuple(
        calculate_frequency(
            dataset.observations,
            column_name,
        )        for column_name in dataset.columns
    )

    return StatisticalFrequencyBaseline(
        market_id=dataset.contract.market_id,
        analysis_version=dataset.contract.analysis_version,
        baseline_version=dataset.contract.baseline_version,
        frequencies=results,
    )


def validate_statistical_frequency_baseline(
    baseline: StatisticalFrequencyBaseline,
) -> None:
    """Validate a complete frequency baseline."""
    if not isinstance(
        baseline,
        StatisticalFrequencyBaseline,
    ):
        raise TypeError(
            "baseline must be a StatisticalFrequencyBaseline instance."
        )

    if not isinstance(baseline.market_id, int) or isinstance(
        baseline.market_id,
        bool,
    ) or baseline.market_id <= 0:
        raise ValueError("market_id must be a positive integer.")

    if not isinstance(        baseline.analysis_version,
        str,
    ) or not baseline.analysis_version.strip():
        raise ValueError(
            "analysis_version must be a non-empty string."
        )

    if not isinstance(
        baseline.baseline_version,
        str,
    ) or not baseline.baseline_version.strip():
        raise ValueError(
            "baseline_version must be a non-empty string."
        )

    if not isinstance(baseline.frequencies, tuple):
        raise TypeError("frequencies must be a tuple.")

    for result in baseline.frequencies:
        if not isinstance(result, FrequencyAnalysisResult):
            raise TypeError("frequencies must contain FrequencyAnalysisResult instances.")

    expected_columns = tuple(
        result.column_name
        for result in baseline.frequencies
    )

    if expected_columns != baseline.columns:
        raise ValueError(
            "Frequency baseline columns must be deterministic."
        )

    if len(baseline.frequencies) != len(
        set(expected_columns)    ):
        raise ValueError(
            "Frequency baseline columns must be unique."
        )

    for index, result in enumerate(baseline.frequencies):
        if not isinstance(result, FrequencyAnalysisResult):
            raise TypeError(
                "frequencies must contain "
                "FrequencyAnalysisResult instances."
            )

        if result.column_name not in ANALYSIS_COLUMNS:
            raise ValueError(
                "Frequency baseline contains an unsupported column: "
                f"{result.column_name}"
            )

        if index > 0 and (
            baseline.frequencies[index - 1].column_name
            >= result.column_name
        ):
            raise ValueError(
                "Frequency baseline columns must be in deterministic "
                "analysis-column order."
            )

        if result.total_observations < 0:
            raise ValueError(
                "Frequency total_observations cannot be negative."            )

        if len(result.records) != 10:
            raise ValueError(
                "Each frequency baseline must contain digits 0-9."
            )

        digits = tuple(record.digit for record in result.records)
        if digits != tuple(range(10)):
            raise ValueError(
                "Frequency records must contain digits 0-9 in order."
            )

        counted_total = sum(
            record.count for record in result.records
        )

        if counted_total != result.total_observations:
            raise ValueError(
                "Frequency counts must equal total_observations."
            )

        for record in result.records:
            if record.count < 0:
                raise ValueError(
                    "Frequency counts cannot be negative."
                )

            if record.percentage < 0 or record.percentage > 100:
                raise ValueError(                    "Frequency percentages must be between 0 and 100."
                )

            expected_percentage = (
                0.0
                if result.total_observations == 0
                else (
                    record.count
                    / result.total_observations
                    * 100
                )
            )

            if abs(
                record.percentage - expected_percentage
            ) > 1e-12:
                raise ValueError(
                    "Frequency percentage does not match its count."
                )

        percentage_total = sum(
            record.percentage
            for record in result.records
        )

        if result.total_observations > 0 and abs(
            percentage_total - 100.0
        ) > 1e-10:
            raise ValueError(
                "Frequency percentages must sum to 100."            )

        if result.total_observations == 0 and percentage_total != 0.0:
            raise ValueError(
                "Empty frequency baselines must have zero percentages."
            )


def validate_statistical_frequency_baseline_result(
    baseline: StatisticalFrequencyBaseline,
) -> StatisticalFrequencyBaselineValidationResult:
    """Return a non-raising validation result."""
    if not isinstance(
        baseline,
        StatisticalFrequencyBaseline,
    ):
        return StatisticalFrequencyBaselineValidationResult(
            status=INVALID,
            issues=(
                _issue(
                    "INVALID_BASELINE_TYPE",
                    (
                        "baseline must be a "
                        "StatisticalFrequencyBaseline instance."
                    ),
                ),
            ),
        )

    try:        validate_statistical_frequency_baseline(baseline)
    except (TypeError, ValueError) as exc:
        return StatisticalFrequencyBaselineValidationResult(
            status=INVALID,
            issues=(
                _issue(
                    "INVALID_FREQUENCY_BASELINE",
                    str(exc),
                ),
            ),
        )

    return StatisticalFrequencyBaselineValidationResult(
        status=VALID,
        issues=(),
    )


def is_statistical_frequency_baseline_valid(
    baseline: StatisticalFrequencyBaseline,
) -> bool:
    return validate_statistical_frequency_baseline_result(
        baseline
    ).is_valid


def get_frequency_baseline(
    baseline: StatisticalFrequencyBaseline,
    column_name: str,
) -> FrequencyAnalysisResult:
    """Return the frequency result for one baseline column."""
    validate_statistical_frequency_baseline(baseline)

    for result in baseline.frequencies:
        if result.column_name == column_name:
            return result

    raise ValueError(
        "Frequency baseline not found for column: "
        f"{column_name}"
    )


def get_frequency_baseline_columns(
    baseline: StatisticalFrequencyBaseline,
) -> tuple[str, ...]:
    """Return baseline columns in deterministic order."""
    validate_statistical_frequency_baseline(baseline)
    return baseline.columns


def get_frequency_baseline_observation_count(
    baseline: StatisticalFrequencyBaseline,
    column_name: str,
) -> int:
    """Return the observation count for one baseline column."""
    return get_frequency_baseline(
        baseline,
        column_name,
    ).total_observations