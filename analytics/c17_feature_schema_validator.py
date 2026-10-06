from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence


C17_VERSION = "C.17.0"


@dataclass(frozen=True)
class SchemaValidation:
    status: str
    temporal_safe: bool
    feature_count: int
    missing: tuple[str, ...]
    extra: tuple[str, ...]
    nonfinite: tuple[str, ...]
    target_dependent: tuple[str, ...]
    identity: str


def validate_feature_schema(
    feature_rows: Sequence[Mapping[str, float]],
    expected_features: Sequence[str] | None = None,
    forbidden_tokens: Sequence[str] = (),
) -> SchemaValidation:
    if not feature_rows:
        raise ValueError("feature_rows must not be empty")

    union = set().union(*(set(row) for row in feature_rows))
    expected = set(expected_features or union)
    missing = tuple(sorted(expected - union))
    extra = tuple(sorted(union - expected))

    nonfinite: set[str] = set()
    for row in feature_rows:
        nonfinite.update(
            str(k) for k, v in row.items()
            if not isinstance(v, (int, float)) or not __import__("math").isfinite(float(v))
        )

    target_dependent: set[str] = set()
    for name in union:
        if any(token.lower() in name.lower() for token in forbidden_tokens):
            target_dependent.add(name)

    schema_identity = hashlib.sha256(
        json.dumps(sorted(union), separators=(",", ":")).encode()
    ).hexdigest()

    temporal_safe = not missing and not extra and not nonfinite and not target_dependent
    status = "VALID" if temporal_safe else "INVALID"

    return SchemaValidation(
        status=status,
        temporal_safe=temporal_safe,
        feature_count=len(union),
        missing=missing,
        extra=extra,
        nonfinite=tuple(sorted(nonfinite)),
        target_dependent=tuple(sorted(target_dependent)),
        identity=schema_identity,
    )


def write_report(validation: SchemaValidation, path: str | Path) -> None:
    payload = {
        "version": C17_VERSION,
        "status": validation.status,
        "temporal_safe": validation.temporal_safe,
        "feature_count": validation.feature_count,
        "missing": list(validation.missing),
        "extra": list(validation.extra),
        "nonfinite": list(validation.nonfinite),
        "target_dependent": list(validation.target_dependent),
        "identity": validation.identity,
    }
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


__all__ = ["C17_VERSION", "SchemaValidation", "validate_feature_schema", "write_report"]
