from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analytics.production_promotion_gate import run_gate, write_report

c17_path = ROOT / "reports" / "c17_feature_schema_validation.json"
c18_path = ROOT / "reports" / "model_integrity_reproducibility.json"

c17 = json.loads(c17_path.read_text(encoding="utf-8"))
c18 = json.loads(c18_path.read_text(encoding="utf-8"))

tests = [
    "tests/test_c17_feature_schema_validator.py",
    "tests/test_c18_model_integrity_reproducibility.py",
    "tests/test_c19_production_promotion_gate.py",
]
cmd = [sys.executable, "-m", "pytest", "-q", *tests]
completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
regression_passed = completed.returncode == 0

production_path_exists = (
    (ROOT / "analytics" / "production_hierarchical_prediction.py").is_file()
    and (ROOT / "analytics" / "production_service.py").is_file()
)

result = run_gate(c17, c18, regression_passed, production_path_exists)

payload = {
    "version": "C.19.0",
    "status": result.status,
    "promotion_allowed": result.promotion_allowed,
    "gates": result.gates,
    "regression_return_code": completed.returncode,
    "regression_output": completed.stdout[-4000:],
    "regression_error": completed.stderr[-2000:],
    "identity": result.identity,
}

out = ROOT / "reports" / "production_promotion_gate.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
