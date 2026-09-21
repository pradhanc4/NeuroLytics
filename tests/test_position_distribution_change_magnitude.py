from __future__ import annotations

import pytest

from analytics.position_distribution_change_magnitude import (
    PositionDistributionChangeMagnitude,
    classify_change_magnitude,
    classify_change_magnitudes,
)


def test_change_below_low_threshold_is_low() -> None:
    result = classify_change_magnitude(
        position="col1",
        digit=3,
        absolute_change=1.5,
    )

    assert result.magnitude == "LOW"


def test_change_equal_to_low_threshold_is_medium() -> None:
    result = classify_change_magnitude(
        position="col1",
        digit=3,
        absolute_change=2.0,
    )

    assert result.magnitude == "MEDIUM"


def test_change_between_thresholds_is_medium() -> None:
    result = classify_change_magnitude(
        position="col1",
        digit=3,
        absolute_change=3.5,
    )

    assert result.magnitude == "MEDIUM"


def test_change_equal_to_high_threshold_is_high() -> None:
    result = classify_change_magnitude(
        position="col1",
        digit=3,
        absolute_change=5.0,
    )

    assert result.magnitude == "HIGH"


def test_change_above_high_threshold_is_high() -> None:
    result = classify_change_magnitude(
        position="col1",
        digit=3,
        absolute_change=8.0,
    )

    assert result.magnitude == "HIGH"


def test_position_is_preserved() -> None:
    result = classify_change_magnitude(
        position="col7",
        digit=4,
        absolute_change=6.0,
    )

    assert result.position == "col7"


def test_digit_is_preserved() -> None:
    result = classify_change_magnitude(
        position="col7",
        digit=4,
        absolute_change=6.0,
    )

    assert result.digit == 4


def test_absolute_change_is_preserved() -> None:
    result = classify_change_magnitude(
        position="col7",
        digit=4,
        absolute_change=6.25,
    )

    assert result.absolute_change == 6.25


def test_custom_thresholds_are_preserved() -> None:
    result = classify_change_magnitude(
        position="col2",
        digit=8,
        absolute_change=4.0,
        low_threshold=3.0,
        high_threshold=7.0,
    )

    assert result.low_threshold == 3.0
    assert result.high_threshold == 7.0
    assert result.magnitude == "MEDIUM"


def test_zero_change_is_low_with_default_thresholds() -> None:
    result = classify_change_magnitude(
        position="col3",
        digit=0,
        absolute_change=0.0,
    )

    assert result.magnitude == "LOW"


def test_all_ten_digit_changes_are_classified() -> None:
    changes = (
        0.0,
        1.0,
        2.0,
        2.5,
        3.0,
        4.0,
        5.0,
        6.0,
        7.0,
        10.0,
    )

    results = classify_change_magnitudes(
        position="col4",
        changes=changes,
    )

    assert len(results) == 10
    assert all(
        isinstance(
            result,
            PositionDistributionChangeMagnitude,
        )
        for result in results
    )


def test_digit_indexes_are_assigned_from_zero_to_nine() -> None:
    changes = (
        0.0,
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
        6.0,
        7.0,
        8.0,
        9.0,
    )

    results = classify_change_magnitudes(
        position="col5",
        changes=changes,
    )

    assert tuple(result.digit for result in results) == tuple(
        range(10)
    )


def test_invalid_digit_is_rejected() -> None:
    with pytest.raises(ValueError):
        classify_change_magnitude(
            position="col1",
            digit=10,
            absolute_change=2.0,
        )


def test_negative_absolute_change_is_rejected() -> None:
    with pytest.raises(ValueError):
        classify_change_magnitude(
            position="col1",
            digit=2,
            absolute_change=-1.0,
        )


def test_negative_low_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        classify_change_magnitude(
            position="col1",
            digit=2,
            absolute_change=2.0,
            low_threshold=-1.0,
        )


def test_high_threshold_cannot_be_less_than_low_threshold() -> None:
    with pytest.raises(ValueError):
        classify_change_magnitude(
            position="col1",
            digit=2,
            absolute_change=2.0,
            low_threshold=5.0,
            high_threshold=3.0,
        )


def test_empty_change_sequence_returns_empty_result() -> None:
    result = classify_change_magnitudes(
        position="col8",
        changes=(),
    )

    assert result == ()


def test_custom_thresholds_classify_all_changes() -> None:
    changes = (
        1.0,
        3.0,
        5.0,
    )

    results = classify_change_magnitudes(
        position="col6",
        changes=changes,
        low_threshold=2.0,
        high_threshold=4.0,
    )

    assert tuple(result.magnitude for result in results) == (
        "LOW",
        "MEDIUM",
        "HIGH",
    )


def test_dataclass_is_frozen() -> None:
    result = classify_change_magnitude(
        position="col1",
        digit=1,
        absolute_change=2.0,
    )

    with pytest.raises(AttributeError):
        result.magnitude = "HIGH"