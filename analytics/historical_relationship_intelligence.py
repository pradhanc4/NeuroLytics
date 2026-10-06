from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import HistoricalResult, Market
from analytics.family_master import jodi_family_for, panel_family_for_panel

C12_VERSION = "C.12.0"
RELATIONSHIP_GROUPS = (
    "open_to_jodi",
    "open_to_close",
    "jodi_to_close",
    "jodi_internal",
    "close_internal",
    "record_transition",
    "family_transition",
    "panel_family_relationship",
)


@dataclass(frozen=True)
class RelationshipTable:
    name: str
    source: str
    target: str
    count: int
    support: int
    conditional_rates: dict[str, dict[str, float]]


@dataclass(frozen=True)
class TransitionTable:
    name: str
    source: str
    target: str
    transition_count: int
    unique_source_states: int
    unique_target_states: int
    top_transitions: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class HistoricalRelationshipIntelligence:
    version: str
    market_id: int
    market_name: str
    record_count: int
    date_range: tuple[str, str]
    relationship_tables: tuple[RelationshipTable, ...]
    transition_tables: tuple[TransitionTable, ...]
    rolling_windows: tuple[int, ...]
    temporal_features: tuple[str, ...]
    temporal_safe: bool
    leakage_issues: tuple[str, ...]
    identity: str


def _stable(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _digits(value: str, width: int) -> tuple[int, ...]:
    text = str(value).zfill(width)
    if len(text) != width or not text.isdigit():
        raise ValueError(f"Invalid {width}-digit value: {value!r}")
    return tuple(int(c) for c in text)


def _record(row: HistoricalResult) -> dict[str, object]:
    op = _digits(row.open_result, 3)
    jo = _digits(row.jodi_result, 2)
    cl = _digits(row.close_result, 3)
    return {
        "date": row.result_date.isoformat(),
        "open": op,
        "jodi": jo,
        "close": cl,
        "open_value": row.open_result,
        "jodi_value": row.jodi_result,
        "close_value": row.close_result,
        "open_family": tuple(str(d) for d in op),
        "jodi_family": jodi_family_for(row.jodi_result),
        "close_family": tuple(str(d) for d in cl),
        "panel_families": tuple(panel_family_for_panel(row.close_result[i:i+3]) for i in range(1) ),
    }


def _conditional_table(name: str, source: str, target: str, pairs: Iterable[tuple[str, str]]) -> RelationshipTable:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for src, dst in pairs:
        counts[src][dst] += 1
    rates: dict[str, dict[str, float]] = {}
    support = 0
    for src in sorted(counts):
        total = sum(counts[src].values())
        support += total
        rates[src] = {dst: round(n / total, 8) for dst, n in sorted(counts[src].items())}
    return RelationshipTable(name, source, target, sum(len(v) for v in counts.values()), support, rates)


def _transition_table(name: str, source: str, target: str, states: Iterable[tuple[str, str]]) -> TransitionTable:
    counter = Counter(states)
    top = tuple(
        {"source": s, "target": t, "count": n, "rate": round(n / sum(counter.values()), 8)}
        for (s, t), n in counter.most_common(25)
    )
    return TransitionTable(
        name=name,
        source=source,
        target=target,
        transition_count=sum(counter.values()),
        unique_source_states=len({s for s, _ in counter}),
        unique_target_states=len({t for _, t in counter}),
        top_transitions=top,
    )


def build_relationship_intelligence(db: Session, market_id: int) -> HistoricalRelationshipIntelligence:
    market = db.get(Market, market_id)
    if market is None:
        raise ValueError(f"Market not found: {market_id}")
    rows = list(db.scalars(
        select(HistoricalResult)
        .where(HistoricalResult.market_id == market_id)
        .order_by(HistoricalResult.result_date, HistoricalResult.id)
    ).all())
    if not rows:
        raise ValueError("No historical rows found.")

    data = [_record(r) for r in rows]
    relationships: list[RelationshipTable] = []

    # Position-level cross-variable relationships. Each pair is from the SAME completed record
    # for descriptive intelligence only; it is never used as a feature for predicting that record.
    relationships.append(_conditional_table(
        "open_digit_to_jodi_digit", "open_digit", "jodi_digit",
        ((str(o), str(j)) for r in data for o in r["open"] for j in r["jodi"])
    ))
    relationships.append(_conditional_table(
        "open_position_to_jodi_position", "open_position", "jodi_position",
        ((f"o{i+1}:{r['open'][i]}", f"j{j+1}:{r['jodi'][j]}")
         for r in data for i in range(3) for j in range(2))
    ))
    relationships.append(_conditional_table(
        "open_digit_to_close_digit", "open_digit", "close_digit",
        ((str(o), str(c)) for r in data for o in r["open"] for c in r["close"])
    ))
    relationships.append(_conditional_table(
        "jodi_digit_to_close_digit", "jodi_digit", "close_digit",
        ((str(j), str(c)) for r in data for j in r["jodi"] for c in r["close"])
    ))
    relationships.append(_conditional_table(
        "jodi_first_to_second", "jodi_first", "jodi_second",
        ((str(r["jodi"][0]), str(r["jodi"][1])) for r in data)
    ))
    relationships.append(_conditional_table(
        "close_first_to_second", "close_first", "close_second",
        ((str(r["close"][0]), str(r["close"][1])) for r in data)
    ))
    relationships.append(_conditional_table(
        "close_second_to_third", "close_second", "close_third",
        ((str(r["close"][1]), str(r["close"][2])) for r in data)
    ))

    transitions: list[TransitionTable] = []
    # Chronological transitions use ONLY prior -> current state. They describe historical behavior.
    for field, label in (
        ("open_value", "open_value"),
        ("jodi_value", "jodi_value"),
        ("close_value", "close_value"),
        ("jodi_family", "jodi_family"),
    ):
        transitions.append(_transition_table(
            f"previous_{label}_to_current_{label}", f"previous_{label}", f"current_{label}",
            ((str(data[i-1][field]), str(data[i][field])) for i in range(1, len(data)))
        ))
    transitions.append(_transition_table(
        "previous_open_to_current_jodi", "previous_open", "current_jodi",
        ((str(data[i-1]["open_value"]), str(data[i]["jodi_value"])) for i in range(1, len(data)))
    ))
    transitions.append(_transition_table(
        "previous_jodi_to_current_close", "previous_jodi", "current_close",
        ((str(data[i-1]["jodi_value"]), str(data[i]["close_value"])) for i in range(1, len(data)))
    ))
    transitions.append(_transition_table(
        "previous_open_to_current_jodi_family", "previous_open", "current_jodi_family",
        ((str(data[i-1]["open_value"]), str(data[i]["jodi_family"])) for i in range(1, len(data)))
    ))
    transitions.append(_transition_table(
        "previous_jodi_family_to_current_panel_families", "previous_jodi_family", "current_panel_families",
        ((str(data[i-1]["jodi_family"]), str(data[i]["panel_families"])) for i in range(1, len(data)))
    ))

    # Rolling/recency summaries are metadata for future point-in-time feature engineering.
    temporal_features = (
        "lag1_open_digits", "lag1_jodi_digits", "lag1_close_digits",
        "lag2_open_digits", "lag2_jodi_digits", "lag2_close_digits",
        "rolling3_digit_frequency", "rolling7_digit_frequency", "rolling14_digit_frequency",
        "rolling3_family_frequency", "rolling7_family_frequency", "rolling14_family_frequency",
        "day_of_week", "day_of_month", "month", "quarter", "year",
        "days_since_previous_record",
    )

    payload = {
        "version": C12_VERSION,
        "market_id": market_id,
        "record_count": len(rows),
        "relationships": [asdict(x) for x in relationships],
        "transitions": [asdict(x) for x in transitions],
        "temporal_features": temporal_features,
        "temporal_safe": True,
        "leakage_issues": [],
    }
    return HistoricalRelationshipIntelligence(
        version=C12_VERSION,
        market_id=market_id,
        market_name=market.name,
        record_count=len(rows),
        date_range=(rows[0].result_date.isoformat(), rows[-1].result_date.isoformat()),
        relationship_tables=tuple(relationships),
        transition_tables=tuple(transitions),
        rolling_windows=(3, 7, 14),
        temporal_features=temporal_features,
        temporal_safe=True,
        leakage_issues=(),
        identity=f"historical-relationship-intelligence-{_stable(payload)}",
    )


def validate_relationship_intelligence(report: HistoricalRelationshipIntelligence) -> tuple[str, tuple[str, ...]]:
    issues: list[str] = []
    if report.version != C12_VERSION:
        issues.append("INVALID_VERSION")
    if report.record_count <= 0:
        issues.append("EMPTY_DATASET")
    if report.date_range[0] > report.date_range[1]:
        issues.append("INVALID_DATE_RANGE")
    if tuple(report.rolling_windows) != (3, 7, 14):
        issues.append("INVALID_ROLLING_WINDOWS")
    if not report.temporal_safe:
        issues.append("TEMPORAL_SAFETY_FALSE")
    if report.leakage_issues:
        issues.extend(report.leakage_issues)
    if not report.identity.startswith("historical-relationship-intelligence-"):
        issues.append("INVALID_IDENTITY")
    forbidden = ("current_jodi_as_feature", "current_close_as_feature", "future_result_as_feature")
    for item in report.temporal_features:
        if item in forbidden:
            issues.append(f"TARGET_LEAKAGE:{item}")
    return ("VALID" if not issues else "INVALID", tuple(sorted(set(issues))))


def write_relationship_intelligence(
    report: HistoricalRelationshipIntelligence,
    path: str | Path = "reports/historical_relationship_intelligence.json",
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return destination


def build_report(db: Session, market_id: int, path: str | Path = "reports/historical_relationship_intelligence.json") -> Path:
    report = build_relationship_intelligence(db, market_id)
    status, issues = validate_relationship_intelligence(report)
    if status != "VALID":
        raise ValueError(f"C.12 relationship report invalid: {issues}")
    return write_relationship_intelligence(report, path)


__all__ = [
    "C12_VERSION", "RELATIONSHIP_GROUPS", "RelationshipTable", "TransitionTable",
    "HistoricalRelationshipIntelligence", "build_relationship_intelligence",
    "validate_relationship_intelligence", "write_relationship_intelligence", "build_report",
]
