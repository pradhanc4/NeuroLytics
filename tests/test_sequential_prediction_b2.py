from datetime import date

import analytics.sequential_prediction as sp


def _candidates(weighted):
    base = (1.0 - sum(weighted.values())) / (10 - len(weighted))
    probs = {digit: weighted.get(digit, base) for digit in range(10)}
    return [
        {"digit": digit, "probability": probs[digit], "rank": rank}
        for rank, digit in enumerate(
            sorted(range(10), key=lambda d: (-probs[d], d)),
            start=1,
        )
    ]


def test_predict_jodi_candidates_integrates_b1_ranking_and_family_constraint(monkeypatch):
    monkeypatch.setattr(
        sp,
        "predict_jodi_digits",
        lambda *args, **kwargs: {
            "status": "VALID",
            "stage": "JODI_B1",
            "jodi_first_candidates": _candidates({6: 0.50, 4: 0.20}),
            "jodi_second_candidates": _candidates({4: 0.50, 6: 0.20}),
            "model_identities": {"jodi_first": "b1-first"},
        },
    )

    result = sp.predict_jodi_candidates(
        "123",
        target_date=date(2026, 10, 4),
        top_k=10,
        market_name="Excel Sequential Market",
    )

    assert result["stage"] == "JODI_B2"
    assert result["candidates"][0].jodi == "64"
    assert result["candidates"][0].jodi_family_id == "14"
    assert result["family_constraint"]["status"] == "VALID"
    assert result["top_candidate_panel_constraints"]["first_digit"]["panel_family_id"] == "6"
    assert result["top_candidate_panel_constraints"]["second_digit"]["panel_family_id"] == "4"
