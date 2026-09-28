from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.leakage_detector import (
    CLEAN,
    LEAKAGE,
    DUPLICATE_DATE,
    FUTURE_ROW,
    TARGET_DATE_INCLUDED,
    TEMPORAL_ORDER,
    detect_history_leakage,
)
from features.sequence_dataset import (
    SequenceDataset,
    SequenceSample,
    validate_sequence_dataset,
)
from features.sequence_targets import (
    SequenceTargetDataset,
    validate_sequence_target_dataset,
)
from features.sequence_windows import (
    SequenceWindowDataset,
    validate_sequence_window_dataset,
)


# ---------------------------------------------------------------------------
# Sequence-specific issue codes
# ---------------------------------------------------------------------------

SEQUENCE_TARGET_MISMATCH = "SEQUENCE_TARGET_MISMATCH"
SEQUENCE_DATE_MISMATCH = "SEQUENCE_DATE_MISMATCH"
TARGET_IN_SEQUENCE = "TARGET_IN_SEQUENCE"


# ---------------------------------------------------------------------------
# Result / issue contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SequenceLeakageIssue:
    code: str
    message: str
    sample_index: int | None = None
    result_id: int | None = None
    target_date: date | None = None


@dataclass(frozen=True)
class SequenceLeakageResult:
    status: str
    target_date: date | None
    sample_count: int
    issues: tuple[SequenceLeakageIssue, ...]

    @property
    def is_clean(self) -> bool:
        return self.status == CLEAN

    @property
    def has_leakage(self) -> bool:
        return self.status == LEAKAGE

    @property
    def issue_count(self) -> int:
        return len(self.issues)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _issue(
    code: str,
    message: str,
    *,
    sample_index: int | None = None,
    result_id: int | None = None,
    target_date: date | None = None,
) -> SequenceLeakageIssue:
    return SequenceLeakageIssue(
        code=code,
        message=message,
        sample_index=sample_index,
        result_id=result_id,
        target_date=target_date,
    )


def _validate_observations(
    observations: tuple[HistoricalFeatureObservation, ...],
) -> tuple[SequenceLeakageIssue, ...]:
    issues: list[SequenceLeakageIssue] = []

    for observation in observations:
        observation_date = getattr(
            observation,
            "result_date",
            None,
        )

        if observation_date is None:
            issues.append(
                _issue(
                    SEQUENCE_DATE_MISMATCH,
                    "Historical observation is missing a date.",
                    result_id=getattr(
                        observation,
                        "result_id",
                        None,
                    ),
                )
            )

    return tuple(issues)


def _observation_by_result_id(
    observations: tuple[HistoricalFeatureObservation, ...],
) -> dict[int, HistoricalFeatureObservation]:
    result: dict[int, HistoricalFeatureObservation] = {}

    for observation in observations:
        result_id = getattr(
            observation,
            "result_id",
            None,
        )

        if result_id is None:
            continue

        result[result_id] = observation

    return result


def _observation_date(
    observation: HistoricalFeatureObservation,
) -> date | None:
    return getattr(
        observation,
        "result_date",
        None,
    )


def _validate_history_structure(
    observations: tuple[HistoricalFeatureObservation, ...],
) -> tuple[SequenceLeakageIssue, ...]:
    """
    Validate global historical structure.

    Only duplicate-date and temporal-order problems are treated as global
    history violations here.

    FUTURE_ROW is intentionally handled relative to a specific sequence
    validation horizon.
    """

    if not observations:
        return ()

    detected = detect_history_leakage(
        observations,
        date.max,
    )

    issues: list[SequenceLeakageIssue] = []

    for detected_issue in detected.issues:
        if detected_issue.code not in {
            DUPLICATE_DATE,
            TEMPORAL_ORDER,
        }:
            continue

        issues.append(
            _issue(
                detected_issue.code,
                detected_issue.message,
                result_id=getattr(
                    detected_issue,
                    "result_id",
                    None,
                ),
                target_date=getattr(
                    detected_issue,
                    "target_date",
                    None,
                ),
            )
        )

    return tuple(issues)


def _sequence_observations_for_sample(
    observations: tuple[HistoricalFeatureObservation, ...],
    sample: SequenceSample,
) -> tuple[HistoricalFeatureObservation, ...]:
    """
    Reconstruct the observations represented by a final SequenceSample.

    SequenceSample stores sequence dates/features rather than result IDs, so
    membership is reconstructed from the declared date range.
    """

    result: list[HistoricalFeatureObservation] = []

    for observation in observations:
        observation_date = _observation_date(
            observation
        )

        if observation_date is None:
            continue

        if (
            sample.sequence_start_date
            <= observation_date
            <= sample.sequence_end_date
        ):
            result.append(observation)

    return tuple(result)


def _validate_sample_sequence_dates(
    sample: SequenceSample,
) -> tuple[SequenceLeakageIssue, ...]:
    issues: list[SequenceLeakageIssue] = []

    if sample.sequence_start_date > sample.sequence_end_date:
        issues.append(
            _issue(
                SEQUENCE_DATE_MISMATCH,
                (
                    "Sequence start date must not be after "
                    "sequence end date."
                ),
                sample_index=sample.sample_index,
                target_date=sample.target_date,
            )
        )

    if sample.target_date <= sample.sequence_end_date:
        # This is specifically the PIT boundary violation expected by
        # the leakage detector contract.
        issues.append(
            _issue(
                TARGET_DATE_INCLUDED,
                (
                    "Target date is on or before the sequence "
                    "end date and is therefore included in the "
                    "historical sequence horizon."
                ),
                sample_index=sample.sample_index,
                target_date=sample.target_date,
            )
        )

        issues.append(
            _issue(
                SEQUENCE_TARGET_MISMATCH,
                (
                    "Target date must be strictly after "
                    "sequence end date."
                ),
                sample_index=sample.sample_index,
                target_date=sample.target_date,
            )
        )

    return tuple(issues)


def _validate_target_not_in_sequence(
    sample: SequenceSample,
    observations: tuple[HistoricalFeatureObservation, ...],
) -> tuple[SequenceLeakageIssue, ...]:
    issues: list[SequenceLeakageIssue] = []

    for observation in observations:
        observation_date = _observation_date(
            observation
        )

        if observation_date is None:
            continue

        if observation_date == sample.target_date:
            issues.append(
                _issue(
                    TARGET_IN_SEQUENCE,
                    (
                        "Target observation is included inside "
                        "the sequence history."
                    ),
                    sample_index=sample.sample_index,
                    result_id=getattr(
                        observation,
                        "result_id",
                        None,
                    ),
                    target_date=sample.target_date,
                )
            )

    return tuple(issues)


def _validate_observation_sequence(
    sample: SequenceSample,
    observations: tuple[HistoricalFeatureObservation, ...],
) -> tuple[SequenceLeakageIssue, ...]:
    issues: list[SequenceLeakageIssue] = []

    sequence_observations = _sequence_observations_for_sample(
        observations,
        sample,
    )

    if len(sequence_observations) != sample.sequence_length:
        issues.append(
            _issue(
                SEQUENCE_DATE_MISMATCH,
                (
                    "Historical observations represented by "
                    "the sequence dates do not match sequence length."
                ),
                sample_index=sample.sample_index,
                target_date=sample.target_date,
            )
        )

    for observation in sequence_observations:
        observation_date = _observation_date(
            observation
        )

        if observation_date is None:
            continue

        if observation_date >= sample.target_date:
            issues.append(
                _issue(
                    FUTURE_ROW,
                    (
                        "Sequence contains an observation on or "
                        "after the target date."
                    ),
                    sample_index=sample.sample_index,
                    result_id=getattr(
                        observation,
                        "result_id",
                        None,
                    ),
                    target_date=sample.target_date,
                )
            )

    sequence_history_issues = _validate_history_structure(
        sequence_observations,
    )

    issues.extend(sequence_history_issues)

    issues.extend(
        _validate_target_not_in_sequence(
            sample,
            sequence_observations,
        )
    )

    return tuple(issues)


def _validate_sample_target(
    sample: SequenceSample,
    observations: tuple[HistoricalFeatureObservation, ...],
) -> tuple[SequenceLeakageIssue, ...]:
    issues: list[SequenceLeakageIssue] = []

    observation_by_date: dict[
        date,
        HistoricalFeatureObservation,
    ] = {}

    for observation in observations:
        observation_date = _observation_date(
            observation
        )

        if observation_date is None:
            continue

        observation_by_date[observation_date] = observation

    target_observation = observation_by_date.get(
        sample.target_date
    )

    # A target must exist in the historical source.
    if target_observation is None:
        issues.append(
            _issue(
                SEQUENCE_TARGET_MISMATCH,
                (
                    "Sequence target date does not exist "
                    "in historical observations."
                ),
                sample_index=sample.sample_index,
                target_date=sample.target_date,
            )
        )

    if sample.target_date <= sample.sequence_end_date:
        return tuple(issues)

    sequence_observations = _sequence_observations_for_sample(
        observations,
        sample,
    )

    for observation in sequence_observations:
        observation_date = _observation_date(
            observation
        )

        if observation_date is None:
            continue

        if observation_date >= sample.target_date:
            issues.append(
                _issue(
                    FUTURE_ROW,
                    (
                        "An observation at or after the target "
                        "date appears inside the sample sequence."
                    ),
                    sample_index=sample.sample_index,
                    result_id=getattr(
                        observation,
                        "result_id",
                        None,
                    ),
                    target_date=sample.target_date,
                )
            )

    return tuple(issues)


# ---------------------------------------------------------------------------
# Sample-level validation
# ---------------------------------------------------------------------------


def validate_sequence_sample_point_in_time(
    sample: SequenceSample,
    observations: tuple[HistoricalFeatureObservation, ...],
) -> SequenceLeakageResult:
    """
    Validate one final sequence sample for point-in-time correctness.
    """

    if not isinstance(sample, SequenceSample):
        raise TypeError(
            "sample must be a SequenceSample"
        )

    if not isinstance(observations, tuple):
        raise TypeError(
            "observations must be a tuple"
        )

    for observation in observations:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "observations must contain "
                "HistoricalFeatureObservation objects"
            )

    issues: list[SequenceLeakageIssue] = []

    issues.extend(
        _validate_observations(observations)
    )

    issues.extend(
        _validate_history_structure(observations)
    )

    issues.extend(
        _validate_sample_sequence_dates(sample)
    )

    issues.extend(
        _validate_observation_sequence(
            sample,
            observations,
        )
    )

    issues.extend(
        _validate_sample_target(
            sample,
            observations,
        )
    )

    status = LEAKAGE if issues else CLEAN

    return SequenceLeakageResult(
        status=status,
        target_date=sample.target_date,
        sample_count=1,
        issues=tuple(issues),
    )


# ---------------------------------------------------------------------------
# Complete final dataset validation
# ---------------------------------------------------------------------------


def validate_sequence_dataset_point_in_time(
    dataset: SequenceDataset,
    observations: tuple[HistoricalFeatureObservation, ...],
) -> SequenceLeakageResult:
    """
    Validate the complete final SequenceDataset for PIT leakage.
    """

    if not isinstance(dataset, SequenceDataset):
        raise TypeError(
            "dataset must be a SequenceDataset"
        )

    if not isinstance(observations, tuple):
        raise TypeError(
            "observations must be a tuple"
        )

    for observation in observations:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "observations must contain "
                "HistoricalFeatureObservation objects"
            )

    issues: list[SequenceLeakageIssue] = []

    try:
        validate_sequence_dataset(dataset)
    except Exception as exc:
        issues.append(
            _issue(
                SEQUENCE_DATE_MISMATCH,
                f"Sequence dataset contract validation failed: {exc}",
            )
        )

    issues.extend(
        _validate_observations(observations)
    )

    issues.extend(
        _validate_history_structure(observations)
    )

    for sample in dataset.samples:
        sample_result = validate_sequence_sample_point_in_time(
            sample,
            observations,
        )

        issues.extend(
            sample_result.issues
        )

    target_date = None

    if dataset.samples:
        target_date = max(
            sample.target_date
            for sample in dataset.samples
        )

    status = LEAKAGE if issues else CLEAN

    return SequenceLeakageResult(
        status=status,
        target_date=target_date,
        sample_count=len(dataset.samples),
        issues=tuple(issues),
    )


# ---------------------------------------------------------------------------
# Component-level validation
# ---------------------------------------------------------------------------


def validate_sequence_components_point_in_time(
    windows: SequenceWindowDataset,
    targets: SequenceTargetDataset,
    observations: tuple[HistoricalFeatureObservation, ...],
) -> SequenceLeakageResult:
    """
    Validate sequence windows and targets before final dataset assembly.

    Important:
    The component validation horizon is the latest target date represented
    by the supplied target components.

    Historical observations after that horizon are future rows relative to
    the component dataset and must not be available to the validation
    context.
    """

    if not isinstance(
        windows,
        SequenceWindowDataset,
    ):
        raise TypeError(
            "windows must be a SequenceWindowDataset"
        )

    if not isinstance(
        targets,
        SequenceTargetDataset,
    ):
        raise TypeError(
            "targets must be a SequenceTargetDataset"
        )

    if not isinstance(observations, tuple):
        raise TypeError(
            "observations must be a tuple"
        )

    for observation in observations:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "observations must contain "
                "HistoricalFeatureObservation objects"
            )

    issues: list[SequenceLeakageIssue] = []

    # ---------------------------------------------------------------
    # Base component contracts
    # ---------------------------------------------------------------

    try:
        validate_sequence_window_dataset(windows)
    except Exception as exc:
        issues.append(
            _issue(
                SEQUENCE_DATE_MISMATCH,
                f"Sequence window validation failed: {exc}",
            )
        )

    try:
        validate_sequence_target_dataset(targets)
    except Exception as exc:
        issues.append(
            _issue(
                SEQUENCE_TARGET_MISMATCH,
                f"Sequence target validation failed: {exc}",
            )
        )

    # ---------------------------------------------------------------
    # Historical observations
    # ---------------------------------------------------------------

    issues.extend(
        _validate_observations(observations)
    )

    issues.extend(
        _validate_history_structure(observations)
    )

    observation_by_result_id = _observation_by_result_id(
        observations
    )

    # ---------------------------------------------------------------
    # Component validation horizon
    # ---------------------------------------------------------------

    target_dates = [
        target.target_date
        for target in targets.targets
        if target.target_date is not None
    ]

    component_horizon = (
        max(target_dates)
        if target_dates
        else None
    )

    # Any observation after the latest supplied target belongs to the
    # future relative to this component dataset.
    if component_horizon is not None:
        for observation in observations:
            observation_date = _observation_date(
                observation
            )

            if observation_date is None:
                continue

            if observation_date > component_horizon:
                issues.append(
                    _issue(
                        FUTURE_ROW,
                        (
                            "Historical observation occurs after "
                            "the latest target date represented by "
                            "the sequence components."
                        ),
                        result_id=getattr(
                            observation,
                            "result_id",
                            None,
                        ),
                        target_date=component_horizon,
                    )
                )

    # ---------------------------------------------------------------
    # Window validation
    # ---------------------------------------------------------------

    for window in windows.windows:
        window_observations: list[
            HistoricalFeatureObservation
        ] = []

        for result_id in window.result_ids:
            observation = observation_by_result_id.get(
                result_id
            )

            if observation is None:
                issues.append(
                    _issue(
                        SEQUENCE_DATE_MISMATCH,
                        (
                            "Sequence window references a result ID "
                            "that does not exist in historical observations."
                        ),
                        result_id=result_id,
                    )
                )
                continue

            window_observations.append(
                observation
            )

        previous_date: date | None = None

        for observation in window_observations:
            observation_date = _observation_date(
                observation
            )

            if observation_date is None:
                continue

            if previous_date is not None:
                if observation_date <= previous_date:
                    issues.append(
                        _issue(
                            TEMPORAL_ORDER,
                            (
                                "Sequence window observations are "
                                "not strictly chronological."
                            ),
                            result_id=getattr(
                                observation,
                                "result_id",
                                None,
                            ),
                        )
                    )

            previous_date = observation_date

        for observation in window_observations:
            observation_date = _observation_date(
                observation
            )

            if observation_date is None:
                continue

            if observation_date > window.sequence_end_date:
                issues.append(
                    _issue(
                        FUTURE_ROW,
                        (
                            "Sequence window contains an observation "
                            "after its sequence end date."
                        ),
                        result_id=getattr(
                            observation,
                            "result_id",
                            None,
                        ),
                    )
                )

            if observation_date < window.sequence_start_date:
                issues.append(
                    _issue(
                        SEQUENCE_DATE_MISMATCH,
                        (
                            "Sequence window contains an observation "
                            "before its sequence start date."
                        ),
                        result_id=getattr(
                            observation,
                            "result_id",
                            None,
                        ),
                    )
                )

    # ---------------------------------------------------------------
    # Target validation
    # ---------------------------------------------------------------

    target_by_window_index = {
        target.window_index: target
        for target in targets.targets
    }

    for window in windows.windows:
        target = target_by_window_index.get(
            window.window_index
        )

        if target is None:
            # A terminal window ending exactly at the latest historical
            # observation legitimately has no future target yet.
            latest_history_date = None

            valid_dates = [
                _observation_date(observation)
                for observation in observations
                if _observation_date(observation) is not None
            ]

            if valid_dates:
                latest_history_date = max(valid_dates)

            if (
                latest_history_date is not None
                and window.sequence_end_date
                == latest_history_date
            ):
                continue

            issues.append(
                _issue(
                    SEQUENCE_TARGET_MISMATCH,
                    (
                        "Sequence window does not have a "
                        "corresponding target."
                    ),
                    sample_index=window.window_index,
                )
            )
            continue

        if target.target_date <= window.sequence_end_date:
            issues.append(
                _issue(
                    SEQUENCE_TARGET_MISMATCH,
                    (
                        "Sequence target date must be strictly "
                        "after the sequence window end date."
                    ),
                    result_id=getattr(
                        target,
                        "result_id",
                        None,
                    ),
                    target_date=target.target_date,
                )
            )

            issues.append(
                _issue(
                    TARGET_DATE_INCLUDED,
                    (
                        "Sequence target date is on or before "
                        "the sequence window end date."
                    ),
                    result_id=getattr(
                        target,
                        "result_id",
                        None,
                    ),
                    target_date=target.target_date,
                )
            )

        target_observation = observation_by_result_id.get(
            target.result_id
        )

        if target_observation is None:
            issues.append(
                _issue(
                    SEQUENCE_TARGET_MISMATCH,
                    (
                        "Sequence target references a result ID "
                        "that does not exist in historical observations."
                    ),
                    result_id=target.result_id,
                    target_date=target.target_date,
                )
            )
            continue

        target_observation_date = _observation_date(
            target_observation
        )

        if target_observation_date != target.target_date:
            issues.append(
                _issue(
                    SEQUENCE_DATE_MISMATCH,
                    (
                        "Sequence target date does not match "
                        "the historical observation date."
                    ),
                    result_id=target.result_id,
                    target_date=target.target_date,
                )
            )

        if target.result_id in window.result_ids:
            issues.append(
                _issue(
                    TARGET_IN_SEQUENCE,
                    (
                        "Sequence target result ID is also "
                        "present inside the sequence window."
                    ),
                    result_id=target.result_id,
                    target_date=target.target_date,
                )
            )

        if (
            target_observation_date is not None
            and target_observation_date <= window.sequence_end_date
        ):
            issues.append(
                _issue(
                    FUTURE_ROW,
                    (
                        "Sequence target observation is not "
                        "strictly after the sequence window."
                    ),
                    result_id=target.result_id,
                    target_date=target.target_date,
                )
            )

    # ---------------------------------------------------------------
    # Result
    # ---------------------------------------------------------------

    status = LEAKAGE if issues else CLEAN

    return SequenceLeakageResult(
        status=status,
        target_date=component_horizon,
        sample_count=len(windows.windows),
        issues=tuple(issues),
    )


# ---------------------------------------------------------------------------
# Convenience accessors
# ---------------------------------------------------------------------------


def get_sequence_leakage_status(
    result: SequenceLeakageResult,
) -> str:
    return result.status


def get_sequence_leakage_issue_count(
    result: SequenceLeakageResult,
) -> int:
    return result.issue_count


def get_sequence_leakage_issues(
    result: SequenceLeakageResult,
) -> tuple[SequenceLeakageIssue, ...]:
    return result.issues


def is_sequence_dataset_clean(
    result: SequenceLeakageResult,
) -> bool:
    return result.is_clean


def is_sequence_leakage_free(
    result: SequenceLeakageResult,
) -> bool:
    return result.is_clean


def has_sequence_leakage(
    result: SequenceLeakageResult,
) -> bool:
    return result.has_leakage