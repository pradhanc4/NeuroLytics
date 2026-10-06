from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analytics.unified_relationship_aware_features import UnifiedRelationshipAwareFeatureBuilder
from analytics.model_integrity_reproducibility import build_report

source = ROOT / "data" / "RawData.xlsx"
df = pd.read_excel(source, sheet_name="Open Jodi Close")

rows = [
    {
        "date": str(r["Date"])[:10],
        "open": int(r["Open"]),
        "jodi": int(r["Jodi"]),
        "close": int(r["Close"]),
    }
    for _, r in df.iterrows()
]

built_a = UnifiedRelationshipAwareFeatureBuilder(rows).build()
built_b = UnifiedRelationshipAwareFeatureBuilder(rows).build()

stage1_a = [x.features for x in built_a if x.stage == "stage1_jodi"]
stage2_a = [x.features for x in built_a if x.stage == "stage2_close"]
stage1_b = [x.features for x in built_b if x.stage == "stage1_jodi"]
stage2_b = [x.features for x in built_b if x.stage == "stage2_close"]

report = build_report(
    rows,
    stage1_a,
    stage2_a,
    ROOT / "models" / "relationship_aware",
)

# Explicit deterministic checks over independently generated artifacts.
report["independent_stage1_identity_match"] = (
    [x.features for x in built_a if x.stage == "stage1_jodi"]
    == [x.features for x in built_b if x.stage == "stage1_jodi"]
)
report["independent_stage2_identity_match"] = (
    [x.features for x in built_a if x.stage == "stage2_close"]
    == [x.features for x in built_b if x.stage == "stage2_close"]
)
report["status"] = (
    "VALID"
    if report["status"] == "VALID"
    and report["independent_stage1_identity_match"]
    and report["independent_stage2_identity_match"]
    else "INVALID"
)

out = ROOT / "reports" / "model_integrity_reproducibility.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(report, indent=2, sort_keys=True))
