from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from analytics.production_hierarchical_prediction import (
    INTEGRATION_VERSION,
    predict_production_hierarchical,
)
from analytics.production_model_qualification import QUALIFIED, VALID


def _qualification(tmp_path: Path) -> Path:
    path = tmp_path / "qualification.json"
    path.write_text(
        json.dumps(
            {
                "status": VALID,
                "overall_qualification": QUALIFIED,
                "temporal_safe": True,
                "report_identity": "production-model-qualification-test",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_version_and_operational_top_k():
    assert INTEGRATION_VERSION == "C.11.0"


def test_production_hierarchical_prediction_uses_jodi_then_families(monkeypatch, tmp_path):
    class Candidate:
        def __init__(self, jodi, probability, rank):
            self.jodi = jodi
            self.probability = probability
            self.rank = rank
            self.jodi_family_id = "14"
            self.first_panel_family_id = jodi[0]
            self.second_panel_family_id = jodi[1]

    class Ranking:
        group_id = "test-group"
        candidates = (
            Candidate("64", 0.6, 1),
            Candidate("63", 0.4, 2),
        )

    monkeypatch.setattr(
        "analytics.production_hierarchical_prediction.predict_jodi_candidates",
        lambda *args, **kwargs: {"ranking": Ranking()},
    )

    class Panel:
        def __init__(self, panel, probability):
            self.panel = panel
            self.probability = probability

    def fake_stage2(open_result, jodi_first, **kwargs):
        return {
            "close_digit_candidates": {
                "first": [{"digit": 7, "probability": 0.7}],
                "second": [{"digit": 8, "probability": 0.8}],
                "third": [{"digit": 9, "probability": 0.9}],
            }
        }

    monkeypatch.setattr(
        "analytics.production_hierarchical_prediction.predict_stage_2",
        fake_stage2,
    )

    def fake_panel(**kwargs):
        jodi = kwargs["jodi"]
        first_panel = {"6": "123", "3": "120"}[jodi[0]]
        second_panel = {"4": "130", "3": "120"}[jodi[1]]
        return {
            "digits": {
                "first": {"ranking": type("R", (), {"candidates": (Panel(first_panel, 0.7),)})()},
                "second": {"ranking": type("R", (), {"candidates": (Panel(second_panel, 0.8),)})()},
            }
        }

    monkeypatch.setattr(
        "analytics.production_hierarchical_prediction.rank_family_constrained_panels",
        fake_panel,
    )

    result = predict_production_hierarchical(
        open_result="123",
        target_date=date(2026, 10, 4),
        market_name="Excel Sequential Market",
        qualification_path=_qualification(tmp_path),
        top_k=2,
    )

    assert result.status == VALID
    assert result.qualification == QUALIFIED
    assert result.selected_jodi == "64"
    assert result.temporal_safe is True
    assert result.family_constraints_enforced is True
    assert result.selected is not None
    assert result.selected.jodi == "64"
    assert result.selected.first_panel_family_id == "6"
    assert result.selected.second_panel_family_id == "4"
    assert result.selected.first_panel == "123"
    assert result.selected.second_panel == "130"


def test_rejects_unqualified_production_artifact(tmp_path):
    path = tmp_path / "qualification.json"
    path.write_text(
        json.dumps(
            {
                "status": "INVALID",
                "overall_qualification": "HOLD",
                "temporal_safe": False,
            }
        ),
        encoding="utf-8",
    )
    try:
        predict_production_hierarchical(
            open_result="123",
            target_date=date(2026, 10, 4),
            qualification_path=path,
        )
    except ValueError as exc:
        assert "not VALID" in str(exc)
    else:
        raise AssertionError("Unqualified artifact must be rejected")
