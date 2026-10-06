from __future__ import annotations

import gc
import hashlib
import json
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from database.models import HistoricalResult, Market


PERFORMANCE_SCALABILITY_VERSION = "95.0.0"
VALID = "VALID"
INVALID = "INVALID"
WARNING = "WARNING"

DEFAULT_THRESHOLDS = {
    "database_count_ms": 250.0,
    "database_fetch_1000_ms": 1000.0,
    "feature_probe_ms": 250.0,
    "prediction_1000_ms": 5000.0,
    "panel_ranking_1000_ms": 5000.0,
    "jodi_ranking_1000_ms": 2500.0,
    "memory_growth_mb": 256.0,
}


@dataclass(frozen=True)
class PerformanceMeasurement:
    name: str
    iterations: int
    elapsed_ms: float
    per_iteration_ms: float
    throughput_per_second: float
    status: str
    threshold_ms: float | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ScalabilityMeasurement:
    name: str
    input_size: int
    elapsed_ms: float
    per_item_us: float
    throughput_per_second: float
    status: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PerformanceScalabilityReport:
    version: str
    status: str
    measurements: tuple[PerformanceMeasurement, ...]
    scalability: tuple[ScalabilityMeasurement, ...]
    environment: dict[str, Any]
    bottlenecks: tuple[str, ...]
    report_identity: str


def _identity(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "performance-scalability-" + hashlib.sha256(raw).hexdigest()


def _measure(
    name: str,
    fn: Callable[[], Any],
    iterations: int,
    threshold_ms: float | None,
    metadata: dict[str, Any] | None = None,
) -> PerformanceMeasurement:
    if iterations < 1:
        raise ValueError("iterations must be positive.")
    fn()
    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    elapsed = (time.perf_counter() - start) * 1000.0
    per = elapsed / iterations
    status = VALID if threshold_ms is None or per <= threshold_ms else WARNING
    return PerformanceMeasurement(
        name=name,
        iterations=iterations,
        elapsed_ms=elapsed,
        per_iteration_ms=per,
        throughput_per_second=1000.0 / per if per > 0 else math.inf,
        status=status,
        threshold_ms=threshold_ms,
        metadata=metadata or {},
    )


def _memory_mb() -> float:
    try:
        import resource
        return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0
    except Exception:
        return 0.0


def _environment() -> dict[str, Any]:
    import os
    import platform
    import sys
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "cpu_count": os.cpu_count(),
        "process_id": os.getpid(),
    }


def _database_measurements(db: Session, thresholds: dict[str, float]) -> tuple[PerformanceMeasurement, ...]:
    count = _measure(
        "database_count",
        lambda: db.scalar(select(func.count()).select_from(HistoricalResult)),
        20,
        thresholds["database_count_ms"],
    )

    def fetch():
        return db.scalars(
            select(HistoricalResult)
            .order_by(HistoricalResult.result_date, HistoricalResult.id)
            .limit(1000)
        ).all()

    fetch_measurement = _measure(
        "database_fetch_1000",
        fetch,
        10,
        thresholds["database_fetch_1000_ms"],
    )
    return count, fetch_measurement


def _prediction_benchmark(thresholds: dict[str, float]) -> PerformanceMeasurement:
    from analytics.end_to_end_prediction import _prediction

    probabilities = [0.1] * 10

    def predict():
        return _prediction("col1", probabilities, "phase95-benchmark-model", "95.0.0")

    return _measure(
        "prediction_1000",
        predict,
        1000,
        thresholds["prediction_1000_ms"],
        {"positions": 1, "probabilities": 10},
    )


def _ranking_benchmarks(thresholds: dict[str, float]) -> tuple[PerformanceMeasurement, PerformanceMeasurement]:
    from analytics.learning_to_rank_model import LearningToRankPrediction
    from analytics.panel_ranking import PanelCandidateInput, rank_panels_from_predictions
    from analytics.jodi_ranking import JodiCandidateInput, rank_jodis_from_predictions

    def learning(position: str) -> LearningToRankPrediction:
        return LearningToRankPrediction(
            group_id="phase95",
            target_date="2026-01-01",
            candidate_digits=tuple(range(10)),
            scores=tuple([0.1] * 10),
            probabilities=tuple([0.1] * 10),
            ranks=tuple(range(1, 11)),
            actual_digit=0,
            top_candidate=0,
            top_k_candidates=(0, 1, 2),
        )

    predictions = tuple(learning(f"col{i}") for i in range(1, 4))
    panels = tuple(PanelCandidateInput(f"{a}{b}{c}") for a in range(10) for b in range(10) for c in range(10))
    jodis = tuple(JodiCandidateInput(f"{a}{b}") for a in range(10) for b in range(10))

    panel = _measure(
        "panel_ranking_1000",
        lambda: rank_panels_from_predictions(
            predictions, panels, group_id="phase95-panel", target_date=__import__("datetime").date(2026, 1, 1), target_position="panel", top_k=1000
        ),
        5,
        thresholds["panel_ranking_1000_ms"],
        {"candidate_count": 1000},
    )
    jodi = _measure(
        "jodi_ranking_100",
        lambda: rank_jodis_from_predictions(
            predictions[:2], jodis, group_id="phase95-jodi", target_date=__import__("datetime").date(2026, 1, 1), target_position="jodi", top_k=100
        ),
        10,
        thresholds["jodi_ranking_1000_ms"],
        {"candidate_count": 100},
    )
    return panel, jodi


def _feature_scalability() -> tuple[ScalabilityMeasurement, ...]:
    values = list(range(10000))
    measurements = []
    for size in (100, 1000, 5000, 10000):
        start = time.perf_counter()
        result = [value * 2 + 1 for value in values[:size]]
        elapsed = (time.perf_counter() - start) * 1000.0
        per_item = (elapsed * 1000.0 / size) if size else 0.0
        measurements.append(
            ScalabilityMeasurement(
                "feature_vector_scaling",
                size,
                elapsed,
                per_item,
                size / (elapsed / 1000.0) if elapsed > 0 else math.inf,
                VALID,
                {"operation": "deterministic_numeric_feature_materialization"},
            )
        )
        if len(result) != size:
            raise AssertionError("scalability benchmark produced incorrect output.")
    return tuple(measurements)


def _ranking_scalability() -> tuple[ScalabilityMeasurement, ...]:
    from analytics.panel_ranking import PanelCandidateInput
    measurements = []
    for size in (100, 500, 1000):
        candidates = tuple(
            PanelCandidateInput(f"{index // 100}{(index // 10) % 10}{index % 10}")
            for index in range(min(size, 1000))
        )
        start = time.perf_counter()
        sorted_candidates = sorted(candidates, key=lambda item: item.panel)
        elapsed = (time.perf_counter() - start) * 1000.0
        measurements.append(
            ScalabilityMeasurement(
                "candidate_sort_scaling",
                len(candidates),
                elapsed,
                elapsed * 1000.0 / max(1, len(candidates)),
                len(candidates) / (elapsed / 1000.0) if elapsed > 0 else math.inf,
                VALID,
                {"operation": "candidate_sort"},
            )
        )
        if not sorted_candidates:
            raise AssertionError("scalability benchmark produced no candidates.")
    return tuple(measurements)


def run_performance_scalability_audit(
    db: Session,
    *,
    thresholds: dict[str, float] | None = None,
) -> PerformanceScalabilityReport:
    active = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        active.update(thresholds)

    measurements = list(_database_measurements(db, active))
    measurements.append(_prediction_benchmark(active))
    measurements.extend(_ranking_benchmarks(active))

    before = _memory_mb()
    gc.collect()
    _ = [list(range(1000)) for _ in range(100)]
    gc.collect()
    after = _memory_mb()
    memory_growth = max(0.0, after - before)
    measurements.append(
        PerformanceMeasurement(
            "memory_growth_probe",
            1,
            memory_growth,
            memory_growth,
            0.0,
            VALID if memory_growth <= active["memory_growth_mb"] else WARNING,
            active["memory_growth_mb"],
            {"unit": "MB", "before_mb": before, "after_mb": after},
        )
    )

    scalability = _feature_scalability() + _ranking_scalability()

    warnings = [item.name for item in measurements if item.status == WARNING]
    bottlenecks = tuple(warnings)

    status = VALID if not warnings else WARNING
    identity = _identity({
        "version": PERFORMANCE_SCALABILITY_VERSION,
        "status": status,
        "measurements": [
            (item.name, item.per_iteration_ms, item.status)
            for item in measurements
        ],
        "scalability": [
            (item.name, item.input_size, item.elapsed_ms)
            for item in scalability
        ],
        "environment": _environment(),
    })
    return PerformanceScalabilityReport(
        PERFORMANCE_SCALABILITY_VERSION,
        status,
        tuple(measurements),
        scalability,
        _environment(),
        bottlenecks,
        identity,
    )


def performance_scalability_summary(report: PerformanceScalabilityReport) -> dict[str, Any]:
    return {
        "status": report.status,
        "version": report.version,
        "measurements": [
            {
                "name": item.name,
                "iterations": item.iterations,
                "elapsed_ms": round(item.elapsed_ms, 4),
                "per_iteration_ms": round(item.per_iteration_ms, 6),
                "throughput_per_second": round(item.throughput_per_second, 3),
                "status": item.status,
                "threshold_ms": item.threshold_ms,
                "metadata": item.metadata,
            }
            for item in report.measurements
        ],
        "scalability": [
            {
                "name": item.name,
                "input_size": item.input_size,
                "elapsed_ms": round(item.elapsed_ms, 4),
                "per_item_us": round(item.per_item_us, 6),
                "throughput_per_second": round(item.throughput_per_second, 3),
                "status": item.status,
                "metadata": item.metadata,
            }
            for item in report.scalability
        ],
        "environment": report.environment,
        "bottlenecks": list(report.bottlenecks),
        "report_identity": report.report_identity,
    }


def write_performance_scalability_report(
    report: PerformanceScalabilityReport,
    path: str | Path | None = None,
) -> Path:
    destination = Path(path or "reports/performance_scalability_audit.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(performance_scalability_summary(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination


__all__ = [
    "PERFORMANCE_SCALABILITY_VERSION",
    "VALID",
    "INVALID",
    "WARNING",
    "DEFAULT_THRESHOLDS",
    "PerformanceMeasurement",
    "ScalabilityMeasurement",
    "PerformanceScalabilityReport",
    "run_performance_scalability_audit",
    "performance_scalability_summary",
    "write_performance_scalability_report",
]
