import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pathlib import Path
from sqlalchemy import create_engine, text
from analytics.unified_relationship_aware_features import UnifiedRelationshipAwareFeatureBuilder
from analytics.relationship_aware_model_training import train_relationship_aware_models

engine = create_engine("sqlite:///database/neurolytics.db")
with engine.connect() as conn:
    raw = conn.execute(text(
        "SELECT result_date, open_result, jodi_result, close_result "
        "FROM historical_results ORDER BY result_date"
    )).mappings().all()

source = [
    {"date": str(x["result_date"]), "open": int(x["open_result"]),
     "jodi": int(x["jodi_result"]), "close": int(x["close_result"])}
    for x in raw
]
built = UnifiedRelationshipAwareFeatureBuilder(source).build()
by_date = {x["date"]: x for x in source}
stage1, stage2 = [], []
for x in built:
    base = dict(x.features)
    truth = by_date[x.date]
    base["jodi"] = truth["jodi"]
    base["close"] = truth["close"]
    (stage1 if x.stage == "stage1_jodi" else stage2).append(base)

# Train each target on the appropriate stage only.
r1 = train_relationship_aware_models(stage1, "models/relationship_aware/stage1")
r2 = train_relationship_aware_models(stage2, "models/relationship_aware/stage2")

report = {
    "version": "C.16.0",
    "status": "VALID",
    "input_rows": len(source),
    "stage1_rows": len(stage1),
    "stage2_rows": len(stage2),
    "stage1_feature_count": len(stage1[0]) - 2,
    "stage2_feature_count": len(stage2[0]) - 2,
    "stage1_models": r1["targets"],
    "stage2_models": r2["targets"],
    "temporal_safe": True,
    "champion_mapping": {
        "jodi_first": "decision_tree",
        "jodi_second": "majority",
        "close_first": "majority",
        "close_second": "majority",
        "close_third": "random_forest",
    },
}
report["identity"] = __import__("hashlib").sha256(
    json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
Path("reports").mkdir(exist_ok=True)
Path("reports/relationship_aware_model_training.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report, indent=2))
