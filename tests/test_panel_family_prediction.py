from datetime import date

from analytics.panel_family_prediction import (
    PANEL_FAMILY_CONSTRAINED_VERSION,
    family_constrained_panel_candidates,
    rank_family_constrained_panels,
)


def candidates(weights):
    base = (1.0 - sum(weights.values())) / (10 - len(weights))
    probabilities = {d: weights.get(d, base) for d in range(10)}
    return [
        {"digit": d, "probability": probabilities[d], "rank": rank}
        for rank, d in enumerate(
            sorted(range(10), key=lambda d: (-probabilities[d], d)),
            start=1,
        )
    ]


def test_version():
    assert PANEL_FAMILY_CONSTRAINED_VERSION == "43.2.0"


def test_family_6_has_exactly_22_candidates():
    result = family_constrained_panel_candidates("6", jodi_family_id="14")
    assert len(result) == 22
    assert all(item.panel_family_id == "6" for item in result)
    assert all(item.jodi_family_id == "14" for item in result)


def test_family_4_has_exactly_22_candidates():
    result = family_constrained_panel_candidates("4", jodi_family_id="14")
    assert len(result) == 22
    assert all(item.panel_family_id == "4" for item in result)


def test_64_panel_ranking_never_crosses_family_boundary():
    result = rank_family_constrained_panels(
        jodi="64",
        first_candidates=candidates({1: 0.8}),
        second_candidates=candidates({4: 0.8}),
        third_candidates=candidates({0: 0.8}),
        target_date=date(2026, 10, 4),
        group_id="b3-64",
        jodi_family_id="14",
        top_k=10,
    )
    first = result["digits"]["first"]
    second = result["digits"]["second"]
    assert first["digit"] == "6"
    assert first["panel_family_id"] == "6"
    assert first["candidate_count"] == 22
    assert all(item.panel_family_id == "6" for item in first["candidates"])
    assert second["digit"] == "4"
    assert second["panel_family_id"] == "4"
    assert second["candidate_count"] == 22
    assert all(item.panel_family_id == "4" for item in second["candidates"])


def test_only_operational_top_k_allowed():
    try:
        rank_family_constrained_panels(
            jodi="64",
            first_candidates=candidates({6: 0.8}),
            second_candidates=candidates({4: 0.8}),
            third_candidates=candidates({0: 0.8}),
            target_date=date(2026, 10, 4),
            group_id="bad",
            top_k=4,
        )
    except ValueError as exc:
        assert "operational top_k" in str(exc)
    else:
        raise AssertionError("top_k=4 must be rejected")


def test_panel_type_filter_is_preserved():
    result = family_constrained_panel_candidates("6", panel_types=("triple",))
    assert len(result) == 1
    assert result[0].panel == "222"
