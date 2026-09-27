from datetime import date

import pytest

from analytics.temporal_position_change_detection import (
    CHANGE_DIRECTIONS,
    MISSING_CHANGE_DIRECTION,
    TemporalPositionChange,
    TemporalPositionChangeDetection,
    TemporalPositionChangeDetectionResult,
    build_temporal_position_change_detection,
    build_temporal_position_change_detection_result,
    get_temporal_position_change_detection,
    iter_temporal_position_changes,
    iter_temporal_position_change_detections,
)


def test_expected_change_directions():
    assert CHANGE_DIRECTIONS == (
        "INCREASE",
        "DECREASE",
        "UNCHANGED",
    )


def test_basic_change_detection():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 2),
            (date(2026, 1, 2), 5),
            (date(2026, 1, 3), 5),
            (date(2026, 1, 4), 1),
        ),
    )

    assert result.position == "col1"
    assert result.observation_count == 4
    assert result.change_count == 3

    assert result.changes[0].change == 3
    assert result.changes[0].absolute_change == 3
    assert result.changes[0].direction == "INCREASE"

    assert result.changes[1].change == 0
    assert result.changes[1].absolute_change == 0
    assert result.changes[1].direction == "UNCHANGED"

    assert result.changes[2].change == -4
    assert result.changes[2].absolute_change == 4
    assert result.changes[2].direction == "DECREASE"


def test_observations_are_sorted_by_date():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 3), 5),
            (date(2026, 1, 1), 1),
            (date(2026, 1, 2), 3),
        ),
    )

    assert result.changes[0].previous_date == date(2026, 1, 1)
    assert result.changes[0].current_date == date(2026, 1, 2)
    assert result.changes[0].change == 2

    assert result.changes[1].previous_date == date(2026, 1, 2)
    assert result.changes[1].current_date == date(2026, 1, 3)
    assert result.changes[1].change == 2


def test_increase_direction():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 2),
            (date(2026, 1, 2), 7),
        ),
    )

    change = result.changes[0]

    assert change.change == 5
    assert change.absolute_change == 5
    assert change.direction == "INCREASE"


def test_decrease_direction():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 8),
            (date(2026, 1, 2), 3),
        ),
    )

    change = result.changes[0]

    assert change.change == -5
    assert change.absolute_change == 5
    assert change.direction == "DECREASE"


def test_unchanged_direction():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 4),
            (date(2026, 1, 2), 4),
        ),
    )

    change = result.changes[0]

    assert change.change == 0
    assert change.absolute_change == 0
    assert change.direction == "UNCHANGED"


def test_zero_is_valid_value():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 0),
            (date(2026, 1, 2), 4),
            (date(2026, 1, 3), 0),
        ),
    )

    assert result.changes[0].change == 4
    assert result.changes[0].direction == "INCREASE"
    assert result.changes[1].change == -4
    assert result.changes[1].direction == "DECREASE"


def test_missing_previous_value_is_not_converted_to_zero():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), None),
            (date(2026, 1, 2), 4),
        ),
    )

    change = result.changes[0]

    assert change.previous_value is None
    assert change.current_value == 4
    assert change.change is None
    assert change.absolute_change is None
    assert change.direction == MISSING_CHANGE_DIRECTION


def test_missing_current_value_is_not_converted_to_zero():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 4),
            (date(2026, 1, 2), None),
        ),
    )

    change = result.changes[0]

    assert change.previous_value == 4
    assert change.current_value is None
    assert change.change is None
    assert change.absolute_change is None
    assert change.direction == MISSING_CHANGE_DIRECTION


def test_missing_between_valid_values_creates_missing_transitions():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 2),
            (date(2026, 1, 2), None),
            (date(2026, 1, 3), 5),
        ),
    )

    assert len(result.changes) == 2
    assert result.changes[0].direction == MISSING_CHANGE_DIRECTION
    assert result.changes[1].direction == MISSING_CHANGE_DIRECTION


def test_single_observation_has_no_changes():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 4),
        ),
    )

    assert result.observation_count == 1
    assert result.change_count == 0
    assert result.changes == ()


def test_empty_observations():
    result = build_temporal_position_change_detection(
        "col1",
        (),
    )

    assert result.observation_count == 0
    assert result.change_count == 0
    assert result.changes == ()


def test_multiple_positions_result():
    result = build_temporal_position_change_detection_result(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 2),
            ),
            "col2": (
                (date(2026, 1, 1), 5),
                (date(2026, 1, 2), 3),
            ),
        }
    )

    assert result.position_count == 2
    assert result.positions == ("col1", "col2")
    assert len(result.detections) == 2


def test_position_order_is_preserved():
    result = build_temporal_position_change_detection_result(
        {
            "col4": (
                (date(2026, 1, 1), 4),
                (date(2026, 1, 2), 5),
            ),
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 2),
            ),
            "col8": (
                (date(2026, 1, 1), 8),
                (date(2026, 1, 2), 7),
            ),
        }
    )

    assert result.positions == (
        "col4",
        "col1",
        "col8",
    )


def test_all_eight_positions():
    observations = {
        f"col{i}": (
            (date(2026, 1, 1), i % 10),
            (date(2026, 1, 2), (i + 1) % 10),
        )
        for i in range(1, 9)
    }

    result = build_temporal_position_change_detection_result(
        observations
    )

    assert result.position_count == 8
    assert len(result.detections) == 8


def test_duplicate_dates_are_rejected():
    with pytest.raises(
        ValueError,
        match="duplicate dates",
    ):
        build_temporal_position_change_detection(
            "col1",
            (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 1), 2),
            ),
        )


def test_invalid_position_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_detection(
            "",
            (),
        )


def test_invalid_observation_shape_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_detection(
            "col1",
            (
                (date(2026, 1, 1), 1, 2),
            ),
        )


def test_invalid_date_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_detection(
            "col1",
            (
                ("2026-01-01", 1),
            ),
        )


def test_boolean_value_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_detection(
            "col1",
            (
                (date(2026, 1, 1), True),
            ),
        )


def test_negative_value_is_rejected():
    with pytest.raises(ValueError):
        build_temporal_position_change_detection(
            "col1",
            (
                (date(2026, 1, 1), -1),
            ),
        )


def test_value_above_nine_is_rejected():
    with pytest.raises(ValueError):
        build_temporal_position_change_detection(
            "col1",
            (
                (date(2026, 1, 1), 10),
            ),
        )


def test_invalid_observation_container_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_detection(
            "col1",
            "invalid",
        )


def test_invalid_result_container_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_detection_result([])


def test_invalid_result_lookup_is_rejected():
    with pytest.raises(TypeError):
        get_temporal_position_change_detection(
            object(),
            "col1",
        )


def test_unknown_position_lookup_is_rejected():
    result = build_temporal_position_change_detection_result(
        {
            "col1": (
                (date(2026, 1, 1), 1),
            ),
        }
    )

    with pytest.raises(
        ValueError,
        match="not found",
    ):
        get_temporal_position_change_detection(
            result,
            "col2",
        )


def test_getter_returns_correct_detection():
    result = build_temporal_position_change_detection_result(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 5),
            ),
        }
    )

    detection = get_temporal_position_change_detection(
        result,
        "col1",
    )

    assert detection.position == "col1"
    assert detection.changes[0].change == 4


def test_change_iterator_returns_tuple():
    detection = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 1),
            (date(2026, 1, 2), 2),
        ),
    )

    changes = iter_temporal_position_changes(detection)

    assert isinstance(changes, tuple)
    assert len(changes) == 1


def test_detection_iterator_returns_tuple():
    result = build_temporal_position_change_detection_result(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 2),
            ),
            "col2": (
                (date(2026, 1, 1), 3),
                (date(2026, 1, 2), 4),
            ),
        }
    )

    detections = iter_temporal_position_change_detections(result)

    assert isinstance(detections, tuple)
    assert len(detections) == 2


def test_change_is_frozen():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 1),
            (date(2026, 1, 2), 2),
        ),
    )

    change = result.changes[0]

    with pytest.raises((AttributeError, TypeError)):
        change.change = 99


def test_detection_is_frozen():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 1),
            (date(2026, 1,2), 2),
        ),
    )

    with pytest.raises((AttributeError, TypeError)):
        result.change_count = 99


def test_result_is_frozen():
    result = build_temporal_position_change_detection_result(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 2),
            ),
        }
    )

    with pytest.raises((AttributeError, TypeError)):
        result.position_count = 99


def test_change_contains_both_dates_and_values():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 2),
            (date(2026, 1, 3), 7),
        ),
    )

    change = result.changes[0]

    assert change.previous_date == date(2026, 1, 1)
    assert change.current_date == date(2026, 1, 3)
    assert change.previous_value == 2
    assert change.current_value == 7


def test_absolute_change_is_always_non_negative():
    result = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 8),
            (date(2026, 1, 2), 2),
        ),
    )

    assert result.changes[0].change == -6
    assert result.changes[0].absolute_change == 6


def test_no_prediction_or_ranking_fields():
    result = build_temporal_position_change_detection_result(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 2),
            ),
        }
    )

    assert not hasattr(result, "prediction")
    assert not hasattr(result, "score")
    assert not hasattr(result, "rank")
    assert not hasattr(result, "recommended_position")


def test_dataclass_types():
    detection = build_temporal_position_change_detection(
        "col1",
        (
            (date(2026, 1, 1), 1),
            (date(2026, 1, 2), 2),
        ),
    )

    result = build_temporal_position_change_detection_result(
        {
            "col1": (
                (date(2026, 1, 1), 1),
                (date(2026, 1, 2), 2),
            ),
        }
    )

    assert isinstance(
        detection.changes[0],
        TemporalPositionChange,
    )
    assert isinstance(
        detection,
        TemporalPositionChangeDetection,
    )
    assert isinstance(
        result,
        TemporalPositionChangeDetectionResult,
    )