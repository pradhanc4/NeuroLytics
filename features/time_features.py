from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TimeFeatureRecord:
    feature_name: str
    value: int | float | str
    feature_type: str
    source: str


@dataclass(frozen=True)
class TimeFeatureResult:
    target_date: date
    records: tuple[TimeFeatureRecord, ...]


def _validate_target_date(target_date: date) -> None:
    if not isinstance(target_date, date):
        raise TypeError(
            "target_date must be a datetime.date instance."
        )


def _build_feature_name(name: str) -> str:
    return f"time_{name}"


def _cyclical_value(
    value: int,
    period: int,
) -> tuple[float, float]:
    """Return sine and cosine representations of a cyclic value."""

    angle = (2.0 * math.pi * value) / period

    return (
        math.sin(angle),
        math.cos(angle),
    )


def _build_cyclical_records(
    target_date: date,
) -> tuple[TimeFeatureRecord, ...]:
    """Build cyclical calendar representations."""

    day_of_week = target_date.weekday()

    # Day of week:
    # Monday=0 ... Sunday=6.
    # The seven positions form one complete weekly cycle.
    day_of_week_sin, day_of_week_cos = _cyclical_value(
        day_of_week,
        7,
    )

    # Day of month:
    # Use the actual number of days in the target month so that
    # February, 30-day months, and 31-day months are represented
    # according to their real calendar cycle.
    days_in_month = calendar.monthrange(
        target_date.year,
        target_date.month,
    )[1]

    day_of_month_sin, day_of_month_cos = _cyclical_value(
        target_date.day - 1,
        days_in_month,
    )

    # Day of year:
    # Use the actual number of days in the target year.
    days_in_year = (
        366
        if calendar.isleap(target_date.year)
        else 365
    )

    day_of_year = target_date.timetuple().tm_yday

    day_of_year_sin, day_of_year_cos = _cyclical_value(
        day_of_year - 1,
        days_in_year,
    )

    # ISO week of year.
    iso_week = target_date.isocalendar().week

    # ISO years can contain week 53.
    # Use 53 as the stable maximum ISO-week cycle.
    week_of_year_sin, week_of_year_cos = _cyclical_value(
        iso_week - 1,
        53,
    )

    # Month:
    # January=1 ... December=12.
    month_sin, month_cos = _cyclical_value(
        target_date.month - 1,
        12,
    )

    # Quarter:
    # Q1=1 ... Q4=4.
    quarter = ((target_date.month - 1) // 3) + 1

    quarter_sin, quarter_cos = _cyclical_value(
        quarter - 1,
        4,
    )

    return (
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "day_of_week_sin"
            ),
            value=day_of_week_sin,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "day_of_week_cos"
            ),
            value=day_of_week_cos,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "day_of_month_sin"
            ),
            value=day_of_month_sin,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "day_of_month_cos"
            ),
            value=day_of_month_cos,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "day_of_year_sin"
            ),
            value=day_of_year_sin,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "day_of_year_cos"
            ),
            value=day_of_year_cos,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "week_of_year_sin"
            ),
            value=week_of_year_sin,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "week_of_year_cos"
            ),
            value=week_of_year_cos,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "month_sin"
            ),
            value=month_sin,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "month_cos"
            ),
            value=month_cos,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "quarter_sin"
            ),
            value=quarter_sin,
            feature_type="cyclical_time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "quarter_cos"
            ),
            value=quarter_cos,
            feature_type="cyclical_time",
            source="target_date",
        ),
    )


def build_time_features(
    target_date: date,
) -> TimeFeatureResult:
    """
    Build deterministic calendar and cyclical time features.

    These features depend only on the target date and do not inspect
    historical observations.
    """

    _validate_target_date(target_date)

    iso_calendar = target_date.isocalendar()

    calendar_records = (
        TimeFeatureRecord(
            feature_name=_build_feature_name("day_of_week"),
            value=target_date.strftime("%A"),
            feature_type="time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name(
                "day_of_week_number"
            ),
            value=target_date.weekday(),
            feature_type="time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name("day_of_month"),
            value=target_date.day,
            feature_type="time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name("day_of_year"),
            value=target_date.timetuple().tm_yday,
            feature_type="time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name("week_of_year"),
            value=iso_calendar.week,
            feature_type="time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name("month"),
            value=target_date.month,
            feature_type="time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name("month_name"),
            value=calendar.month_name[target_date.month],
            feature_type="time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name("quarter"),
            value=((target_date.month - 1) // 3) + 1,
            feature_type="time",
            source="target_date",
        ),
        TimeFeatureRecord(
            feature_name=_build_feature_name("year"),
            value=target_date.year,
            feature_type="time",
            source="target_date",
        ),
    )

    cyclical_records = _build_cyclical_records(
        target_date
    )

    return TimeFeatureResult(
        target_date=target_date,
        records=calendar_records + cyclical_records,
    )


def get_time_feature_value(
    result: TimeFeatureResult,
    feature_name: str,
) -> int | float | str:
    """Return one time feature value."""

    if not isinstance(result, TimeFeatureResult):
        raise TypeError(
            "result must be a TimeFeatureResult instance."
        )

    if not isinstance(feature_name, str):
        raise TypeError(
            "feature_name must be a string."
        )

    for record in result.records:
        if record.feature_name == feature_name:
            return record.value

    raise ValueError(
        f"Time feature not found: {feature_name}"
    )


def get_time_feature_names(
    result: TimeFeatureResult,
) -> tuple[str, ...]:
    """Return all time feature names."""

    if not isinstance(result, TimeFeatureResult):
        raise TypeError(
            "result must be a TimeFeatureResult instance."
        )

    return tuple(
        record.feature_name
        for record in result.records
    )


def get_time_feature_values(
    result: TimeFeatureResult,
) -> dict[str, int | float | str]:
    """Return time features as a name/value mapping."""

    if not isinstance(result, TimeFeatureResult):
        raise TypeError(
            "result must be a TimeFeatureResult instance."
        )

    return {
        record.feature_name: record.value
        for record in result.records
    }