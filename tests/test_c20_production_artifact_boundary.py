from pathlib import Path
from analytics.production_artifact_boundary import (
    build_boundary_manifest,
    validate_boundary,
)


def test_experimental_artifacts_are_not_approved(tmp_path):
    root = tmp_path / "models"
    exp = root / "relationship_aware"
    exp.mkdir(parents=True)
    (exp / "stage1.joblib").write_bytes(b"artifact")
    manifest = build_boundary_manifest(root)
    ok, issues = validate_boundary(manifest)
    assert ok
    assert not issues
    assert manifest["artifacts"][0]["experimental"] is True
    assert manifest["artifacts"][0]["approved"] is False


def test_missing_hash_is_rejected():
    ok, issues = validate_boundary({
        "artifacts": [{"path": "models/x.joblib", "approved": False, "experimental": False}]
    })
    assert not ok
    assert "missing hash" in issues[0]


def test_experimental_approval_is_rejected():
    ok, issues = validate_boundary({
        "artifacts": [{
            "path": "models/relationship_aware/x.joblib",
            "approved": True,
            "experimental": True,
            "sha256": "abc",
        }]
    })
    assert not ok
    assert "experimental artifact marked approved" in issues[0]
