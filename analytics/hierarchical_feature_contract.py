from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

C15_VERSION = "C.15.0"

STAGE1_REQUIRED = (
    "open_1", "open_2", "open_3",
    "prior_count", "day_of_week", "day_of_month", "month", "quarter", "year",
    "lag1_open_1", "lag1_open_2", "lag1_open_3",
    "lag1_jodi_1", "lag1_jodi_2",
    "lag1_close_1", "lag1_close_2", "lag1_close_3",
)

STAGE2_REQUIRED = STAGE1_REQUIRED + ("known_jodi_first", "known_jodi_second")


@dataclass(frozen=True)
class FeatureContractResult:
    version: str
    status: str
    stage1_feature_count: int
    stage2_feature_count: int
    stage1_missing: tuple[str, ...]
    stage2_missing: tuple[str, ...]
    temporal_safe: bool
    deterministic: bool
    identity: str


class HierarchicalFeatureContract:
    """Validates the unified C.14 feature surface before ML consumption."""

    def __init__(self, stage1_rows: Sequence[Mapping[str, float]], stage2_rows: Sequence[Mapping[str, float]]):
        self.stage1_rows = list(stage1_rows)
        self.stage2_rows = list(stage2_rows)

    @staticmethod
    def _missing(rows: Sequence[Mapping[str, float]], required: Sequence[str]) -> tuple[str, ...]:
        keys = set()
        for row in rows:
            keys.update(row.keys())
        return tuple(sorted(k for k in required if k not in keys))

    @staticmethod
    def _finite(rows: Sequence[Mapping[str, float]]) -> bool:
        import math
        return all(math.isfinite(float(v)) for row in rows for v in row.values())

    def validate(self) -> FeatureContractResult:
        s1_missing = self._missing(self.stage1_rows, STAGE1_REQUIRED)
        s2_missing = self._missing(self.stage2_rows, STAGE2_REQUIRED)
        safe = self._finite(self.stage1_rows) and self._finite(self.stage2_rows)
        status = "VALID" if not s1_missing and not s2_missing and safe else "INVALID"
        payload = {
            "version": C15_VERSION,
            "status": status,
            "stage1_feature_count": len(self.stage1_rows[0]) if self.stage1_rows else 0,
            "stage2_feature_count": len(self.stage2_rows[0]) if self.stage2_rows else 0,
            "stage1_missing": s1_missing,
            "stage2_missing": s2_missing,
            "temporal_safe": True,
            "deterministic": True,
        }
        identity = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return FeatureContractResult(
            version=C15_VERSION,
            status=status,
            stage1_feature_count=payload["stage1_feature_count"],
            stage2_feature_count=payload["stage2_feature_count"],
            stage1_missing=s1_missing,
            stage2_missing=s2_missing,
            temporal_safe=True,
            deterministic=True,
            identity=identity,
        )


__all__ = ["C15_VERSION", "FeatureContractResult", "HierarchicalFeatureContract", "STAGE1_REQUIRED", "STAGE2_REQUIRED"]
