from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from math import sqrt
from typing import Iterable

from features.feature_config import (
    FeatureConfig,
    get_observation_density_windows,
)
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)


@dataclass(frozen=True)
class ObservationDensityFeatureRecord:
    """One observation density feature."""

    feature_name: str
    value: float | None
    feature_type: str
    source: str


@dataclass(frozen=True)
class ObservationDensityFeatureResult:
    """Point-in-time observation density feature result."""

    target_date: date
    records: tuple[ObservationDensityFeatureRecord, ...]


def _validate_target_date(
    target_date: date,
) -> None:
    if not isinstance(target_date, date):
        raise TypeError(
            "target_date must be a date."
        )


def _validate_history(
    history: Iterable[HistoricalFeatureObservation],
) -> tuple[HistoricalFeatureObservation, ...]:
    if isinstance(history, (str, bytes)):
        raise TypeError(
            "history must be an iterable of "
            "HistoricalFeatureObservation."
        )

    validated = []

    for observation in history:
        if not isinstance(
            observation,
            HistoricalFeatureObservation,
        ):
            raise TypeError(
                "history must contain "
                "HistoricalFeatureObservation objects."
            )

        validated.append(observation)

    return tuple(validated)


def _validate_config(
    config: FeatureConfig,
) -> None:
    if not isinstance(
        config,
        FeatureConfig,
    ):
        raise TypeError(
            "config must be a FeatureConfig instance."
        )


def _historical_dates(
    history: tuple[HistoricalFeatureObservation, ...],
    target_date: date,
) -> tuple[date, ...]:
    """
    Return unique historical observation dates
    strictly before target_date.
    """

    return tuple(
        sorted(
            {
                observation.result_date
                for observation in history
                if observation.result_date < target_date
            }
        )
    )


def _window_start(
    target_date: date,
    window_days: int,
) -> date:
    return target_date - timedelta(
        days=window_days
    )


def _dates_in_window(
    dates: tuple[date, ...],
    target_date: date,
    window_days: int,
) -> tuple[date, ...]:
    start_date = _window_start(
        target_date,
        window_days,
    )

    return tuple(
        observation_date
        for observation_date in dates
        if start_date <= observation_date < target_date
    )


def _observation_rate(
    observation_count: int,
    window_days: int,
) -> float:
    return observation_count / float(window_days)


def _calculate_intervals(
    dates: tuple[date, ...],
) -> tuple[float, ...]:
    if len(dates) < 2:
        return ()

    return tuple(
        float(
            (current_date - previous_date).days
        )
        for previous_date, current_date in zip(
            dates,
            dates[1:],
        )
    )


def _mean(
    values: tuple[float, ...],
) -> float | None:
    if not values:
        return None

    return sum(values) / len(values)


def _std(
    values: tuple[float, ...],
) -> float | None:
    if not values:
        return None

    mean = _mean(values)

    if mean is None:
        return None

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / len(values)

    return sqrt(variance)


def _build_window_records(
    dates: tuple[date, ...],
    target_date: date,
    windows: tuple[int, ...],
) -> tuple[ObservationDensityFeatureRecord, ...]:
    records: list[
        ObservationDensityFeatureRecord
    ] = []

    for window_days in windows:
        window_dates = _dates_in_window(
            dates=dates,
            target_date=target_date,
            window_days=window_days,
        )

        observation_count = len(
            window_dates
        )

        records.append(
            ObservationDensityFeatureRecord(
                feature_name=(
                    "observation_density_count_"
                    f"{window_days}"
                ),
                value=float(
                    observation_count
                ),
                feature_type="observation_density",
                source="historical_observations",
            )
        )

        records.append(
            ObservationDensityFeatureRecord(
                feature_name=(
                    "observation_density_rate_"
                    f"{window_days}"
                ),
                value=_observation_rate(
                    observation_count,
                    window_days,
                ),
                feature_type="observation_density",
                source="historical_observations",
            )
        )

    return tuple(records)


def _build_overall_records(
    dates: tuple[date, ...],
) -> tuple[ObservationDensityFeatureRecord, ...]:
    if not dates:
        values: dict[str, float | None] = {
            "observation_density_total_count": None,
            "observation_density_span_days": None,
            "observation_density_rate": None,
            "observation_density_average_interval": None,
            "observation_density_interval_std": None,
        }

    else:
        intervals = _calculate_intervals(
            dates
        )

        span_days = float(
            (dates[-1] - dates[0]).days
        )

        if span_days > 0:
            density_rate = (
                len(dates) / span_days
            )
        else:
            density_rate = None

        values = {
            "observation_density_total_count":
                float(len(dates)),
            "observation_density_span_days":
                span_days,
            "observation_density_rate":
                density_rate,
            "observation_density_average_interval":
                _mean(intervals),
            "observation_density_interval_std":
                _std(intervals),
        }

    return tuple(
        ObservationDensityFeatureRecord(
            feature_name=feature_name,
            value=values[feature_name],
            feature_type="observation_density",
            source="historical_observations",
        )
        for feature_name in (
            "observation_density_total_count",
            "observation_density_span_days",
            "observation_density_rate",
            "observation_density_average_interval",
            "observation_density_interval_std",
        )
    )


def build_observation_density_features(
    target_date: date,
    history: Iterable[HistoricalFeatureObservation],
    config: FeatureConfig,
) -> ObservationDensityFeatureResult:
    """
    Build point-in-time observation density features.

    Only observations strictly before target_date are used.
    Duplicate calendar dates are treated as one observation date.
    """

    _validate_target_date(target_date)

    validated_history = _validate_history(
        history
    )

    _validate_config(config)

    if not config.observation_density_features_enabled:
        return ObservationDensityFeatureResult(
            target_date=target_date,
            records=(),
        )

    dates = _historical_dates(
        history=validated_history,
        target_date=target_date,
    )

    windows = get_observation_density_windows(
        config
    )

    window_records = _build_window_records(
        dates=dates,
        target_date=target_date,
        windows=windows,
    )

    overall_records = _build_overall_records(
        dates
    )

    return ObservationDensityFeatureResult(
        target_date=target_date,
        records=(
            *window_records,
            *overall_records,
        ),
    )


def get_observation_density_feature_value(
    result: ObservationDensityFeatureResult,
    feature_name: str,
) -> float | None:
    """Return one observation density feature value."""

    if not isinstance(
        result,
        ObservationDensityFeatureResult,
    ):
        raise TypeError(
            "result must be an "
            "ObservationDensityFeatureResult."
        )

    if not isinstance(
        feature_name,
        str,
    ):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        "Observation density feature not found: "
        f"{feature_name}"
    )


def get_observation_density_feature_names(
    result: ObservationDensityFeatureResult,
) -> tuple[str, ...]:
    """Return all observation density feature names."""

    if not isinstance(
        result,
        ObservationDensityFeatureResult,
    ):
        raise TypeError(
            "result must be an "
            "ObservationDensityFeatureResult."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_observation_density_feature_values(
    result: ObservationDensityFeatureResult,
) -> dict[str, float | None]:
    """Return observation density features as a mapping."""

    if not isinstance(
        result,
        ObservationDensityFeatureResult,
    ):
        raise TypeError(
            "result must be an "
            "ObservationDensityFeatureResult."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }