from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from analytics.frequency_analysis import FrequencyRecord
from analytics.position_frequency import PositionFrequencyResult


@dataclass(frozen=True)
class PositionFrequencySummary:
    """
    Summary statistics for one digit position.

    The summary is derived from an already-calculated
    PositionFrequencyResult and does not recalculate frequencies.
    """

    position: str
    total_observations: int

    most_frequent_digits: tuple[int, ...]
    highest_count: int
    highest_percentage: float

    least_frequent_digits: tuple[int, ...]
    lowest_count: int
    lowest_percentage: float


def _find_records_with_count(
    records: Iterable[FrequencyRecord],
    target_count: int,
) -> tuple[FrequencyRecord, ...]:
    """
    Return all frequency records matching the target count.
    """

    return tuple(
        record
        for record in records
        if record.count == target_count
    )


def summarize_position_frequency(
    result: PositionFrequencyResult,
) -> PositionFrequencySummary:
    """
    Build a summary from one position-frequency result.

    Ties are preserved. If multiple digits share the highest or
    lowest frequency, all tied digits are returned.
    """

    if not result.records:
        raise ValueError(
            "Position frequency result must contain frequency records."
        )

    highest_count = max(
        record.count
        for record in result.records
    )

    lowest_count = min(
        record.count
        for record in result.records
    )

    highest_records = _find_records_with_count(
        result.records,
        highest_count,
    )

    lowest_records = _find_records_with_count(
        result.records,
        lowest_count,
    )

    return PositionFrequencySummary(
        position=result.position,
        total_observations=result.total_observations,
        most_frequent_digits=tuple(
            record.digit
            for record in highest_records
        ),
        highest_count=highest_count,
        highest_percentage=highest_records[0].percentage,
        least_frequent_digits=tuple(
            record.digit
            for record in lowest_records
        ),
        lowest_count=lowest_count,
        lowest_percentage=lowest_records[0].percentage,
    )


def summarize_all_position_frequencies(
    results: dict[str, PositionFrequencyResult],
) -> dict[str, PositionFrequencySummary]:
    """
    Build frequency summaries for all supplied positions.

    The input results are assumed to have already been validated and
    calculated by the position-frequency analysis layer.
    """

    return {
        position: summarize_position_frequency(result)
        for position, result in results.items()
    }