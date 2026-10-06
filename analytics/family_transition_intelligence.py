from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable


C12_FAMILY_TRANSITION_VERSION = "C.12.0"


@dataclass(frozen=True)
class FamilyTransition:
    source_family: str
    target_family: str
    count: int
    probability: float


def build_family_transition_table(
    pairs: Iterable[tuple[str, str]],
) -> tuple[FamilyTransition, ...]:
    counter = Counter((str(a), str(b)) for a, b in pairs)
    totals = Counter()
    for (source, _), count in counter.items():
        totals[source] += count
    return tuple(
        FamilyTransition(a, b, n, round(n / totals[a], 8))
        for (a, b), n in sorted(counter.items())
    )


__all__ = ["C12_FAMILY_TRANSITION_VERSION", "FamilyTransition", "build_family_transition_table"]
