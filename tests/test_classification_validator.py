import pytest

from database.classification_rules import (
    classify_historical_result,
)
from database.classification_validator import (
    ClassificationValidationError,
    validate_classification,
)
from database.models import HistoricalResult


def create_historical_result(
    open_result="123",
    jodi_result="45",
    close_result="321",
):
    """Create an unsaved historical result for validation tests."""

    return HistoricalResult(
        open_result=open_result,
        jodi_result=jodi_result,
        close_result=close_result,
        col1=int(open_result[0]),
        col2=int(open_result[1]),
        col3=int(open_result[2]),
        col4=int(jodi_result[0]),
        col5=int(jodi_result[1]),
        col6=int(close_result[0]),
        col7=int(close_result[1]),
        col8=int(close_result[2]),
    )


def get_valid_classification(
    historical_result,
    version="v1",
):
    """Generate a valid classification for test reuse."""

    return classify_historical_result(
        historical_result=historical_result,
        classification_version=version,
    )


def test_valid_classification_passes():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    result = validate_classification(
        historical_result=historical_result,
        classification_data=classification,
        classification_version="v1",
    )

    assert result == classification
    assert result["classification_version"] == "v1"


def test_missing_open_class_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification.pop("open_class")

    with pytest.raises(
        ClassificationValidationError,
        match="Missing classification fields",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_missing_jodi_class_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification.pop("jodi_class")

    with pytest.raises(
        ClassificationValidationError,
        match="Missing classification fields",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_missing_close_class_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification.pop("close_class")

    with pytest.raises(
        ClassificationValidationError,
        match="Missing classification fields",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_missing_overall_class_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification.pop("overall_class")

    with pytest.raises(
        ClassificationValidationError,
        match="Missing classification fields",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_non_dictionary_classification_fails():
    historical_result = create_historical_result()

    with pytest.raises(
        ClassificationValidationError,
        match="Classification data must be a dictionary",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=None,
        )


def test_missing_historical_result_fails():
    with pytest.raises(
        ClassificationValidationError,
        match="Historical result is required",
    ):
        validate_classification(
            historical_result=None,
            classification_data={},
        )


def test_empty_version_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Classification version is required",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
            classification_version="",
        )


def test_long_version_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    with pytest.raises(
        ClassificationValidationError,
        match="at most 20 characters",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
            classification_version="v" + "1" * 20,
        )


def test_empty_classification_value_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["open_class"] = ""

    with pytest.raises(
        ClassificationValidationError,
        match="non-empty strings",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_three_digit_structure_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["open_class"] = (
        "INVALID_STRUCTURE|NO_ZERO|MEDIUM_SUM|OOO|ASCENDING"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid three-digit structure",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_zero_classification_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["open_class"] = (
        "TRIPLE_UNIQUE|INVALID_ZERO|MEDIUM_SUM|OEO|ASCENDING"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid zero classification",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_digit_sum_classification_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["open_class"] = (
        "TRIPLE_UNIQUE|NO_ZERO|INVALID_SUM|OEO|ASCENDING"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid digit-sum classification",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_parity_classification_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["open_class"] = (
        "TRIPLE_UNIQUE|NO_ZERO|MEDIUM_SUM|XXX|ASCENDING"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid parity classification",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_order_classification_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["open_class"] = (
        "TRIPLE_UNIQUE|NO_ZERO|MEDIUM_SUM|OEO|INVALID_ORDER"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid order classification",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_jodi_double_classification_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["jodi_class"] = (
        "INVALID_DOUBLE|DIFFERENT_DIGIT|EO"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid Jodi double classification",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_jodi_digit_classification_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["jodi_class"] = (
        "NON_DOUBLE|INVALID_DIGIT|EO"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid Jodi digit classification",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_jodi_parity_classification_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["jodi_class"] = (
        "NON_DOUBLE|DIFFERENT_DIGIT|XX"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid Jodi parity classification",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_overall_relationship_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["overall_class"] = (
        "INVALID_RELATIONSHIP|1_MATCH"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid Open/Close relationship",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_invalid_overlap_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["overall_class"] = (
        "REVERSED|INVALID_MATCH"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="Invalid digit overlap classification",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_open_class_mismatch_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["open_class"] = (
        "TRIPLE_UNIQUE|NO_ZERO|HIGH_SUM|OEO|ASCENDING"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="does not match the historical result",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_jodi_class_mismatch_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["jodi_class"] = (
        "DOUBLE|SAME_DIGIT|EE"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="does not match the historical result",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_close_class_mismatch_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["close_class"] = (
        "TRIPLE_UNIQUE|NO_ZERO|HIGH_SUM|OEO|DESCENDING"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="does not match the historical result",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_overall_class_mismatch_fails():
    historical_result = create_historical_result()

    classification = get_valid_classification(
        historical_result
    )

    classification["overall_class"] = (
        "SAME|3_MATCH"
    )

    with pytest.raises(
        ClassificationValidationError,
        match="does not match the historical result",
    ):
        validate_classification(
            historical_result=historical_result,
            classification_data=classification,
        )


def test_leading_zero_values_are_validated_correctly():
    historical_result = create_historical_result(
        open_result="005",
        jodi_result="05",
        close_result="007",
    )

    classification = get_valid_classification(
        historical_result
    )

    result = validate_classification(
        historical_result=historical_result,
        classification_data=classification,
    )

    assert result["classification_version"] == "v1"
    assert result["open_class"] == classification["open_class"]
    assert result["jodi_class"] == classification["jodi_class"]
    assert result["close_class"] == classification["close_class"]
    assert result["overall_class"] == classification["overall_class"]