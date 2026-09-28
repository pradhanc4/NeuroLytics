from datetime import date

from database.models import (
    HistoricalResult,
    JodiFamily,
    JodiFamilyMember,
    PannaReference,
    PanelFamily,
    PanelFamilyMember,
)
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.jodi_family import resolve_jodi_family
from features.panna_panel_family import (
    resolve_panel_family,
    resolve_panna_family,
)
from features.point_in_time import (
    PointInTimeHistory,
)
from features.position_family import (
    PositionFamilyRecord,
    PositionFamilyResult,
    build_position_family_features,
    get_position_family_record,
    get_position_family_records,
)
from features.feature_config import FeatureConfig


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


# ---------------------------------------------------------------------------
# Active Panna / Jodi / Panel family resolution
# ---------------------------------------------------------------------------


def test_build_position_family_features_resolves_all_position_groups(db):
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

    db.add_all([
        panna,
        jodi_family,
        panel_family,
    ])
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

    db.add_all([
        jodi_member,
        panel_member,
    ])
    db.commit()

    history = _build_history(
        (1, 2, 3, 4, 5, 6, 7, 8)
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    assert result.target_date == date(2026, 9, 28)
    assert len(result.records) == 3

    assert result.records[0] == PositionFamilyRecord(
        position_group="col1-col3",
        family_type="panna",
        value="123",
        family="Panna Family A",
        family_id=None,
        is_mapped=True,
        is_active=True,
    )

    assert result.records[1] == PositionFamilyRecord(
        position_group="col4-col5",
        family_type="jodi",
        value="45",
        family="Jodi Family A",
        family_id=jodi_family.id,
        is_mapped=True,
        is_active=True,
    )

    assert result.records[2] == PositionFamilyRecord(
        position_group="col6-col8",
        family_type="panel",
        value="678",
        family="Panel Family A",
        family_id=panel_family.id,
        is_mapped=True,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Leading-zero preservation
# ---------------------------------------------------------------------------


def test_position_family_preserves_leading_zero_jodi(db):
    family = JodiFamily(
        family_name="Jodi Zero Family",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = JodiFamilyMember(
        family_id=family.id,
        jodi="05",
        digit_1=0,
        digit_2=5,
        is_active=True,
    )

    db.add(member)
    db.commit()

    history = _build_history(
        (1, 2, 3, 0, 5, 6, 7, 8)
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    jodi_record = get_position_family_record(
        result,
        "col4-col5",
    )

    assert jodi_record.value == "05"
    assert jodi_record.family == "Jodi Zero Family"
    assert jodi_record.is_mapped is True


def test_position_family_preserves_leading_zero_panna(db):
    panna = PannaReference(
        panna="005",
        digit_1=0,
        digit_2=0,
        digit_3=5,
        panna_type="Panna Zero Family",
        is_active=True,
    )

    db.add(panna)
    db.commit()

    history = _build_history(
        (0, 0, 5, 4, 5, 6, 7, 8)
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    panna_record = get_position_family_record(
        result,
        "col1-col3",
    )

    assert panna_record.value == "005"
    assert panna_record.family == "Panna Zero Family"
    assert panna_record.is_mapped is True


def test_position_family_preserves_leading_zero_panel(db):
    family = PanelFamily(
        family_name="Panel Zero Family",
        is_active=True,
    )

    db.add(family)
    db.commit()

    member = PanelFamilyMember(
        family_id=family.id,
        panel="007",
        digit_1=0,
        digit_2=0,
        digit_3=7,
        is_active=True,
    )

    db.add(member)
    db.commit()

    history = _build_history(
        (1, 2, 3, 4, 5, 0, 0, 7)
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    panel_record = get_position_family_record(
        result,
        "col6-col8",
    )

    assert panel_record.value == "007"
    assert panel_record.family == "Panel Zero Family"
    assert panel_record.is_mapped is True


# ---------------------------------------------------------------------------
# Missing / inactive mappings
# ---------------------------------------------------------------------------


def test_unmapped_position_families_are_explicit(db):
    history = _build_history(
        (1, 2, 3, 4, 5, 6, 7, 8)
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    assert result.records == (
        PositionFamilyRecord(
            position_group="col1-col3",
            family_type="panna",
            value="123",
            family=None,
            family_id=None,
            is_mapped=False,
            is_active=False,
        ),
        PositionFamilyRecord(
            position_group="col4-col5",
            family_type="jodi",
            value="45",
            family=None,
            family_id=None,
            is_mapped=False,
            is_active=False,
        ),
        PositionFamilyRecord(
            position_group="col6-col8",
            family_type="panel",
            value="678",
            family=None,
            family_id=None,
            is_mapped=False,
            is_active=False,
        ),
    )


def test_inactive_position_family_mappings_are_unmapped(db):
    panna = PannaReference(
        panna="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        panna_type="Inactive Panna Family",
        is_active=False,
    )

    jodi_family = JodiFamily(
        family_name="Inactive Jodi Family",
        is_active=False,
    )

    panel_family = PanelFamily(
        family_name="Inactive Panel Family",
        is_active=False,
    )

    db.add_all([
        panna,
        jodi_family,
        panel_family,
    ])
    db.commit()

    db.add_all([
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
    ])
    db.commit()

    history = _build_history(
        (1, 2, 3, 4, 5, 6, 7, 8)
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    for record in result.records:
        assert record.family is None
        assert record.family_id is None
        assert record.is_mapped is False
        assert record.is_active is False


# ---------------------------------------------------------------------------
# Point-in-time behavior
# ---------------------------------------------------------------------------


def test_position_family_uses_latest_prior_observation(db):
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

    db.add_all([
        first_panna,
        second_panna,
    ])
    db.commit()

    first_observation = HistoricalFeatureObservation(
        result_id=1,
        market_id=1,
        result_date=date(2026, 9, 26),
        positions=(1, 2, 3, 4, 5, 6, 7, 8),
    )

    second_observation = HistoricalFeatureObservation(
        result_id=2,
        market_id=1,
        result_date=date(2026, 9, 27),
        positions=(9, 8, 7, 4, 5, 6, 7, 8),
    )

    history = PointInTimeHistory(
        target_date=date(2026, 9, 28),
        observations=(
            first_observation,
            second_observation,
        ),
        observation_count=2,
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    panna_record = get_position_family_record(
        result,
        "col1-col3",
    )

    assert panna_record.value == "987"
    assert panna_record.family == "Second Panna Family"


def test_position_family_does_not_use_future_observation(db):
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

    db.add_all([
        panna,
        future_panna,
    ])
    db.commit()

    historical_observation = HistoricalFeatureObservation(
        result_id=1,
        market_id=1,
        result_date=date(2026, 9, 27),
        positions=(1, 2, 3, 4, 5, 6, 7, 8),
    )

    future_observation = HistoricalFeatureObservation(
        result_id=2,
        market_id=1,
        result_date=date(2026, 9, 29),
        positions=(9, 8, 7, 4, 5, 6, 7, 8),
    )

    history = PointInTimeHistory(
        target_date=date(2026, 9, 28),
        observations=(
            historical_observation,
        ),
        observation_count=1,
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    panna_record = get_position_family_record(
        result,
        "col1-col3",
    )

    assert panna_record.value == "123"
    assert panna_record.family == "Historical Panna Family"
    assert panna_record.family != "Future Panna Family"


# ---------------------------------------------------------------------------
# Empty point-in-time history
# ---------------------------------------------------------------------------


def test_position_family_with_no_history_returns_unmapped_records(db):
    history = PointInTimeHistory(
        target_date=date(2026, 9, 28),
        observations=(),
        observation_count=0,
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    assert len(result.records) == 3

    for record in result.records:
        assert record.value is None
        assert record.family is None
        assert record.family_id is None
        assert record.is_mapped is False
        assert record.is_active is False


# ---------------------------------------------------------------------------
# Result accessors
# ---------------------------------------------------------------------------


def test_get_position_family_record_returns_requested_group(db):
    history = _build_history(
        (1, 2, 3, 4, 5, 6, 7, 8)
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    record = get_position_family_record(
        result,
        "col4-col5",
    )

    assert isinstance(
        record,
        PositionFamilyRecord,
    )

    assert record.position_group == "col4-col5"
    assert record.family_type == "jodi"
    assert record.value == "45"


def test_get_position_family_records_returns_all_records(db):
    history = _build_history(
        (1, 2, 3, 4, 5, 6, 7, 8)
    )

    result = build_position_family_features(
        db=db,
        history=history,
        config=_build_config(),
    )

    records = get_position_family_records(result)

    assert isinstance(records, tuple)
    assert len(records) == 3
    assert tuple(
        record.position_group
        for record in records
    ) == (
        "col1-col3",
        "col4-col5",
        "col6-col8",
    )


def test_position_family_result_requires_exactly_eight_positions(db):
    history = PointInTimeHistory(
        target_date=date(2026, 9, 28),
        observations=(
            HistoricalFeatureObservation(
                result_id=1,
                market_id=1,
                result_date=date(2026, 9, 27),
                positions=(1, 2, 3, 4, 5, 6, 7),
            ),
        ),
        observation_count=1,
    )

    try:
        build_position_family_features(
            db=db,
            history=history,
            config=_build_config(),
        )
    except ValueError as exc:
        assert str(exc) == (
            "Historical observation must contain exactly eight positions."
        )
    else:
        raise AssertionError(
            "Expected ValueError for invalid position count."
        )