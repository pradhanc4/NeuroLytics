import pytest

from database.jodi_relationship import (
    analyze_jodi_relationship,
)


def test_same_jodi_relationship():
    result = analyze_jodi_relationship(
        "05",
        "05",
    )

    assert result["jodi_a"] == "05"
    assert result["jodi_b"] == "05"
    assert result["same_jodi"] is True
    assert result["reversed_jodi"] is False
    assert result["same_first_digit"] is True
    assert result["same_second_digit"] is True
    assert result["digit_differences"] == [0, 0]
    assert result["total_digit_difference"] == 0
    assert result["same_digit_sum"] is True


def test_reversed_jodi_relationship():
    result = analyze_jodi_relationship(
        "05",
        "50",
    )

    assert result["same_jodi"] is False
    assert result["reversed_jodi"] is True
    assert result["same_first_digit"] is False
    assert result["same_second_digit"] is False


def test_same_first_digit_relationship():
    result = analyze_jodi_relationship(
        "12",
        "15",
    )

    assert result["same_first_digit"] is True
    assert result["same_second_digit"] is False
    assert result["digit_differences"] == [0, 3]
    assert result["total_digit_difference"] == 3


def test_same_second_digit_relationship():
    result = analyze_jodi_relationship(
        "12",
        "52",
    )

    assert result["same_first_digit"] is False
    assert result["same_second_digit"] is True
    assert result["digit_differences"] == [4, 0]
    assert result["total_digit_difference"] == 4


def test_same_digit_sum_relationship():
    result = analyze_jodi_relationship(
        "05",
        "14",
    )

    assert result["digit_sum_a"] == 5
    assert result["digit_sum_b"] == 5
    assert result["same_digit_sum"] is True


def test_different_digit_sum_relationship():
    result = analyze_jodi_relationship(
        "12",
        "45",
    )

    assert result["digit_sum_a"] == 3
    assert result["digit_sum_b"] == 9
    assert result["same_digit_sum"] is False


def test_leading_zero_is_preserved():
    result = analyze_jodi_relationship(
        "05",
        "06",
    )

    assert result["jodi_a"] == "05"
    assert result["jodi_b"] == "06"


def test_invalid_first_jodi_is_rejected():
    with pytest.raises(
        ValueError,
        match="Jodi must contain exactly 2 digits",
    ):
        analyze_jodi_relationship(
            "5",
            "05",
        )


def test_invalid_second_jodi_is_rejected():
    with pytest.raises(
        ValueError,
        match="Jodi must contain exactly 2 digits",
    ):
        analyze_jodi_relationship(
            "05",
            "5",
        )


def test_non_numeric_jodi_is_rejected():
    with pytest.raises(
        ValueError,
        match="Jodi must contain digits only",
    ):
        analyze_jodi_relationship(
            "A5",
            "05",
        )