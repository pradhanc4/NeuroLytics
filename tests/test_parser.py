import pytest

from database.parser import ResultValidationError, parse_results


def test_parse_standard_results():
    result = parse_results("123", "45", "678")

    assert result["open_result"] == "123"
    assert result["jodi_result"] == "45"
    assert result["close_result"] == "678"

    assert [
        result["col1"],
        result["col2"],
        result["col3"],
        result["col4"],
        result["col5"],
        result["col6"],
        result["col7"],
        result["col8"],
    ] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_parse_preserves_leading_zeros():
    result = parse_results("005", "05", "007")

    assert result["open_result"] == "005"
    assert result["jodi_result"] == "05"
    assert result["close_result"] == "007"

    assert [
        result["col1"],
        result["col2"],
        result["col3"],
        result["col4"],
        result["col5"],
        result["col6"],
        result["col7"],
        result["col8"],
    ] == [0, 0, 5, 0, 5, 0, 0, 7]


def test_invalid_open_length():
    with pytest.raises(
        ResultValidationError,
        match="Open must contain exactly 3 digits",
    ):
        parse_results("12", "45", "678")


def test_invalid_jodi_length():
    with pytest.raises(
        ResultValidationError,
        match="Jodi must contain exactly 2 digits",
    ):
        parse_results("123", "5", "678")


def test_invalid_close_length():
    with pytest.raises(
        ResultValidationError,
        match="Close must contain exactly 3 digits",
    ):
        parse_results("123", "45", "67")


def test_non_numeric_open():
    with pytest.raises(
        ResultValidationError,
        match="Open must contain digits only",
    ):
        parse_results("12A", "45", "678")


def test_missing_open():
    with pytest.raises(
        ResultValidationError,
        match="Open is required",
    ):
        parse_results("", "45", "678")