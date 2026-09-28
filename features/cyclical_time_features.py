from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CyclicalTimeFeatureRecord:
    """One cyclical time feature."""

    feature_name: str
    value: float
    feature_type: str
    source: str


@dataclass(frozen=True)
class CyclicalTimeFeatureResult:
    """Complete cyclical time feature result for one target date."""

    target_date: date
    records: tuple[CyclicalTimeFeatureRecord, ...]


def _validate_target_date(target_date: date) -> None:
    if not isinstance(target_date, date):
        raise TypeError("target_date must be a date instance.")


def _sin_cos(value: float, period: float) -> tuple[float, float]:
    angle = 2.0 * math.pi * value / period
    return math.sin(angle), math.cos(angle)


def build_cyclical_time_features(
    target_date: date,
) -> CyclicalTimeFeatureResult:
    """
    Build cyclical calendar features from the target date only.

    No historical observations are used.
    Therefore these features are inherently point-in-time safe.
    """

    _validate_target_date(target_date)

    records: list[CyclicalTimeFeatureRecord] = []

    # Monday=0 ... Sunday=6
    day_of_week = target_date.weekday()
    day_of_week_sin, day_of_week_cos = _sin_cos(
        day_of_week,
        7.0,
    )

    records.extend(
        [
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_day_of_week_sin",
                value=day_of_week_sin,
                feature_type="cyclical_time",
                source="target_date",
            ),
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_day_of_week_cos",
                value=day_of_week_cos,
                feature_type="cyclical_time",
                source="target_date",
            ),
        ]
    )

    # Day of month: 1..31
    day_of_month = target_date.day
    day_of_month_sin, day_of_month_cos = _sin_cos(
        day_of_month - 1,
        31.0,
    )

    records.extend(
        [
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_day_of_month_sin",
                value=day_of_month_sin,
                feature_type="cyclical_time",
                source="target_date",
            ),
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_day_of_month_cos",
                value=day_of_month_cos,
                feature_type="cyclical_time",
                source="target_date",
            ),
        ]
    )

    # ISO week: 1..53
    iso_week = target_date.isocalendar().week
    iso_week_sin, iso_week_cos = _sin_cos(
        iso_week - 1,
        53.0,
    )

    records.extend(
        [
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_week_of_year_sin",
                value=iso_week_sin,
                feature_type="cyclical_time",
                source="target_date",
            ),
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_week_of_year_cos",
                value=iso_week_cos,
                feature_type="cyclical_time",
                source="target_date",
            ),
        ]
    )

    # Month: 1..12
    month = target_date.month
    month_sin, month_cos = _sin_cos(
        month - 1,
        12.0,
    )

    records.extend(
        [
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_month_sin",
                value=month_sin,
                feature_type="cyclical_time",
                source="target_date",
            ),
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_month_cos",
                value=month_cos,
                feature_type="cyclical_time",
                source="target_date",
            ),
        ]
    )

    # Quarter: 1..4
    quarter = ((target_date.month - 1) // 3) + 1
    quarter_sin, quarter_cos = _sin_cos(
        quarter - 1,
        4.0,
    )

    records.extend(
        [
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_quarter_sin",
                value=quarter_sin,
                feature_type="cyclical_time",
                source="target_date",
            ),
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_quarter_cos",
                value=quarter_cos,
                feature_type="cyclical_time",
                source="target_date",
            ),
        ]
    )

    # Day of year: 1..366.
    # Leap/non-leap year is determined from the target date itself.
    days_in_year = 366 if _is_leap_year(target_date.year) else 365
    day_of_year = target_date.timetuple().tm_yday

    day_of_year_sin, day_of_year_cos = _sin_cos(
        day_of_year - 1,
        float(days_in_year),
    )

    records.extend(
        [
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_day_of_year_sin",
                value=day_of_year_sin,
                feature_type="cyclical_time",
                source="target_date",
            ),
            CyclicalTimeFeatureRecord(
                feature_name="cyclical_day_of_year_cos",
                value=day_of_year_cos,
                feature_type="cyclical_time",
                source="target_date",
            ),
        ]
    )

    return CyclicalTimeFeatureResult(
        target_date=target_date,
        records=tuple(records),
    )


def _is_leap_year(year: int) -> bool:
    """Return whether a calendar year is a leap year."""

    return year % 4 == 0 and (
        year % 100 != 0 or year % 400 == 0
    )


def get_cyclical_time_feature_value(
    result: CyclicalTimeFeatureResult,
    feature_name: str,
) -> float:
    """Return one cyclical time feature value."""

    if not isinstance(result, CyclicalTimeFeatureResult):
        raise TypeError(
            "result must be a CyclicalTimeFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Cyclical time feature not found: {feature_name}"
    )


def get_cyclical_time_feature_names(
    result: CyclicalTimeFeatureResult,
) -> tuple[str, ...]:
    """Return all cyclical time feature names."""

    if not isinstance(result, CyclicalTimeFeatureResult):
        raise TypeError(
            "result must be a CyclicalTimeFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_cyclical_time_feature_values(
    result: CyclicalTimeFeatureResult,
) -> dict[str, float]:
    """Return cyclical time features as a name/value mapping."""

    if not isinstance(result, CyclicalTimeFeatureResult):
        raise TypeError(
            "result must be a CyclicalTimeFeatureResult instance."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }