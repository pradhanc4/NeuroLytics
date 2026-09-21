from __future__ import annotations

import pytest

from analytics.position_distribution_change import (
    PositionDistributionDigitChange,
)
from analytics.position_distribution_change_classification import (
    PositionDistributionChangeClassification,
    classify_position_distribution_change,
    classify_position_distribution_changes,
)


def make_change(
    digit: int,
    absolute_change: float,
    direction: str,
    position: str = "col1",
) -> PositionDistributionDigitChange:
    return PositionDistributionDigitChange(
        position=position,
        digit=digit,
        percentage_a=10.0,
        percentage_b=10.0,
        absolute_change=absolute_change,
        direction=direction,
    )


def test_increased_change_is_classified_as_increased() -> None:
    change = make_change(
        digit=3,
        absolute_change=5.0,
        direction="increased",
    )

    result = classify_position_distribution_change(change)

    assert isinstance(
        result,
        PositionDistributionChangeClassification,
    )
    assert result.position == "col1"
    assert result.digit == 3
    assert result.absolute_change == 5.0
    assert result.threshold == 0.0
    assert result.classification == "increased"


def test_decreased_change_is_classified_as_decreased() -> None:
    change = make_change(
        digit=4,
        absolute_change=7.5,
        direction="decreased",
    )

    result = classify_position_distribution_change(change)

    assert result.classification == "decreased"


def test_zero_change_is_classified_as_unchanged() -> None:
    change = make_change(
        digit=5,
        absolute_change=0.0,
        direction="unchanged",
    )

    result = classify_position_distribution_change(change)

    assert result.classification == "unchanged"


def test_change_equal_to_threshold_is_unchanged() -> None:
    change = make_change(
        digit=6,
        absolute_change=2.0,
        direction="increased",
    )

    result = classify_position_distribution_change(
        change=change,
        threshold=2.0,
    )

    assert result.classification == "unchanged"
    assert result.threshold == 2.0


def test_change_above_threshold_is_classified() -> None:
    change = make_change(
        digit=7,
        absolute_change=2.01,
        direction="increased",
    )

    result = classify_position_distribution_change(
        change=change,
        threshold=2.0,
    )

    assert result.classification == "increased"


def test_small_change_below_threshold_is_unchanged() -> None:
    change = make_change(
        digit=8,
        absolute_change=0.25,
        direction="decreased",
    )

    result = classify_position_distribution_change(
        change=change,
        threshold=1.0,
    )

    assert result.classification == "unchanged"


def test_threshold_zero_preserves_nonzero_direction() -> None:
    change = make_change(
        digit=9,
        absolute_change=0.0001,
        direction="decreased",
    )

    result = classify_position_distribution_change(
        change=change,
        threshold=0.0,
    )

    assert result.classification == "decreased"


def test_negative_threshold_is_rejected() -> None:
    change = make_change(
        digit=0,
        absolute_change=1.0,
        direction="increased",
    )

    with pytest.raises(
        ValueError,
        match="greater than or equal to zero",
    ):
        classify_position_distribution_change(
            change=change,
            threshold=-0.1,
        )


def test_multiple_changes_are_classified() -> None:
    changes = (
        make_change(
            digit=0,
            absolute_change=5.0,
            direction="increased",
        ),
        make_change(
            digit=1,
            absolute_change=0.5,
            direction="decreased",
        ),
        make_change(
            digit=2,
            absolute_change=0.0,
            direction="unchanged",
        ),
    )

    result = classify_position_distribution_changes(
        changes=changes,
        threshold=1.0,
    )

    assert len(result) == 3
    assert result[0].classification == "increased"
    assert result[1].classification == "unchanged"
    assert result[2].classification == "unchanged"


def test_multiple_changes_preserve_order() -> None:
    changes = (
        make_change(
            digit=8,
            absolute_change=4.0,
            direction="increased",
        ),
        make_change(
            digit=2,
            absolute_change=3.0,
            direction="decreased",
        ),
        make_change(
            digit=5,
            absolute_change=0.0,
            direction="unchanged",
        ),
    )

    result = classify_position_distribution_changes(
        changes=changes,
        threshold=1.0,
    )

    assert tuple(item.digit for item in result) == (8, 2, 5)


def test_empty_changes_return_empty_result() -> None:
    result = classify_position_distribution_changes(
        changes=(),
    )

    assert result == ()


def test_negative_threshold_is_rejected_for_multiple_changes() -> None:
    changes = (
        make_change(
            digit=1,
            absolute_change=1.0,
            direction="increased",
        ),
    )

    with pytest.raises(
        ValueError,
        match="greater than or equal to zero",
    ):
        classify_position_distribution_changes(
            changes=changes,
            threshold=-1.0,
        )