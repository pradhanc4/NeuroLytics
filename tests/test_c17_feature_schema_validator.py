from analytics.c17_feature_schema_validator import validate_feature_schema
from analytics.unified_relationship_aware_features import UnifiedRelationshipAwareFeatureBuilder


def sample_rows():
    return [
        {"date": "2026-01-01", "open": 123, "jodi": 45, "close": 678},
        {"date": "2026-01-02", "open": 456, "jodi": 67, "close": 890},
    ]


def test_stage1_relationship_features_are_target_independent():
    built = UnifiedRelationshipAwareFeatureBuilder(sample_rows()).build()
    stage1 = [x.features for x in built if x.stage == "stage1_jodi"]
    assert len(stage1) == 2
    assert not any("current_jodi" in k or "target_jodi" in k for k in stage1[0])


def test_stage2_schema_is_target_safe():
    built = UnifiedRelationshipAwareFeatureBuilder(sample_rows()).build()
    stage2 = [x.features for x in built if x.stage == "stage2_close"]
    result = validate_feature_schema(
        stage2,
        forbidden_tokens=("target_jodi", "target_close", "current_close"),
    )
    assert result.status == "VALID"
    assert result.temporal_safe


def test_schema_detects_missing_features():
    result = validate_feature_schema(
        [{"a": 1.0, "b": 2.0}, {"a": 3.0}],
        expected_features=("a", "b", "c"),
    )
    assert result.status == "INVALID"
    assert result.missing == ("c",)


def test_schema_detects_nonfinite_values():
    result = validate_feature_schema([{"a": float("nan")}])
    assert result.status == "INVALID"
    assert "a" in result.nonfinite
