from datetime import date


class DataQualityValidationError(ValueError):
    """Raised when a historical record fails data-quality validation."""


def _validate_required_text(
    value: str | None,
    field_name: str,
) -> str:
    """Validate that a required text value exists."""

    if value is None:
        raise DataQualityValidationError(
            f"{field_name} is required."
        )

    value = str(value).strip()

    if not value:
        raise DataQualityValidationError(
            f"{field_name} is required."
        )

    return value


def _validate_digit_string(
    value: str | None,
    expected_length: int,
    field_name: str,
) -> str:
    """
    Validate a numeric result while preserving leading zeros.
    """

    value = _validate_required_text(
        value=value,
        field_name=field_name,
    )

    if not value.isdigit():
        raise DataQualityValidationError(
            f"{field_name} must contain digits only."
        )

    if len(value) != expected_length:
        raise DataQualityValidationError(
            f"{field_name} must contain exactly "
            f"{expected_length} digits."
        )

    return value


def validate_result_date(
    result_date: date | None,
) -> None:
    """Validate that a historical result has a date."""

    if result_date is None:
        raise DataQualityValidationError(
            "Result date is required."
        )

    if not isinstance(result_date, date):
        raise DataQualityValidationError(
            "Result date must be a valid date."
        )


def validate_market_id(
    market_id: int | None,
) -> None:
    """Validate that a historical result references a market."""

    if market_id is None:
        raise DataQualityValidationError(
            "Market ID is required."
        )

    if not isinstance(market_id, int):
        raise DataQualityValidationError(
            "Market ID must be an integer."
        )

    if market_id <= 0:
        raise DataQualityValidationError(
            "Market ID must be greater than zero."
        )


def validate_result_components(
    open_result: str | None,
    jodi_result: str | None,
    close_result: str | None,
) -> dict:
    """
    Validate Open, Jodi, and Close components.

    Leading zeros are intentionally preserved.
    """

    open_result = _validate_digit_string(
        value=open_result,
        expected_length=3,
        field_name="Open",
    )

    jodi_result = _validate_digit_string(
        value=jodi_result,
        expected_length=2,
        field_name="Jodi",
    )

    close_result = _validate_digit_string(
        value=close_result,
        expected_length=3,
        field_name="Close",
    )

    return {
        "open_result": open_result,
        "jodi_result": jodi_result,
        "close_result": close_result,
    }


def validate_digit_columns(
    columns: dict,
) -> None:
    """
    Validate col1-col8 values.

    Actual zero is valid and must not be treated as missing.
    """

    required_columns = [
        "col1",
        "col2",
        "col3",
        "col4",
        "col5",
        "col6",
        "col7",
        "col8",
    ]

    for column_name in required_columns:
        if column_name not in columns:
            raise DataQualityValidationError(
                f"{column_name} is missing."
            )

        value = columns[column_name]

        if value is None:
            raise DataQualityValidationError(
                f"{column_name} cannot be NULL."
            )

        if not isinstance(value, int):
            raise DataQualityValidationError(
                f"{column_name} must be an integer."
            )

        if value < 0 or value > 9:
            raise DataQualityValidationError(
                f"{column_name} must be between 0 and 9."
            )


def validate_derived_columns(
    open_result: str,
    jodi_result: str,
    close_result: str,
    columns: dict,
) -> None:
    """
    Verify that col1-col8 exactly match the digits from
    Open + Jodi + Close.
    """

    digits = (
        open_result
        + jodi_result
        + close_result
    )

    expected_columns = {
        "col1": int(digits[0]),
        "col2": int(digits[1]),
        "col3": int(digits[2]),
        "col4": int(digits[3]),
        "col5": int(digits[4]),
        "col6": int(digits[5]),
        "col7": int(digits[6]),
        "col8": int(digits[7]),
    }

    for column_name, expected_value in expected_columns.items():
        actual_value = columns[column_name]

        if actual_value != expected_value:
            raise DataQualityValidationError(
                f"{column_name} does not match the corresponding "
                f"digit from Open + Jodi + Close."
            )


def validate_historical_record(
    market_id: int | None,
    result_date: date | None,
    open_result: str | None,
    jodi_result: str | None,
    close_result: str | None,
    columns: dict,
) -> dict:
    """
    Run all Phase 8.2 data-quality validation rules.

    Returns the normalized values when validation succeeds.
    """

    validate_market_id(
        market_id=market_id,
    )

    validate_result_date(
        result_date=result_date,
    )

    validated_results = validate_result_components(
        open_result=open_result,
        jodi_result=jodi_result,
        close_result=close_result,
    )

    validate_digit_columns(
        columns=columns,
    )

    validate_derived_columns(
        open_result=validated_results["open_result"],
        jodi_result=validated_results["jodi_result"],
        close_result=validated_results["close_result"],
        columns=columns,
    )

    return {
        "market_id": market_id,
        "result_date": result_date,
        **validated_results,
        **columns,
    }
