import pytest

from database.panel_relationship import (
    analyze_panel_relationship,
)


def test_same_panel():
    result = analyze_panel_relationship(
        "123",
        "123",
    )

    assert result["same_panel"] is True


def test_reversed_panel():
    result = analyze_panel_relationship(
        "123",
        "321",
    )

    assert result["reversed_panel"] is True


def test_same_first_digit():
    result = analyze_panel_relationship(
        "123",
        "156",
    )

    assert result["same_first_digit"] is True


def test_same_second_digit():
    result = analyze_panel_relationship(
        "123",
        "423",
    )

    assert result["same_second_digit"] is True


def test_same_third_digit():
    result = analyze_panel_relationship(
        "123",
        "453",
    )

    assert result["same_third_digit"] is True


def test_same_digit_sum():
    result = analyze_panel_relationship(
        "123",
        "321",
    )

    assert result["same_digit_sum"] is True


def test_digit_differences():
    result = analyze_panel_relationship(
        "123",
        "105",
    )

    assert result["digit_differences"] == [
        0,
        2,
        2,
    ]


def test_total_digit_difference():
    result = analyze_panel_relationship(
        "123",
        "105",
    )

    assert result[
        "total_digit_difference"
    ] == 4


def test_leading_zero_is_preserved():
    result = analyze_panel_relationship(
        "005",
        "050",
    )

    assert result["panel_a"] == "005"
    assert result["panel_b"] == "050"


def test_invalid_panel_is_rejected():
    with pytest.raises(ValueError):
        analyze_panel_relationship(
            "12",
            "123",
        )