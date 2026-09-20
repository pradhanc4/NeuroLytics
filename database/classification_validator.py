from database.classification_rules import (
    _classify_digit_sum,
    _classify_digit_overlap,
    _classify_jodi,
    _classify_open_close_relationship,
    _classify_order,
    _classify_parity,
    _classify_three_digit_structure,
    _classify_zero,
)
from database.parser import parse_results


class ClassificationValidationError(ValueError):
    """Raised when a historical classification is invalid."""


VALID_THREE_DIGIT_STRUCTURES = {
    "TRIPLE_UNIQUE",
    "ONE_PAIR",
    "TRIPLE_REPEAT",
}

VALID_ZERO_CLASSES = {
    "HAS_ZERO",
    "NO_ZERO",
}

VALID_DIGIT_SUM_CLASSES = {
    "LOW_SUM",
    "MEDIUM_SUM",
    "HIGH_SUM",
}

VALID_ORDER_CLASSES = {
    "ASCENDING",
    "DESCENDING",
    "MIXED",
}

VALID_OPEN_CLOSE_RELATIONSHIPS = {
    "SAME",
    "REVERSED",
    "PARTIAL_MATCH",
    "NO_POSITIONAL_MATCH",
}


def _validate_version(
    classification_version: str,
) -> str:
    """Validate the classification version."""

    if classification_version is None:
        raise ClassificationValidationError(
            "Classification version is required."
        )

    classification_version = str(
        classification_version
    ).strip()

    if not classification_version:
        raise ClassificationValidationError(
            "Classification version is required."
        )

    if len(classification_version) > 20:
        raise ClassificationValidationError(
            "Classification version must contain at most 20 characters."
        )

    return classification_version


def _validate_three_digit_class(
    value: str,
    expected_value: str,
) -> None:
    """Validate a three-digit classification component."""

    parts = value.split("|")

    if len(parts) != 5:
        raise ClassificationValidationError(
            "Three-digit classification must contain exactly 5 components."
        )

    structure, zero, digit_sum, parity, order = parts

    if structure not in VALID_THREE_DIGIT_STRUCTURES:
        raise ClassificationValidationError(
            f"Invalid three-digit structure: {structure}."
        )

    if zero not in VALID_ZERO_CLASSES:
        raise ClassificationValidationError(
            f"Invalid zero classification: {zero}."
        )

    if digit_sum not in VALID_DIGIT_SUM_CLASSES:
        raise ClassificationValidationError(
            f"Invalid digit-sum classification: {digit_sum}."
        )

    if len(parity) != 3 or any(
        digit not in {"E", "O"}
        for digit in parity
    ):
        raise ClassificationValidationError(
            f"Invalid parity classification: {parity}."
        )

    if order not in VALID_ORDER_CLASSES:
        raise ClassificationValidationError(
            f"Invalid order classification: {order}."
        )

    if value != expected_value:
        raise ClassificationValidationError(
            "Three-digit classification does not match "
            "the historical result."
        )


def _validate_jodi_class(
    value: str,
    expected_value: str,
) -> None:
    """Validate a Jodi classification."""

    parts = value.split("|")

    if len(parts) != 3:
        raise ClassificationValidationError(
            "Jodi classification must contain exactly 3 components."
        )

    double_class, digit_class, parity = parts

    if double_class not in {
        "DOUBLE",
        "NON_DOUBLE",
    }:
        raise ClassificationValidationError(
            f"Invalid Jodi double classification: {double_class}."
        )

    if digit_class not in {
        "SAME_DIGIT",
        "DIFFERENT_DIGIT",
    }:
        raise ClassificationValidationError(
            f"Invalid Jodi digit classification: {digit_class}."
        )

    if len(parity) != 2 or any(
        digit not in {"E", "O"}
        for digit in parity
    ):
        raise ClassificationValidationError(
            f"Invalid Jodi parity classification: {parity}."
        )

    if value != expected_value:
        raise ClassificationValidationError(
            "Jodi classification does not match "
            "the historical result."
        )


def _validate_overall_class(
    value: str,
    expected_value: str,
) -> None:
    """Validate the overall classification."""

    parts = value.split("|")

    if len(parts) != 2:
        raise ClassificationValidationError(
            "Overall classification must contain exactly 2 components."
        )

    relationship, overlap = parts

    if relationship not in VALID_OPEN_CLOSE_RELATIONSHIPS:
        raise ClassificationValidationError(
            f"Invalid Open/Close relationship: {relationship}."
        )

    if overlap not in {
        "0_MATCH",
        "1_MATCH",
        "2_MATCH",
        "3_MATCH",
    }:
        raise ClassificationValidationError(
            f"Invalid digit overlap classification: {overlap}."
        )

    if value != expected_value:
        raise ClassificationValidationError(
            "Overall classification does not match "
            "the historical result."
        )


def validate_classification(
    historical_result,
    classification_data: dict,
    classification_version: str = "v1",
) -> dict:
    """
    Validate a complete historical classification.

    This function verifies that:
    - the historical result is valid
    - required classification fields exist
    - classification values use known labels
    - classification values match the historical result
    - the classification version is valid
    """

    if historical_result is None:
        raise ClassificationValidationError(
            "Historical result is required."
        )

    classification_version = _validate_version(
        classification_version
    )

    if not isinstance(classification_data, dict):
        raise ClassificationValidationError(
            "Classification data must be a dictionary."
        )

    required_fields = {
        "open_class",
        "jodi_class",
        "close_class",
        "overall_class",
    }

    missing_fields = [
        field
        for field in required_fields
        if field not in classification_data
    ]

    if missing_fields:
        raise ClassificationValidationError(
            "Missing classification fields: "
            + ", ".join(sorted(missing_fields))
        )

    parsed = parse_results(
        open_result=historical_result.open_result,
        jodi_result=historical_result.jodi_result,
        close_result=historical_result.close_result,
    )

    open_result = parsed["open_result"]
    jodi_result = parsed["jodi_result"]
    close_result = parsed["close_result"]

    expected_open_class = "|".join(
        [
            _classify_three_digit_structure(open_result),
            _classify_zero(open_result),
            _classify_digit_sum(open_result),
            _classify_parity(open_result),
            _classify_order(open_result),
        ]
    )

    expected_jodi_class = _classify_jodi(
        jodi_result
    )

    expected_close_class = "|".join(
        [
            _classify_three_digit_structure(close_result),
            _classify_zero(close_result),
            _classify_digit_sum(close_result),
            _classify_parity(close_result),
            _classify_order(close_result),
        ]
    )

    expected_overall_class = "|".join(
        [
            _classify_open_close_relationship(
                open_result,
                close_result,
            ),
            _classify_digit_overlap(
                open_result,
                close_result,
            ),
        ]
    )

    open_class = classification_data["open_class"]
    jodi_class = classification_data["jodi_class"]
    close_class = classification_data["close_class"]
    overall_class = classification_data["overall_class"]

    if not all(
        isinstance(value, str) and value.strip()
        for value in [
            open_class,
            jodi_class,
            close_class,
            overall_class,
        ]
    ):
        raise ClassificationValidationError(
            "Classification values must be non-empty strings."
        )

    _validate_three_digit_class(
        open_class,
        expected_open_class,
    )

    _validate_jodi_class(
        jodi_class,
        expected_jodi_class,
    )

    _validate_three_digit_class(
        close_class,
        expected_close_class,
    )

    _validate_overall_class(
        overall_class,
        expected_overall_class,
    )

    return {
        "classification_version": classification_version,
        "open_class": open_class,
        "jodi_class": jodi_class,
        "close_class": close_class,
        "overall_class": overall_class,
    }