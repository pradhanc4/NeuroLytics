from datetime import date

from database.engine import SessionLocal
from analytics.historical_feature_dataset import (
    FEATURE_VERSION,
    build_historical_feature_dataset,
    validate_historical_feature_dataset,
)


def test_c3_feature_dataset_is_temporally_safe_and_complete():
    db = SessionLocal()
    try:
        dataset = build_historical_feature_dataset(db, 1)
    finally:
        db.close()

    status, issues = validate_historical_feature_dataset(dataset)

    assert FEATURE_VERSION == "C.3.0"
    assert status == "VALID"
    assert issues == ()
    assert dataset.record_count == 1990
    assert dataset.temporal_safe is True
    assert len(dataset.feature_names) == 74
    assert dataset.rows[0].result_date == "2021-02-01"
    assert dataset.rows[0].source_history_end_date is None
    assert dataset.rows[1].source_history_end_date == "2021-02-01"
    assert dataset.rows[-1].result_date == "2026-07-31"
    assert dataset.dataset_identity.startswith("historical-feature-dataset-")


def test_c3_features_do_not_expose_current_jodi_or_close_targets():
    db = SessionLocal()
    try:
        dataset = build_historical_feature_dataset(db, 1)
    finally:
        db.close()

    forbidden = {"jodi_1", "jodi_2", "close_1", "close_2", "close_3"}
    assert forbidden.isdisjoint(dataset.feature_names)
    assert set(dataset.target_names) == {
        "jodi_first",
        "jodi_second",
        "close_first",
        "close_second",
        "close_third",
    }


def test_c3_transition_features_use_completed_history_only():
    db = SessionLocal()
    try:
        dataset = build_historical_feature_dataset(db, 1)
    finally:
        db.close()

    first = dataset.rows[0]
    second = dataset.rows[1]
    third = dataset.rows[2]

    assert first.features["open_change_sum"] == 0
    assert second.features["jodi_change_sum"] == 0
    assert second.features["close_change_sum"] == 0
    assert third.features["open_change_sum"] >= 0
    assert third.features["jodi_change_sum"] >= 0
    assert third.features["close_change_sum"] >= 0


def test_c3_history_end_is_strictly_before_result_date():
    db = SessionLocal()
    try:
        dataset = build_historical_feature_dataset(db, 1)
    finally:
        db.close()

    for row in dataset.rows:
        if row.source_history_end_date is not None:
            assert date.fromisoformat(row.source_history_end_date) < date.fromisoformat(row.result_date)
