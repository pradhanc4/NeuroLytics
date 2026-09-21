from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


# Historical result columns that can be used by the statistical
# analysis layer.
ANALYSIS_COLUMNS = (
    "col1",
    "col2",
    "col3",
    "col4",
    "col5",
    "col6",
    "col7",
    "col8",
)


@dataclass(frozen=True)
class StatisticalAnalysisRequest:
    """
    Defines the input window for a statistical analysis.

    This class contains only analysis scope information.
    It does not perform prediction or modify historical data.
    """

    market_id: int
    start_date: date | None = None
    end_date: date | None = None
    analysis_version: str = "v1"


@dataclass(frozen=True)
class StatisticalObservation:
    """
    Represents one numeric historical observation.

    The source date is retained so later statistical modules can
    perform time-aware analysis without losing historical context.
    """

    record_date: date
    column_name: str
    value: int


@dataclass(frozen=True)
class StatisticalAnalysisResult:
    """
    Standard container for statistical-analysis output.

    Later Phase 9 modules can extend this structure without changing
    the meaning of the underlying historical data.
    """

    market_id: int
    analysis_version: str
    start_date: date | None
    end_date: date | None
    observation_count: int


def validate_analysis_request(
    request: StatisticalAnalysisRequest,
) -> None:
    """
    Validate the statistical-analysis scope.

    Raises:
        ValueError: If the request contains an invalid market ID,
        invalid analysis version, or invalid date range.
    """

    if not isinstance(request.market_id, int):
        raise ValueError("market_id must be an integer.")

    if request.market_id <= 0:
        raise ValueError("market_id must be greater than zero.")

    if not request.analysis_version:
        raise ValueError("analysis_version is required.")

    if request.start_date is not None and not isinstance(
        request.start_date,
        date,
    ):
        raise ValueError("start_date must be a date or None.")

    if request.end_date is not None and not isinstance(
        request.end_date,
        date,
    ):
        raise ValueError("end_date must be a date or None.")

    if (
        request.start_date is not None
        and request.end_date is not None
        and request.start_date > request.end_date
    ):
        raise ValueError(
            "start_date cannot be later than end_date."
        )


def validate_analysis_column(column_name: str) -> None:
    """
    Validate that a requested column belongs to the supported
    historical analysis columns.
    """

    if column_name not in ANALYSIS_COLUMNS:
        raise ValueError(
            f"Unsupported analysis column: {column_name}. "
            f"Supported columns: {', '.join(ANALYSIS_COLUMNS)}."
        )


def extract_observations(
    records: Iterable[object],
    column_name: str,
) -> list[StatisticalObservation]:
    """
    Extract numeric observations from historical records.

    Only non-NULL integer values are accepted.

    Actual zero values are preserved as valid observations.

    No missing value is converted into zero.
    """

    validate_analysis_column(column_name)

    observations: list[StatisticalObservation] = []

    for record in records:
        record_date = getattr(record, "result_date", None)
        value = getattr(record, column_name, None)

        if record_date is None:
            raise ValueError(
                "Historical record is missing result_date."
            )

        if value is None:
            continue

        if isinstance(value, bool):
            raise ValueError(
                f"{column_name} contains an invalid boolean value."
            )

        if not isinstance(value, int):
            raise ValueError(
                f"{column_name} must contain integer values."
            )

        if value < 0 or value > 9:
            raise ValueError(
                f"{column_name} contains value outside the "
                "valid digit range 0-9."
            )

        observations.append(
            StatisticalObservation(
                record_date=record_date,
                column_name=column_name,
                value=value,
            )
        )

    return observations


def build_analysis_result(
    request: StatisticalAnalysisRequest,
    observations: Iterable[StatisticalObservation],
) -> StatisticalAnalysisResult:
    """
    Build the standard statistical-analysis result metadata.
    """

    validate_analysis_request(request)

    observation_list = list(observations)

    return StatisticalAnalysisResult(
        market_id=request.market_id,
        analysis_version=request.analysis_version,
        start_date=request.start_date,
        end_date=request.end_date,
        observation_count=len(observation_list),
    )