from datetime import date

from analytics.jodi_ranking import (
    OPERATIONAL_TOP_K,
    build_authoritative_jodi_candidates,
    jodi_top_k_views,
    panel_candidates_for_jodi,
    rank_jodis_from_b1_outputs,
    validate_jodi_family_constraint,
)


def digit_candidates(weighted):
    remaining = [digit for digit in range(10) if digit not in weighted]
    base = (1.0 - sum(weighted.values())) / len(remaining)
    probabilities = {digit: weighted.get(digit, base) for digit in range(10)}
    return [
        {
            "digit": digit,
            "probability": probabilities[digit],
            "rank": rank,
        }
        for rank, digit in enumerate(
            sorted(range(10), key=lambda d: (-probabilities[d], d)),
            start=1,
        )
    ]


def test_authoritative_universe_contains_all_100_jodis():
    candidates = build_authoritative_jodi_candidates()
    assert len(candidates) == 100
    assert {item.jodi for item in candidates} == {
        f"{value:02d}" for value in range(100)
    }


def test_authoritative_family_mapping_for_64():
    item = next(
        item for item in build_authoritative_jodi_candidates()
        if item.jodi == "64"
    )
    assert item.jodi_family_id == "14"
    assert item.first_panel_family_id == "6"
    assert item.second_panel_family_id == "4"


def test_b1_outputs_rank_joint_jodi_64_first():
    first = digit_candidates({6: 0.50, 4: 0.20})
    second = digit_candidates({4: 0.50, 6: 0.20})
    ranking = rank_jodis_from_b1_outputs(
        first,
        second,
        group_id="b2-test",
        target_date=date(2026, 10, 4),
        top_k=10,
    )
    assert ranking.candidates[0].jodi == "64"
    assert ranking.candidates[0].jodi_family_id == "14"
    assert ranking.candidates[0].first_panel_family_id == "6"
    assert ranking.candidates[0].second_panel_family_id == "4"


def test_operational_top_k_views_are_1_2_3_5_10():
    first = digit_candidates({6: 0.50, 4: 0.20})
    second = digit_candidates({4: 0.50, 6: 0.20})
    ranking = rank_jodis_from_b1_outputs(
        first,
        second,
        group_id="views",
        target_date=date(2026, 10, 4),
        top_k=10,
    )
    views = jodi_top_k_views(ranking)
    assert tuple(views) == OPERATIONAL_TOP_K
    assert len(views[1]) == 1
    assert len(views[2]) == 2
    assert len(views[3]) == 3
    assert len(views[5]) == 5
    assert len(views[10]) == 10


def test_family_constraint_passes_for_ranked_candidates():
    first = digit_candidates({6: 0.50, 4: 0.20})
    second = digit_candidates({4: 0.50, 6: 0.20})
    ranking = rank_jodis_from_b1_outputs(
        first,
        second,
        group_id="constraint",
        target_date=date(2026, 10, 4),
        top_k=10,
    )
    result = validate_jodi_family_constraint(ranking)
    assert result.is_valid
    assert result.issues == ()


def test_family_constraint_detects_tampering():
    first = digit_candidates({6: 0.50, 4: 0.20})
    second = digit_candidates({4: 0.50, 6: 0.20})
    ranking = rank_jodis_from_b1_outputs(
        first,
        second,
        group_id="tamper",
        target_date=date(2026, 10, 4),
        top_k=10,
    )
    candidate = ranking.candidates[0]
    tampered = type(candidate)(
        candidate.jodi,
        candidate.probability,
        candidate.score,
        candidate.rank,
        candidate.jodi_family_id,
        candidate.panel_family_id,
        "9",
        candidate.second_panel_family_id,
    )
    bad = type(ranking)(
        ranking.group_id,
        ranking.target_date,
        ranking.target_position,
        (tampered,) + ranking.candidates[1:],
        ranking.actual_jodi,
        ranking.top_probability,
        ranking.probability_margin,
        ranking.ranking_identity,
    )
    result = validate_jodi_family_constraint(bad)
    assert not result.is_valid
    assert any(issue.startswith("FIRST_PANEL_FAMILY_MISMATCH:64") for issue in result.issues)


def test_panel_candidates_for_64_are_hard_family_constrained():
    result = panel_candidates_for_jodi("64")
    assert result["jodi_family_id"] == "14"
    first = result["first_digit"]
    second = result["second_digit"]
    assert first["panel_family_id"] == "6"
    assert second["panel_family_id"] == "4"
    assert len(first["panels"]) == 22
    assert len(second["panels"]) == 22
    assert result["hard_constraint"] is True


def test_non_operational_top_k_rejected():
    first = digit_candidates({6: 0.50, 4: 0.20})
    second = digit_candidates({4: 0.50, 6: 0.20})
    try:
        rank_jodis_from_b1_outputs(
            first,
            second,
            group_id="bad-k",
            target_date=date(2026, 10, 4),
            top_k=4,
        )
    except ValueError as exc:
        assert "operational top_k" in str(exc)
    else:
        raise AssertionError("top_k=4 must be rejected")
