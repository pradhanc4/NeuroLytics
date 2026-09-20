class ResultValidationError(ValueError):
    """Raised when Open/Jodi/Close input is invalid."""


def _validate_digit_string(value: str, expected_length: int, field_name: str) -> str:
    """
    Validate a result component while preserving leading zeros.
    """

    if value is None:
        raise ResultValidationError(
            f"{field_name} is required."
        )

    value = str(value).strip()

    if not value:
        raise ResultValidationError(
            f"{field_name} is required."
        )

    if not value.isdigit():
        raise ResultValidationError(
            f"{field_name} must contain digits only."
        )

    if len(value) != expected_length:
        raise ResultValidationError(
            f"{field_name} must contain exactly {expected_length} digits."
        )

    return value


def parse_results(
    open_result: str,
    jodi_result: str,
    close_result: str,
) -> dict:
    """
    Validate Open/Jodi/Close and derive Col1-Col8.

    Example:
        Open  = 123
        Jodi  = 45
        Close = 678

    Produces:
        Col1-Col8 = 1,2,3,4,5,6,7,8
    """

    open_result = _validate_digit_string(
        open_result,
        expected_length=3,
        field_name="Open",
    )

    jodi_result = _validate_digit_string(
        jodi_result,
        expected_length=2,
        field_name="Jodi",
    )

    close_result = _validate_digit_string(
        close_result,
        expected_length=3,
        field_name="Close",
    )

    digits = open_result + jodi_result + close_result

    return {
        "open_result": open_result,
        "jodi_result": jodi_result,
        "close_result": close_result,
        "col1": int(digits[0]),
        "col2": int(digits[1]),
        "col3": int(digits[2]),
        "col4": int(digits[3]),
        "col5": int(digits[4]),
        "col6": int(digits[5]),
        "col7": int(digits[6]),
        "col8": int(digits[7]),
    }