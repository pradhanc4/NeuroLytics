from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

C12_DIGIT_TRANSITION_VERSION = "C.12.0"


@dataclass(frozen=True)
class DigitTransition:
    source_digit: int
    target_digit: int
    count: int
    probability: float


def build_digit_transition_matrix(pairs: Iterable[tuple[int, int]]) -> tuple[DigitTransition, ...]:
    counter = Counter((int(a), int(b)) for a, b in pairs)
    totals = Counter()
    for (source, _), count in counter.items():
        totals[source] += count
    return tuple(
        DigitTransition(a, b, n, round(n / totals[a], 8))
        for (a, b), n in sorted(counter.items())
    )


def matrix_from_sequences(sequences: Iterable[Iterable[int]]) -> tuple[DigitTransition, ...]:
    pairs = []
    for sequence in sequences:
        values = [int(v) for v in sequence]
        pairs.extend(zip(values, values[1:]))
    return build_digit_transition_matrix(pairs)


__all__ = ["C12_DIGIT_TRANSITION_VERSION", "DigitTransition", "build_digit_transition_matrix", "matrix_from_sequences"]
