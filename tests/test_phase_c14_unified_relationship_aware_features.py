from analytics.unified_relationship_aware_features import (
    C14_VERSION,
    UnifiedRelationshipAwareFeatureBuilder,
)


def sample():
    return [
        {"date":"2021-01-01","open":123,"jodi":45,"close":678},
        {"date":"2021-01-02","open":124,"jodi":46,"close":679},
        {"date":"2021-01-03","open":125,"jodi":56,"close":689},
    ]


def test_version_and_two_contexts():
    rows = UnifiedRelationshipAwareFeatureBuilder(sample()).build()
    assert C14_VERSION == "C.14.0"
    assert len(rows) == 6
    assert rows[0].stage == "stage1_jodi"
    assert rows[1].stage == "stage2_close"


def test_point_in_time_first_row_has_no_relationship_history():
    row = UnifiedRelationshipAwareFeatureBuilder(sample()).build()[0]
    assert row.features["prior_count"] == 0
    assert row.features["rel_open1_d1_to_jodi1_d4"] == 0.0


def test_second_row_uses_only_first_row_history():
    row = UnifiedRelationshipAwareFeatureBuilder(sample()).build()[2]
    assert row.features["prior_count"] == 1
    assert row.features["rel_open1_d1_to_jodi1_d4"] == 1.0


def test_stage2_known_jodi_context():
    row = UnifiedRelationshipAwareFeatureBuilder(sample()).build()[3]
    assert row.features["known_jodi_first"] == 4.0
    assert row.features["known_jodi_second"] == 6.0


def test_deterministic_identity():
    b = UnifiedRelationshipAwareFeatureBuilder(sample())
    rows = b.build()
    assert len(b.identity(rows)) == 64
    assert b.identity(rows) == b.identity(rows)
