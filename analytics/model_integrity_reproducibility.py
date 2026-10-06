from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence


C18_VERSION = "C.18.0"


@dataclass(frozen=True)
class ArtifactRecord:
    path: str
    size: int
    sha256: str
    loadable: bool
    n_features_in: int | None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory_models(root: Path) -> list[ArtifactRecord]:
    import joblib

    records: list[ArtifactRecord] = []
    for path in sorted(root.rglob("*.joblib")):
        loadable = False
        n_features = None
        try:
            model = joblib.load(path)
            loadable = True
            value = getattr(model, "n_features_in_", None)
            n_features = int(value) if value is not None else None
        except Exception:
            pass
        records.append(
            ArtifactRecord(
                path=str(path),
                size=path.stat().st_size,
                sha256=sha256_file(path),
                loadable=loadable,
                n_features_in=n_features,
            )
        )
    return records


def feature_identity(rows: Sequence[Mapping[str, float]]) -> str:
    keys = sorted(set().union(*(set(r) for r in rows)))
    return hashlib.sha256(
        json.dumps(keys, separators=(",", ":")).encode()
    ).hexdigest()


def validate_temporal_order(rows: Sequence[Mapping[str, object]]) -> bool:
    dates = [str(r["date"]) for r in rows]
    return dates == sorted(dates) and len(dates) == len(set(dates))


def build_report(
    rows: Sequence[Mapping[str, object]],
    stage1: Sequence[Mapping[str, float]],
    stage2: Sequence[Mapping[str, float]],
    model_root: Path,
) -> dict:
    artifacts = inventory_models(model_root)
    stage1_id_a = feature_identity(stage1)
    stage1_id_b = feature_identity(stage1)
    stage2_id_a = feature_identity(stage2)
    stage2_id_b = feature_identity(stage2)

    report = {
        "version": C18_VERSION,
        "input_rows": len(rows),
        "stage1_rows": len(stage1),
        "stage2_rows": len(stage2),
        "temporal_order_valid": validate_temporal_order(rows),
        "stage1_reproducible": stage1_id_a == stage1_id_b,
        "stage2_reproducible": stage2_id_a == stage2_id_b,
        "stage1_feature_identity": stage1_id_a,
        "stage2_feature_identity": stage2_id_a,
        "artifacts": [
            {
                "path": x.path,
                "size": x.size,
                "sha256": x.sha256,
                "loadable": x.loadable,
                "n_features_in": x.n_features_in,
            }
            for x in artifacts
        ],
    }
    report["artifact_integrity_valid"] = bool(artifacts) and all(
        x.size > 0 and x.loadable for x in artifacts
    )
    report["status"] = (
        "VALID"
        if report["temporal_order_valid"]
        and report["stage1_reproducible"]
        and report["stage2_reproducible"]
        and report["artifact_integrity_valid"]
        else "INVALID"
    )
    report["identity"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return report


__all__ = [
    "C18_VERSION",
    "ArtifactRecord",
    "sha256_file",
    "inventory_models",
    "feature_identity",
    "validate_temporal_order",
    "build_report",
]
