import pytest

from analytics.historical_feature_dataset import build_historical_feature_dataset
from analytics.model_stability import (
    STABILITY_VERSION,
    VALID,
    PERTURBATION_MODES,
    build_model_stability_report,
    validate_model_stability_report,
)
from analytics.temporal_backtesting import build_temporal_split
from database.engine import SessionLocal


@pytest.fixture(scope="module")
def c9_report():
    db = SessionLocal()
    try:
        dataset = build_historical_feature_dataset(db, 1)
    finally:
        db.close()
    split = build_temporal_split(dataset)
    return build_model_stability_report(dataset, split)


def test_c9_report_valid_and_temporally_safe(c9_report):
    status, issues = validate_model_stability_report(c9_report)
    assert STABILITY_VERSION == "C.9.0"
    assert c9_report.status == VALID
    assert c9_report.temporal_safe is True
    assert status == VALID
    assert issues == ()
    assert len(c9_report.fold_stability) == 5


def test_c9_robustness_and_sensitivity(c9_report):
    assert len(c9_report.robustness) == 5 * len(PERTURBATION_MODES)
    assert {item.mode for item in c9_report.robustness} == set(PERTURBATION_MODES)
    assert c9_report.feature_sensitivity
    assert {item.feature_group for item in c9_report.feature_sensitivity} >= {"current_open", "lags", "rolling"}
    assert c9_report.conclusion


def test_c9_metrics_are_bounded(c9_report):
    for item in c9_report.robustness:
        assert 0.0 <= item.top1 <= item.top5 <= item.top10 <= 1.0
    for item in c9_report.fold_stability:
        assert 0.0 <= item.top1_min <= item.top1_max <= 1.0
        assert item.top1_range >= 0.0
