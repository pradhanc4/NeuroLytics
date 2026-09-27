from datetime import date

import pytest

from analytics.temporal_position_change_classification import (
    CHANGE_MAGNITUDE_CLASSES,
    CLASSIFICATION_MISSING,
    CLASSIFICATION_UNCHANGED,
    TemporalPositionChangeClassification,
    TemporalPositionChangeClassificationCollection,
    TemporalPositionChangeClassificationResult,
    build_temporal_position_change_classification,
    build_temporal_position_change_classification_collection,
    classify_temporal_position_change,
    get_classification_counts,
    get_temporal_position_change_classification,
    iter_temporal_position_change_classifications,
)
from analytics.temporal_position_change_detection import (
    build_temporal_position_change_detection,
)


def make_change(
    previous_value: int | None,
    current_value: int | None,
    position: str = "col1",
) -> object:
    result = build_temporal_position_change_detection(
        position,
        (
            (date(2026, 1, 1), previous_value),
            (date(2026, 1, 2), current_value),
        ),
    )

    return result.changes[0]


def test_expected_magnitude_classes():
    assert CHANGE_MAGNITUDE_CLASSES == (
        "LOW",
        "MEDIUM",
        "HIGH",
    )


def test_unchanged_classification():
    change = make_change(4, 4)

    classification = classify_temporal_position_change(change)

    assert classification.direction == "UNCHANGED"
    assert classification.absolute_change == 0
    assert classification.magnitude_class == CLASSIFICATION_UNCHANGED


def test_low_magnitude_classification():
    change = make_change(4, 5)

    classification = classify_temporal_position_change(change)

    assert classification.direction == "INCREASE"
    assert classification.absolute_change == 1
    assert classification.magnitude_class == "LOW"


def test_medium_magnitude_lower_boundary():
    change = make_change(1, 3)

    classification = classify_temporal_position_change(change)

    assert classification.absolute_change == 2
    assert classification.magnitude_class == "MEDIUM"


def test_medium_magnitude_upper_boundary():
    change = make_change(1, 5)

    classification = classify_temporal_position_change(change)

    assert classification.absolute_change == 4
    assert classification.magnitude_class == "MEDIUM"


def test_high_magnitude_lower_boundary():
    change = make_change(0, 5)

    classification = classify_temporal_position_change(change)

    assert classification.absolute_change == 5
    assert classification.magnitude_class == "HIGH"


def test_high_magnitude_maximum_digit_change():
    change = make_change(0, 9)

    classification = classify_temporal_position_change(change)

    assert classification.absolute_change == 9
    assert classification.magnitude_class == "HIGH"


def test_decrease_preserves_direction():
    change = make_change(8, 3)

    classification = classify_temporal_position_change(change)

    assert classification.change == -5
    assert classification.absolute_change == 5
    assert classification.direction == "DECREASE"
    assert classification.magnitude_class == "HIGH"


def test_missing_previous_value_is_missing_classification():
    change = make_change(None, 4)

    classification = classify_temporal_position_change(change)

    assert classification.change is None
    assert classification.absolute_change is None
    assert classification.magnitude_class == CLASSIFICATION_MISSING


def test_missing_current_value_is_missing_classification():
    change = make_change(4, None)

    classification = classify_temporal_position_change(change)

    assert classification.change is None
    assert classification.absolute_change is None
    assert classification.magnitude_class == CLASSIFICATION_MISSING


def test_missing_classification_does_not_become_zero():
    change = make_change(None, 0)

    classification = classify_temporal_position_change(change)

    assert classification.previous_value is None
    assert classification.current_value == 0
    assert classification.absolute_change is None
    assert classification.magnitude_class == CLASSIFICATION_MISSING


def test_zero_is_valid_for_classification():
    change = make_change(0, 1)

    classification = classify_temporal_position_change(change)

    assert classification.previous_value == 0
    assert classification.current_value == 1
    assert classification.magnitude_class == "LOW"


def test_result_builder():
    changes = (
        make_change(1, 2),
        make_change(2, 6),
    )

    result = build_temporal_position_change_classification(
        "col1",
        changes,
    )

    assert result.position == "col1"
    assert result.change_count == 2
    assert result.classifications[0].magnitude_class == "LOW"
    assert result.classifications[1].magnitude_class == "MEDIUM"


def test_result_preserves_change_order():
    changes = (
        make_change(1, 2),
        make_change(2, 7),
        make_change(7, 7),
    )

    result = build_temporal_position_change_classification(
        "col1",
        changes,
    )

    assert tuple(
        item.magnitude_class
        for item in result.classifications
    ) == (
        "LOW",
        "HIGH",
        "UNCHANGED",
    )


def test_collection_builder():
    result1 = build_temporal_position_change_classification(
        "col1",
        (make_change(1, 2, "col1"),),
    )

    result2 = build_temporal_position_change_classification(
        "col2",
        (make_change(2, 4, "col2"),),
    )

    collection = (
        build_temporal_position_change_classification_collection(
            (result1, result2)
        )
    )

    assert collection.position_count == 2
    assert collection.positions == ("col1", "col2")
    assert len(collection.results) == 2


def test_collection_preserves_position_order():
    result1 = build_temporal_position_change_classification(
        "col4",
        (make_change(1, 2, "col4"),),
    )

    result2 = build_temporal_position_change_classification(
        "col1",
        (make_change(2, 3, "col1"),),
    )

    collection = (
        build_temporal_position_change_classification_collection(
            (result1, result2)
        )
    )

    assert collection.positions == ("col4", "col1")


def test_duplicate_positions_are_rejected():
    result1 = build_temporal_position_change_classification(
        "col1",
        (make_change(1, 2, "col1"),),
    )

    result2 = build_temporal_position_change_classification(
        "col1",
        (make_change(2, 3, "col1"),),
    )

    with pytest.raises(
        ValueError,
        match="duplicate positions",
    ):
        build_temporal_position_change_classification_collection(
            (result1, result2)
        )


def test_getter_returns_requested_index():
    result = build_temporal_position_change_classification(
        "col1",
        (
            make_change(1, 2),
            make_change(2, 7),
        ),
    )

    classification = get_temporal_position_change_classification(
        result,
        1,
    )

    assert classification.absolute_change == 5
    assert classification.magnitude_class == "HIGH"


def test_negative_index_is_supported_by_tuple_semantics():
    result = build_temporal_position_change_classification(
        "col1",
        (
            make_change(1, 2),
            make_change(2, 7),
        ),
    )

    classification = get_temporal_position_change_classification(
        result,
        -1,
    )

    assert classification.magnitude_class == "HIGH"


def test_invalid_index_type_is_rejected():
    result = build_temporal_position_change_classification(
        "col1",
        (make_change(1, 2),),
    )

    with pytest.raises(TypeError):
        get_temporal_position_change_classification(
            result,
            "0",
        )


def test_missing_index_is_rejected():
    result = build_temporal_position_change_classification(
        "col1",
        (make_change(1, 2),),
    )

    with pytest.raises(
        ValueError,
        match="classification index not found",
    ):
        get_temporal_position_change_classification(
            result,
            5,
        )


def test_iterator_returns_tuple():
    result = build_temporal_position_change_classification(
        "col1",
        (
            make_change(1, 2),
            make_change(2, 3),
        ),
    )

    classifications = (
        iter_temporal_position_change_classifications(result)
    )

    assert isinstance(classifications, tuple)
    assert len(classifications) == 2


def test_classification_counts_preserve_first_seen_order():
    result = build_temporal_position_change_classification(
        "col1",
        (
            make_change(1, 2),
            make_change(2, 7),
            make_change(7, 7),
            make_change(7, 8),
        ),
    )

    counts = get_classification_counts(result)

    assert counts == (
        ("LOW", 2),
        ("HIGH", 1),
        ("UNCHANGED", 1),
    )


def test_classification_counts_include_missing():
    result = build_temporal_position_change_classification(
        "col1",
        (
            make_change(None, 2),
            make_change(2, 3),
            make_change(3, 8),
        ),
    )

    counts = get_classification_counts(result)

    assert counts == (
        ("MISSING", 1),
        ("LOW", 1),
        ("HIGH", 1),
    )


def test_empty_result():
    result = build_temporal_position_change_classification(
        "col1",
        (),
    )

    assert result.change_count == 0
    assert result.classifications == ()
    assert get_classification_counts(result) == ()


def test_invalid_change_is_rejected():
    with pytest.raises(TypeError):
        classify_temporal_position_change(object())


def test_invalid_changes_container_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_classification(
            "col1",
            "invalid",
        )


def test_position_mismatch_is_rejected():
    change = build_temporal_position_change_detection(
        "col2",
        (
            (date(2026, 1, 1), 1),
            (date(2026, 1, 2), 2),
        ),
    ).changes[0]

    with pytest.raises(
        ValueError,
        match="supplied position",
    ):
        build_temporal_position_change_classification(
            "col1",
            (change,),
        )


def test_invalid_position_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_classification(
            "",
            (),
        )


def test_invalid_collection_container_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_classification_collection(
            "invalid",
        )


def test_invalid_collection_item_is_rejected():
    with pytest.raises(TypeError):
        build_temporal_position_change_classification_collection(
            (object(),),
        )


def test_result_is_frozen():
    result = build_temporal_position_change_classification(
        "col1",
        (make_change(1, 2),),
    )

    with pytest.raises((AttributeError, TypeError)):
        result.change_count = 99


def test_classification_is_frozen():
    result = build_temporal_position_change_classification(
        "col1",
        (make_change(1, 2),),
    )

    with pytest.raises((AttributeError, TypeError)):
        result.classifications[0].magnitude_class = "HIGH"


def test_collection_is_frozen():
    result = build_temporal_position_change_classification(
        "col1",
        (make_change(1, 2),),
    )

    collection = (
        build_temporal_position_change_classification_collection(
            (result,)
        )
    )

    with pytest.raises((AttributeError, TypeError)):
        collection.position_count = 99


def test_dataclass_types():
    change = make_change(1, 2)

    classification = classify_temporal_position_change(change)

    result = build_temporal_position_change_classification(
        "col1",
        (change,),
    )

    collection = (
        build_temporal_position_change_classification_collection(
            (result,)
        )
    )

    assert isinstance(
        classification,
        TemporalPositionChangeClassification,
    )

    assert isinstance(
        result,
        TemporalPositionChangeClassificationResult,
    )

    assert isinstance(
        collection,
        TemporalPositionChangeClassificationCollection,
    )


def test_classification_preserves_dates_and_values():
    change = make_change(2, 7)

    classification = classify_temporal_position_change(change)

    assert classification.previous_date == date(2026, 1, 1)
    assert classification.current_date == date(2026, 1, 2)
    assert classification.previous_value == 2
    assert classification.current_value == 7
    assert classification.change == 5
    assert classification.absolute_change == 5


def test_descriptive_only():
    result = build_temporal_position_change_classification(
        "col1",
        (make_change(1, 2),),
    )

    assert not hasattr(result, "prediction")
    assert not hasattr(result, "score")
    assert not hasattr(result, "rank")
    assert not hasattr(result, "recommended_position")