import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text
from analytics.unified_relationship_aware_features import UnifiedRelationshipAwareFeatureBuilder
from analytics.hierarchical_feature_contract import HierarchicalFeatureContract

engine = create_engine("sqlite:///database/neurolytics.db")
with engine.connect() as conn:
    raw = conn.execute(text(
        "SELECT result_date, open_result, jodi_result, close_result "
        "FROM historical_results ORDER BY result_date"
    )).mappings().all()

rows = [
    {"date": str(x["result_date"]), "open": int(x["open_result"]),
     "jodi": int(x["jodi_result"]), "close": int(x["close_result"])}
    for x in raw
]
built = UnifiedRelationshipAwareFeatureBuilder(rows).build()
s1 = [x.features for x in built if x.stage == "stage1_jodi"]
s2 = [x.features for x in built if x.stage == "stage2_close"]
q = HierarchicalFeatureContract(s1, s2).validate()

out = {
    "version": "C.15.0",
    "status": q.status,
    "input_rows": len(rows),
    "stage1_rows": len(s1),
    "stage2_rows": len(s2),
    "stage1_feature_count": q.stage1_feature_count,
    "stage2_feature_count": q.stage2_feature_count,
    "stage1_missing": list(q.stage1_missing),
    "stage2_missing": list(q.stage2_missing),
    "temporal_safe": q.temporal_safe,
    "deterministic": q.deterministic,
    "identity": q.identity,
}
with open("reports/hierarchical_feature_contract.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
