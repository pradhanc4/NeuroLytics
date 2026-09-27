from dataclasses import dataclass

import pytest

from analytics.cross_position_relationship_change_detection import (
    RELATIONSHIP_DIRECTIONS,
    RELATIONSHIP_STRENGTHS,
    CrossPositionRelationshipChange,
    CrossPositionRelationshipChangeDetection,
    build_cross_position_relationship_change_detection,
    get_cross_position_relationship_change,
    iter_cross_position_relationship_changes,
)


@dataclass(frozen=True)
class Window:
    window_index: int
    correlation: float | None
    direction: str
    strength: str


def make_windows():
    return (
        Window(1, 0.80, "POSITIVE", "STRONG"),
        Window(2, 0.60, "POSITIVE", "MODERATE"),
        Window(3, -0.40, "NEGATIVE", "MODERATE"),
        Window(4, -0.10, "NEGATIVE", "WEAK"),
    )


def test_constants_are_defined():
    assert RELATIONSHIP_DIRECTIONS == (
        "POSITIVE",
        "NEGATIVE",
        "NEUTRAL",
        "INSUFFICIENT_DATA",
    )

    assert RELATIONSHIP_STRENGTHS == (
        "NONE",
        "WEAK",
        "MODERATE",
        "STRONG",
        "INSUFFICIENT_DATA",
    )


def test_build_returns_expected_type():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    assert isinstance(
        result,
        CrossPositionRelationshipChangeDetection,
    )


def test_position_names_are_preserved():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    assert result.position_a == "col1"
    assert result.position_b == "col2"


def test_window_count_is_correct():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    assert result.window_count == 4


def test_comparison_count_is_previous_current_pairs():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    assert result.comparison_count == 3


def test_first_change_has_correct_window_indices():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    change = result.changes[0]

    assert change.previous_window_index == 1
    assert change.current_window_index == 2


def test_correlation_change_is_current_minus_previous():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    change = result.changes[0]

    assert change.correlation_change == pytest.approx(-0.20)


def test_absolute_correlation_change_uses_absolute_values():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    change = result.changes[1]

    assert change.previous_correlation == pytest.approx(0.60)
    assert change.current_correlation == pytest.approx(-0.40)
    assert change.absolute_correlation_change == pytest.approx(-0.20)


def test_direction_change_is_detected():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    change = result.changes[1]

    assert change.previous_direction == "POSITIVE"
    assert change.current_direction == "NEGATIVE"
    assert change.direction_changed is True


def test_no_direction_change_is_detected():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    change = result.changes[0]

    assert change.previous_direction == "POSITIVE"
    assert change.current_direction == "POSITIVE"
    assert change.direction_changed is False


def test_strength_change_is_detected():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    change = result.changes[0]

    assert change.previous_strength == "STRONG"
    assert change.current_strength == "MODERATE"
    assert change.strength_changed is True


def test_strength_change_can_be_false():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    change = result.changes[1]

    assert change.previous_strength == "MODERATE"
    assert change.current_strength == "MODERATE"
    assert change.strength_changed is False


def test_relationship_change_is_true_when_correlation_changes():
    windows = (
        Window(1, 0.50, "POSITIVE", "MODERATE"),
        Window(2, 0.40, "POSITIVE", "MODERATE"),
    )

    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        windows,
    )

    assert result.changes[0].relationship_changed is True


def test_relationship_change_is_true_when_direction_changes():
    windows = (
        Window(1, 0.50, "POSITIVE", "MODERATE"),
        Window(2, -0.50, "NEGATIVE", "MODERATE"),
    )

    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        windows,
    )

    assert result.changes[0].relationship_changed is True


def test_relationship_change_is_true_when_strength_changes():
    windows = (
        Window(1, 0.20, "POSITIVE", "WEAK"),
        Window(2, 0.60, "POSITIVE", "MODERATE"),
    )

    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        windows,
    )

    assert result.changes[0].relationship_changed is True


def test_no_relationship_change_for_identical_window_relationship():
    windows = (
        Window(1, 0.50, "POSITIVE", "MODERATE"),
        Window(2, 0.50, "POSITIVE", "MODERATE"),
    )

    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        windows,
    )

    change = result.changes[0]

    assert change.correlation_change == pytest.approx(0.0)
    assert change.absolute_correlation_change == pytest.approx(0.0)
    assert change.direction_changed is False
    assert change.strength_changed is False
    assert change.relationship_changed is False


def test_direction_change_count_is_correct():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    assert result.direction_change_count == 1


def test_strength_change_count_is_correct():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    assert result.strength_change_count == 2


def test_relationship_change_count_is_correct():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    assert result.relationship_change_count == 3


def test_insufficient_data_is_detected():
    windows = (
        Window(1, None, "INSUFFICIENT_DATA", "INSUFFICIENT_DATA"),
        Window(2, 0.50, "POSITIVE", "MODERATE"),
    )

    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        windows,
    )

    change = result.changes[0]

    assert change.correlation_change is None
    assert change.absolute_correlation_change is None
    assert change.previous_direction == "INSUFFICIENT_DATA"
    assert change.current_direction == "POSITIVE"
    assert change.direction_changed is True
    assert result.insufficient_data_change_count == 1


def test_both_insufficient_windows_are_supported():
    windows = (
        Window(1, None, "INSUFFICIENT_DATA", "INSUFFICIENT_DATA"),
        Window(2, None, "INSUFFICIENT_DATA", "INSUFFICIENT_DATA"),
    )

    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        windows,
    )

    change = result.changes[0]

    assert change.correlation_change is None
    assert change.absolute_correlation_change is None
    assert change.direction_changed is False
    assert change.strength_changed is False
    assert change.relationship_changed is False
    assert result.insufficient_data_change_count == 1


def test_empty_windows_return_empty_detection():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        (),
    )

    assert result.window_count == 0
    assert result.comparison_count == 0
    assert result.changes == ()
    assert result.direction_change_count == 0
    assert result.strength_change_count == 0
    assert result.relationship_change_count == 0
    assert result.insufficient_data_change_count == 0


def test_single_window_has_no_comparison():
    windows = (
        Window(1, 0.50, "POSITIVE", "MODERATE"),
    )

    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        windows,
    )

    assert result.window_count == 1
    assert result.comparison_count == 0
    assert result.changes == ()


def test_get_specific_relationship_change():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    change = get_cross_position_relationship_change(
        result,
        2,
        3,
    )

    assert isinstance(change, CrossPositionRelationshipChange)
    assert change.previous_window_index == 2
    assert change.current_window_index == 3
    assert change.previous_correlation == pytest.approx(0.60)
    assert change.current_correlation == pytest.approx(-0.40)


def test_get_missing_relationship_change_raises():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    with pytest.raises(ValueError, match="Relationship change not found"):
        get_cross_position_relationship_change(
            result,
            1,
            4,
        )


def test_iter_returns_all_changes():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    changes = iter_cross_position_relationship_changes(result)

    assert changes == result.changes
    assert len(changes) == 3


def test_invalid_same_positions_raise():
    with pytest.raises(
        ValueError,
        match="position_a and position_b must be different",
    ):
        build_cross_position_relationship_change_detection(
            "col1",
            "col1",
            make_windows(),
        )


def test_empty_position_a_raises():
    with pytest.raises(ValueError, match="position must not be empty"):
        build_cross_position_relationship_change_detection(
            "",
            "col2",
            make_windows(),
        )


def test_non_string_position_raises():
    with pytest.raises(TypeError, match="position must be a string"):
        build_cross_position_relationship_change_detection(
            1,
            "col2",
            make_windows(),
        )


def test_non_iterable_windows_raise():
    with pytest.raises(
        TypeError,
        match="windows must be an iterable",
    ):
        build_cross_position_relationship_change_detection(
            "col1",
            "col2",
            None,
        )


def test_string_windows_raise():
    with pytest.raises(
        TypeError,
        match="windows must be an iterable",
    ):
        build_cross_position_relationship_change_detection(
            "col1",
            "col2",
            "invalid",
        )


def test_duplicate_window_indices_raise():
    windows = (
        Window(1, 0.50, "POSITIVE", "MODERATE"),
        Window(1, 0.60, "POSITIVE", "MODERATE"),
    )

    with pytest.raises(
        ValueError,
        match="window_index values must be unique",
    ):
        build_cross_position_relationship_change_detection(
            "col1",
            "col2",
            windows,
        )


def test_unsorted_window_indices_raise():
    windows = (
        Window(2, 0.50, "POSITIVE", "MODERATE"),
        Window(1, 0.60, "POSITIVE", "MODERATE"),
    )

    with pytest.raises(
        ValueError,
        match="windows must be ordered by window_index",
    ):
        build_cross_position_relationship_change_detection(
            "col1",
            "col2",
            windows,
        )


def test_invalid_window_index_raises():
    windows = (
        Window(0, 0.50, "POSITIVE", "MODERATE"),
    )

    with pytest.raises(
        ValueError,
        match="window_index must be at least 1",
    ):
        build_cross_position_relationship_change_detection(
            "col1",
            "col2",
            windows,
        )


def test_invalid_direction_raises():
    windows = (
        Window(1, 0.50, "INVALID", "MODERATE"),
    )

    with pytest.raises(
        ValueError,
        match="Invalid relationship direction",
    ):
        build_cross_position_relationship_change_detection(
            "col1",
            "col2",
            windows,
        )


def test_invalid_strength_raises():
    windows = (
        Window(1, 0.50, "POSITIVE", "INVALID"),
    )

    with pytest.raises(
        ValueError,
        match="Invalid relationship strength",
    ):
        build_cross_position_relationship_change_detection(
            "col1",
            "col2",
            windows,
        )


def test_non_finite_correlation_raises():
    windows = (
        Window(1, float("nan"), "POSITIVE", "MODERATE"),
    )

    with pytest.raises(
        ValueError,
        match="correlation must be finite",
    ):
        build_cross_position_relationship_change_detection(
            "col1",
            "col2",
            windows,
        )


def test_result_is_immutable():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    with pytest.raises(AttributeError):
        result.window_count = 99


def test_changes_are_immutable():
    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        make_windows(),
    )

    with pytest.raises(AttributeError):
        result.changes[0].relationship_changed = False


def test_generator_input_is_supported():
    windows = (
        Window(1, 0.80, "POSITIVE", "STRONG"),
        Window(2, 0.60, "POSITIVE", "MODERATE"),
    )

    result = build_cross_position_relationship_change_detection(
        "col1",
        "col2",
        (window for window in windows),
    )

    assert result.window_count == 2
    assert result.comparison_count == 1
    assert result.changes[0].correlation_change == pytest.approx(-0.20)