from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from analytics.statistical_baseline_contract import (
    StatisticalBaselineContract,
    validate_statistical_baseline_contract,
)
from analytics.statistical_foundation import (
    ANALYSIS_COLUMNS,
    StatisticalObservation,
)


VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class StatisticalBaselineDataset:
    """
    Immutable Phase 18.2 statistical baseline dataset.

    The dataset contains validated historical statistical observations
    together with the structural baseline contract that defines its
    scope.

    This class does not calculate statistical measures and does not
    perform prediction.
    """

    contract: StatisticalBaselineContract
    observations: tuple[StatisticalObservation, ...]

    @property
    def observation_count(self) -> int:
        """Return the number of observations in the dataset."""

        return len(self.observations)

    @property
    def dates(self) -> tuple[date, ...]:
        """Return unique observation dates in deterministic order."""

        return tuple(
            sorted(
                {
                    observation.record_date
                    for observation in self.observations
                }
            )
        )

    @property
    def columns(self) -> tuple[str, ...]:
        """Return the declared analysis columns."""

        return self.contract.analysis_columns


@dataclass(frozen=True)
class StatisticalBaselineDatasetValidationIssue:
    """One Phase 18.2 dataset validation issue."""

    code: str
    message: str


@dataclass(frozen=True)
class StatisticalBaselineDatasetValidationResult:
    """Result of Phase 18.2 dataset validation."""

    status: str
    issues: tuple[
        StatisticalBaselineDatasetValidationIssue,
        ...,
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
) -> StatisticalBaselineDatasetValidationIssue:
    return StatisticalBaselineDatasetValidationIssue(
        code=code,
        message=message,
    )


def _column_order(
    columns: tuple[str, ...],
) -> dict[str, int]:
    """
    Build deterministic column ordering.

    The declared contract ordering is authoritative.
    """

    return {
        column_name: index
        for index, column_name in enumerate(columns)
    }


def _observation_sort_key(
    observation: StatisticalObservation,
    column_order: dict[str, int],
) -> tuple[date, int]:
    """Return the deterministic ordering key for one observation."""

    return (
        observation.record_date,
        column_order[observation.column_name],
    )


def _validate_observation(
    observation: StatisticalObservation,
) -> None:
    """Validate one statistical observation."""

    if not isinstance(
        observation,
        StatisticalObservation,
    ):
        raise TypeError(
            "observations must contain "
            "StatisticalObservation instances."
        )

    if not isinstance(
        observation.record_date,
        date,
    ):
        raise ValueError(
            "Observation record_date must be a date."
        )

    if observation.column_name not in ANALYSIS_COLUMNS:
        raise ValueError(
            "Unsupported column in observation: "
            f"{observation.column_name}"
        )

    if isinstance(
        observation.value,
        bool,
    ) or not isinstance(
        observation.value,
        int,
    ):
        raise ValueError(
            "Observation value must be an integer."
        )

    if observation.value < 0 or observation.value > 9:
        raise ValueError(
            "Observation value must be within the digit range 0-9."
        )


def _validate_observation_date(
    observation: StatisticalObservation,
    contract: StatisticalBaselineContract,
) -> None:
    """Validate one observation against the contract date range."""

    if (
        contract.start_date is not None
        and observation.record_date < contract.start_date
    ):
        raise ValueError(
            "Observation occurs before the contract start date: "
            f"{observation.record_date}"
        )

    if (
        contract.end_date is not None
        and observation.record_date > contract.end_date
    ):
        raise ValueError(
            "Observation occurs after the contract end date: "
            f"{observation.record_date}"
        )


def _validate_duplicate_observations(
    observations: tuple[StatisticalObservation, ...],
) -> None:
    """
    Reject duplicate date/column observations.

    A single historical date/column pair represents one statistical
    observation in the baseline dataset.
    """

    seen: set[tuple[date, str]] = set()

    for observation in observations:
        key = (
            observation.record_date,
            observation.column_name,
        )

        if key in seen:
            raise ValueError(
                "Duplicate statistical observation detected for "
                f"date={observation.record_date}, "
                f"column={observation.column_name}."
            )

        seen.add(key)


def _validate_contract_alignment(
    contract: StatisticalBaselineContract,
    observations: tuple[StatisticalObservation, ...],
) -> None:
    """Validate dataset observations against contract metadata."""

    if len(observations) != contract.observation_count:
        raise ValueError(
            "Dataset observation count does not match "
            "the statistical baseline contract."
        )

    counts = {
        column_name: 0
        for column_name in contract.analysis_columns
    }

    for observation in observations:
        if observation.column_name not in counts:
            raise ValueError(
                "Observation column is not declared by "
                "the statistical baseline contract: "
                f"{observation.column_name}"
            )

        counts[observation.column_name] += 1

    actual_counts = tuple(
        (
            column_name,
            counts[column_name],
        )
        for column_name in contract.analysis_columns
    )

    if actual_counts != contract.column_observation_counts:
        raise ValueError(
            "Dataset column observation counts do not match "
            "the statistical baseline contract."
        )


def build_statistical_baseline_dataset(
    contract: StatisticalBaselineContract,
    observations: tuple[StatisticalObservation, ...],
) -> StatisticalBaselineDataset:
    """
    Build a deterministic Phase 18.2 baseline dataset.

    Existing StatisticalObservation objects remain the source of truth.
    No new statistical values are calculated.
    """

    if not isinstance(
        contract,
        StatisticalBaselineContract,
    ):
        raise TypeError(
            "contract must be a StatisticalBaselineContract instance."
        )

    if not isinstance(
        observations,
        tuple,
    ):
        raise TypeError(
            "observations must be a tuple of "
            "StatisticalObservation objects."
        )

    contract_validation = (
        validate_statistical_baseline_contract(
            contract
        )
    )

    if not contract_validation.is_valid:
        raise ValueError(
            "Cannot build baseline dataset from an invalid "
            "statistical baseline contract."
        )

    for observation in observations:
        _validate_observation(
            observation
        )

        _validate_observation_date(
            observation,
            contract,
        )

    _validate_duplicate_observations(
        observations
    )

    _validate_contract_alignment(
        contract,
        observations,
    )

    column_order = _column_order(
        contract.analysis_columns
    )

    ordered_observations = tuple(
        sorted(
            observations,
            key=lambda observation: _observation_sort_key(
                observation,
                column_order,
            ),
        )
    )

    return StatisticalBaselineDataset(
        contract=contract,
        observations=ordered_observations,
    )


def build_statistical_baseline_dataset_from_list(
    contract: StatisticalBaselineContract,
    observations: list[StatisticalObservation],
) -> StatisticalBaselineDataset:
    """
    Convenience builder for list-based observation input.

    The resulting dataset remains immutable.
    """

    if not isinstance(
        observations,
        list,
    ):
        raise TypeError(
            "observations must be a list."
        )

    return build_statistical_baseline_dataset(
        contract=contract,
        observations=tuple(observations),
    )


def validate_statistical_baseline_dataset(
    dataset: StatisticalBaselineDataset,
) -> None:
    """
    Validate an already-built statistical baseline dataset.
    """

    if not isinstance(
        dataset,
        StatisticalBaselineDataset,
    ):
        raise TypeError(
            "dataset must be a StatisticalBaselineDataset instance."
        )

    contract_validation = (
        validate_statistical_baseline_contract(
            dataset.contract
        )
    )

    if not contract_validation.is_valid:
        raise ValueError(
            "Statistical baseline contract is invalid."
        )

    if not isinstance(
        dataset.observations,
        tuple,
    ):
        raise TypeError(
            "Dataset observations must be a tuple."
        )

    for observation in dataset.observations:
        _validate_observation(
            observation
        )

        _validate_observation_date(
            observation,
            dataset.contract,
        )

    _validate_duplicate_observations(
        dataset.observations
    )

    _validate_contract_alignment(
        dataset.contract,
        dataset.observations,
    )

    column_order = _column_order(
        dataset.contract.analysis_columns
    )

    expected_order = tuple(
        sorted(
            dataset.observations,
            key=lambda observation: _observation_sort_key(
                observation,
                column_order,
            ),
        )
    )

    if dataset.observations != expected_order:
        raise ValueError(
            "Statistical baseline observations must be in "
            "deterministic date/column order."
        )


def get_statistical_baseline_observations(
    dataset: StatisticalBaselineDataset,
) -> tuple[StatisticalObservation, ...]:
    """Return all baseline observations."""

    validate_statistical_baseline_dataset(
        dataset
    )

    return dataset.observations


def get_statistical_baseline_observation_count(
    dataset: StatisticalBaselineDataset,
) -> int:
    """Return the baseline observation count."""

    validate_statistical_baseline_dataset(
        dataset
    )

    return dataset.observation_count


def get_statistical_baseline_dates(
    dataset: StatisticalBaselineDataset,
) -> tuple[date, ...]:
    """Return unique baseline dates."""

    validate_statistical_baseline_dataset(
        dataset
    )

    return dataset.dates


def get_statistical_baseline_columns(
    dataset: StatisticalBaselineDataset,
) -> tuple[str, ...]:
    """Return declared baseline columns."""

    validate_statistical_baseline_dataset(
        dataset
    )

    return dataset.columns


def validate_statistical_baseline_dataset_result(
    dataset: StatisticalBaselineDataset,
) -> StatisticalBaselineDatasetValidationResult:
    """
    Return a non-raising validation result for a baseline dataset.
    """

    if not isinstance(
        dataset,
        StatisticalBaselineDataset,
    ):
        return StatisticalBaselineDatasetValidationResult(
            status=INVALID,
            issues=(
                _build_issue(
                    "INVALID_DATASET_TYPE",
                    (
                        "dataset must be a "
                        "StatisticalBaselineDataset instance."
                    ),
                ),
            ),
        )

    issues: list[
        StatisticalBaselineDatasetValidationIssue
    ] = []

    try:
        validate_statistical_baseline_dataset(
            dataset
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        issues.append(
            _build_issue(
                "INVALID_BASELINE_DATASET",
                str(exc),
            )
        )

    return StatisticalBaselineDatasetValidationResult(
        status=(
            VALID
            if not issues
            else INVALID
        ),
        issues=tuple(issues),
    )


def is_statistical_baseline_dataset_valid(
    dataset: StatisticalBaselineDataset,
) -> bool:
    """Return whether the complete baseline dataset is valid."""

    result = validate_statistical_baseline_dataset_result(
        dataset
    )

    return result.is_valid