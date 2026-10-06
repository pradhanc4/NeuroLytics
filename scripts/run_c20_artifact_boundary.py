from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analytics.production_artifact_boundary import (
    C20_VERSION,
    build_boundary_manifest,
    validate_boundary,
    write_manifest,
)

model_root = ROOT / "models"
manifest = build_boundary_manifest(model_root)
valid, issues = validate_boundary(manifest)

# Existing production path must remain present; no relationship-aware artifact
# is treated as production-approved by this phase.
production_files = [
    ROOT / "analytics" / "production_service.py",
    ROOT / "analytics" / "production_hierarchical_prediction.py",
]
production_path_present = all(p.is_file() for p in production_files)

payload = {
    "version": C20_VERSION,
    "status": "VALID" if valid and production_path_present else "INVALID",
    "production_path_present": production_path_present,
    "boundary_valid": valid,
    "issues": issues,
    "artifact_count": manifest["artifact_count"],
    "experimental_approved_count": sum(
        1 for a in manifest["artifacts"]
        if a["experimental"] and a["approved"]
    ),
}

out = ROOT / "reports" / "production_artifact_boundary.json"
identity = write_manifest({**manifest, **payload}, out)
saved = json.loads(out.read_text(encoding="utf-8"))
saved["identity"] = identity
out.write_text(json.dumps(saved, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(saved, indent=2, sort_keys=True))
