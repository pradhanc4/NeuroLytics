from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.point_in_time import (
    PointInTimeHistory,
    get_point_in_time_observations,
)


LEAKAGE = "LEAKAGE"
CLEAN = "CLEAN"

FUTURE_ROW = "FUTURE_ROW"
TARGET_DATE_INCLUDED = "TARGET_DATE_INCLUDED"
DUPLICATE_DATE = "DUPLICATE_DATE"
TEMPORAL_ORDER = "TEMPORAL_ORDER"


@dataclass(frozen=True)
class LeakageIssue:
    """One detected temporal leakage issue."""

    code: str
    message: str
    result_date: date | None


@dataclass(frozen=True)
class LeakageDetectionResult:
    """Complete leakage detection result."""

    status: str
    target_date: date
    observation_count: int
    issues: tuple[LeakageIssue, ...]

    @property
    def is_clean(self) -> bool:
        return self.status == CLEAN

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _build_issue(
    code: str,
    message: str,
    result_date: date | None,
) -> LeakageIssue:
    return LeakageIssue(
        code=code,
        message=message,
        result_date=result_date,
    )


def _validate_observation(
    observation: HistoricalFeatureObservation,
) -> None:
    if not isinstance(
        observation,
        HistoricalFeatureObservation,
    ):
        raise TypeError(
            "observations must contain only "
            "HistoricalFeatureObservation objects."
        )

    if not isinstance(
        observation.result_date,
        date,
    ):
        raise TypeError(
            "Historical observation result_date "
            "must be a date."
        )


def _detect_duplicate_dates(
    observations: tuple[
        HistoricalFeatureObservation,
        ...,
    ],
) -> list[LeakageIssue]:
    issues: list[LeakageIssue] = []

    seen_dates: set[date] = set()

    for observation in observations:
        if observation.result_date in seen_dates:
            issues.append(
                _build_issue(
                    code=DUPLICATE_DATE,
                    message=(
                        "Duplicate historical observation "
                        "date detected."
                    ),
                    result_date=observation.result_date,
                )
            )
        else:
            seen_dates.add(
                observation.result_date
            )

    return issues


def _detect_future_rows(
    observations: tuple[
        HistoricalFeatureObservation,
        ...,
    ],
    target_date: date,
) -> list[LeakageIssue]:
    issues: list[LeakageIssue] = []

    for observation in observations:
        if observation.result_date > target_date:
            issues.append(
                _build_issue(
                    code=FUTURE_ROW,
                    message=(
                        "Historical observation occurs "
                        "after the target date."
                    ),
                    result_date=observation.result_date,
                )
            )

    return issues


def _detect_target_date_inclusion(
    observations: tuple[
        HistoricalFeatureObservation,
        ...,
    ],
    target_date: date,
) -> list[LeakageIssue]:
    issues: list[LeakageIssue] = []

    for observation in observations:
        if observation.result_date == target_date:
            issues.append(
                _build_issue(
                    code=TARGET_DATE_INCLUDED,
                    message=(
                        "Target-date observation is included "
                        "in the feature history."
                    ),
                    result_date=observation.result_date,
                )
            )

    return issues


def _detect_temporal_order(
    observations: tuple[
        HistoricalFeatureObservation,
        ...,
    ],
) -> list[LeakageIssue]:
    issues: list[LeakageIssue] = []

    previous_date: date | None = None

    for observation in observations:
        current_date = observation.result_date

        if (
            previous_date is not None
            and current_date <= previous_date
        ):
            issues.append(
                _build_issue(
                    code=TEMPORAL_ORDER,
                    message=(
                        "Historical observations are not "
                        "strictly chronological."
                    ),
                    result_date=current_date,
                )
            )

        previous_date = current_date

    return issues


def detect_history_leakage(
    observations: tuple[
        HistoricalFeatureObservation,
        ...,
    ],
    target_date: date,
) -> LeakageDetectionResult:
    """
    Detect temporal leakage in a historical observation collection.

    A leakage-free feature history may contain only observations
    strictly before the target date.
    """

    if not isinstance(
        target_date,
        date,
    ):
        raise TypeError(
            "target_date must be a datetime.date instance."
        )

    if isinstance(
        observations,
        (str, bytes),
    ):
        raise TypeError(
            "observations must be an iterable of "
            "HistoricalFeatureObservation objects."
        )

    try:
        materialized = tuple(
            observations
        )
    except TypeError as exc:
        raise TypeError(
            "observations must be an iterable of "
            "HistoricalFeatureObservation objects."
        ) from exc

    for observation in materialized:
        _validate_observation(
            observation
        )

    issues: list[LeakageIssue] = []

    issues.extend(
        _detect_duplicate_dates(
            materialized
        )
    )

    issues.extend(
        _detect_future_rows(
            materialized,
            target_date,
        )
    )

    issues.extend(
        _detect_target_date_inclusion(
            materialized,
            target_date,
        )
    )

    issues.extend(
        _detect_temporal_order(
            materialized
        )
    )

    final_issues = tuple(
        issues
    )

    status = (
        LEAKAGE
        if final_issues
        else CLEAN
    )

    return LeakageDetectionResult(
        status=status,
        target_date=target_date,
        observation_count=len(
            materialized
        ),
        issues=final_issues,
    )


def detect_point_in_time_history_leakage(
    history: PointInTimeHistory,
) -> LeakageDetectionResult:
    """
    Validate an already-built point-in-time history.

    The PointInTimeHistory contract requires every observation
    to occur strictly before its target date.
    """

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    observations = get_point_in_time_observations(
        history
    )

    return detect_history_leakage(
        observations,
        history.target_date,
    )


def get_leakage_status(
    result: LeakageDetectionResult,
) -> str:
    if not isinstance(
        result,
        LeakageDetectionResult,
    ):
        raise TypeError(
            "result must be a LeakageDetectionResult instance."
        )

    return result.status


def get_leakage_issues(
    result: LeakageDetectionResult,
) -> tuple[LeakageIssue, ...]:
    if not isinstance(
        result,
        LeakageDetectionResult,
    ):
        raise TypeError(
            "result must be a LeakageDetectionResult instance."
        )

    return result.issues


def get_leakage_issue_count(
    result: LeakageDetectionResult,
) -> int:
    if not isinstance(
        result,
        LeakageDetectionResult,
    ):
        raise TypeError(
            "result must be a LeakageDetectionResult instance."
        )

    return result.issue_count


def is_leakage_free(
    result: LeakageDetectionResult,
) -> bool:
    if not isinstance(
        result,
        LeakageDetectionResult,
    ):
        raise TypeError(
            "result must be a LeakageDetectionResult instance."
        )

    return result.is_clean