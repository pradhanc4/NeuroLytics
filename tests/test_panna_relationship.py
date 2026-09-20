import pytest

from database.panna_relationship import (
    analyze_panna_structure,
)


def test_analyze_standard_panna():
    result = analyze_panna_structure("123")

    assert result["panna"] == "123"
    assert result["digits"] == [1, 2, 3]
    assert result["sorted_digits"] == [1, 2, 3]
    assert result["unique_digits"] == [1, 2, 3]
    assert result["unique_digit_count"] == 3
    assert result["repeated_digit_count"] == 0
    assert result["has_repeated_digit"] is False


def test_analyze_repeated_digit_panna():
    result = analyze_panna_structure("112")

    assert result["panna"] == "112"
    assert result["digits"] == [1, 1, 2]
    assert result["sorted_digits"] == [1, 1, 2]
    assert result["unique_digits"] == [1, 2]
    assert result["unique_digit_count"] == 2
    assert result["repeated_digit_count"] == 1
    assert result["has_repeated_digit"] is True


def test_analyze_all_same_digit_panna():
    result = analyze_panna_structure("111")

    assert result["panna"] == "111"
    assert result["digits"] == [1, 1, 1]
    assert result["sorted_digits"] == [1, 1, 1]
    assert result["unique_digits"] == [1]
    assert result["unique_digit_count"] == 1
    assert result["repeated_digit_count"] == 2
    assert result["has_repeated_digit"] is True


def test_leading_zero_is_preserved():
    result = analyze_panna_structure("005")

    assert result["panna"] == "005"
    assert result["digits"] == [0, 0, 5]
    assert result["sorted_digits"] == [0, 0, 5]
    assert result["unique_digits"] == [0, 5]
    assert result["unique_digit_count"] == 2
    assert result["repeated_digit_count"] == 1
    assert result["has_repeated_digit"] is True


def test_digits_are_kept_in_original_order():
    result = analyze_panna_structure("321")

    assert result["digits"] == [3, 2, 1]
    assert result["sorted_digits"] == [1, 2, 3]


def test_empty_panna_is_rejected():
    with pytest.raises(
        ValueError,
        match="Panna is required",
    ):
        analyze_panna_structure("")


def test_non_numeric_panna_is_rejected():
    with pytest.raises(
        ValueError,
        match="Panna must contain digits only",
    ):
        analyze_panna_structure("12A")


def test_invalid_length_is_rejected():
    with pytest.raises(
        ValueError,
        match="Panna must contain exactly 3 digits",
    ):
        analyze_panna_structure("12")