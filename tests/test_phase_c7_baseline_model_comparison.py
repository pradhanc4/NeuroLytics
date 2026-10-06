import pytest

from analytics.baseline_model_comparison import (
    COMPARISON_VERSION, MODEL_NAMES, TARGET_NAMES, VALID,
    compare_baselines, validate_comparison_report,
)
from analytics.historical_feature_dataset import build_historical_feature_dataset
from analytics.temporal_backtesting import build_temporal_split
from database.engine import SessionLocal


@pytest.fixture(scope="module")
def c7_report():
    db = SessionLocal()
    try:
        dataset = build_historical_feature_dataset(db, 1)
    finally:
        db.close()
    split = build_temporal_split(dataset)
    return compare_baselines(dataset, split)


def test_c7_report_structure_and_temporal_safety(c7_report):
    status, issues = validate_comparison_report(c7_report)
    assert COMPARISON_VERSION == "C.7.0"
    assert c7_report.status == VALID
    assert status == VALID
    assert issues == ()
    assert c7_report.temporal_safe is True
    assert c7_report.models == MODEL_NAMES
    assert c7_report.targets == TARGET_NAMES
    assert len(c7_report.holdout_results) == 20
    assert len(c7_report.walk_forward_results) == 5


def test_c7_every_model_target_has_benchmark(c7_report):
    for result in c7_report.holdout_results:
        assert 0.0 <= result.test_top1 <= result.test_top5 <= result.test_top10 <= 1.0
        assert result.test_log_loss >= 0.0
    for fold in c7_report.walk_forward_results:
        assert len(fold.results) == 20
        assert all(result.test_top1 <= result.test_top5 <= result.test_top10 for result in fold.results)


def test_c7_statistical_summaries_cover_every_pair(c7_report):
    assert len(c7_report.summaries) == 20
    for summary in c7_report.summaries:
        assert summary.model in MODEL_NAMES
        assert summary.target in TARGET_NAMES
        assert summary.folds == 5
        assert 0.0 <= summary.mean_test_top1 <= 1.0
        assert 0.0 <= summary.mean_test_top5 <= 1.0
        assert summary.std_test_top1 >= 0.0
        assert summary.mean_test_log_loss >= 0.0
