import pytest

from database.jodi_validator import (
    JodiValidationError,
    validate_jodi,
)


def test_valid_jodi():
    assert validate_jodi("12") == "12"


def test_leading_zero_is_preserved():
    assert validate_jodi("05") == "05"


def test_whitespace_is_stripped():
    assert validate_jodi(" 05 ") == "05"


def test_zero_zero_is_valid():
    assert validate_jodi("00") == "00"


def test_none_is_rejected():
    with pytest.raises(
        JodiValidationError,
        match="Jodi is required",
    ):
        validate_jodi(None)


def test_empty_value_is_rejected():
    with pytest.raises(
        JodiValidationError,
        match="Jodi is required",
    ):
        validate_jodi("")


def test_short_jodi_is_rejected():
    with pytest.raises(
        JodiValidationError,
        match="exactly 2 digits",
    ):
        validate_jodi("5")


def test_long_jodi_is_rejected():
    with pytest.raises(
        JodiValidationError,
        match="exactly 2 digits",
    ):
        validate_jodi("123")


def test_nonnumeric_jodi_is_rejected():
    with pytest.raises(
        JodiValidationError,
        match="digits only",
    ):
        validate_jodi("A5")