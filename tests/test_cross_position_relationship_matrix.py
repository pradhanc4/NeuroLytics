import pytest

from analytics.cross_position_relationship_matrix import (
    CrossPositionRelationship,
    CrossPositionRelationshipMatrix,
    build_cross_position_relationship,
    build_cross_position_relationship_matrix,
    get_cross_position_relationship,
    iter_cross_position_relationships,
)


def test_positive_relationship():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
            (4, 8),
        ),
    )

    assert result.position_a == "col1"
    assert result.position_b == "col2"
    assert result.valid_pair_count == 4
    assert result.correlation == pytest.approx(1.0)
    assert result.direction == "POSITIVE"
    assert result.strength == "STRONG"


def test_negative_relationship():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 8),
            (2, 6),
            (3, 4),
            (4, 2),
        ),
    )

    assert result.valid_pair_count == 4
    assert result.correlation == pytest.approx(-1.0)
    assert result.absolute_correlation == pytest.approx(1.0)
    assert result.direction == "NEGATIVE"
    assert result.strength == "STRONG"


def test_neutral_relationship():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 1),
            (2, 2),
            (3, 1),
            (4, 2),
        ),
    )

    assert result.valid_pair_count == 4
    assert result.correlation == pytest.approx(0.4472135955)
    assert result.direction == "POSITIVE"
    assert result.strength == "MODERATE"


def test_zero_correlation():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (-1, -1),
            (0, 0),
            (1, -1),
        ),
    )

    assert result.correlation == pytest.approx(0.0)
    assert result.absolute_correlation == pytest.approx(0.0)
    assert result.direction == "NEUTRAL"
    assert result.strength == "NONE"


def test_zero_values_are_valid():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (0, 0),
            (1, 1),
            (2, 2),
        ),
    )

    assert result.valid_pair_count == 3
    assert result.correlation == pytest.approx(1.0)
    assert result.direction == "POSITIVE"


def test_missing_values_are_excluded_pairwise():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 2),
            (None, 4),
            (3, None),
            (4, 8),
        ),
    )

    assert result.valid_pair_count == 2
    assert result.correlation == pytest.approx(1.0)
    assert result.direction == "POSITIVE"


def test_insufficient_data():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 2),
            (None, 4),
        ),
    )

    assert result.valid_pair_count == 1
    assert result.covariance is None
    assert result.correlation is None
    assert result.absolute_correlation is None
    assert result.direction == "INSUFFICIENT_DATA"
    assert result.strength == "INSUFFICIENT_DATA"


def test_constant_position_has_no_correlation():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 2),
            (1, 3),
            (1, 4),
            (1, 5),
        ),
    )

    assert result.valid_pair_count == 4
    assert result.correlation is None
    assert result.direction == "INSUFFICIENT_DATA"
    assert result.strength == "INSUFFICIENT_DATA"


def test_covariance_uses_population_formula():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
            (3, 6),
        ),
    )

    assert result.covariance == pytest.approx(
        4 / 3
    )


def test_weak_relationship():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 4),
            (2, 3),
            (3, 5),
            (4, 2),
            (5, 4),
        ),
    )

    assert result.correlation is not None
    assert 0 < abs(result.correlation) < 0.30
    assert result.strength == "WEAK"


def test_position_names_must_differ():
    with pytest.raises(
        ValueError,
        match="must be different",
    ):
        build_cross_position_relationship(
            "col1",
            "col1",
            (
                (1, 2),
                (2, 3),
            ),
        )


def test_empty_observations():
    result = build_cross_position_relationship(
        "col1",
        "col2",
        (),
    )

    assert result.valid_pair_count == 0
    assert result.covariance is None
    assert result.correlation is None
    assert result.direction == "INSUFFICIENT_DATA"
    assert result.strength == "INSUFFICIENT_DATA"


def test_matrix_builds_unique_pairs():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2", "col3"),
        {
            ("col1", "col2"): (
                (1, 2),
                (2, 4),
                (3, 6),
            ),
            ("col1", "col3"): (
                (1, 3),
                (2, 2),
                (3, 1),
            ),
            ("col2", "col3"): (
                (2, 3),
                (4, 2),
                (6, 1),
            ),
        },
    )

    assert matrix.positions == (
        "col1",
        "col2",
        "col3",
    )

    assert matrix.relationship_count == 3


def test_matrix_pair_order_is_preserved():
    matrix = build_cross_position_relationship_matrix(
        ("col3", "col1", "col2"),
        {
            ("col3", "col1"): (
                (1, 2),
                (2, 3),
            ),
            ("col3", "col2"): (
                (1, 4),
                (2, 5),
            ),
            ("col1", "col2"): (
                (2, 4),
                (3, 5),
            ),
        },
    )

    assert tuple(
        (
            relationship.position_a,
            relationship.position_b,
        )
        for relationship in matrix.relationships
    ) == (
        ("col3", "col1"),
        ("col3", "col2"),
        ("col1", "col2"),
    )


def test_matrix_supports_reverse_pair_key():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2"),
        {
            ("col2", "col1"): (
                (2, 1),
                (4, 2),
                (6, 3),
            ),
        },
    )

    relationship = matrix.relationships[0]

    assert relationship.position_a == "col1"
    assert relationship.position_b == "col2"
    assert relationship.correlation == pytest.approx(1.0)


def test_matrix_missing_pair_is_insufficient_data():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2", "col3"),
        {
            ("col1", "col2"): (
                (1, 2),
                (2, 3),
            ),
        },
    )

    col1_col3 = get_cross_position_relationship(
        matrix,
        "col1",
        "col3",
    )

    assert col1_col3.valid_pair_count == 0
    assert col1_col3.direction == "INSUFFICIENT_DATA"


def test_matrix_empty_positions():
    matrix = build_cross_position_relationship_matrix(
        (),
        {},
    )

    assert isinstance(
        matrix,
        CrossPositionRelationshipMatrix,
    )

    assert matrix.positions == ()
    assert matrix.relationship_count == 0
    assert matrix.relationships == ()


def test_matrix_single_position():
    matrix = build_cross_position_relationship_matrix(
        ("col1",),
        {},
    )

    assert matrix.relationship_count == 0
    assert matrix.relationships == ()


def test_duplicate_positions_are_rejected():
    with pytest.raises(
        ValueError,
        match="duplicates",
    ):
        build_cross_position_relationship_matrix(
            ("col1", "col1"),
            {},
        )


def test_invalid_positions_container():
    with pytest.raises(TypeError):
        build_cross_position_relationship_matrix(
            "col1",
            {},
        )


def test_invalid_observations_container():
    with pytest.raises(TypeError):
        build_cross_position_relationship_matrix(
            ("col1", "col2"),
            [],
        )


def test_invalid_observation_shape():
    with pytest.raises(ValueError):
        build_cross_position_relationship(
            "col1",
            "col2",
            (
                (1,),
            ),
        )


def test_boolean_value_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_relationship(
            "col1",
            "col2",
            (
                (True, 2),
                (2, 3),
            ),
        )


def test_invalid_value_type_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_relationship(
            "col1",
            "col2",
            (
                ("1", 2),
                (2, 3),
            ),
        )


def test_invalid_position_type_is_rejected():
    with pytest.raises(TypeError):
        build_cross_position_relationship(
            1,
            "col2",
            (
                (1, 2),
            ),
        )


def test_empty_position_is_rejected():
    with pytest.raises(ValueError):
        build_cross_position_relationship(
            "",
            "col2",
            (
                (1, 2),
            ),
        )


def test_get_relationship_supports_reverse_lookup():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2"),
        {
            ("col1", "col2"): (
                (1, 2),
                (2, 4),
            ),
        },
    )

    relationship = get_cross_position_relationship(
        matrix,
        "col2",
        "col1",
    )

    assert relationship.position_a == "col1"
    assert relationship.position_b == "col2"


def test_missing_relationship_is_rejected():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2"),
        {
            ("col1", "col2"): (
                (1, 2),
            ),
        },
    )

    with pytest.raises(
        ValueError,
        match="Relationship not found",
    ):
        get_cross_position_relationship(
            matrix,
            "col1",
            "col3",
        )


def test_iterator_returns_tuple():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2", "col3"),
        {},
    )

    relationships = iter_cross_position_relationships(
        matrix
    )

    assert isinstance(relationships, tuple)
    assert len(relationships) == 3


def test_iterator_rejects_invalid_matrix():
    with pytest.raises(TypeError):
        iter_cross_position_relationships(
            object()
        )


def test_getter_rejects_invalid_matrix():
    with pytest.raises(TypeError):
        get_cross_position_relationship(
            object(),
            "col1",
            "col2",
        )


def test_dataclass_types():
    relationship = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
        ),
    )

    assert isinstance(
        relationship,
        CrossPositionRelationship,
    )

    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2"),
        {
            ("col1", "col2"): (
                (1, 2),
                (2, 4),
            ),
        },
    )

    assert isinstance(
        matrix,
        CrossPositionRelationshipMatrix,
    )


def test_relationship_is_frozen():
    relationship = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
        ),
    )

    with pytest.raises((AttributeError, TypeError)):
        relationship.correlation = 0.5


def test_matrix_is_frozen():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2"),
        {},
    )

    with pytest.raises((AttributeError, TypeError)):
        matrix.relationship_count = 99


def test_descriptive_only():
    relationship = build_cross_position_relationship(
        "col1",
        "col2",
        (
            (1, 2),
            (2, 4),
        ),
    )

    assert not hasattr(
        relationship,
        "prediction",
    )

    assert not hasattr(
        relationship,
        "score",
    )

    assert not hasattr(
        relationship,
        "recommended_position",
    )


def test_three_position_matrix_has_three_pairs():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2", "col3"),
        {},
    )

    assert matrix.relationship_count == 3


def test_four_position_matrix_has_six_pairs():
    matrix = build_cross_position_relationship_matrix(
        ("col1", "col2", "col3", "col4"),
        {},
    )

    assert matrix.relationship_count == 6