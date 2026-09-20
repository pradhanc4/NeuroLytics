import pytest

from database.panna_validator import (
    PannaValidationError,
    validate_panna,
)


def test_valid_panna():
    assert validate_panna("123") == "123"


def test_panna_preserves_leading_zeros():
    assert validate_panna("005") == "005"


def test_panna_strips_whitespace():
    assert validate_panna(" 123 ") == "123"


def test_none_panna_is_rejected():
    with pytest.raises(
        PannaValidationError,
        match="Panna is required",
    ):
        validate_panna(None)


def test_empty_panna_is_rejected():
    with pytest.raises(
        PannaValidationError,
        match="Panna is required",
    ):
        validate_panna("")


def test_short_panna_is_rejected():
    with pytest.raises(
        PannaValidationError,
        match="exactly 3 digits",
    ):
        validate_panna("12")


def test_long_panna_is_rejected():
    with pytest.raises(
        PannaValidationError,
        match="exactly 3 digits",
    ):
        validate_panna("1234")


def test_non_numeric_panna_is_rejected():
    with pytest.raises(
        PannaValidationError,
        match="digits only",
    ):
        validate_panna("1A3")