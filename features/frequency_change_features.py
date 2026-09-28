from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from analytics.frequency_analysis import calculate_frequency
from analytics.statistical_foundation import StatisticalObservation
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
class FrequencyChangeFeatureRecord:
    feature_name: str
    value: float
    feature_type: str
    position: str
    comparison_index: int
    older_window: int
    recent_window: int
    digit: int
    source: str


@dataclass(frozen=True)
class FrequencyChangeFeatureResult:
    target_date: date
    records: tuple[FrequencyChangeFeatureRecord, ...]


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


def _frequency_percentages(
    observations: Iterable[HistoricalFeatureObservation],
    position: str,
    window: int,
) -> dict[int, float]:
    window_observations = tuple(observations)[-window:]

    statistical_observations = _build_statistical_observations(
        window_observations,
        position,
    )

    frequency_result = calculate_frequency(
        statistical_observations,
        position,
    )

    return {
        record.digit: float(record.percentage)
        for record in frequency_result.records
    }


def _feature_name(
    position: str,
    comparison_index: int,
    older_window: int,
    recent_window: int,
    digit: int,
) -> str:
    return (
        f"{position}_frequency_change_"
        f"{comparison_index}_"
        f"{older_window}_"
        f"{recent_window}_"
        f"{digit}"
    )


def _build_comparison_records(
    observations: tuple[HistoricalFeatureObservation, ...],
    position: str,
    comparison_index: int,
    older_window: int,
    recent_window: int,
) -> tuple[FrequencyChangeFeatureRecord, ...]:
    older_percentages = _frequency_percentages(
        observations,
        position,
        older_window,
    )

    recent_percentages = _frequency_percentages(
        observations,
        position,
        recent_window,
    )

    records = []

    for digit in DIGITS:
        older_value = older_percentages.get(
            digit,
            0.0,
        )

        recent_value = recent_percentages.get(
            digit,
            0.0,
        )

        change = older_value - recent_value

        records.append(
            FrequencyChangeFeatureRecord(
                feature_name=_feature_name(
                    position,
                    comparison_index,
                    older_window,
                    recent_window,
                    digit,
                ),
                value=change,
                feature_type="frequency_change",
                position=position,
                comparison_index=comparison_index,
                older_window=older_window,
                recent_window=recent_window,
                digit=digit,
                source="analytics.frequency_analysis",
            )
        )

    return tuple(records)


def build_frequency_change_features(
    history: Iterable[HistoricalFeatureObservation],
    target_date: date,
    config: FeatureConfig,
) -> FrequencyChangeFeatureResult:
    """
    Build point-in-time frequency-change features.

    For each configured position and comparison pair:

        change = older percentage - recent percentage

    Each comparison window is an independent trailing
    observation-count window.

    The target date itself is excluded.

    Future observations are excluded.

    Windows are observation-count windows rather than
    calendar-day windows.
    """

    _validate_target_date(target_date)
    _validate_config(config)

    observations = _get_prior_history(
        history,
        target_date,
    )

    comparison_windows = tuple(
        config.frequency_comparison_windows
    )

    records = []

    for position in config.positions:
        for comparison_index, (
            older_window,
            recent_window,
        ) in enumerate(
            comparison_windows,
            start=1,
        ):
            records.extend(
                _build_comparison_records(
                    observations,
                    position,
                    comparison_index,
                    older_window,
                    recent_window,
                )
            )

    return FrequencyChangeFeatureResult(
        target_date=target_date,
        records=tuple(records),
    )


def get_frequency_change_feature_value(
    result: FrequencyChangeFeatureResult,
    feature_name: str,
) -> float:
    if not isinstance(
        result,
        FrequencyChangeFeatureResult,
    ):
        raise TypeError(
            "result must be a FrequencyChangeFeatureResult."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Frequency change feature not found: {feature_name}"
    )


def get_frequency_change_feature_names(
    result: FrequencyChangeFeatureResult,
) -> tuple[str, ...]:
    if not isinstance(
        result,
        FrequencyChangeFeatureResult,
    ):
        raise TypeError(
            "result must be a FrequencyChangeFeatureResult."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_frequency_change_feature_values(
    result: FrequencyChangeFeatureResult,
) -> dict[str, float]:
    if not isinstance(
        result,
        FrequencyChangeFeatureResult,
    ):
        raise TypeError(
            "result must be a FrequencyChangeFeatureResult."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }