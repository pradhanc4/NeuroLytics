from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from analytics.frequency_analysis import calculate_frequency
from analytics.statistical_foundation import StatisticalObservation
from features.feature_config import FeatureConfig
from features.point_in_time import HistoricalFeatureObservation


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
class HistoricalFrequencyFeatureRecord:
    """One historical frequency feature."""

    feature_name: str
    value: float | int | None
    feature_type: str
    source: str
    position: str
    digit: int
    window: int


@dataclass(frozen=True)
class HistoricalFrequencyFeatureResult:
    """Historical frequency expansion for one target date."""

    target_date: date
    records: tuple[HistoricalFrequencyFeatureRecord, ...]


def _validate_target_date(target_date: date) -> None:
    if not isinstance(target_date, date):
        raise TypeError(
            "target_date must be a date instance."
        )


def _validate_history(
    history: Iterable[HistoricalFeatureObservation],
) -> tuple[HistoricalFeatureObservation, ...]:
    if history is None:
        raise TypeError(
            "history must be an iterable of "
            "HistoricalFeatureObservation."
        )

    try:
        observations = tuple(history)
    except TypeError as exc:
        raise TypeError(
            "history must be an iterable of "
            "HistoricalFeatureObservation."
        ) from exc

    for observation in observations:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "history must contain only "
                "HistoricalFeatureObservation values."
            )

    return observations


def _validate_config(
    config: FeatureConfig,
) -> None:
    if not isinstance(config, FeatureConfig):
        raise TypeError(
            "config must be a FeatureConfig instance."
        )


def _get_prior_history(
    history: Iterable[HistoricalFeatureObservation],
    target_date: date,
) -> tuple[HistoricalFeatureObservation, ...]:
    """
    Return observations strictly before target_date.

    Target-date and future observations are excluded.
    """

    observations = _validate_history(history)

    prior = [
        observation
        for observation in observations
        if observation.result_date < target_date
    ]

    return tuple(
        sorted(
            prior,
            key=lambda observation: observation.result_date,
        )
    )


def _get_window_history(
    history: tuple[HistoricalFeatureObservation, ...],
    window: int,
) -> tuple[HistoricalFeatureObservation, ...]:
    """
    Select the latest `window` historical observations.

    This is an observation-count window.
    """

    return tuple(history[-window:])


def _build_statistical_observations(
    history: tuple[HistoricalFeatureObservation, ...],
    position: str,
) -> tuple[StatisticalObservation, ...]:
    """
    Adapt historical feature observations to the existing
    Phase 9 statistical frequency engine.
    """

    position_index = POSITIONS.index(position)

    return tuple(
        StatisticalObservation(
            record_date=observation.result_date,
            column_name=position,
            value=observation.positions[position_index],
        )
        for observation in history
    )


def _extract_frequency_values(
    frequency_result,
) -> tuple[tuple[int, int, float], ...]:
    """
    Extract digit, count, and percentage from the existing
    frequency-analysis result.
    """

    records = []

    for record in frequency_result.records:
        records.append(
            (
                record.digit,
                record.count,
                record.percentage,
            )
        )

    return tuple(records)


def build_historical_frequency_features(
    history: Iterable[HistoricalFeatureObservation],
    target_date: date,
    config: FeatureConfig,
) -> HistoricalFrequencyFeatureResult:
    """
    Build multi-window historical frequency features.

    Point-in-time rule:

        observation.result_date < target_date

    Only historical observations strictly before the target
    date are used.

    The configured observation-count windows select the latest
    historical observations available before the target date.

    The existing Phase 9 frequency engine performs the actual
    digit-frequency calculation.
    """

    _validate_target_date(target_date)
    _validate_config(config)

    observations = _get_prior_history(
        history,
        target_date,
    )

    # Use the Phase 14 configuration field directly.
    # This preserves compatibility with the current FeatureConfig
    # implementation without changing existing Phase 13 contracts.
    windows = config.frequency_windows

    records: list[
        HistoricalFrequencyFeatureRecord
    ] = []

    for window in windows:
        window_history = _get_window_history(
            observations,
            window,
        )

        for position in config.positions:
            statistical_observations = (
                _build_statistical_observations(
                    window_history,
                    position,
                )
            )

            frequency_result = calculate_frequency(
                statistical_observations,
                position,
            )

            frequency_values = _extract_frequency_values(
                frequency_result
            )

            for digit, count, percentage in frequency_values:
                records.append(
                    HistoricalFrequencyFeatureRecord(
                        feature_name=(
                            f"{position}_frequency_count_"
                            f"{window}_{digit}"
                        ),
                        value=count,
                        feature_type="historical_frequency",
                        source="analytics.frequency_analysis",
                        position=position,
                        digit=digit,
                        window=window,
                    )
                )

                records.append(
                    HistoricalFrequencyFeatureRecord(
                        feature_name=(
                            f"{position}_frequency_percentage_"
                            f"{window}_{digit}"
                        ),
                        value=percentage,
                        feature_type="historical_frequency",
                        source="analytics.frequency_analysis",
                        position=position,
                        digit=digit,
                        window=window,
                    )
                )

    return HistoricalFrequencyFeatureResult(
        target_date=target_date,
        records=tuple(records),
    )


def get_historical_frequency_feature_value(
    result: HistoricalFrequencyFeatureResult,
    feature_name: str,
) -> float | int | None:
    """Return one historical frequency feature value."""

    if not isinstance(
        result,
        HistoricalFrequencyFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "HistoricalFrequencyFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        "Historical frequency feature not found: "
        f"{feature_name}"
    )


def get_historical_frequency_feature_names(
    result: HistoricalFrequencyFeatureResult,
) -> tuple[str, ...]:
    """Return all historical frequency feature names."""

    if not isinstance(
        result,
        HistoricalFrequencyFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "HistoricalFrequencyFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_historical_frequency_feature_values(
    result: HistoricalFrequencyFeatureResult,
) -> dict[str, float | int | None]:
    """Return historical frequency features as a mapping."""

    if not isinstance(
        result,
        HistoricalFrequencyFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "HistoricalFrequencyFeatureResult instance."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }