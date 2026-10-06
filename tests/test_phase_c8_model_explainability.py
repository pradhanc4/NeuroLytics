import pytest

from analytics.historical_feature_dataset import build_historical_feature_dataset
from analytics.model_explainability import (
    EXPLAINABILITY_VERSION,
    VALID,
    build_explainability_report,
    validate_explainability_report,
)
from analytics.temporal_backtesting import build_temporal_split
from database.engine import SessionLocal


@pytest.fixture(scope="module")
def c8_report():
    db = SessionLocal()
    try:
        dataset = build_historical_feature_dataset(db, 1)
    finally:
        db.close()
    split = build_temporal_split(dataset)
    return build_explainability_report(dataset, split)


def test_c8_report_is_temporally_safe(c8_report):
    status, issues = validate_explainability_report(c8_report)
    assert EXPLAINABILITY_VERSION == "C.8.0"
    assert c8_report.status == VALID
    assert c8_report.temporal_safe is True
    assert status == VALID
    assert issues == ()
    assert len(c8_report.fold_explanations) == 5


def test_c8_feature_importance_and_paths(c8_report):
    assert c8_report.focus_model == "decision_tree"
    assert c8_report.focus_target == "jodi_first"
    assert len(c8_report.aggregate_features) > 0
    assert len(c8_report.feature_temporal_stability) > 0
    assert len(c8_report.decision_paths) == 5
    assert all(item.decision_path for item in c8_report.decision_paths)
    assert all(0.0 <= item.test_top1 <= item.test_top5 <= item.test_top10 <= 1.0 for item in c8_report.fold_explanations)


def test_c8_per_digit_analysis_is_complete(c8_report):
    assert len(c8_report.digit_performance) == 50
    for item in c8_report.digit_performance:
        assert 0 <= item.digit <= 9
        assert item.support >= 0
        assert 0.0 <= item.top1_rate <= 1.0
        assert 0.0 <= item.top5_rate <= 1.0
