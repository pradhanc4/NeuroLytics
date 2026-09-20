from datetime import date

import pytest

from database.data_quality_rules import (
    DataQualityValidationError,
    validate_digit_columns,
    validate_derived_columns,
    validate_historical_record,
    validate_market_id,
    validate_result_components,
    validate_result_date,
)


def valid_columns():
    """Return valid derived columns for 12345678."""

    return {
        "col1": 1,
        "col2": 2,
        "col3": 3,
        "col4": 4,
        "col5": 5,
        "col6": 6,
        "col7": 7,
        "col8": 8,
    }


def zero_columns():
    """Return valid derived columns containing actual zero values."""

    return {
        "col1": 0,
        "col2": 0,
        "col3": 0,
        "col4": 0,
        "col5": 0,
        "col6": 0,
        "col7": 0,
        "col8": 0,
    }


def test_valid_historical_record():
    """A valid historical record should pass all rules."""

    result = validate_historical_record(
        market_id=1,
        result_date=date(2026, 9, 19),
        open_result="123",
        jodi_result="45",
        close_result="678",
        columns=valid_columns(),
    )

    assert result["market_id"] == 1
    assert result["result_date"] == date(2026, 9, 19)
    assert result["open_result"] == "123"
    assert result["jodi_result"] == "45"
    assert result["close_result"] == "678"

    assert result["col1"] == 1
    assert result["col8"] == 8


def test_leading_zero_results_are_valid():
    """Leading zeros must be preserved and accepted."""

    result = validate_historical_record(
        market_id=1,
        result_date=date(2026, 9, 19),
        open_result="005",
        jodi_result="05",
        close_result="007",
        columns={
            "col1": 0,
            "col2": 0,
            "col3": 5,
            "col4": 0,
            "col5": 5,
            "col6": 0,
            "col7": 0,
            "col8": 7,
        },
    )

    assert result["open_result"] == "005"
    assert result["jodi_result"] == "05"
    assert result["close_result"] == "007"

    assert result["col1"] == 0
    assert result["col2"] == 0
    assert result["col3"] == 5
    assert result["col4"] == 0
    assert result["col5"] == 5
    assert result["col6"] == 0
    assert result["col7"] == 0
    assert result["col8"] == 7


def test_actual_zero_digit_values_are_valid():
    """Actual zero digits must not be treated as missing."""

    validate_digit_columns(
        zero_columns()
    )


def test_null_digit_column_is_rejected():
    """NULL in a required digit column must be rejected."""

    columns = valid_columns()
    columns["col1"] = None

    with pytest.raises(
        DataQualityValidationError,
        match="col1 cannot be NULL",
    ):
        validate_digit_columns(columns)


def test_missing_digit_column_is_rejected():
    """A missing digit column must be rejected."""

    columns = valid_columns()
    del columns["col8"]

    with pytest.raises(
        DataQualityValidationError,
        match="col8 is missing",
    ):
        validate_digit_columns(columns)


def test_negative_digit_is_rejected():
    """Negative digit values must be rejected."""

    columns = valid_columns()
    columns["col1"] = -1

    with pytest.raises(
        DataQualityValidationError,
        match="col1 must be between 0 and 9",
    ):
        validate_digit_columns(columns)


def test_digit_greater_than_nine_is_rejected():
    """Digit values greater than 9 must be rejected."""

    columns = valid_columns()
    columns["col1"] = 10

    with pytest.raises(
        DataQualityValidationError,
        match="col1 must be between 0 and 9",
    ):
        validate_digit_columns(columns)


def test_non_integer_digit_is_rejected():
    """Digit columns must contain integers."""

    columns = valid_columns()
    columns["col1"] = "1"

    with pytest.raises(
        DataQualityValidationError,
        match="col1 must be an integer",
    ):
        validate_digit_columns(columns)


@pytest.mark.parametrize(
    "open_result,jodi_result,close_result",
    [
        ("12", "45", "678"),
        ("1234", "45", "678"),
        ("123", "4", "678"),
        ("123", "456", "678"),
        ("123", "45", "67"),
        ("123", "45", "6789"),
    ],
)
def test_invalid_result_lengths_are_rejected(
    open_result,
    jodi_result,
    close_result,
):
    """Incorrect result lengths must be rejected."""

    with pytest.raises(
        DataQualityValidationError
    ):
        validate_result_components(
            open_result=open_result,
            jodi_result=jodi_result,
            close_result=close_result,
        )


@pytest.mark.parametrize(
    "open_result,jodi_result,close_result",
    [
        ("12A", "45", "678"),
        ("123", "4B", "678"),
        ("123", "45", "67C"),
    ],
)
def test_non_numeric_results_are_rejected(
    open_result,
    jodi_result,
    close_result,
):
    """Non-numeric result components must be rejected."""

    with pytest.raises(
        DataQualityValidationError
    ):
        validate_result_components(
            open_result=open_result,
            jodi_result=jodi_result,
            close_result=close_result,
        )


def test_null_open_result_is_rejected():
    """NULL Open result must be rejected."""

    with pytest.raises(
        DataQualityValidationError,
        match="Open is required",
    ):
        validate_result_components(
            open_result=None,
            jodi_result="45",
            close_result="678",
        )


def test_null_jodi_result_is_rejected():
    """NULL Jodi result must be rejected."""

    with pytest.raises(
        DataQualityValidationError,
        match="Jodi is required",
    ):
        validate_result_components(
            open_result="123",
            jodi_result=None,
            close_result="678",
        )


def test_null_close_result_is_rejected():
    """NULL Close result must be rejected."""

    with pytest.raises(
        DataQualityValidationError,
        match="Close is required",
    ):
        validate_result_components(
            open_result="123",
            jodi_result="45",
            close_result=None,
        )


def test_incorrect_derived_column_is_rejected():
    """Derived columns must match Open + Jodi + Close."""

    columns = valid_columns()
    columns["col8"] = 9

    with pytest.raises(
        DataQualityValidationError,
        match="col8 does not match",
    ):
        validate_derived_columns(
            open_result="123",
            jodi_result="45",
            close_result="678",
            columns=columns,
        )


def test_result_date_is_required():
    """Historical records must have a result date."""

    with pytest.raises(
        DataQualityValidationError,
        match="Result date is required",
    ):
        validate_result_date(None)


def test_result_date_must_be_date():
    """Result date must be a date object."""

    with pytest.raises(
        DataQualityValidationError,
        match="Result date must be a valid date",
    ):
        validate_result_date("2026-09-19")


def test_market_id_is_required():
    """Historical records must reference a market."""

    with pytest.raises(
        DataQualityValidationError,
        match="Market ID is required",
    ):
        validate_market_id(None)


def test_market_id_must_be_positive():
    """Market ID must be greater than zero."""

    with pytest.raises(
        DataQualityValidationError,
        match="Market ID must be greater than zero",
    ):
        validate_market_id(0)


def test_market_id_must_be_integer():
    """Market ID must be an integer."""

    with pytest.raises(
        DataQualityValidationError,
        match="Market ID must be an integer",
    ):
        validate_market_id("1")
