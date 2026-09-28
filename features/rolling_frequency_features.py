from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from analytics.statistical_foundation import StatisticalObservation
from analytics.frequency_analysis import calculate_frequency
from features.feature_config import FeatureConfig
from features.historical_data_loader import HistoricalFeatureObservation


POSITIONS = (
    "col1",
    "col2",
    "col3",
    "col4",
    "col5",
    "col6",
    "col7",
    "col8",
)

DIGITS = tuple(range(10))


@dataclass(frozen=True)
class RollingFrequencyFeatureRecord:
    feature_name: str
    value: float
    feature_type: str
    position: str
    window: int
    digit: int
    source: str


@dataclass(frozen=True)
class RollingFrequencyFeatureResult:
    target_date: date
    records: tuple[RollingFrequencyFeatureRecord, ...]


def _validate_target_date(target_date: date) -> None:
    if not isinstance(target_date, date):
        raise TypeError("target_date must be a date.")


def _validate_history(
    history: Iterable[HistoricalFeatureObservation],
) -> tuple[HistoricalFeatureObservation, ...]:
    observations = tuple(history)

    for observation in observations:
        if not isinstance(observation, HistoricalFeatureObservation):
            raise TypeError(
                "history must contain HistoricalFeatureObservation values."
            )

    return observations


def _validate_config(config: FeatureConfig) -> None:
    if not isinstance(config, FeatureConfig):
        raise TypeError("config must be a FeatureConfig.")


def _get_prior_history(
    history: Iterable[HistoricalFeatureObservation],
    target_date: date,
) -> tuple[HistoricalFeatureObservation, ...]:
    observations = _validate_history(history)

    prior = [
        observation
        for observation in observations
        if observation.result_date < target_date
    ]

    prior.sort(key=lambda observation: observation.result_date)

    return tuple(prior)


def _build_statistical_observations(
    observations: Iterable[HistoricalFeatureObservation],
    position: str,
) -> tuple[StatisticalObservation, ...]:
    position_index = POSITIONS.index(position)

    return tuple(
        StatisticalObservation(
            record_date=observation.result_date,
            column_name=position,
            value=observation.positions[position_index],
        )
        for observation in observations
    )


def _feature_name(
    position: str,
    window: int,
    digit: int,
) -> str:
    return f"{position}_rolling_frequency_{window}_{digit}"


def _build_window_records(
    observations: tuple[HistoricalFeatureObservation, ...],
    position: str,
    window: int,
) -> tuple[RollingFrequencyFeatureRecord, ...]:
    window_observations = observations[-window:]

    statistical_observations = _build_statistical_observations(
        window_observations,
        position,
    )

    frequency_result = calculate_frequency(
        statistical_observations,
        position,
    )

    records = []

    for frequency_record in frequency_result.records:
        records.append(
            RollingFrequencyFeatureRecord(
                feature_name=_feature_name(
                    position,
                    window,
                    frequency_record.digit,
                ),
                value=float(frequency_record.percentage),
                feature_type="rolling_frequency_percentage",
                position=position,
                window=window,
                digit=frequency_record.digit,
                source="analytics.frequency_analysis",
            )
        )

    return tuple(records)


def build_rolling_frequency_features(
    history: Iterable[HistoricalFeatureObservation],
    target_date: date,
    config: FeatureConfig,
) -> RollingFrequencyFeatureResult:
    """
    Build rolling frequency features for each configured position/window.

    Point-in-time rule:
        observation.result_date < target_date

    Only the most recent configured number of prior observations are used
    for each rolling window.

    The Phase 9 frequency engine remains the source of the actual frequency
    calculation.

    Rolling windows are observation-count windows, not calendar-day windows.
    """

    _validate_target_date(target_date)
    _validate_config(config)

    observations = _get_prior_history(
        history,
        target_date,
    )

    windows = tuple(config.frequency_windows)

    records = []

    for position in config.positions:
        for window in windows:
            records.extend(
                _build_window_records(
                    observations,
                    position,
                    window,
                )
            )

    return RollingFrequencyFeatureResult(
        target_date=target_date,
        records=tuple(records),
    )


def get_rolling_frequency_feature_value(
    result: RollingFrequencyFeatureResult,
    feature_name: str,
) -> float:
    if not isinstance(result, RollingFrequencyFeatureResult):
        raise TypeError(
            "result must be a RollingFrequencyFeatureResult."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Rolling frequency feature not found: {feature_name}"
    )


def get_rolling_frequency_feature_names(
    result: RollingFrequencyFeatureResult,
) -> tuple[str, ...]:
    if not isinstance(result, RollingFrequencyFeatureResult):
        raise TypeError(
            "result must be a RollingFrequencyFeatureResult."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_rolling_frequency_feature_values(
    result: RollingFrequencyFeatureResult,
) -> dict[str, float]:
    if not isinstance(result, RollingFrequencyFeatureResult):
        raise TypeError(
            "result must be a RollingFrequencyFeatureResult."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }