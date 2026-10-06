from analytics.historical_feature_dataset import build_historical_feature_dataset
from analytics.temporal_backtesting import (
    BACKTEST_VERSION,
    VALID,
    build_temporal_split,
    validate_temporal_split,
)
from database.engine import SessionLocal


def _dataset():
    db = SessionLocal()
    try:
        return build_historical_feature_dataset(db, 1)
    finally:
        db.close()


def test_c5_temporal_split_is_chronological_and_complete():
    split = build_temporal_split(_dataset(), walk_forward_folds=5)
    status, issues = validate_temporal_split(split)
    assert BACKTEST_VERSION == "C.5.0"
    assert status == VALID
    assert issues == ()
    assert split.train_count == 1393
    assert split.validation_count == 298
    assert split.test_count == 299
    assert split.temporal_safe is True
    assert len(split.windows) == 5
    assert split.train_start == "2021-02-01"
    assert split.test_end == "2026-07-31"


def test_c5_walk_forward_windows_do_not_overlap_test_periods():
    split = build_temporal_split(_dataset(), walk_forward_folds=5)
    previous_test_end = None
    for window in split.windows:
        assert window.train_end < window.validation_start <= window.validation_end < window.test_start <= window.test_end
        if previous_test_end is not None:
            assert window.test_start > previous_test_end
        previous_test_end = window.test_end


def test_c5_split_identity_is_deterministic():
    first = build_temporal_split(_dataset())
    second = build_temporal_split(_dataset())
    assert first.split_identity == second.split_identity
