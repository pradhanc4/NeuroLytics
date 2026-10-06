from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

C20_VERSION = "C.20.0"
EXPERIMENTAL_ROOT = Path("models") / "relationship_aware"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_artifacts(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []


def build_boundary_manifest(root: Path, approved: Iterable[Path] = ()) -> dict:
    approved_set = {Path(p).resolve() for p in approved}
    artifacts = discover_artifacts(root)
    entries = []
    for path in artifacts:
        resolved = path.resolve()
        entries.append({
            "path": str(path.relative_to(root.parent.parent)).replace("\\", "/"),
            "sha256": sha256_file(path),
            "approved": resolved in approved_set,
            "experimental": EXPERIMENTAL_ROOT.as_posix() in str(path).replace("\\", "/"),
        })
    return {
        "version": C20_VERSION,
        "artifact_root": str(root).replace("\\", "/"),
        "experimental_root": EXPERIMENTAL_ROOT.as_posix(),
        "artifact_count": len(entries),
        "artifacts": entries,
        "policy": "relationship-aware artifacts are isolated and never implicitly production-approved",
    }


def validate_boundary(manifest: dict) -> tuple[bool, list[str]]:
    issues = []
    for entry in manifest.get("artifacts", []):
        if entry.get("experimental") and entry.get("approved"):
            issues.append(f"experimental artifact marked approved: {entry.get('path')}")
        if not entry.get("sha256"):
            issues.append(f"missing hash: {entry.get('path')}")
    return not issues, issues


def write_manifest(manifest: dict, path: Path) -> str:
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    identity = hashlib.sha256(payload.encode()).hexdigest()
    output = dict(manifest)
    output["status"] = "VALID"
    output["identity"] = identity
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    return identity
