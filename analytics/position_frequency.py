from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.statistical_foundation import (
    ANALYSIS_COLUMNS,
    StatisticalObservation,
    validate_analysis_column,
)
from analytics.frequency_analysis import (
    FrequencyRecord,
)


@dataclass(frozen=True)
class PositionFrequencyResult:
    """
    Frequency information for one digit position.

    The position corresponds to one of the supported historical
    columns: col1 through col8.
    """

    position: str
    total_observations: int
    records: tuple[FrequencyRecord, ...]


def calculate_position_frequency(
    observations: Iterable[StatisticalObservation],
    position: str,
) -> PositionFrequencyResult:
    """
    Calculate the digit-frequency distribution for one exact position.

    Only observations belonging to the requested position are included.

    Digits 0-9 are always represented in the result, including digits
    that have zero historical occurrences.

    Actual zero values are counted as valid observations.

    Missing observations are not converted into zero.
    """

    validate_analysis_column(position)

    filtered_observations = [
        observation
        for observation in observations
        if observation.column_name == position
    ]

    counts = {digit: 0 for digit in range(10)}

    for observation in filtered_observations:
        counts[observation.value] += 1

    total_observations = len(filtered_observations)

    records: list[FrequencyRecord] = []

    for digit in range(10):
        count = counts[digit]

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

    return PositionFrequencyResult(
        position=position,
        total_observations=total_observations,
        records=tuple(records),
    )


def calculate_all_position_frequencies(
    observations: Iterable[StatisticalObservation],
) -> dict[str, PositionFrequencyResult]:
    """
    Calculate independent frequency distributions for all
    supported digit positions.

    Each position receives its own distribution for digits 0-9.
    """

    observation_list = list(observations)

    return {
        position: calculate_position_frequency(
            observation_list,
            position,
        )
        for position in ANALYSIS_COLUMNS
    }


def get_position_frequency_record(
    result: PositionFrequencyResult,
    digit: int,
) -> FrequencyRecord:
    """
    Return the frequency record for one digit from a position result.
    """

    if not isinstance(digit, int) or isinstance(digit, bool):
        raise ValueError("digit must be an integer between 0 and 9.")

    if digit < 0 or digit > 9:
        raise ValueError("digit must be between 0 and 9.")

    return result.records[digit]