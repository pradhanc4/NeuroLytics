from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from analytics.statistical_foundation import (
    ANALYSIS_COLUMNS,
    StatisticalAnalysisResult,
    StatisticalObservation,
)


VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class StatisticalBaselineContract:
    """
    Immutable structural contract for a Phase 18 statistical baseline.

    This contract defines the scope and structural metadata of a
    statistical baseline. It does not calculate statistical measures
    and does not perform prediction.
    """

    market_id: int
    analysis_version: str
    baseline_version: str
    start_date: date | None
    end_date: date | None
    analysis_columns: tuple[str, ...]
    observation_count: int
    column_observation_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class StatisticalBaselineValidationIssue:
    """
    One statistical baseline contract validation issue.
    """

    code: str
    message: str


@dataclass(frozen=True)
class StatisticalBaselineValidationResult:
    """
    Result of statistical baseline contract validation.
    """

    status: str
    issues: tuple[StatisticalBaselineValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _build_issue(
    code: str,
    message: str,
) -> StatisticalBaselineValidationIssue:
    return StatisticalBaselineValidationIssue(
        code=code,
        message=message,
    )


def _validate_columns(
    columns: tuple[str, ...],
) -> list[StatisticalBaselineValidationIssue]:
    issues: list[StatisticalBaselineValidationIssue] = []

    if not isinstance(columns, tuple):
        issues.append(
            _build_issue(
                "INVALID_ANALYSIS_COLUMNS",
                "Analysis columns must be a tuple.",
            )
        )
        return issues

    if not columns:
        issues.append(
            _build_issue(
                "EMPTY_ANALYSIS_COLUMNS",
                "At least one analysis column is required.",
            )
        )
        return issues

    for column_name in columns:
        if column_name not in ANALYSIS_COLUMNS:
            issues.append(
                _build_issue(
                    "UNSUPPORTED_ANALYSIS_COLUMN",
                    (
                        f"Unsupported analysis column: "
                        f"{column_name}."
                    ),
                )
            )

    if len(columns) != len(set(columns)):
        issues.append(
            _build_issue(
                "DUPLICATE_ANALYSIS_COLUMNS",
                "Analysis columns must be unique.",
            )
        )

    return issues


def _validate_counts(
    contract: StatisticalBaselineContract,
) -> list[StatisticalBaselineValidationIssue]:
    issues: list[StatisticalBaselineValidationIssue] = []

    if contract.observation_count < 0:
        issues.append(
            _build_issue(
                "INVALID_OBSERVATION_COUNT",
                "Observation count cannot be negative.",
            )
        )

    declared_columns = contract.analysis_columns
    count_columns = tuple(
        column_name
        for column_name, _ in contract.column_observation_counts
    )

    if count_columns != declared_columns:
        issues.append(
            _build_issue(
                "COLUMN_COUNT_ALIGNMENT_MISMATCH",
                (
                    "Column observation counts must exactly match "
                    "the declared analysis columns and ordering."
                ),
            )
        )

    for column_name, count in (
        contract.column_observation_counts
    ):
        if count < 0:
            issues.append(
                _build_issue(
                    "INVALID_COLUMN_OBSERVATION_COUNT",
                    (
                        f"Observation count cannot be negative "
                        f"for {column_name}."
                    ),
                )
            )

    declared_total = sum(
        count
        for _, count in contract.column_observation_counts
    )

    if declared_total != contract.observation_count:
        issues.append(
            _build_issue(
                "OBSERVATION_COUNT_MISMATCH",
                (
                    "Total observation count does not match "
                    "the sum of column observation counts."
                ),
            )
        )

    return issues


def _validate_metadata(
    contract: StatisticalBaselineContract,
) -> list[StatisticalBaselineValidationIssue]:
    issues: list[StatisticalBaselineValidationIssue] = []

    if (
        not isinstance(contract.market_id, int)
        or isinstance(contract.market_id, bool)
        or contract.market_id <= 0
    ):
        issues.append(
            _build_issue(
                "INVALID_MARKET_ID",
                "Market ID must be a positive integer.",
            )
        )

    if (
        not isinstance(contract.analysis_version, str)
        or not contract.analysis_version.strip()
    ):
        issues.append(
            _build_issue(
                "INVALID_ANALYSIS_VERSION",
                "Analysis version must be a non-empty string.",
            )
        )

    if (
        not isinstance(contract.baseline_version, str)
        or not contract.baseline_version.strip()
    ):
        issues.append(
            _build_issue(
                "INVALID_BASELINE_VERSION",
                "Baseline version must be a non-empty string.",
            )
        )

    if (
        contract.start_date is not None
        and not isinstance(contract.start_date, date)
    ):
        issues.append(
            _build_issue(
                "INVALID_START_DATE",
                "Start date must be a date or None.",
            )
        )

    if (
        contract.end_date is not None
        and not isinstance(contract.end_date, date)
    ):
        issues.append(
            _build_issue(
                "INVALID_END_DATE",
                "End date must be a date or None.",
            )
        )

    if (
        isinstance(contract.start_date, date)
        and isinstance(contract.end_date, date)
        and contract.start_date > contract.end_date
    ):
        issues.append(
            _build_issue(
                "INVALID_DATE_RANGE",
                "Start date cannot be later than end date.",
            )
        )

    return issues


def build_statistical_baseline_contract(
    result: StatisticalAnalysisResult,
    observations: Iterable[StatisticalObservation],
    analysis_columns: tuple[str, ...] = ANALYSIS_COLUMNS,
    baseline_version: str = "v1",
) -> StatisticalBaselineContract:
    """
    Build a statistical baseline contract from the existing
    statistical foundation result and observations.

    Existing statistical observation extraction remains the
    source of truth for historical observations.
    """

    if not isinstance(
        result,
        StatisticalAnalysisResult,
    ):
        raise TypeError(
            "result must be a StatisticalAnalysisResult instance."
        )

    if not isinstance(
        analysis_columns,
        tuple,
    ):
        raise TypeError(
            "analysis_columns must be a tuple."
        )

    if not isinstance(
        baseline_version,
        str,
    ) or not baseline_version.strip():
        raise ValueError(
            "baseline_version must be a non-empty string."
        )

    observation_list = list(observations)

    column_counts = {
        column_name: 0
        for column_name in analysis_columns
    }

    for observation in observation_list:
        if not isinstance(
            observation,
            StatisticalObservation,
        ):
            raise TypeError(
                "observations must contain "
                "StatisticalObservation instances."
            )

        if observation.column_name not in column_counts:
            raise ValueError(
                (
                    "Observation column is not included in "
                    "the declared analysis columns: "
                    f"{observation.column_name}."
                )
            )

        column_counts[observation.column_name] += 1

    return StatisticalBaselineContract(
        market_id=result.market_id,
        analysis_version=result.analysis_version,
        baseline_version=baseline_version,
        start_date=result.start_date,
        end_date=result.end_date,
        analysis_columns=analysis_columns,
        observation_count=len(observation_list),
        column_observation_counts=tuple(
            (
                column_name,
                column_counts[column_name],
            )
            for column_name in analysis_columns
        ),
    )


def validate_statistical_baseline_contract(
    contract: StatisticalBaselineContract,
) -> StatisticalBaselineValidationResult:
    """
    Validate the complete statistical baseline contract.
    """

    if not isinstance(
        contract,
        StatisticalBaselineContract,
    ):
        raise TypeError(
            "contract must be a StatisticalBaselineContract instance."
        )

    issues: list[
        StatisticalBaselineValidationIssue
    ] = []

    issues.extend(
        _validate_metadata(contract)
    )

    issues.extend(
        _validate_columns(
            contract.analysis_columns
        )
    )

    issues.extend(
        _validate_counts(contract)
    )

    final_issues = tuple(issues)

    return StatisticalBaselineValidationResult(
        status=(
            INVALID
            if final_issues
            else VALID
        ),
        issues=final_issues,
    )


def build_statistical_baseline_contract_from_observations(
    result: StatisticalAnalysisResult,
    observations: Iterable[StatisticalObservation],
    baseline_version: str = "v1",
) -> StatisticalBaselineContract:
    """
    Convenience builder using all supported analysis columns.
    """

    return build_statistical_baseline_contract(
        result=result,
        observations=observations,
        analysis_columns=ANALYSIS_COLUMNS,
        baseline_version=baseline_version,
    )


def get_baseline_market_id(
    contract: StatisticalBaselineContract,
) -> int:
    if not isinstance(
        contract,
        StatisticalBaselineContract,
    ):
        raise TypeError(
            "contract must be a StatisticalBaselineContract instance."
        )

    return contract.market_id


def get_baseline_analysis_version(
    contract: StatisticalBaselineContract,
) -> str:
    if not isinstance(
        contract,
        StatisticalBaselineContract,
    ):
        raise TypeError(
            "contract must be a StatisticalBaselineContract instance."
        )

    return contract.analysis_version


def get_baseline_version(
    contract: StatisticalBaselineContract,
) -> str:
    if not isinstance(
        contract,
        StatisticalBaselineContract,
    ):
        raise TypeError(
            "contract must be a StatisticalBaselineContract instance."
        )

    return contract.baseline_version


def get_baseline_analysis_columns(
    contract: StatisticalBaselineContract,
) -> tuple[str, ...]:
    if not isinstance(
        contract,
        StatisticalBaselineContract,
    ):
        raise TypeError(
            "contract must be a StatisticalBaselineContract instance."
        )

    return contract.analysis_columns


def get_baseline_observation_count(
    contract: StatisticalBaselineContract,
) -> int:
    if not isinstance(
        contract,
        StatisticalBaselineContract,
    ):
        raise TypeError(
            "contract must be a StatisticalBaselineContract instance."
        )

    return contract.observation_count


def get_baseline_column_observation_counts(
    contract: StatisticalBaselineContract,
) -> tuple[tuple[str, int], ...]:
    if not isinstance(
        contract,
        StatisticalBaselineContract,
    ):
        raise TypeError(
            "contract must be a StatisticalBaselineContract instance."
        )

    return contract.column_observation_counts


def get_baseline_validation_status(
    result: StatisticalBaselineValidationResult,
) -> str:
    if not isinstance(
        result,
        StatisticalBaselineValidationResult,
    ):
        raise TypeError(
            "result must be a StatisticalBaselineValidationResult instance."
        )

    return result.status


def get_baseline_validation_issues(
    result: StatisticalBaselineValidationResult,
) -> tuple[StatisticalBaselineValidationIssue, ...]:
    if not isinstance(
        result,
        StatisticalBaselineValidationResult,
    ):
        raise TypeError(
            "result must be a StatisticalBaselineValidationResult instance."
        )

    return result.issues


def is_statistical_baseline_contract_valid(
    result: StatisticalBaselineValidationResult,
) -> bool:
    if not isinstance(
        result,
        StatisticalBaselineValidationResult,
    ):
        raise TypeError(
            "result must be a StatisticalBaselineValidationResult instance."
        )

    return result.is_valid