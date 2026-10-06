from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import HistoricalResult, Market
from analytics.family_master import jodi_family_for, panel_family_for_digit

PROFILE_VERSION = "C.2.0"
DIGITS = tuple(range(10))
JODI_FAMILIES = (
    "12 FAMILY", "13 FAMILY", "14 FAMILY", "15 FAMILY",
    "23 FAMILY", "24 FAMILY", "25 FAMILY", "34 FAMILY",
    "35 FAMILY", "45 FAMILY", "HALF RED", "FULL RED",
)


@dataclass(frozen=True)
class HistoricalStatisticalProfile:
    version: str
    market_id: int
    market_name: str
    record_count: int
    first_date: str | None
    last_date: str | None
    missing_calendar_days: int
    column_statistics: dict
    digit_distributions: dict
    relationships: dict
    family_frequencies: dict
    temporal_profile: dict
    profile_identity: str


def _digits(value: object, width: int) -> tuple[int, ...]:
    text = str(value).strip().zfill(width)
    if len(text) != width or not text.isdigit():
        raise ValueError(f"Invalid {width}-digit value: {value!r}")
    return tuple(int(char) for char in text)


def _distribution(values: list[int]) -> dict:
    counts = Counter(values)
    total = len(values)
    return {
        str(digit): {
            "count": counts.get(digit, 0),
            "percentage": round((counts.get(digit, 0) / total) * 100, 6) if total else 0.0,
        }
        for digit in DIGITS
    }


def _entropy(values: list[int]) -> float:
    total = len(values)
    if not total:
        return 0.0
    counts = Counter(values)
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values()),
        8,
    )


def _summary(values: list[int]) -> dict:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "entropy_bits": 0.0}
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = float(ordered[middle]) if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": round(sum(values) / len(values), 8),
        "median": median,
        "entropy_bits": _entropy(values),
    }


def _conditional_table(pairs: list[tuple[int, int]]) -> dict:
    counts = [[0 for _ in DIGITS] for _ in DIGITS]
    totals = [0 for _ in DIGITS]
    for left, right in pairs:
        counts[left][right] += 1
        totals[left] += 1
    return {
        str(left): {
            str(right): round(counts[left][right] / totals[left], 8) if totals[left] else 0.0
            for right in DIGITS
        }
        for left in DIGITS
    }


def _stable_identity(payload: dict) -> str:
    import hashlib
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_historical_statistical_profile(
    db: Session,
    market_id: int,
) -> HistoricalStatisticalProfile:
    market = db.get(Market, market_id)
    if market is None:
        raise ValueError(f"Market not found: {market_id}")

    rows = db.scalars(
        select(HistoricalResult)
        .where(HistoricalResult.market_id == market_id)
        .order_by(HistoricalResult.result_date, HistoricalResult.id)
    ).all()

    if not rows:
        raise ValueError("No historical results available for the requested market.")

    dates = [row.result_date for row in rows]
    opens = [_digits(row.open_result, 3) for row in rows]
    jodis = [_digits(row.jodi_result, 2) for row in rows]
    closes = [_digits(row.close_result, 3) for row in rows]

    position_values = {f"col{i + 1}": [] for i in range(8)}
    for index, row in enumerate(rows):
        values = opens[index] + jodis[index] + closes[index]
        for position, digit in enumerate(values):
            position_values[f"col{position + 1}"].append(digit)

    all_digits = {name: values for name, values in position_values.items()}
    jodi_first = [value[0] for value in jodis]
    jodi_second = [value[1] for value in jodis]

    month_counts = Counter(row.result_date.strftime("%Y-%m") for row in rows)
    year_counts = Counter(str(row.result_date.year) for row in rows)

    gaps = sum(
        max(0, (later - earlier).days - 1)
        for earlier, later in zip(dates, dates[1:])
    )

    relationships = {
        "open_to_jodi_first": _conditional_table([
            (open_value[0], jodi_value[0]) for open_value, jodi_value in zip(opens, jodis)
        ]),
        "open_to_jodi_second": _conditional_table([
            (open_value[0], jodi_value[1]) for open_value, jodi_value in zip(opens, jodis)
        ]),
        "jodi_first_to_jodi_second": _conditional_table(list(zip(jodi_first, jodi_second))),
        "jodi_first_to_close_first": _conditional_table([
            (jodi_value[0], close_value[0]) for jodi_value, close_value in zip(jodis, closes)
        ]),
        "jodi_second_to_close_first": _conditional_table([
            (jodi_value[1], close_value[0]) for jodi_value, close_value in zip(jodis, closes)
        ]),
    }

    jodi_family_counts = Counter(jodi_family_for(f"{a}{b}") for a, b in jodis)
    first_panel_family_counts = Counter(panel_family_for_digit(str(a)) for a in jodi_first)
    second_panel_family_counts = Counter(panel_family_for_digit(str(b)) for b in jodi_second)

    column_statistics = {name: _summary(values) for name, values in all_digits.items()}
    digit_distributions = {name: _distribution(values) for name, values in all_digits.items()}

    identity_payload = {
        "version": PROFILE_VERSION,
        "market_id": market_id,
        "record_count": len(rows),
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
        "column_statistics": column_statistics,
        "digit_distributions": digit_distributions,
        "relationships": relationships,
        "family_frequencies": {
            "jodi": dict(sorted(jodi_family_counts.items())),
            "first_panel_digit_family": dict(sorted(first_panel_family_counts.items())),
            "second_panel_digit_family": dict(sorted(second_panel_family_counts.items())),
        },
        "temporal_profile": {
            "monthly_record_counts": dict(sorted(month_counts.items())),
            "yearly_record_counts": dict(sorted(year_counts.items())),
            "missing_calendar_days_between_records": gaps,
        },
    }

    return HistoricalStatisticalProfile(
        version=PROFILE_VERSION,
        market_id=market_id,
        market_name=market.name,
        record_count=len(rows),
        first_date=dates[0].isoformat(),
        last_date=dates[-1].isoformat(),
        missing_calendar_days=gaps,
        column_statistics=column_statistics,
        digit_distributions=digit_distributions,
        relationships=relationships,
        family_frequencies=identity_payload["family_frequencies"],
        temporal_profile=identity_payload["temporal_profile"],
        profile_identity=f"historical-statistical-profile-{_stable_identity(identity_payload)}",
    )


def write_historical_statistical_profile(
    profile: HistoricalStatisticalProfile,
    path: str | Path = "reports/historical_statistical_profile.json",
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(asdict(profile), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination


__all__ = [
    "PROFILE_VERSION",
    "HistoricalStatisticalProfile",
    "build_historical_statistical_profile",
    "write_historical_statistical_profile",
]
