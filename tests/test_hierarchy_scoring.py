from datetime import date
from analytics.hierarchy_scoring import build_joint_selection
from analytics.family_master import jodi_family_for as jodi_family
from analytics.jodi_ranking import JodiRankedCandidate, JodiRankingObservation


def _digits():
    return [{"digit": d, "probability": 0.1} for d in range(10)]


def _jodi_ranking():
    candidates = []
    for rank, jodi in enumerate(("64", "12", "35"), 1):
        candidates.append(JodiRankedCandidate(
            jodi=jodi, probability=0.5 / rank, score=50.0 / rank,
            rank=rank, jodi_family_id=jodi_family(jodi), panel_family_id=None,
            first_panel_family_id=jodi[0],
            second_panel_family_id=jodi[1],
        ))
    return JodiRankingObservation(
        group_id="g", target_date=date(2026, 1, 1), target_position="jodi",
        candidates=tuple(candidates), actual_jodi=None,
        top_probability=0.5, probability_margin=0.1,
        ranking_identity="jodi-ranking-test",
    )


def test_joint_selection_is_family_constrained():
    result = build_joint_selection(
        jodi_ranking=_jodi_ranking(),
        first_candidates=_digits(),
        second_candidates=_digits(),
        third_candidates=_digits(),
        target_date=date(2026, 1, 1),
        group_id="b4",
        top_k=5,
    )
    assert result.status == "VALID"
    assert result.selected is not None
    for item in result.candidates:
        assert item.first_panel_family_id == item.jodi[0]
        assert item.second_panel_family_id == item.jodi[1]


def test_operational_views_use_only_supported_top_k():
    result = build_joint_selection(
        jodi_ranking=_jodi_ranking(),
        first_candidates=_digits(),
        second_candidates=_digits(),
        third_candidates=_digits(),
        target_date=date(2026, 1, 1),
        group_id="b4",
        top_k=10,
    )
    from analytics.hierarchy_scoring import operational_views
    views = operational_views(result)
    assert tuple(views) == (1, 2, 3, 5, 10)
    assert len(views[1]) == 1


def test_joint_score_multiplies_three_probabilities():
    result = build_joint_selection(
        jodi_ranking=_jodi_ranking(),
        first_candidates=_digits(),
        second_candidates=_digits(),
        third_candidates=_digits(),
        target_date=date(2026, 1, 1),
        group_id="b4",
        top_k=1,
    )
    assert result.selected is not None
    expected = (
        result.selected.jodi_probability
        * result.selected.first_panel_probability
        * result.selected.second_panel_probability
    )
    assert result.selected.joint_score == expected
