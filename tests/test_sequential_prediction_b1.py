from datetime import date, timedelta

from analytics.sequential_prediction import (
    JODI_TOP_K,
    _close_features,
    _jodi_features,
    _targets,
)


class FakeRow:
    def __init__(self, open_result, jodi_result, close_result, market_id=1, row_id=1):
        self.open_result = open_result
        self.jodi_result = jodi_result
        self.close_result = close_result
        self.market_id = market_id
        self.id = row_id
        self.result_date = date(2026, 1, 1) + timedelta(days=row_id)


def test_b1_jodi_features_do_not_use_current_jodi():
    row_a = FakeRow("123", "45", "678", row_id=1)
    row_b = FakeRow("123", "99", "678", row_id=1)

    rows_a = [row_a]
    rows_b = [row_b]

    assert _jodi_features(rows_a, 0) == _jodi_features(rows_b, 0)


def test_b1_jodi_features_use_open_and_prior_history():
    first = FakeRow("123", "45", "678", row_id=1)
    second = FakeRow("456", "78", "901", row_id=2)

    features = _jodi_features([first, second], 1)

    assert len(features) == 28
    assert features[-11:] == [
        4, 5, 6,
        1, 2, 3, 4, 5, 6, 7, 8,
    ]


def test_close_features_use_actual_jodi_first():
    first = FakeRow("123", "45", "678", row_id=1)
    second_a = FakeRow("456", "78", "901", row_id=2)
    second_b = FakeRow("456", "98", "901", row_id=2)

    assert _close_features([first, second_a], 1) != _close_features(
        [first, second_b], 1
    )


def test_targets_contain_both_jodi_digits_before_close_digits():
    row = FakeRow("123", "45", "678")

    assert _targets(row) == [4, 5, 6, 7, 8]


def test_operational_jodi_top_k_is_explicit():
    assert JODI_TOP_K == (1, 2, 3, 5, 10)
