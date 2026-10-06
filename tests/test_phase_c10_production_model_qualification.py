import pytest

from analytics.historical_feature_dataset import build_historical_feature_dataset
from analytics.model_stability import build_model_stability_report
from analytics.production_model_qualification import (
    EXPECTED_TARGET_CHAMPIONS,
    QUALIFICATION_VERSION,
    QUALIFIED,
    VALID,
    build_production_model_qualification,
    validate_production_model_qualification,
)
from analytics.temporal_backtesting import build_temporal_split
from database.engine import SessionLocal


@pytest.fixture(scope="module")
def c10_report():
    db = SessionLocal()
    try:
        dataset = build_historical_feature_dataset(db, 1)
    finally:
        db.close()
    split = build_temporal_split(dataset)
    stability = build_model_stability_report(dataset, split)
    return build_production_model_qualification(dataset, split, stability)


def test_c10_qualification_is_valid(c10_report):
    status, issues = validate_production_model_qualification(c10_report)
    assert QUALIFICATION_VERSION == "C.10.0"
    assert c10_report.status == VALID
    assert c10_report.overall_qualification == QUALIFIED
    assert c10_report.temporal_safe is True
    assert status == VALID
    assert issues == ()


def test_c10_target_champions(c10_report):
    actual = {item.target: item.champion_model for item in c10_report.target_qualifications}
    assert actual == EXPECTED_TARGET_CHAMPIONS
    assert all(item.qualification == QUALIFIED for item in c10_report.target_qualifications)


def test_c10_production_safeguards(c10_report):
    assert c10_report.jodi_first_open_dependency is True
    assert "JODI_FIRST" in c10_report.production_hierarchy
    assert "PANEL_FAMILY" in c10_report.production_hierarchy
    assert "FAMILY_CONSTRAINED_PANEL" in c10_report.production_hierarchy
    assert "STRICT_TEMPORAL_TRAINING" in c10_report.safeguards
    assert "EXACT_MATCH_EVALUATION" in c10_report.safeguards
    assert "NO_GUARANTEED_OUTCOME_CLAIM" in c10_report.safeguards
