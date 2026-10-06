from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from collections import Counter
from typing import Sequence
import hashlib
import json

C13_VERSION = "C.13.0"


def _digits(value: int, width: int) -> list[int]:
    return [int(c) for c in f"{int(value):0{width}d}"]


def _rate(counter: Counter, key: int, total: int) -> float:
    return round(counter.get(key, 0) / total, 8) if total else 0.0


def _rolling(values: Sequence[int], window: int) -> dict[str, float]:
    vals = list(values[-window:])
    n = len(vals)
    return {f"digit_{d}": round(vals.count(d) / n, 8) if n else 0.0 for d in range(10)}


def _stable_id(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class C13FeatureRow:
    date: str
    stage: str
    features: dict[str, float]


class RelationshipAwareTemporalFeatureBuilder:
    """Point-in-time relationship features. Current targets are never used as predictors."""

    def __init__(self, rows: Sequence[dict]):
        self.rows = sorted(rows, key=lambda r: r["date"])

    def build(self) -> list[C13FeatureRow]:
        out: list[C13FeatureRow] = []
        prior: list[dict] = []
        for row in self.rows:
            op = _digits(int(row["open"]), 3)
            f = self._base(row, op, prior)
            out.append(C13FeatureRow(row["date"], "stage1_jodi", f))

            # Stage 2 is a known-Jodi-First context. Only the first Jodi digit is exposed.
            jf = int(_digits(int(row["jodi"]), 2)[0])
            sf = dict(f)
            sf["known_jodi_first"] = float(jf)
            sf.update(self._conditional_features(prior, op, jf))
            out.append(C13FeatureRow(row["date"], "stage2_close", sf))
            prior.append(row)

        return out

    def _base(self, row: dict, op: list[int], prior: Sequence[dict]) -> dict[str, float]:
        features: dict[str, float] = {}
        for i, d in enumerate(op, 1):
            features[f"open_{i}"] = float(d)
        if prior:
            prev = prior[-1]
            for name, width, key in (("open",3,"open"),("jodi",2,"jodi"),("close",3,"close")):
                ds = _digits(int(prev[key]), width)
                for i, d in enumerate(ds, 1):
                    features[f"lag1_{name}_{i}"] = float(d)

        for w in (3, 7, 14):
            history = prior[-w:]
            for pos in range(3):
                features[f"roll{w}_open_{pos+1}_d{op[pos]}"] = _rate(
                    Counter(_digits(int(r["open"]),3)[pos] for r in history), op[pos], len(history)
                )

        # Open-position -> historical Jodi-position relationship rates.
        for oi, od in enumerate(op):
            for ji in range(2):
                c = Counter(_digits(int(r["jodi"]),2)[ji] for r in prior
                            if _digits(int(r["open"]),3)[oi] == od)
                total = sum(c.values())
                for jd in range(10):
                    features[f"rel_open{oi+1}_d{od}_to_jodi{ji+1}_d{jd}"] = _rate(c, jd, total)

        # Open-position -> historical Close-position relationship rates.
        for oi, od in enumerate(op):
            for ci in range(3):
                c = Counter(_digits(int(r["close"]),3)[ci] for r in prior
                            if _digits(int(r["open"]),3)[oi] == od)
                total = sum(c.values())
                for cd in range(10):
                    features[f"rel_open{oi+1}_d{od}_to_close{ci+1}_d{cd}"] = _rate(c, cd, total)

        # Chronological previous -> current transition features.
        for pos in range(3):
            current = op[pos]
            prev_vals = [_digits(int(r["open"]),3)[pos] for r in prior]
            c = Counter(prev_vals)
            features[f"prev_to_current_open_{pos+1}_same"] = _rate(c, current, len(prev_vals))

        for w in (3, 7, 14):
            for key, value in _rolling(
                [_digits(int(r["open"]), 3)[0] for r in prior], w
            ).items():
                features[f"temporal_{w}_{key}"] = value

        dt = date.fromisoformat(str(row["date"]))
        features["day_of_week"] = float(dt.weekday())
        features["day_of_month"] = float(dt.day)
        features["month"] = float(dt.month)
        features["quarter"] = float((dt.month - 1) // 3 + 1)
        features["year"] = float(dt.year)
        features["prior_count"] = float(len(prior))
        return features

    def _conditional_features(self, prior: Sequence[dict], op: list[int], jf: int) -> dict[str, float]:
        c = Counter(
            _digits(int(r["close"]),3)[ci]
            for r in prior
            if _digits(int(r["jodi"]),2)[0] == jf
            for ci in range(3)
        )
        total = sum(c.values())
        return {f"rel_jodi_first_d{jf}_to_close_d{d}": _rate(c, d, total) for d in range(10)}

    def identity(self, features: Sequence[C13FeatureRow]) -> str:
        return _stable_id({
            "version": C13_VERSION,
            "rows": [{"date": x.date, "stage": x.stage, "features": x.features} for x in features],
        })


__all__ = ["C13_VERSION", "C13FeatureRow", "RelationshipAwareTemporalFeatureBuilder"]
