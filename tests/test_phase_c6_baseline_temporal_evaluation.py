import pytest

from analytics.baseline_temporal_evaluation import (
    BASELINE_VERSION,
    VALID,
    TARGET_NAMES,
    evaluate_baselines,
    validate_baseline_report,
)
from analytics.historical_feature_dataset import build_historical_feature_dataset
from analytics.temporal_backtesting import build_temporal_split
from database.engine import SessionLocal


@pytest.fixture(scope="module")
def c6_report():
    db = SessionLocal()
    try:
        dataset = build_historical_feature_dataset(db, 1)
    finally:
        db.close()
    split = build_temporal_split(dataset)
    return evaluate_baselines(dataset, split, model_kind="majority")


def test_c6_baseline_report_is_temporally_valid(c6_report):
    report = c6_report
    status, issues = validate_baseline_report(report)
    assert BASELINE_VERSION == "C.6.0"
    assert report.status == VALID
    assert status == VALID
    assert issues == ()
    assert report.temporal_safe is True
    assert report.record_count == 1990
    assert report.train_count == 1393
    assert report.validation_count == 298
    assert report.test_count == 299
    assert len(report.holdout_results) == 5
    assert len(report.walk_forward_results) == 5


def test_c6_all_targets_have_operational_top_k_metrics(c6_report):
    report = c6_report
    assert tuple(target.target for target in report.holdout_results) == TARGET_NAMES
    for result in report.holdout_results:
        assert 0.0 <= result.validation_top1 <= result.validation_top2 <= 1.0
        assert result.validation_top2 <= result.validation_top3 <= 1.0
        assert result.validation_top3 <= result.validation_top5 <= 1.0
        assert result.validation_top5 <= result.validation_top10 <= 1.0
        assert 0.0 <= result.test_top1 <= result.test_top2 <= 1.0
        assert result.test_top2 <= result.test_top3 <= 1.0
        assert result.test_top3 <= result.test_top5 <= 1.0
        assert result.test_top5 <= result.test_top10 <= 1.0


def test_c6_walk_forward_folds_have_all_targets(c6_report):
    report = c6_report
    for fold in report.walk_forward_results:
        assert fold.test_count > 0
        assert tuple(target.target for target in fold.target_results) == TARGET_NAMES
        assert all(target.test_count == fold.test_count for target in fold.target_results)
