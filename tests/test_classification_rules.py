from types import SimpleNamespace

import pytest

from database.classification_rules import (
    _classify_digit_sum,
    _classify_digit_overlap,
    _classify_jodi,
    _classify_open_close_relationship,
    _classify_order,
    _classify_parity,
    _classify_three_digit_structure,
    _classify_zero,
    classify_historical_result,
)


def make_result(
    open_result: str,
    jodi_result: str,
    close_result: str,
):
    """Create a lightweight historical-result test object."""

    return SimpleNamespace(
        open_result=open_result,
        jodi_result=jodi_result,
        close_result=close_result,
    )


def test_three_digit_structure_unique():
    assert _classify_three_digit_structure("123") == (
        "TRIPLE_UNIQUE"
    )


def test_three_digit_structure_one_pair():
    assert _classify_three_digit_structure("122") == (
        "ONE_PAIR"
    )


def test_three_digit_structure_triple_repeat():
    assert _classify_three_digit_structure("111") == (
        "TRIPLE_REPEAT"
    )


def test_zero_classification():
    assert _classify_zero("123") == "NO_ZERO"
    assert _classify_zero("105") == "HAS_ZERO"


def test_digit_sum_classification():
    assert _classify_digit_sum("123") == "LOW_SUM"
    assert _classify_digit_sum("111") == "LOW_SUM"
    assert _classify_digit_sum("666") == "MEDIUM_SUM"
    assert _classify_digit_sum("999") == "HIGH_SUM"


def test_parity_classification():
    assert _classify_parity("123") == "OEO"
    assert _classify_parity("246") == "EEE"
    assert _classify_parity("135") == "OOO"


def test_order_classification():
    assert _classify_order("123") == "ASCENDING"
    assert _classify_order("321") == "DESCENDING"
    assert _classify_order("132") == "MIXED"


def test_jodi_classification():
    assert _classify_jodi("11") == (
        "DOUBLE|SAME_DIGIT|OO"
    )

    assert _classify_jodi("45") == (
        "NON_DOUBLE|DIFFERENT_DIGIT|EO"
    )


def test_open_close_same():
    assert _classify_open_close_relationship(
        "123",
        "123",
    ) == "SAME"


def test_open_close_reversed():
    assert _classify_open_close_relationship(
        "123",
        "321",
    ) == "REVERSED"


def test_open_close_partial_match():
    assert _classify_open_close_relationship(
        "123",
        "145",
    ) == "PARTIAL_MATCH"


def test_open_close_no_match():
    assert _classify_open_close_relationship(
        "123",
        "456",
    ) == "NO_POSITIONAL_MATCH"


def test_digit_overlap():
    assert _classify_digit_overlap(
        "123",
        "345",
    ) == "1_MATCH"

    assert _classify_digit_overlap(
        "123",
        "456",
    ) == "0_MATCH"


def test_complete_historical_classification():
    result = make_result(
        open_result="123",
        jodi_result="45",
        close_result="321",
    )

    classification = classify_historical_result(
        historical_result=result,
        classification_version="v1",
    )

    assert classification == {
        "classification_version": "v1",
        "open_class": (
            "TRIPLE_UNIQUE|NO_ZERO|LOW_SUM|OEO|ASCENDING"
        ),
        "jodi_class": (
            "NON_DOUBLE|DIFFERENT_DIGIT|EO"
        ),
        "close_class": (
            "TRIPLE_UNIQUE|NO_ZERO|LOW_SUM|OEO|DESCENDING"
        ),
        "overall_class": (
            "REVERSED|3_MATCH"
        ),
    }


def test_classification_requires_result():
    with pytest.raises(
        ValueError,
        match="Historical result is required",
    ):
        classify_historical_result(None)


def test_classification_requires_version():
    result = make_result(
        open_result="123",
        jodi_result="45",
        close_result="678",
    )

    with pytest.raises(
        ValueError,
        match="Classification version is required",
    ):
        classify_historical_result(
            historical_result=result,
            classification_version="",
        )