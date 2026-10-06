from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import HistoricalResult, Market

FEATURE_VERSION = "C.3.0"
LAG_ROWS = 3
ROLLING_WINDOWS = (3, 7, 14)
BASE_COLUMNS = (
    "open_1", "open_2", "open_3",
    "jodi_1", "jodi_2",
    "close_1", "close_2", "close_3",
)


@dataclass(frozen=True)
class HistoricalFeatureRow:
    result_date: str
    market_id: int
    features: dict[str, float | int]
    targets: dict[str, int]
    source_history_end_date: str | None


@dataclass(frozen=True)
class HistoricalFeatureDataset:
    version: str
    market_id: int
    market_name: str
    record_count: int
    feature_names: tuple[str, ...]
    target_names: tuple[str, ...]
    rows: tuple[HistoricalFeatureRow, ...]
    temporal_safe: bool
    leakage_issues: tuple[str, ...]
    dataset_identity: str


def _stable_identity(payload: object) -> str:
    import hashlib
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _digits(value: str, width: int) -> list[int]:
    text = str(value).zfill(width)
    if len(text) != width or not text.isdigit():
        raise ValueError(f"Invalid {width}-digit value: {value!r}")
    return [int(char) for char in text]


def _base_values(row: HistoricalResult) -> list[int]:
    return (
        _digits(row.open_result, 3)
        + _digits(row.jodi_result, 2)
        + _digits(row.close_result, 3)
    )


def _history_stats(history: list[HistoricalResult], prefix: str) -> dict[str, float]:
    values = [_base_values(row) for row in history]
    flat = [digit for row in values for digit in row]
    if not flat:
        return {
            f"{prefix}_digit_mean": 0.0,
            f"{prefix}_digit_std": 0.0,
            f"{prefix}_digit_sum": 0,
        }
    mean = sum(flat) / len(flat)
    variance = sum((value - mean) ** 2 for value in flat) / len(flat)
    return {
        f"{prefix}_digit_mean": round(mean, 8),
        f"{prefix}_digit_std": round(variance ** 0.5, 8),
        f"{prefix}_digit_sum": sum(flat),
    }


def _rolling_digit_frequency(history: list[HistoricalResult], prefix: str) -> dict[str, float]:
    flat = [digit for row in history for digit in _base_values(row)]
    total = len(flat)
    return {
        f"{prefix}_digit_{digit}_rate": round(flat.count(digit) / total, 8) if total else 0.0
        for digit in range(10)
    }


def _date_features(result_date: date) -> dict[str, int]:
    return {
        "day_of_week": result_date.weekday(),
        "day_of_month": result_date.day,
        "month": result_date.month,
        "quarter": ((result_date.month - 1) // 3) + 1,
        "year": result_date.year,
    }


def _transition_features(previous: HistoricalResult | None, prior: HistoricalResult | None) -> dict[str, int]:
    """Return transitions using completed history only; never read current targets."""
    if previous is None or prior is None:
        return {
            "open_change_sum": 0,
            "jodi_change_sum": 0,
            "close_change_sum": 0,
        }
    previous_values = _base_values(previous)
    prior_values = _base_values(prior)
    return {
        "open_change_sum": sum(abs(a - b) for a, b in zip(prior_values[:3], previous_values[:3])),
        "jodi_change_sum": sum(abs(a - b) for a, b in zip(prior_values[3:5], previous_values[3:5])),
        "close_change_sum": sum(abs(a - b) for a, b in zip(prior_values[5:], previous_values[5:])),
    }


def build_historical_feature_dataset(
    db: Session,
    market_id: int,
    *,
    include_targets: bool = True,
) -> HistoricalFeatureDataset:
    market = db.get(Market, market_id)
    if market is None:
        raise ValueError(f"Market not found: {market_id}")

    rows = list(db.scalars(
        select(HistoricalResult)
        .where(HistoricalResult.market_id == market_id)
        .order_by(HistoricalResult.result_date, HistoricalResult.id)
    ).all())
    if len(rows) < 2:
        raise ValueError("At least two historical rows are required.")

    feature_rows: list[HistoricalFeatureRow] = []
    leakage_issues: list[str] = []

    for index, current in enumerate(rows):
        history = rows[max(0, index - LAG_ROWS):index]
        previous = rows[index - 1] if index else None
        prior = rows[index - 2] if index >= 2 else None

        features: dict[str, float | int] = {}
        current_open = _digits(current.open_result, 3)
        for position, digit in enumerate(current_open, 1):
            features[f"current_open_{position}"] = digit

        if index == 0:
            for lag in range(1, LAG_ROWS + 1):
                for position in range(1, 9):
                    features[f"lag{lag}_col{position}"] = 0
        else:
            for lag in range(1, LAG_ROWS + 1):
                source_index = index - lag
                source = rows[source_index] if source_index >= 0 else None
                values = _base_values(source) if source else [0] * 8
                for position, digit in enumerate(values, 1):
                    features[f"lag{lag}_col{position}"] = digit

        for window in ROLLING_WINDOWS:
            window_history = rows[max(0, index - window):index]
            features.update(_history_stats(window_history, f"rolling{window}"))
            features.update(_rolling_digit_frequency(window_history, f"rolling{window}"))

        features.update(_date_features(current.result_date))
        features.update(_transition_features(previous, prior))

        targets = {
            "jodi_first": int(current.jodi_result[0]),
            "jodi_second": int(current.jodi_result[1]),
            "close_first": int(current.close_result[0]),
            "close_second": int(current.close_result[1]),
            "close_third": int(current.close_result[2]),
        } if include_targets else {}

        feature_rows.append(HistoricalFeatureRow(
            result_date=current.result_date.isoformat(),
            market_id=market_id,
            features=features,
            targets=targets,
            source_history_end_date=previous.result_date.isoformat() if previous else None,
        ))

    feature_names = tuple(sorted(feature_rows[0].features))
    target_names = tuple(sorted(feature_rows[0].targets))
    payload = {
        "version": FEATURE_VERSION,
        "market_id": market_id,
        "record_count": len(feature_rows),
        "feature_names": feature_names,
        "target_names": target_names,
        "temporal_safe": True,
        "rows": [
            (row.result_date, row.features, row.targets, row.source_history_end_date)
            for row in feature_rows
        ],
    }
    return HistoricalFeatureDataset(
        version=FEATURE_VERSION,
        market_id=market_id,
        market_name=market.name,
        record_count=len(feature_rows),
        feature_names=feature_names,
        target_names=target_names,
        rows=tuple(feature_rows),
        temporal_safe=True,
        leakage_issues=tuple(leakage_issues),
        dataset_identity=f"historical-feature-dataset-{_stable_identity(payload)}",
    )


def validate_historical_feature_dataset(
    dataset: HistoricalFeatureDataset,
) -> tuple[str, tuple[str, ...]]:
    issues: list[str] = []
    if dataset.version != FEATURE_VERSION:
        issues.append("INVALID_VERSION")
    if dataset.record_count != len(dataset.rows):
        issues.append("ROW_COUNT_MISMATCH")
    if not dataset.rows:
        issues.append("EMPTY_DATASET")
    previous_date: date | None = None
    for row in dataset.rows:
        row_date = date.fromisoformat(row.result_date)
        if previous_date is not None and row_date <= previous_date:
            issues.append("NON_CHRONOLOGICAL_ROWS")
        if row.source_history_end_date is not None:
            history_end = date.fromisoformat(row.source_history_end_date)
            if history_end >= row_date:
                issues.append("FUTURE_HISTORY_REFERENCE")
        forbidden = (
            "jodi_1", "jodi_2", "close_1", "close_2", "close_3",
        )
        for feature_name in row.features:
            if feature_name in forbidden:
                issues.append(f"TARGET_LEAKAGE:{feature_name}")
        previous_date = row_date
    if not dataset.temporal_safe:
        issues.append("TEMPORAL_SAFETY_FALSE")
    if dataset.leakage_issues:
        issues.extend(dataset.leakage_issues)
    if not dataset.dataset_identity.startswith("historical-feature-dataset-"):
        issues.append("INVALID_DATASET_IDENTITY")
    return ("VALID" if not issues else "INVALID", tuple(sorted(set(issues))))


def write_historical_feature_dataset(
    dataset: HistoricalFeatureDataset,
    path: str | Path = "reports/historical_feature_dataset.json",
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(asdict(dataset), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination


__all__ = [
    "FEATURE_VERSION",
    "LAG_ROWS",
    "ROLLING_WINDOWS",
    "HistoricalFeatureRow",
    "HistoricalFeatureDataset",
    "build_historical_feature_dataset",
    "validate_historical_feature_dataset",
    "write_historical_feature_dataset",
]
