from datetime import date

from database.models import (
    JodiFamily,
    JodiFamilyMember,
    PannaReference,
    PanelFamily,
    PanelFamilyMember,
)
from features.feature_config import FeatureConfig
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.point_in_time import (
    PointInTimeHistory,
)
from features.cross_position_family_relationships import (
    CrossPositionFamilyRelationshipRecord,
    CrossPositionFamilyRelationshipResult,
    build_cross_position_family_relationships,
    get_cross_position_family_relationship,
    get_cross_position_family_relationships,
)


def _build_history(
    positions: tuple[int, ...],
    target_date: date = date(2026, 9, 28),
) -> PointInTimeHistory:
    observation = HistoricalFeatureObservation(
        result_id=1,
        market_id=1,
        result_date=date(2026, 9, 27),
        positions=positions,
    )

    return PointInTimeHistory(
        target_date=target_date,
        observations=(observation,),
        observation_count=1,
    )


def _build_config() -> FeatureConfig:
    return FeatureConfig()


def _create_active_family_mappings(db):
    panna = PannaReference(
        panna="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        panna_type="Panna Family A",
        is_active=True,
    )

    jodi_family = JodiFamily(
        family_name="Jodi Family A",
        is_active=True,
    )

    panel_family = PanelFamily(
        family_name="Panel Family A",
        is_active=True,
    )

    db.add_all(
        [
            panna,
            jodi_family,
            panel_family,
        ]
    )
    db.commit()

    jodi_member = JodiFamilyMember(
        family_id=jodi_family.id,
        jodi="45",
        digit_1=4,
        digit_2=5,
        is_active=True,
    )

    panel_member = PanelFamilyMember(
        family_id=panel_family.id,
        panel="678",
        digit_1=6,
        digit_2=7,
        digit_3=8,
        is_active=True,
    )

    db.add_all(
        [
            jodi_member,
            panel_member,
        ]
    )
    db.commit()


# ---------------------------------------------------------------------------
# Basic output contract
# ---------------------------------------------------------------------------


def test_cross_position_family_relationships_return_expected_type(db):
    _create_active_family_mappings(db)

    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 4, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    assert isinstance(
        result,
        CrossPositionFamilyRelationshipResult,
    )

    assert result.target_date == date(2026, 9, 28)


def test_cross_position_family_relationships_generate_three_pairs(db):
    _create_active_family_mappings(db)

    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 4, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    assert len(result.records) == 3

    assert tuple(
        (
            record.left_position_group,
            record.right_position_group,
        )
        for record in result.records
    ) == (
        ("col1-col3", "col4-col5"),
        ("col1-col3", "col6-col8"),
        ("col4-col5", "col6-col8"),
    )


def test_cross_position_family_relationships_resolve_all_families(db):
    _create_active_family_mappings(db)

    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 4, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    panna_jodi = result.records[0]
    panna_panel = result.records[1]
    jodi_panel = result.records[2]

    assert panna_jodi.left_family == "Panna Family A"
    assert panna_jodi.right_family == "Jodi Family A"

    assert panna_panel.left_family == "Panna Family A"
    assert panna_panel.right_family == "Panel Family A"

    assert jodi_panel.left_family == "Jodi Family A"
    assert jodi_panel.right_family == "Panel Family A"


# ---------------------------------------------------------------------------
# Leading-zero preservation
# ---------------------------------------------------------------------------


def test_cross_position_family_relationships_preserve_leading_zero_jodi(
    db,
):
    panna = PannaReference(
        panna="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        panna_type="Panna Family",
        is_active=True,
    )

    jodi_family = JodiFamily(
        family_name="Jodi Zero Family",
        is_active=True,
    )

    panel_family = PanelFamily(
        family_name="Panel Family",
        is_active=True,
    )

    db.add_all(
        [
            panna,
            jodi_family,
            panel_family,
        ]
    )
    db.commit()

    db.add_all(
        [
            JodiFamilyMember(
                family_id=jodi_family.id,
                jodi="05",
                digit_1=0,
                digit_2=5,
                is_active=True,
            ),
            PanelFamilyMember(
                family_id=panel_family.id,
                panel="678",
                digit_1=6,
                digit_2=7,
                digit_3=8,
                is_active=True,
            ),
        ]
    )
    db.commit()

    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 0, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    relationship = get_cross_position_family_relationship(
        result,
        "col1-col3",
        "col4-col5",
    )

    assert relationship.left_value == "123"
    assert relationship.right_value == "05"
    assert relationship.right_family == "Jodi Zero Family"


def test_cross_position_family_relationships_preserve_leading_zero_panna(
    db,
):
    panna = PannaReference(
        panna="005",
        digit_1=0,
        digit_2=0,
        digit_3=5,
        panna_type="Panna Zero Family",
        is_active=True,
    )

    jodi_family = JodiFamily(
        family_name="Jodi Family",
        is_active=True,
    )

    panel_family = PanelFamily(
        family_name="Panel Family",
        is_active=True,
    )

    db.add_all(
        [
            panna,
            jodi_family,
            panel_family,
        ]
    )
    db.commit()

    db.add_all(
        [
            JodiFamilyMember(
                family_id=jodi_family.id,
                jodi="45",
                digit_1=4,
                digit_2=5,
                is_active=True,
            ),
            PanelFamilyMember(
                family_id=panel_family.id,
                panel="678",
                digit_1=6,
                digit_2=7,
                digit_3=8,
                is_active=True,
            ),
        ]
    )
    db.commit()

    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (0, 0, 5, 4, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    relationship = get_cross_position_family_relationship(
        result,
        "col1-col3",
        "col4-col5",
    )

    assert relationship.left_value == "005"
    assert relationship.left_family == "Panna Zero Family"


def test_cross_position_family_relationships_preserve_leading_zero_panel(
    db,
):
    panna = PannaReference(
        panna="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        panna_type="Panna Family",
        is_active=True,
    )

    jodi_family = JodiFamily(
        family_name="Jodi Family",
        is_active=True,
    )

    panel_family = PanelFamily(
        family_name="Panel Zero Family",
        is_active=True,
    )

    db.add_all(
        [
            panna,
            jodi_family,
            panel_family,
        ]
    )
    db.commit()

    db.add_all(
        [
            JodiFamilyMember(
                family_id=jodi_family.id,
                jodi="45",
                digit_1=4,
                digit_2=5,
                is_active=True,
            ),
            PanelFamilyMember(
                family_id=panel_family.id,
                panel="007",
                digit_1=0,
                digit_2=0,
                digit_3=7,
                is_active=True,
            ),
        ]
    )
    db.commit()

    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 4, 5, 0, 0, 7)
        ),
        config=_build_config(),
    )

    relationship = get_cross_position_family_relationship(
        result,
        "col1-col3",
        "col6-col8",
    )

    assert relationship.right_value == "007"
    assert relationship.right_family == "Panel Zero Family"


# ---------------------------------------------------------------------------
# Unmapped / inactive mappings
# ---------------------------------------------------------------------------


def test_cross_position_family_relationships_preserve_unmapped_states(
    db,
):
    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 4, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    assert len(result.records) == 3

    for record in result.records:
        assert record.left_family is None
        assert record.right_family is None
        assert record.left_is_mapped is False
        assert record.right_is_mapped is False
        assert record.left_is_active is False
        assert record.right_is_active is False


def test_cross_position_family_relationships_do_not_infer_family_from_digits(
    db,
):
    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 4, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    for record in result.records:
        assert record.left_family is None
        assert record.right_family is None


# ---------------------------------------------------------------------------
# Point-in-time behavior
# ---------------------------------------------------------------------------


def test_cross_position_family_relationships_use_latest_prior_observation(
    db,
):
    first_panna = PannaReference(
        panna="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        panna_type="First Panna Family",
        is_active=True,
    )

    second_panna = PannaReference(
        panna="987",
        digit_1=9,
        digit_2=8,
        digit_3=7,
        panna_type="Second Panna Family",
        is_active=True,
    )

    db.add_all(
        [
            first_panna,
            second_panna,
        ]
    )
    db.commit()

    history = PointInTimeHistory(
        target_date=date(2026, 9, 28),
        observations=(
            HistoricalFeatureObservation(
                result_id=1,
                market_id=1,
                result_date=date(2026, 9, 26),
                positions=(1, 2, 3, 4, 5, 6, 7, 8),
            ),
            HistoricalFeatureObservation(
                result_id=2,
                market_id=1,
                result_date=date(2026, 9, 27),
                positions=(9, 8, 7, 4, 5, 6, 7, 8),
            ),
        ),
        observation_count=2,
    )

    result = build_cross_position_family_relationships(
        db=db,
        history=history,
        config=_build_config(),
    )

    relationship = get_cross_position_family_relationship(
        result,
        "col1-col3",
        "col4-col5",
    )

    assert relationship.left_value == "987"
    assert relationship.left_family == "Second Panna Family"


def test_cross_position_family_relationships_do_not_use_future_observation(
    db,
):
    panna = PannaReference(
        panna="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        panna_type="Historical Panna Family",
        is_active=True,
    )

    future_panna = PannaReference(
        panna="987",
        digit_1=9,
        digit_2=8,
        digit_3=7,
        panna_type="Future Panna Family",
        is_active=True,
    )

    db.add_all(
        [
            panna,
            future_panna,
        ]
    )
    db.commit()

    history = PointInTimeHistory(
        target_date=date(2026, 9, 28),
        observations=(
            HistoricalFeatureObservation(
                result_id=1,
                market_id=1,
                result_date=date(2026, 9, 27),
                positions=(1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        observation_count=1,
    )

    result = build_cross_position_family_relationships(
        db=db,
        history=history,
        config=_build_config(),
    )

    relationship = get_cross_position_family_relationship(
        result,
        "col1-col3",
        "col4-col5",
    )

    assert relationship.left_value == "123"
    assert relationship.left_family == "Historical Panna Family"
    assert relationship.left_family != "Future Panna Family"


# ---------------------------------------------------------------------------
# Empty history
# ---------------------------------------------------------------------------


def test_cross_position_family_relationships_with_no_history_return_explicit_empty_state(
    db,
):
    history = PointInTimeHistory(
        target_date=date(2026, 9, 28),
        observations=(),
        observation_count=0,
    )

    result = build_cross_position_family_relationships(
        db=db,
        history=history,
        config=_build_config(),
    )

    assert len(result.records) == 3

    for record in result.records:
        assert record.left_value is None
        assert record.right_value is None
        assert record.left_family is None
        assert record.right_family is None
        assert record.left_is_mapped is False
        assert record.right_is_mapped is False


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------


def test_get_cross_position_family_relationships_returns_tuple(db):
    _create_active_family_mappings(db)

    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 4, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    records = get_cross_position_family_relationships(
        result
    )

    assert isinstance(records, tuple)
    assert len(records) == 3


def test_get_cross_position_family_relationship_returns_expected_record(
    db,
):
    _create_active_family_mappings(db)

    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 4, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    record = get_cross_position_family_relationship(
        result,
        "col4-col5",
        "col6-col8",
    )

    assert isinstance(
        record,
        CrossPositionFamilyRelationshipRecord,
    )

    assert record.left_position_group == "col4-col5"
    assert record.right_position_group == "col6-col8"
    assert record.left_family == "Jodi Family A"
    assert record.right_family == "Panel Family A"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_cross_position_family_relationships_require_database(
    db,
):
    history = _build_history(
        (1, 2, 3, 4, 5, 6, 7, 8)
    )

    try:
        build_cross_position_family_relationships(
            db=None,
            history=history,
            config=_build_config(),
        )
    except ValueError as exc:
        assert str(exc) == "db is required."
    else:
        raise AssertionError(
            "Expected ValueError when db is missing."
        )


def test_cross_position_family_relationships_reject_invalid_history(
    db,
):
    try:
        build_cross_position_family_relationships(
            db=db,
            history="invalid",
            config=_build_config(),
        )
    except TypeError as exc:
        assert str(exc) == (
            "history must be a PointInTimeHistory instance."
        )
    else:
        raise AssertionError(
            "Expected TypeError for invalid history."
        )


def test_cross_position_family_relationships_reject_invalid_result_accessor():
    try:
        get_cross_position_family_relationships(
            "invalid"
        )
    except TypeError as exc:
        assert str(exc) == (
            "result must be a "
            "CrossPositionFamilyRelationshipResult instance."
        )
    else:
        raise AssertionError(
            "Expected TypeError for invalid result."
        )


def test_cross_position_family_relationship_accessor_rejects_unknown_pair(
    db,
):
    _create_active_family_mappings(db)

    result = build_cross_position_family_relationships(
        db=db,
        history=_build_history(
            (1, 2, 3, 4, 5, 6, 7, 8)
        ),
        config=_build_config(),
    )

    try:
        get_cross_position_family_relationship(
            result,
            "col6-col8",
            "col1-col3",
        )
    except ValueError as exc:
        assert str(exc) == (
            "Cross-position family relationship not found: "
            "col6-col8 -> col1-col3"
        )
    else:
        raise AssertionError(
            "Expected ValueError for unknown pair."
        )