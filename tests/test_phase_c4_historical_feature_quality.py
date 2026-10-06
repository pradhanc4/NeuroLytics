from analytics.historical_feature_dataset import build_historical_feature_dataset
from analytics.historical_feature_quality import (
    QUALITY_VERSION,
    VALID,
    evaluate_feature_quality,
    validate_feature_quality_report,
)
from database.engine import SessionLocal


def _dataset():
    db = SessionLocal()
    try:
        return build_historical_feature_dataset(db, 1)
    finally:
        db.close()


def test_c4_real_dataset_quality_is_valid():
    report = evaluate_feature_quality(_dataset())
    status, issues = validate_feature_quality_report(report)
    assert QUALITY_VERSION == "C.4.0"
    assert report.status == VALID
    assert status == VALID
    assert issues == ()
    assert report.record_count == 1990
    assert report.feature_count == 74
    assert report.target_count == 5
    assert report.missing_value_count == 0
    assert report.non_finite_value_count == 0
    assert report.duplicate_date_count == 0
    assert report.chronological_violations == 0
    assert report.future_history_violations == 0
    assert report.target_leakage_count == 0
    assert report.temporal_safe is True


def test_c4_feature_statistics_cover_all_features():
    report = evaluate_feature_quality(_dataset())
    assert len(report.feature_minimums) == 74
    assert len(report.feature_maximums) == 74
    assert len(report.feature_means) == 74
    assert all(name for name, _ in report.feature_means)


def test_c4_report_identity_is_deterministic():
    first = evaluate_feature_quality(_dataset())
    second = evaluate_feature_quality(_dataset())
    assert first.report_identity == second.report_identity
