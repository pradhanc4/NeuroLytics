from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from analytics.statistical_foundation import (
    ANALYSIS_COLUMNS,
    StatisticalObservation,
    validate_analysis_column,
)


VALID_DIGITS = tuple(range(10))


@dataclass(frozen=True)
class FrequencyRecord:
    """
    Frequency information for one digit.

    Count represents the number of historical observations
    containing the digit.

    Percentage represents that digit's share of all valid
    observations included in the analysis.
    """

    digit: int
    count: int
    percentage: float


@dataclass(frozen=True)
class FrequencyAnalysisResult:
    """
    Complete frequency-analysis result for one analysis column.
    """

    column_name: str
    total_observations: int
    records: tuple[FrequencyRecord, ...]


def calculate_frequency(
    observations: Iterable[StatisticalObservation],
    column_name: str,
) -> FrequencyAnalysisResult:
    """
    Calculate digit frequency for one historical analysis column.

    Only observations belonging to the requested column are included.

    Digits 0-9 are always represented in the result, including digits
    that have zero historical occurrences.

    Actual zero values are counted normally.

    Missing observations are not converted into zero.
    """

    validate_analysis_column(column_name)

    filtered_observations = [
        observation
        for observation in observations
        if observation.column_name == column_name
    ]

    counts = Counter(
        observation.value
        for observation in filtered_observations
    )

    total_observations = len(filtered_observations)

    records: list[FrequencyRecord] = []

    for digit in VALID_DIGITS:
        count = counts.get(digit, 0)

        if total_observations == 0:
            percentage = 0.0
        else:
            percentage = (count / total_observations) * 100

        records.append(
            FrequencyRecord(
                digit=digit,
                count=count,
                percentage=percentage,
            )
        )

    return FrequencyAnalysisResult(
        column_name=column_name,
        total_observations=total_observations,
        records=tuple(records),
    )


def calculate_all_column_frequencies(
    observations: Iterable[StatisticalObservation],
) -> dict[str, FrequencyAnalysisResult]:
    """
    Calculate frequency distributions for all supported analysis columns.

    Each supported column receives its own independent frequency
    distribution.
    """

    observation_list = list(observations)

    return {
        column_name: calculate_frequency(
            observation_list,
            column_name,
        )
        for column_name in ANALYSIS_COLUMNS
    }


def get_frequency_record(
    result: FrequencyAnalysisResult,
    digit: int,
) -> FrequencyRecord:
    """
    Return the frequency record for one digit.
    """

    if digit not in VALID_DIGITS:
        raise ValueError("digit must be between 0 and 9.")

    for record in result.records:
        if record.digit == digit:
            return record

    raise ValueError(
        f"Frequency record for digit {digit} was not found."
    )
