from pathlib import Path

from analytics.model_integrity_reproducibility import (
    feature_identity,
    validate_temporal_order,
)


def test_temporal_order_and_unique_dates():
    rows = [
        {"date": "2026-01-01"},
        {"date": "2026-01-02"},
    ]
    assert validate_temporal_order(rows)


def test_temporal_order_rejects_duplicate_dates():
    rows = [
        {"date": "2026-01-01"},
        {"date": "2026-01-01"},
    ]
    assert not validate_temporal_order(rows)


def test_feature_identity_is_order_independent():
    a = [{"b": 2.0, "a": 1.0}]
    b = [{"a": 1.0, "b": 2.0}]
    assert feature_identity(a) == feature_identity(b)
