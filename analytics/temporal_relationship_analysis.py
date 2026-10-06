from __future__ import annotations

from datetime import date
from typing import Iterable


C12_TEMPORAL_VERSION = "C.12.0"


def day_gap(previous: date, current: date) -> int:
    if current <= previous:
        raise ValueError("current date must be after previous date")
    return (current - previous).days


def rolling_frequency(values: Iterable[int], window: int) -> dict[int, float]:
    if window <= 0:
        raise ValueError("window must be positive")
    data = [int(v) for v in values]
    data = data[-window:]
    total = len(data)
    return {digit: round(data.count(digit) / total, 8) if total else 0.0 for digit in range(10)}


__all__ = ["C12_TEMPORAL_VERSION", "day_gap", "rolling_frequency"]
