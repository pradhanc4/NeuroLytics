from __future__ import annotations

import json
from pathlib import Path
import sys
import joblib

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analytics.unified_relationship_aware_features import UnifiedRelationshipAwareFeatureBuilder
from analytics.c17_feature_schema_validator import validate_feature_schema, write_report


SOURCE = ROOT / "data" / "RawData.xlsx"
REPORT = ROOT / "reports" / "c17_feature_schema_validation.json"

df = pd.read_excel(SOURCE, sheet_name="Open Jodi Close")
rows = []
for _, r in df.iterrows():
    rows.append({
        "date": str(r["Date"])[:10],
        "open": int(r["Open"]),
        "jodi": int(r["Jodi"]),
        "close": int(r["Close"]),
    })

built = UnifiedRelationshipAwareFeatureBuilder(rows).build()
stage1 = [x.features for x in built if x.stage == "stage1_jodi"]
stage2 = [x.features for x in built if x.stage == "stage2_close"]

v1 = validate_feature_schema(
    stage1,
    forbidden_tokens=("current_jodi", "current_close", "target_jodi", "target_close"),
)
v2 = validate_feature_schema(
    stage2,
    forbidden_tokens=("target_jodi", "target_close", "current_close"),
)

artifact_checks = {}
stage1_schema_size = v1.feature_count
stage2_schema_size = v2.feature_count
for stage_name, schema_size in (("stage1", stage1_schema_size), ("stage2", stage2_schema_size)):
    for p in sorted((ROOT / "models" / "relationship_aware" / stage_name).glob("*.joblib")):
        model = joblib.load(p)
        artifact_checks[str(p.relative_to(ROOT))] = {
            "nonempty": p.stat().st_size > 0,
            "n_features_in": int(getattr(model, "n_features_in_", -1)),
            "schema_compatible": int(getattr(model, "n_features_in_", -1)) == schema_size,
        }

status = "VALID" if (
    v1.status == "VALID"
    and v2.status == "VALID"
    and all(x["nonempty"] and x["schema_compatible"] for x in artifact_checks.values())
) else "INVALID"
payload = {
    "version": "C.17.0",
    "status": status,
    "temporal_safe": v1.temporal_safe and v2.temporal_safe,
    "input_rows": len(rows),
    "stage1_rows": len(stage1),
    "stage2_rows": len(stage2),
    "stage1": v1.__dict__,
    "stage2": v2.__dict__,
    "artifact_checks": artifact_checks,
}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
