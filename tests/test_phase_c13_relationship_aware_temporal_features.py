from datetime import date
from analytics.relationship_aware_temporal_features import (
    C13_VERSION,
    RelationshipAwareTemporalFeatureBuilder,
)


def rows():
    return [
        {"date":"2021-01-01","open":123,"jodi":45,"close":678},
        {"date":"2021-01-02","open":124,"jodi":46,"close":679},
        {"date":"2021-01-03","open":125,"jodi":56,"close":689},
    ]


def test_version_and_two_stage_rows():
    result = RelationshipAwareTemporalFeatureBuilder(rows()).build()
    assert C13_VERSION == "C.13.0"
    assert len(result) == 6
    assert [x.stage for x in result] == [
        "stage1_jodi","stage2_close","stage1_jodi","stage2_close",
        "stage1_jodi","stage2_close"
    ]


def test_first_row_has_no_prior_relationship_signal():
    first = RelationshipAwareTemporalFeatureBuilder(rows()).build()[0]
    assert first.features["prior_count"] == 0
    assert all(v == 0.0 for k,v in first.features.items() if k.startswith("rel_"))


def test_point_in_time_relationships():
    result = RelationshipAwareTemporalFeatureBuilder(rows()).build()
    second = result[2]
    assert second.features["prior_count"] == 1
    assert second.features["rel_open1_d1_to_jodi1_d4"] == 1.0
    assert second.features["rel_open1_d1_to_close1_d6"] == 1.0


def test_stage2_uses_known_jodi_first_only():
    stage2 = RelationshipAwareTemporalFeatureBuilder(rows()).build()[3]
    assert stage2.features["known_jodi_first"] == 4.0
    assert "rel_jodi_first_d4_to_close_d6" in stage2.features


def test_deterministic_identity():
    b = RelationshipAwareTemporalFeatureBuilder(rows())
    a = b.build()
    assert b.identity(a) == b.identity(a)
    assert len(b.identity(a)) == 64
