from analytics.hierarchical_feature_contract import (
    C15_VERSION,
    HierarchicalFeatureContract,
)


def rows():
    base = {
        "open_1":1.0,"open_2":2.0,"open_3":3.0,"prior_count":1.0,
        "day_of_week":1.0,"day_of_month":2.0,"month":1.0,"quarter":1.0,"year":2026.0,
        "lag1_open_1":1.0,"lag1_open_2":2.0,"lag1_open_3":3.0,
        "lag1_jodi_1":4.0,"lag1_jodi_2":5.0,
        "lag1_close_1":6.0,"lag1_close_2":7.0,"lag1_close_3":8.0,
    }
    s2 = dict(base, known_jodi_first=4.0, known_jodi_second=5.0)
    return [base], [s2]


def test_contract_valid():
    s1, s2 = rows()
    r = HierarchicalFeatureContract(s1, s2).validate()
    assert C15_VERSION == "C.15.0"
    assert r.status == "VALID"
    assert r.temporal_safe is True


def test_missing_stage2_context_invalid():
    s1, _ = rows()
    r = HierarchicalFeatureContract(s1, s1).validate()
    assert r.status == "INVALID"
    assert "known_jodi_first" in r.stage2_missing


def test_identity_is_deterministic():
    s1, s2 = rows()
    a = HierarchicalFeatureContract(s1, s2).validate()
    b = HierarchicalFeatureContract(s1, s2).validate()
    assert a.identity == b.identity
    assert len(a.identity) == 64
