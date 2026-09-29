from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean, median
from typing import Iterable

from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)
from analytics.statistical_foundation import (
    StatisticalObservation,
)


VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class DescriptiveStatistics:
    """
    Immutable descriptive statistics for one analysis column.

    Variance and standard deviation are population measures because
    the supplied historical observations are treated as the complete
    baseline population for this analysis.
    """

    column_name: str
    count: int
    minimum: int | None
    maximum: int | None
    range: int | None
    mean: float | None
    median: float | None
    mode: tuple[int, ...]
    variance: float | None
    standard_deviation: float | None


@dataclass(frozen=True)
class StatisticalDescriptiveResult:
    """
    Immutable Phase 18.3 descriptive-statistics result.

    Results are stored in deterministic analysis-column order.
    """

    market_id: int
    analysis_version: str
    baseline_version: str
    statistics: tuple[DescriptiveStatistics, ...]

    @property
    def column_count(self) -> int:
        """Return the number of summarized columns."""

        return len(self.statistics)

    @property
    def columns(self) -> tuple[str, ...]:
        """Return summarized columns in deterministic order."""

        return tuple(
            statistic.column_name
            for statistic in self.statistics
        )


@dataclass(frozen=True)
class StatisticalDescriptiveValidationIssue:
    """One descriptive-statistics validation issue."""

    code: str
    message: str


@dataclass(frozen=True)
class StatisticalDescriptiveValidationResult:
    """Result of descriptive-statistics validation."""

    status: str
    issues: tuple[
        StatisticalDescriptiveValidationIssue,
        ...
    ]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _build_issue(
    code: str,
    message: str,
) -> StatisticalDescriptiveValidationIssue:
    return StatisticalDescriptiveValidationIssue(
        code=code,
        message=message,
    )


def _calculate_mode(
    values: tuple[int, ...],
) -> tuple[int, ...]:
    """
    Return all modes in ascending deterministic order.

    An empty input has no mode.
    If every value occurs equally often, every value is returned
    because all values are tied for the highest frequency.
    """

    if not values:
        return ()

    frequencies: dict[int, int] = {}

    for value in values:
        frequencies[value] = (
            frequencies.get(value, 0) + 1
        )

    highest_frequency = max(
        frequencies.values()
    )

    return tuple(
        sorted(
            value
            for value, frequency in frequencies.items()
            if frequency == highest_frequency
        )
    )


def _calculate_population_variance(
    values: tuple[int, ...],
) -> float | None:
    """Calculate population variance."""

    if not values:
        return None

    average = mean(values)

    return sum(
        (value - average) ** 2
        for value in values
    ) / len(values)


def _build_statistics(
    column_name: str,
    values: tuple[int, ...],
) -> DescriptiveStatistics:
    """Build descriptive statistics for one column."""

    if not values:
        return DescriptiveStatistics(
            column_name=column_name,
            count=0,
            minimum=None,
            maximum=None,
            range=None,
            mean=None,
            median=None,
            mode=(),
            variance=None,
            standard_deviation=None,
        )

    minimum = min(values)
    maximum = max(values)
    population_variance = (
        _calculate_population_variance(
            values
        )
    )

    return DescriptiveStatistics(
        column_name=column_name,
        count=len(values),
        minimum=minimum,
        maximum=maximum,
        range=maximum - minimum,
        mean=float(mean(values)),
        median=float(median(values)),
        mode=_calculate_mode(values),
        variance=population_variance,
        standard_deviation=(
            sqrt(population_variance)
            if population_variance is not None
            else None
        ),
    )


def _group_observations_by_column(
    dataset: StatisticalBaselineDataset,
) -> dict[str, tuple[int, ...]]:
    """
    Group observations by declared analysis column.

    The contract's declared column ordering remains authoritative.
    """

    grouped: dict[str, list[int]] = {
        column_name: []
        for column_name in dataset.columns
    }

    for observation in dataset.observations:
        grouped[
            observation.column_name
        ].append(
            observation.value
        )

    return {
        column_name: tuple(values)
        for column_name, values in grouped.items()
    }


def build_statistical_descriptive_result(
    dataset: StatisticalBaselineDataset,
) -> StatisticalDescriptiveResult:
    """
    Build descriptive statistics from a validated baseline dataset.

    This function performs descriptive calculations only.

    It does not:
    - modify historical data
    - perform prediction
    - create features
    - calculate probabilities
    - rank candidates
    """

    validate_statistical_baseline_dataset(
        dataset
    )

    grouped = _group_observations_by_column(
        dataset
    )

    statistics = tuple(
        _build_statistics(
            column_name=column_name,
            values=grouped[column_name],
        )
        for column_name in dataset.columns
    )

    return StatisticalDescriptiveResult(
        market_id=dataset.contract.market_id,
        analysis_version=(
            dataset.contract.analysis_version
        ),
        baseline_version=(
            dataset.contract.baseline_version
        ),
        statistics=statistics,
    )


def build_statistical_descriptive_result_from_observations(
    market_id: int,
    analysis_version: str,
    baseline_version: str,
    observations: Iterable[StatisticalObservation],
    columns: tuple[str, ...],
) -> StatisticalDescriptiveResult:
    """
    Build descriptive statistics directly from observations.

    This helper is intentionally not a replacement for the
    validated Phase 18.2 dataset path.

    It is provided only for isolated descriptive-statistics
    calculations and requires explicit column ordering.
    """

    if not isinstance(
        columns,
        tuple,
    ):
        raise TypeError(
            "columns must be a tuple."
        )

    grouped: dict[str, list[int]] = {
        column_name: []
        for column_name in columns
    }

    for observation in observations:
        if not isinstance(
            observation,
            StatisticalObservation,
        ):
            raise TypeError(
                "observations must contain "
                "StatisticalObservation instances."
            )

        if observation.column_name not in grouped:
            raise ValueError(
                "Observation column is not included in "
                "the requested descriptive columns: "
                f"{observation.column_name}"
            )

        grouped[
            observation.column_name
        ].append(
            observation.value
        )

    statistics = tuple(
        _build_statistics(
            column_name=column_name,
            values=tuple(
                grouped[column_name]
            ),
        )
        for column_name in columns
    )

    return StatisticalDescriptiveResult(
        market_id=market_id,
        analysis_version=analysis_version,
        baseline_version=baseline_version,
        statistics=statistics,
    )


def validate_descriptive_statistics(
    result: StatisticalDescriptiveResult,
) -> None:
    """Validate a complete descriptive-statistics result."""

    if not isinstance(
        result,
        StatisticalDescriptiveResult,
    ):
        raise TypeError(
            "result must be a StatisticalDescriptiveResult instance."
        )

    if not isinstance(
        result.market_id,
        int,
    ) or isinstance(
        result.market_id,
        bool,
    ) or result.market_id <= 0:
        raise ValueError(
            "market_id must be a positive integer."
        )

    if not isinstance(
        result.analysis_version,
        str,
    ) or not result.analysis_version.strip():
        raise ValueError(
            "analysis_version must be a non-empty string."
        )

    if not isinstance(
        result.baseline_version,
        str,
    ) or not result.baseline_version.strip():
        raise ValueError(
            "baseline_version must be a non-empty string."
        )

    if not isinstance(
        result.statistics,
        tuple,
    ):
        raise TypeError(
            "statistics must be a tuple."
        )

    previous_column = None

    for statistic in result.statistics:
        if not isinstance(
            statistic,
            DescriptiveStatistics,
        ):
            raise TypeError(
                "statistics must contain "
                "DescriptiveStatistics objects."
            )

        if not isinstance(
            statistic.column_name,
            str,
        ) or not statistic.column_name.strip():
            raise ValueError(
                "column_name must be a non-empty string."
            )

        if statistic.count < 0:
            raise ValueError(
                "count cannot be negative."
            )

        if previous_column is not None:
            if statistic.column_name <= previous_column:
                raise ValueError(
                    "Statistics columns must be in "
                    "deterministic order."
                )

        previous_column = statistic.column_name

        if statistic.count == 0:
            if statistic.minimum is not None:
                raise ValueError(
                    "Empty statistics cannot have a minimum."
                )

            if statistic.maximum is not None:
                raise ValueError(
                    "Empty statistics cannot have a maximum."
                )

            if statistic.range is not None:
                raise ValueError(
                    "Empty statistics cannot have a range."
                )

            if statistic.mean is not None:
                raise ValueError(
                    "Empty statistics cannot have a mean."
                )

            if statistic.median is not None:
                raise ValueError(
                    "Empty statistics cannot have a median."
                )

            if statistic.mode:
                raise ValueError(
                    "Empty statistics cannot have a mode."
                )

            if statistic.variance is not None:
                raise ValueError(
                    "Empty statistics cannot have variance."
                )

            if statistic.standard_deviation is not None:
                raise ValueError(
                    "Empty statistics cannot have standard deviation."
                )

            continue

        if statistic.minimum is None:
            raise ValueError(
                "Non-empty statistics require a minimum."
            )

        if statistic.maximum is None:
            raise ValueError(
                "Non-empty statistics require a maximum."
            )

        if statistic.range is None:
            raise ValueError(
                "Non-empty statistics require a range."
            )

        if statistic.mean is None:
            raise ValueError(
                "Non-empty statistics require a mean."
            )

        if statistic.median is None:
            raise ValueError(
                "Non-empty statistics require a median."
            )

        if statistic.variance is None:
            raise ValueError(
                "Non-empty statistics require variance."
            )

        if statistic.standard_deviation is None:
            raise ValueError(
                "Non-empty statistics require standard deviation."
            )

        if statistic.minimum < 0 or statistic.minimum > 9:
            raise ValueError(
                "minimum must be within the digit range 0-9."
            )

        if statistic.maximum < 0 or statistic.maximum > 9:
            raise ValueError(
                "maximum must be within the digit range 0-9."
            )

        if statistic.minimum > statistic.maximum:
            raise ValueError(
                "minimum cannot exceed maximum."
            )

        if statistic.range != (
            statistic.maximum - statistic.minimum
        ):
            raise ValueError(
                "range must equal maximum minus minimum."
            )

        if statistic.variance < 0:
            raise ValueError(
                "variance cannot be negative."
            )

        if statistic.standard_deviation < 0:
            raise ValueError(
                "standard deviation cannot be negative."
            )

        if not statistic.mode:
            raise ValueError(
                "Non-empty statistics require at least one mode."
            )

        for mode_value in statistic.mode:
            if mode_value < 0 or mode_value > 9:
                raise ValueError(
                    "mode values must be within the digit range 0-9."
                )


def validate_statistical_descriptive_result(
    result: StatisticalDescriptiveResult,
) -> StatisticalDescriptiveValidationResult:
    """
    Return a non-raising validation result.
    """

    if not isinstance(
        result,
        StatisticalDescriptiveResult,
    ):
        return StatisticalDescriptiveValidationResult(
            status=INVALID,
            issues=(
                _build_issue(
                    "INVALID_RESULT_TYPE",
                    (
                        "result must be a "
                        "StatisticalDescriptiveResult instance."
                    ),
                ),
            ),
        )

    issues: list[
        StatisticalDescriptiveValidationIssue
    ] = []

    try:
        validate_descriptive_statistics(
            result
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        issues.append(
            _build_issue(
                "INVALID_DESCRIPTIVE_RESULT",
                str(exc),
            )
        )

    return StatisticalDescriptiveValidationResult(
        status=(
            VALID
            if not issues
            else INVALID
        ),
        issues=tuple(issues),
    )


def is_statistical_descriptive_result_valid(
    result: StatisticalDescriptiveResult,
) -> bool:
    """Return whether the descriptive result is valid."""

    validation = validate_statistical_descriptive_result(
        result
    )

    return validation.is_valid


def get_descriptive_statistics(
    result: StatisticalDescriptiveResult,
) -> tuple[DescriptiveStatistics, ...]:
    """Return all column-level descriptive statistics."""

    validate_descriptive_statistics(
        result
    )

    return result.statistics


def get_column_descriptive_statistics(
    result: StatisticalDescriptiveResult,
    column_name: str,
) -> DescriptiveStatistics:
    """Return descriptive statistics for one column."""

    validate_descriptive_statistics(
        result
    )

    for statistic in result.statistics:
        if statistic.column_name == column_name:
            return statistic

    raise ValueError(
        f"Descriptive statistics not found for column: "
        f"{column_name}"
    )


def get_descriptive_column_names(
    result: StatisticalDescriptiveResult,
) -> tuple[str, ...]:
    """Return descriptive-statistics column names."""

    validate_descriptive_statistics(
        result
    )

    return result.columns