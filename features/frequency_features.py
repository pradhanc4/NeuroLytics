from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from analytics.frequency_analysis import calculate_frequency
from analytics.statistical_foundation import StatisticalObservation
from features.feature_config import FeatureConfig, validate_feature_config
from features.point_in_time import (
    PointInTimeHistory,
    get_point_in_time_observations,
)


DIGITS = tuple(range(10))


@dataclass(frozen=True)
class FrequencyFeatureRecord:
    """One digit-frequency feature for one position."""

    position: str
    digit: int
    feature_name: str
    count: int
    percentage: float


@dataclass(frozen=True)
class FrequencyFeatureResult:
    """Complete frequency-feature output for one target date."""

    target_date: date
    window: int
    records: tuple[FrequencyFeatureRecord, ...]


def _build_feature_name(
    position: str,
    digit: int,
    statistic: str,
) -> str:
    """Build a deterministic frequency feature name."""

    return f"{position}_digit_{digit}_frequency_{statistic}"


def _get_window_observations(
    history: PointInTimeHistory,
    window: int,
):
    """Return the most recent point-in-time observations."""

    observations = get_point_in_time_observations(history)

    if not observations:
        return ()

    return observations[-window:]


def _build_statistical_observations(
    observations,
    position: str,
) -> tuple[StatisticalObservation, ...]:
    """
    Adapt point-in-time observations to the existing
    statistical frequency-analysis interface.
    """

    position_index = (
        int(position.replace("col", "")) - 1
    )

    return tuple(
        StatisticalObservation(
            record_date=observation.result_date,
            column_name=position,
            value=observation.positions[position_index],
        )
        for observation in observations
    )


def build_frequency_features(
    history: PointInTimeHistory,
    config: FeatureConfig,
) -> FrequencyFeatureResult:
    """
    Build leakage-safe digit-frequency features.

    Existing frequency-analysis logic is reused. Point-in-time
    observations are adapted to the existing statistical-analysis
    interface before frequency calculation.
    """

    if not isinstance(
        history,
        PointInTimeHistory,
    ):
        raise TypeError(
            "history must be a PointInTimeHistory instance."
        )

    validate_feature_config(config)

    window = config.frequency_window

    observations = _get_window_observations(
        history,
        window,
    )

    records: list[FrequencyFeatureRecord] = []

    for position in config.positions:
        statistical_observations = (
            _build_statistical_observations(
                observations,
                position,
            )
        )

        frequency_result = calculate_frequency(
            statistical_observations,
            position,
        )

        for frequency_record in frequency_result.records:
            records.append(
                FrequencyFeatureRecord(
                    position=position,
                    digit=frequency_record.digit,
                    feature_name=_build_feature_name(
                        position,
                        frequency_record.digit,
                        "count",
                    ),
                    count=frequency_record.count,
                    percentage=frequency_record.percentage,
                )
            )

            records.append(
                FrequencyFeatureRecord(
                    position=position,
                    digit=frequency_record.digit,
                    feature_name=_build_feature_name(
                        position,
                        frequency_record.digit,
                        "percentage",
                    ),
                    count=frequency_record.count,
                    percentage=frequency_record.percentage,
                )
            )

    return FrequencyFeatureResult(
        target_date=history.target_date,
        window=window,
        records=tuple(records),
    )


def get_frequency_feature_count(
    result: FrequencyFeatureResult,
    feature_name: str,
) -> int:
    """Return the count represented by a frequency feature."""

    if not isinstance(
        result,
        FrequencyFeatureResult,
    ):
        raise TypeError(
            "result must be a FrequencyFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.count

    raise ValueError(
        f"Frequency feature not found: {feature_name}"
    )


def get_frequency_feature_percentage(
    result: FrequencyFeatureResult,
    feature_name: str,
) -> float:
    """Return the percentage represented by a frequency feature."""

    if not isinstance(
        result,
        FrequencyFeatureResult,
    ):
        raise TypeError(
            "result must be a FrequencyFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.percentage

    raise ValueError(
        f"Frequency feature not found: {feature_name}"
    )


def get_frequency_feature_names(
    result: FrequencyFeatureResult,
) -> tuple[str, ...]:
    """Return all generated frequency feature names."""

    if not isinstance(
        result,
        FrequencyFeatureResult,
    ):
        raise TypeError(
            "result must be a FrequencyFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )