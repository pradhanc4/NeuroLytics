from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import sqrt
from typing import Iterable

from features.feature_config import FeatureConfig
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)


@dataclass(frozen=True)
class HistoricalIntervalFeatureRecord:
    """One historical interval feature."""

    feature_name: str
    value: float | None
    feature_type: str
    source: str


@dataclass(frozen=True)
class HistoricalIntervalFeatureResult:
    """Point-in-time historical interval feature result."""

    target_date: date
    records: tuple[HistoricalIntervalFeatureRecord, ...]


FEATURE_NAMES = (
    "historical_interval_days_since_last",
    "historical_interval_days_since_first",
    "historical_interval_span_days",
    "historical_interval_mean_days",
    "historical_interval_min_days",
    "historical_interval_max_days",
    "historical_interval_std_days",
)


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


def _point_in_time_dates(
    history: tuple[HistoricalFeatureObservation, ...],
    target_date: date,
) -> tuple[date, ...]:
    """Return unique historical dates strictly before target_date."""

    dates = sorted(
        {
            observation.result_date
            for observation in history
            if observation.result_date < target_date
        }
    )

    return tuple(dates)


def _calculate_intervals(
    dates: tuple[date, ...],
) -> tuple[float, ...]:
    """Calculate elapsed-day intervals between consecutive dates."""

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


def _build_records(
    dates: tuple[date, ...],
    target_date: date,
) -> tuple[HistoricalIntervalFeatureRecord, ...]:
    records: list[
        HistoricalIntervalFeatureRecord
    ] = []

    if not dates:
        values: dict[str, float | None] = {
            name: None
            for name in FEATURE_NAMES
        }

    else:
        intervals = _calculate_intervals(dates)

        days_since_last = float(
            (target_date - dates[-1]).days
        )

        days_since_first = float(
            (target_date - dates[0]).days
        )

        span_days = float(
            (dates[-1] - dates[0]).days
        )

        values = {
            "historical_interval_days_since_last":
                days_since_last,
            "historical_interval_days_since_first":
                days_since_first,
            "historical_interval_span_days":
                span_days,
            "historical_interval_mean_days":
                _mean(intervals),
            "historical_interval_min_days":
                min(intervals)
                if intervals
                else None,
            "historical_interval_max_days":
                max(intervals)
                if intervals
                else None,
            "historical_interval_std_days":
                _std(intervals),
        }

    for feature_name in FEATURE_NAMES:
        records.append(
            HistoricalIntervalFeatureRecord(
                feature_name=feature_name,
                value=values[feature_name],
                feature_type="historical_interval",
                source="historical_observations",
            )
        )

    return tuple(records)


def build_historical_interval_features(
    target_date: date,
    history: Iterable[HistoricalFeatureObservation],
    config: FeatureConfig,
) -> HistoricalIntervalFeatureResult:
    """
    Build point-in-time historical interval features.

    Only observations strictly before target_date are used.

    These features describe elapsed calendar time and spacing between
    historical observations. They do not perform prediction.
    """

    _validate_target_date(target_date)

    validated_history = _validate_history(
        history
    )

    _validate_config(config)

    if not config.historical_interval_features_enabled:
        return HistoricalIntervalFeatureResult(
            target_date=target_date,
            records=(),
        )

    dates = _point_in_time_dates(
        history=validated_history,
        target_date=target_date,
    )

    records = _build_records(
        dates=dates,
        target_date=target_date,
    )

    return HistoricalIntervalFeatureResult(
        target_date=target_date,
        records=records,
    )


def get_historical_interval_feature_value(
    result: HistoricalIntervalFeatureResult,
    feature_name: str,
) -> float | None:
    """Return one historical interval feature value."""

    if not isinstance(
        result,
        HistoricalIntervalFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "HistoricalIntervalFeatureResult."
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
        f"Historical interval feature not found: "
        f"{feature_name}"
    )


def get_historical_interval_feature_names(
    result: HistoricalIntervalFeatureResult,
) -> tuple[str, ...]:
    """Return all historical interval feature names."""

    if not isinstance(
        result,
        HistoricalIntervalFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "HistoricalIntervalFeatureResult."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_historical_interval_feature_values(
    result: HistoricalIntervalFeatureResult,
) -> dict[str, float | None]:
    """Return historical interval features as a mapping."""

    if not isinstance(
        result,
        HistoricalIntervalFeatureResult,
    ):
        raise TypeError(
            "result must be a "
            "HistoricalIntervalFeatureResult."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }