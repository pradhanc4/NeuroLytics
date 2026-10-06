from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from analytics.historical_feature_dataset import HistoricalFeatureDataset

BACKTEST_VERSION = "C.5.0"
VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class TemporalWindow:
    fold: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    train_count: int
    validation_count: int
    test_count: int


@dataclass(frozen=True)
class TemporalDatasetSplit:
    version: str
    dataset_identity: str
    train_count: int
    validation_count: int
    test_count: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    windows: tuple[TemporalWindow, ...]
    temporal_safe: bool
    issues: tuple[str, ...]
    split_identity: str


def _identity(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _dates(dataset: HistoricalFeatureDataset) -> list[date]:
    return [date.fromisoformat(row.result_date) for row in dataset.rows]


def build_temporal_split(
    dataset: HistoricalFeatureDataset,
    *,
    train_ratio: float = 0.70,
    validation_ratio: float = 0.15,
    minimum_train_rows: int = 100,
    walk_forward_folds: int = 5,
) -> TemporalDatasetSplit:
    if not 0 < train_ratio < 1 or not 0 < validation_ratio < 1 or train_ratio + validation_ratio >= 1:
        raise ValueError("train_ratio and validation_ratio must be positive and sum to less than 1.")
    if minimum_train_rows < 1 or walk_forward_folds < 1:
        raise ValueError("minimum_train_rows and walk_forward_folds must be positive.")

    dates = _dates(dataset)
    n = len(dates)
    if n < minimum_train_rows + 3:
        raise ValueError("Dataset is too small for the requested temporal split.")

    train_count = max(minimum_train_rows, int(n * train_ratio))
    validation_count = max(1, int(n * validation_ratio))
    test_count = n - train_count - validation_count
    if test_count < 1:
        raise ValueError("Temporal split leaves no test rows.")

    train_end = train_count
    validation_end = train_count + validation_count
    windows: list[TemporalWindow] = []
    available_test = n - validation_end
    folds = min(walk_forward_folds, available_test)
    test_size = max(1, available_test // folds)

    for fold in range(folds):
        test_start_idx = validation_end + fold * test_size
        if fold == folds - 1:
            test_end_idx = n
        else:
            test_end_idx = min(n, test_start_idx + test_size)
        if test_start_idx >= test_end_idx:
            continue
        validation_start_idx = max(train_count, test_start_idx - validation_count)
        train_end_idx = validation_start_idx
        if train_end_idx < minimum_train_rows:
            continue
        windows.append(TemporalWindow(
            fold=fold + 1,
            train_start=dates[0].isoformat(),
            train_end=dates[train_end_idx - 1].isoformat(),
            validation_start=dates[validation_start_idx].isoformat(),
            validation_end=dates[test_start_idx - 1].isoformat(),
            test_start=dates[test_start_idx].isoformat(),
            test_end=dates[test_end_idx - 1].isoformat(),
            train_count=train_end_idx,
            validation_count=test_start_idx - validation_start_idx,
            test_count=test_end_idx - test_start_idx,
        ))

    issues: list[str] = []
    for window in windows:
        if not (window.train_end < window.validation_start <= window.validation_end < window.test_start <= window.test_end):
            issues.append(f"WINDOW_ORDER:{window.fold}")
        if window.train_count < minimum_train_rows:
            issues.append(f"MIN_TRAIN_ROWS:{window.fold}")
    if not windows:
        issues.append("NO_WALK_FORWARD_WINDOWS")

    temporal_safe = not issues and dataset.temporal_safe
    payload = {
        "version": BACKTEST_VERSION,
        "dataset_identity": dataset.dataset_identity,
        "counts": (train_count, validation_count, test_count),
        "windows": [asdict(window) for window in windows],
        "temporal_safe": temporal_safe,
        "issues": issues,
    }
    return TemporalDatasetSplit(
        version=BACKTEST_VERSION,
        dataset_identity=dataset.dataset_identity,
        train_count=train_count,
        validation_count=validation_count,
        test_count=test_count,
        train_start=dates[0].isoformat(),
        train_end=dates[train_end - 1].isoformat(),
        validation_start=dates[train_end].isoformat(),
        validation_end=dates[validation_end - 1].isoformat(),
        test_start=dates[validation_end].isoformat(),
        test_end=dates[-1].isoformat(),
        windows=tuple(windows),
        temporal_safe=temporal_safe,
        issues=tuple(sorted(set(issues))),
        split_identity=f"temporal-split-{_identity(payload)}",
    )


def validate_temporal_split(split: TemporalDatasetSplit) -> tuple[str, tuple[str, ...]]:
    issues = list(split.issues)
    if split.version != BACKTEST_VERSION:
        issues.append("INVALID_VERSION")
    if not split.temporal_safe:
        issues.append("TEMPORAL_SAFETY_FALSE")
    if split.train_count <= 0 or split.validation_count <= 0 or split.test_count <= 0:
        issues.append("EMPTY_PARTITION")
    if not split.split_identity.startswith("temporal-split-"):
        issues.append("INVALID_SPLIT_IDENTITY")
    if split.windows:
        previous_test_end: date | None = None
        for window in split.windows:
            train_end = date.fromisoformat(window.train_end)
            validation_start = date.fromisoformat(window.validation_start)
            validation_end = date.fromisoformat(window.validation_end)
            test_start = date.fromisoformat(window.test_start)
            test_end = date.fromisoformat(window.test_end)
            if not train_end < validation_start <= validation_end < test_start <= test_end:
                issues.append(f"INVALID_WINDOW:{window.fold}")
            if previous_test_end is not None and test_start <= previous_test_end:
                issues.append(f"OVERLAPPING_TEST_WINDOWS:{window.fold}")
            previous_test_end = test_end
    else:
        issues.append("NO_WINDOWS")
    return (VALID if not issues else INVALID, tuple(sorted(set(issues))))


def write_temporal_split(split: TemporalDatasetSplit, path: str | Path = "reports/temporal_backtest_split.json") -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(split), indent=2, sort_keys=True), encoding="utf-8")
    return destination


__all__ = [
    "BACKTEST_VERSION", "VALID", "INVALID", "TemporalWindow", "TemporalDatasetSplit",
    "build_temporal_split", "validate_temporal_split", "write_temporal_split",
]
