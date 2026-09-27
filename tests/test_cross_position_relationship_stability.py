import pytest

from analytics.cross_position_relationship_stability import (
    CrossPositionRelationshipStability,
    CrossPositionRelationshipWindow,
    build_cross_position_relationship_stability,
    get_cross_position_relationship_stability_window,
    iter_cross_position_relationship_stability_windows,
)


def test_high_stability():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
            (5, 10),
            (6, 12),
        ),
        2,
    )

    assert result.position_a == "col1"
    assert result.position_b == "col2"
    assert result.window_size == 2
    assert result.window_count == 3
    assert result.valid_window_count == 3
    assert result.direction_change_count == 0
    assert result.direction_consistency == 100.0
    assert result.stability_percentage == 100.0
    assert result.stability_level == "HIGH"


def test_low_stability():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (1, 4),
            (2, 2),
            (1, 2),
            (2, 4),
        ),
        2,
    )

    assert result.window_count == 3
    assert result.valid_window_count == 3
    assert result.direction_change_count == 2
    assert result.direction_consistency == 0.0
    assert result.stability_percentage == 0.0
    assert result.stability_level == "LOW"


def test_medium_stability():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
            (1, 4),
            (2, 2),
        ),
        2,
    )

    assert result.window_count == 3
    assert result.valid_window_count == 3
    assert result.direction_change_count == 1
    assert result.direction_consistency == pytest.approx(
        50.0
    )
    assert result.stability_percentage == pytest.approx(
        50.0
    )
    assert result.stability_level == "MEDIUM"


def test_one_direction_change_gives_medium_stability():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
            (1, 4),
            (2, 2),
        ),
        2,
    )

    assert result.window_count == 3
    assert result.valid_window_count == 3
    assert result.direction_change_count == 1
    assert result.direction_consistency == pytest.approx(
        50.0
    )
    assert result.stability_level == "MEDIUM"


def test_missing_values_are_excluded():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (None, 6),
            (4, 8),
            (5, 10),
            (6, 12),
        ),
        2,
    )

    assert result.window_count == 3
    assert result.valid_window_count == 2


def test_zero_is_valid():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (0, 0),
            (1, 1),
            (2, 2),
            (3, 3),
        ),
        2,
    )

    assert result.valid_window_count == 2
    assert result.direction_consistency == 100.0
    assert result.stability_level == "HIGH"


def test_insufficient_data():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (None, 4),
        ),
        2,
    )

    assert result.window_count == 1
    assert result.valid_window_count == 0
    assert result.direction_consistency == 0.0
    assert result.strength_consistency == 0.0
    assert result.stability_level == "INSUFFICIENT_DATA"


def test_constant_window_is_insufficient():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (1, 3),
            (2, 4),
            (3, 6),
        ),
        2,
    )

    assert result.window_count == 2
    assert result.valid_window_count == 1
    assert result.stability_level == "INSUFFICIENT_DATA"


def test_window_count():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
            (5, 10),
        ),
        2,
    )

    assert result.window_count == 3


def test_window_observation_counts():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
            (5, 10),
        ),
        2,
    )

    assert tuple(
        window.observation_count
        for window in result.windows
    ) == (2, 2, 1)


def test_window_indices_are_sequential():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
        ),
        2,
    )

    assert tuple(
        window.window_index
        for window in result.windows
    ) == (1, 2)


def test_window_relationship_values():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
        ),
        2,
    )

    assert all(
        window.direction == "POSITIVE"
        for window in result.windows
    )

    assert all(
        window.strength == "STRONG"
        for window in result.windows
    )


def test_strength_change_count():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 1),
            (2, 2),
            (1, 2),
            (2, 4),
            (1, 4),
            (2, 8),
        ),
        2,
    )

    assert result.valid_window_count == 3
    assert result.strength_change_count >= 0


def test_get_window():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
        ),
        2,
    )

    window = (
        get_cross_position_relationship_stability_window(
            result,
            2,
        )
    )

    assert window.window_index == 2
    assert window.observation_count == 2


def test_unknown_window_is_rejected():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
        ),
        2,
    )

    with pytest.raises(
        ValueError,
        match="Window not found",
    ):
        get_cross_position_relationship_stability_window(
            result,
            99,
        )


def test_iterator_returns_tuple():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
        ),
        2,
    )

    windows = (
        iter_cross_position_relationship_stability_windows(
            result
        )
    )

    assert isinstance(windows, tuple)
    assert len(windows) == 2


def test_invalid_result_for_iterator():
    with pytest.raises(TypeError):
        iter_cross_position_relationship_stability_windows(
            object()
        )


def test_invalid_result_for_getter():
    with pytest.raises(TypeError):
        get_cross_position_relationship_stability_window(
            object(),
            1,
        )


def test_window_size_must_be_at_least_two():
    with pytest.raises(
        ValueError,
        match="at least 2",
    ):
        build_cross_position_relationship_stability(
            "col1",
            "col2",
            (
                (1, 2),
                (2, 4),
            ),
            1,
        )


def test_boolean_window_size_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_relationship_stability(
            "col1",
            "col2",
            (
                (1, 2),
                (2, 4),
            ),
            True,
        )


def test_invalid_window_size_type_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_relationship_stability(
            "col1",
            "col2",
            (
                (1, 2),
                (2, 4),
            ),
            "2",
        )


def test_same_positions_are_rejected():
    with pytest.raises(
        ValueError,
        match="must be different",
    ):
        build_cross_position_relationship_stability(
            "col1",
            "col1",
            (
                (1, 2),
                (2, 4),
            ),
            2,
        )


def test_invalid_position_type_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_relationship_stability(
            1,
            "col2",
            (
                (1, 2),
                (2, 4),
            ),
            2,
        )


def test_empty_position_is_rejected():
    with pytest.raises(ValueError):
        build_cross_position_relationship_stability(
            "",
            "col2",
            (
                (1, 2),
                (2, 4),
            ),
            2,
        )


def test_boolean_observation_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_relationship_stability(
            "col1",
            "col2",
            (
                (True, 2),
                (2, 4),
            ),
            2,
        )


def test_invalid_observation_value_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_relationship_stability(
            "col1",
            "col2",
            (
                ("1", 2),
                (2, 4),
            ),
            2,
        )


def test_invalid_observation_shape_is_rejected():
    with pytest.raises(ValueError):
        build_cross_position_relationship_stability(
            "col1",
            "col2",
            (
                (1,),
                (2, 4),
            ),
            2,
        )


def test_empty_observations():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (),
        2,
    )

    assert result.window_count == 0
    assert result.valid_window_count == 0
    assert result.windows == ()
    assert result.stability_level == "INSUFFICIENT_DATA"


def test_single_observation():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
        ),
        2,
    )

    assert result.window_count == 1
    assert result.valid_window_count == 0
    assert result.stability_level == "INSUFFICIENT_DATA"


def test_frozen_stability_result():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
        ),
        2,
    )

    with pytest.raises((AttributeError, TypeError)):
        result.stability_level = "HIGH"


def test_frozen_window_result():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
        ),
        2,
    )

    with pytest.raises((AttributeError, TypeError)):
        result.windows[0].direction = "NEGATIVE"


def test_dataclass_types():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
        ),
        2,
    )

    assert isinstance(
        result,
        CrossPositionRelationshipStability,
    )

    assert isinstance(
        result.windows[0],
        CrossPositionRelationshipWindow,
    )


def test_descriptive_only():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
        ),
        2,
    )

    assert not hasattr(
        result,
        "prediction",
    )

    assert not hasattr(
        result,
        "score",
    )

    assert not hasattr(
        result,
        "rank",
    )

    assert not hasattr(
        result,
        "recommended_position",
    )


def test_direction_consistency_uses_valid_windows_only():
    result = build_cross_position_relationship_stability(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (None, 3),
            (None, 4),
            (3, 6),
            (4, 8),
        ),
        2,
    )

    assert result.window_count == 3
    assert result.valid_window_count == 2
    assert result.direction_consistency == 100.0
    assert result.stability_level == "HIGH"