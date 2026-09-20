import pytest

from database.panel_validator import (
    PanelValidationError,
    validate_panel,
)


def test_valid_panel():
    assert validate_panel("123") == "123"


def test_panel_preserves_leading_zero():
    assert validate_panel("005") == "005"


def test_panel_preserves_multiple_leading_zeros():
    assert validate_panel("007") == "007"


def test_panel_with_whitespace_is_normalized():
    assert validate_panel(" 123 ") == "123"


def test_panel_zero_value_is_valid():
    assert validate_panel("000") == "000"


def test_none_panel_is_rejected():
    with pytest.raises(
        PanelValidationError,
        match="Panel is required",
    ):
        validate_panel(None)


def test_empty_panel_is_rejected():
    with pytest.raises(
        PanelValidationError,
        match="Panel is required",
    ):
        validate_panel("")


def test_short_panel_is_rejected():
    with pytest.raises(
        PanelValidationError,
        match="exactly 3 digits",
    ):
        validate_panel("12")


def test_long_panel_is_rejected():
    with pytest.raises(
        PanelValidationError,
        match="exactly 3 digits",
    ):
        validate_panel("1234")


def test_nonnumeric_panel_is_rejected():
    with pytest.raises(
        PanelValidationError,
        match="digits only",
    ):
        validate_panel("12A")