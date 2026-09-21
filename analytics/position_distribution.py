from __future__ import annotations

from dataclasses import dataclass

from analytics.frequency_analysis import FrequencyRecord
from analytics.position_frequency import PositionFrequencyResult


VALID_DIGITS = tuple(range(10))


@dataclass(frozen=True)
class PositionDistribution:
    """
    Percentage distribution for one historical digit position.

    The distribution contains one percentage value for every
    digit from 0 through 9.
    """

    position: str
    total_observations: int
    percentages: tuple[float, ...]


def build_position_distribution(
    result: PositionFrequencyResult,
) -> PositionDistribution:
    """
    Convert one PositionFrequencyResult into a fixed 0-9
    percentage distribution.

    The returned percentages follow digit order:

        index 0 -> digit 0
        index 1 -> digit 1
        ...
        index 9 -> digit 9

    No frequency is recalculated here.
    """

    if len(result.records) != len(VALID_DIGITS):
        raise ValueError(
            "Position frequency result must contain exactly "
            "10 digit records."
        )

    records_by_digit: dict[int, FrequencyRecord] = {
        record.digit: record
        for record in result.records
    }

    if set(records_by_digit) != set(VALID_DIGITS):
        raise ValueError(
            "Position frequency result must contain exactly "
            "one record for each digit 0-9."
        )

    percentages = tuple(
        records_by_digit[digit].percentage
        for digit in VALID_DIGITS
    )

    return PositionDistribution(
        position=result.position,
        total_observations=result.total_observations,
        percentages=percentages,
    )


def build_position_distribution_matrix(
    results: dict[str, PositionFrequencyResult],
) -> tuple[PositionDistribution, ...]:
    """
    Build a position-by-digit distribution matrix.

    Each PositionDistribution represents one row of the matrix.
    The digit order is always 0 through 9.
    """

    return tuple(
        build_position_distribution(result)
        for result in results.values()
    )


def get_digit_percentage(
    distribution: PositionDistribution,
    digit: int,
) -> float:
    """
    Return the percentage for one digit from a position distribution.
    """

    if not isinstance(digit, int) or isinstance(digit, bool):
        raise ValueError(
            "digit must be an integer between 0 and 9."
        )

    if digit not in VALID_DIGITS:
        raise ValueError(
            "digit must be between 0 and 9."
        )

    return distribution.percentages[digit]
