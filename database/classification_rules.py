from database.parser import parse_results


def _classify_three_digit_structure(value: str) -> str:
    """Classify the structural pattern of a three-digit value."""

    value = str(value)

    digits = [int(digit) for digit in value]
    unique_count = len(set(digits))

    if unique_count == 3:
        return "TRIPLE_UNIQUE"

    if unique_count == 2:
        return "ONE_PAIR"

    return "TRIPLE_REPEAT"


def _classify_zero(value: str) -> str:
    """Classify whether a value contains zero."""

    return "HAS_ZERO" if "0" in value else "NO_ZERO"


def _classify_digit_sum(value: str) -> str:
    """Classify the digit sum of a three-digit value."""

    digit_sum = sum(int(digit) for digit in value)

    if digit_sum <= 9:
        return "LOW_SUM"

    if digit_sum <= 18:
        return "MEDIUM_SUM"

    return "HIGH_SUM"


def _classify_parity(value: str) -> str:
    """Return the odd/even pattern of the digits."""

    return "".join(
        "E" if int(digit) % 2 == 0 else "O"
        for digit in value
    )


def _classify_order(value: str) -> str:
    """Classify the ordering of a three-digit value."""

    digits = [int(digit) for digit in value]

    if digits[0] < digits[1] < digits[2]:
        return "ASCENDING"

    if digits[0] > digits[1] > digits[2]:
        return "DESCENDING"

    return "MIXED"


def _classify_three_digit_value(value: str) -> str:
    """
    Build a complete structural classification
    for a three-digit value.
    """

    return "|".join(
        [
            _classify_three_digit_structure(value),
            _classify_zero(value),
            _classify_digit_sum(value),
            _classify_parity(value),
            _classify_order(value),
        ]
    )


def _classify_jodi(value: str) -> str:
    """Build a complete structural classification for a Jodi."""

    digits = [int(digit) for digit in value]

    double_class = (
        "DOUBLE"
        if digits[0] == digits[1]
        else "NON_DOUBLE"
    )

    digit_class = (
        "SAME_DIGIT"
        if digits[0] == digits[1]
        else "DIFFERENT_DIGIT"
    )

    parity_class = "".join(
        "E" if digit % 2 == 0 else "O"
        for digit in digits
    )

    return "|".join(
        [
            double_class,
            digit_class,
            parity_class,
        ]
    )


def _classify_open_close_relationship(
    open_result: str,
    close_result: str,
) -> str:
    """Classify the structural relationship between Open and Close."""

    if open_result == close_result:
        return "SAME"

    if open_result == close_result[::-1]:
        return "REVERSED"

    open_digits = set(open_result)
    close_digits = set(close_result)

    overlap_count = len(
        open_digits.intersection(close_digits)
    )

    if overlap_count > 0:
        return "PARTIAL_MATCH"

    return "NO_POSITIONAL_MATCH"


def _classify_digit_overlap(
    open_result: str,
    close_result: str,
) -> str:
    """Classify the number of unique digit values shared by Open and Close."""

    overlap_count = len(
        set(open_result).intersection(
            set(close_result)
        )
    )

    return f"{overlap_count}_MATCH"


def classify_historical_result(
    historical_result,
    classification_version: str = "v1",
) -> dict:
    """
    Generate descriptive classifications for one historical result.

    This function does not generate predictions.
    It only describes structural properties of historical data.
    """

    if historical_result is None:
        raise ValueError(
            "Historical result is required."
        )

    if not classification_version:
        raise ValueError(
            "Classification version is required."
        )

    parsed = parse_results(
        open_result=historical_result.open_result,
        jodi_result=historical_result.jodi_result,
        close_result=historical_result.close_result,
    )

    open_result = parsed["open_result"]
    jodi_result = parsed["jodi_result"]
    close_result = parsed["close_result"]

    open_class = _classify_three_digit_value(
        open_result
    )

    jodi_class = _classify_jodi(
        jodi_result
    )

    close_class = _classify_three_digit_value(
        close_result
    )

    relationship = _classify_open_close_relationship(
        open_result,
        close_result,
    )

    overlap = _classify_digit_overlap(
        open_result,
        close_result,
    )

    overall_class = "|".join(
        [
            relationship,
            overlap,
        ]
    )

    return {
        "classification_version": classification_version,
        "open_class": open_class,
        "jodi_class": jodi_class,
        "close_class": close_class,
        "overall_class": overall_class,
    }