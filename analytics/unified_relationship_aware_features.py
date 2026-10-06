from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from typing import Sequence

C14_VERSION = "C.14.0"


def digits(value: int, width: int) -> list[int]:
    return [int(c) for c in f"{int(value):0{width}d}"]


def rate(counter: Counter, key: int) -> float:
    total = sum(counter.values())
    return round(counter.get(key, 0) / total, 8) if total else 0.0


@dataclass(frozen=True)
class UnifiedFeatureRow:
    date: str
    stage: str
    features: dict[str, float]


class UnifiedRelationshipAwareFeatureBuilder:
    """Incremental, point-in-time unified relationship feature builder."""

    def __init__(self, rows: Sequence[dict]):
        self.rows = sorted(rows, key=lambda r: str(r["date"]))

    def build(self) -> list[UnifiedFeatureRow]:
        result: list[UnifiedFeatureRow] = []
        prior = []
        open_jodi = [[[Counter() for _ in range(10)] for _ in range(3)] for _ in range(2)]
        open_close = [[[Counter() for _ in range(10)] for _ in range(3)] for _ in range(3)]
        jodi_first_close = [Counter() for _ in range(10)]
        transition = [Counter() for _ in range(3)]
        rolling = [[], [], []]

        for row in self.rows:
            op = digits(row["open"], 3)
            jf, js = digits(row["jodi"], 2)
            cl = digits(row["close"], 3)

            base = {f"open_{i+1}": float(d) for i, d in enumerate(op)}
            base["prior_count"] = float(len(prior))
            dt = date.fromisoformat(str(row["date"]))
            base.update({
                "day_of_week": float(dt.weekday()),
                "day_of_month": float(dt.day),
                "month": float(dt.month),
                "quarter": float((dt.month - 1) // 3 + 1),
                "year": float(dt.year),
            })

            if prior:
                po = digits(prior[-1]["open"], 3)
                pj = digits(prior[-1]["jodi"], 2)
                pc = digits(prior[-1]["close"], 3)
                for i, d in enumerate(po, 1): base[f"lag1_open_{i}"] = float(d)
                for i, d in enumerate(pj, 1): base[f"lag1_jodi_{i}"] = float(d)
                for i, d in enumerate(pc, 1): base[f"lag1_close_{i}"] = float(d)
                for i, d in enumerate(op):
                    base[f"transition_open_{i}_to_current_{d}"] = rate(transition[i], d)

            for oi, od in enumerate(op):
                for ji in range(2):
                    for jd in range(10):
                        base[f"rel_open{oi+1}_d{od}_to_jodi{ji+1}_d{jd}"] = rate(open_jodi[ji][oi][od], jd)
                for ci in range(3):
                    for cd in range(10):
                        base[f"rel_open{oi+1}_d{od}_to_close{ci+1}_d{cd}"] = rate(open_close[ci][oi][od], cd)

            # Stage 1 must not depend on the observed/current Jodi target.
            # Emit historical Close-first distributions for every possible Jodi-first
            # candidate as separate, target-independent features.
            for candidate_jf in range(10):
                for d in range(10):
                    base[f"rel_jodi_first_d{candidate_jf}_to_close_d{d}"] = rate(
                        jodi_first_close[candidate_jf], d
                    )

            for pos, d in enumerate(op):
                values = rolling[pos][-14:]
                for w in (3, 7, 14):
                    tail = values[-w:]
                    base[f"rolling{w}_open{pos+1}_d{d}"] = round(tail.count(d) / len(tail), 8) if tail else 0.0

            result.append(UnifiedFeatureRow(str(row["date"]), "stage1_jodi", dict(base)))

            stage2 = dict(base)
            stage2["known_jodi_first"] = float(jf)
            stage2["known_jodi_second"] = float(js)
            # Jodi second is known only after the second Jodi digit is observed.
            # Emit the full prior Close-first distribution; never index a feature by
            # the current Close target, which would leak the label into Stage 2.
            prior_close_by_jodi_second = Counter(
                digits(r["close"], 3)[0]
                for r in prior
                if digits(r["jodi"], 2)[1] == js
            )
            for cd in range(10):
                stage2[f"rel_jodi_second_d{js}_to_close_d{cd}"] = rate(
                    prior_close_by_jodi_second, cd
                )
            result.append(UnifiedFeatureRow(str(row["date"]), "stage2_close", stage2))

            for oi, od in enumerate(op):
                open_jodi[0][oi][od][jf] += 1
                open_jodi[1][oi][od][js] += 1
                for ci, cd in enumerate(cl):
                    open_close[ci][oi][od][cd] += 1
            jodi_first_close[jf][cl[0]] += 1
            for i, d in enumerate(op):
                transition[i][d] += 1
                rolling[i].append(d)
            prior.append(row)

        return result

    @staticmethod
    def identity(rows: Sequence[UnifiedFeatureRow]) -> str:
        payload = {
            "version": C14_VERSION,
            "rows": [{"date": r.date, "stage": r.stage, "features": r.features} for r in rows],
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


__all__ = ["C14_VERSION", "UnifiedFeatureRow", "UnifiedRelationshipAwareFeatureBuilder"]
