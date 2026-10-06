from analytics.relationship_aware_model_training import C16_VERSION, train_relationship_aware_models


def _rows(n=40):
    rows = []
    for i in range(n):
        rows.append({
            "date": f"2026-01-{i+1:02d}",
            "open_1": i % 10,
            "open_2": (i + 1) % 10,
            "open_3": (i + 2) % 10,
            "rel_open_1_to_jodi_first": 0.1 + (i % 3) * 0.1,
            "rel_open_2_to_jodi_second": 0.2,
            "lag1_open_1": (i - 1) % 10,
            "known_jodi_first": i % 10,
            "known_jodi_second": (i + 2) % 10,
            "jodi": (i % 10) * 10 + ((i + 1) % 10),
            "close": ((i + 1) % 10) * 100 + ((i + 2) % 10) * 10 + ((i + 3) % 10),
        })
    return rows


def test_training_contract():
    r = train_relationship_aware_models(_rows())
    assert C16_VERSION == "C.16.0"
    assert r["status"] == "VALID"
    assert set(r["targets"]) == {
        "jodi_first", "jodi_second", "close_first", "close_second", "close_third"
    }
    assert r["temporal_safe"] is True


def test_models_are_champion_mapped():
    r = train_relationship_aware_models(_rows())
    assert r["targets"]["jodi_first"]["model"] == "decision_tree"
    assert r["targets"]["close_third"]["model"] == "random_forest"
