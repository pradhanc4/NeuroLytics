from datetime import date

import pytest

from database.jodi_service import JodiFamilyService
from database.models import PannaReference
from database.panel_service import PanelFamilyService
from features.feature_config import FeatureConfig
from features.family_transitions import (
    FamilyTransitionRecord,
    FamilyTransitionResult,
    build_family_transition_features,
    get_family_transition_feature_names,
    get_family_transition_record,
    get_family_transition_records,
    get_family_transition_value,
)
from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.point_in_time import (
    PointInTimeHistory,
)


def _observation(
    result_id,
    result_date,
    positions,
):
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=positions,
    )


def _history(
    observations,
    target_date,
):
    return PointInTimeHistory(
        target_date=target_date,
        observations=tuple(observations),
        observation_count=len(observations),
    )


def _config(
    enabled=True,
):
    return FeatureConfig(
        family_transition_features_enabled=enabled,
    )


def _create_panna_family(
    db,
    family_name,
    panna,
):
    db.add(
        PannaReference(
            panna=panna,
            digit_1=int(panna[0]),
            digit_2=int(panna[1]),
            digit_3=int(panna[2]),
            panna_type=family_name,
            is_active=True,
        )
    )
    db.commit()


def _create_jodi_family(
    db,
    family_name,
    jodi,
):
    service = JodiFamilyService(db)

    family = service.create_family(
        family_name,
    )

    service.add_member(
        family,
        jodi,
    )

    return family


def _create_panel_family(
    db,
    family_name,
    panel,
):
    service = PanelFamilyService(db)

    family = service.create_family(
        family_name,
    )

    service.add_member(
        family,
        panel,
    )

    return family


def _create_all_family_mappings(db):
    _create_panna_family(
        db,
        "Panna Family A",
        "123",
    )

    _create_panna_family(
        db,
        "Panna Family B",
        "987",
    )

    _create_jodi_family(
        db,
        "Jodi Family A",
        "45",
    )

    _create_jodi_family(
        db,
        "Jodi Family B",
        "05",
    )

    _create_panel_family(
        db,
        "Panel Family A",
        "678",
    )

    _create_panel_family(
        db,
        "Panel Family B",
        "007",
    )


def test_result_type_is_correct(db):
    result = build_family_transition_features(
        db,
        _history(
            (),
            date(2026, 9, 28),
        ),
        _config(),
    )

    assert isinstance(
        result,
        FamilyTransitionResult,
    )


def test_three_family_types_generate_transitions(db):
    _create_all_family_mappings(db)

    observations = (
        _observation(
            1,
            date(2026, 9, 26),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 9, 27),
            (9, 8, 7, 0, 5, 0, 0, 7),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 9, 28),
        ),
        _config(),
    )

    assert len(result.records) == 3

    assert tuple(
        record.family_type
        for record in result.records
    ) == (
        "panna",
        "jodi",
        "panel",
    )


def test_panna_transition_is_resolved(db):
    _create_panna_family(
        db,
        "Panna Family A",
        "123",
    )

    _create_panna_family(
        db,
        "Panna Family B",
        "987",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 3),
        ),
        _config(),
    )

    record = get_family_transition_record(
        result,
        "col1-col3",
        "Panna Family A",
        "Panna Family B",
    )

    assert record.family_type == "panna"
    assert record.from_family == "Panna Family A"
    assert record.to_family == "Panna Family B"
    assert record.from_family_id is None
    assert record.to_family_id is None
    assert record.from_is_mapped is True
    assert record.to_is_mapped is True
    assert record.from_is_active is True
    assert record.to_is_active is True


def test_jodi_transition_is_resolved(db):
    _create_jodi_family(
        db,
        "Jodi Family A",
        "45",
    )

    _create_jodi_family(
        db,
        "Jodi Family B",
        "05",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 0, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 3),
        ),
        _config(),
    )

    record = get_family_transition_record(
        result,
        "col4-col5",
        "Jodi Family A",
        "Jodi Family B",
    )

    assert record.family_type == "jodi"
    assert record.from_family_id is not None
    assert record.to_family_id is not None


def test_panel_transition_is_resolved(db):
    _create_panel_family(
        db,
        "Panel Family A",
        "678",
    )

    _create_panel_family(
        db,
        "Panel Family B",
        "007",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 4, 5, 0, 0, 7),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 3),
        ),
        _config(),
    )

    record = get_family_transition_record(
        result,
        "col6-col8",
        "Panel Family A",
        "Panel Family B",
    )

    assert record.family_type == "panel"
    assert record.from_family_id is not None
    assert record.to_family_id is not None


def test_leading_zero_jodi_transition_is_preserved(db):
    _create_jodi_family(
        db,
        "Jodi Family A",
        "05",
    )

    _create_jodi_family(
        db,
        "Jodi Family B",
        "00",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 0, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 0, 0, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 3),
        ),
        _config(),
    )

    names = get_family_transition_feature_names(
        result,
    )

    assert (
        "jodi_family_transition_"
        "Jodi Family A_to_Jodi Family B"
        in names
    )


def test_zero_digits_are_valid_for_panna_transition(db):
    _create_panna_family(
        db,
        "Panna Zero A",
        "005",
    )

    _create_panna_family(
        db,
        "Panna Zero B",
        "000",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (0, 0, 5, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (0, 0, 0, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 3),
        ),
        _config(),
    )

    assert (
        get_family_transition_value(
            result,
            "panna_family_transition_"
            "Panna Zero A_to_Panna Zero B",
        ).from_family
        == "Panna Zero A"
    )


def test_only_consecutive_observations_create_transitions(db):
    _create_panna_family(
        db,
        "Panna Family A",
        "123",
    )

    _create_panna_family(
        db,
        "Panna Family B",
        "987",
    )

    _create_panna_family(
        db,
        "Panna Family C",
        "456",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 4, 5, 6, 7, 8),
        ),
        _observation(
            3,
            date(2026, 1, 3),
            (4, 5, 6, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 4),
        ),
        _config(),
    )

    assert (
        get_family_transition_record(
            result,
            "col1-col3",
            "Panna Family A",
            "Panna Family B",
        )
    )

    assert (
        get_family_transition_record(
            result,
            "col1-col3",
            "Panna Family B",
            "Panna Family C",
        )
    )


def test_unmapped_observation_breaks_transition_chain(db):
    _create_panna_family(
        db,
        "Panna Family A",
        "123",
    )

    _create_panna_family(
        db,
        "Panna Family B",
        "987",
    )

    _create_panna_family(
        db,
        "Panna Family C",
        "456",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (8, 8, 8, 4, 5, 6, 7, 8),
        ),
        _observation(
            3,
            date(2026, 1, 3),
            (9, 8, 7, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 4),
        ),
        _config(),
    )

    assert len(
        tuple(
            record
            for record in result.records
            if record.family_type == "panna"
        )
    ) == 0


def test_future_observation_is_not_used(db):
    _create_panna_family(
        db,
        "Historical Family",
        "123",
    )

    _create_panna_family(
        db,
        "Future Family",
        "987",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 3),
            (9, 8, 7, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 2),
        ),
        _config(),
    )

    assert result.records == ()


def test_target_date_observation_is_not_used(db):
    _create_panna_family(
        db,
        "Historical Family",
        "123",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 2),
        ),
        _config(),
    )

    assert result.records == ()


def test_single_observation_has_no_transition(db):
    _create_panna_family(
        db,
        "Panna Family A",
        "123",
    )

    result = build_family_transition_features(
        db,
        _history(
            (
                _observation(
                    1,
                    date(2026, 1, 1),
                    (1, 2, 3, 4, 5, 6, 7, 8),
                ),
            ),
            date(2026, 1, 2),
        ),
        _config(),
    )

    assert result.records == ()


def test_empty_history_has_no_transition(db):
    result = build_family_transition_features(
        db,
        _history(
            (),
            date(2026, 1, 2),
        ),
        _config(),
    )

    assert result.records == ()


def test_disabled_feature_returns_empty_result(db):
    _create_panna_family(
        db,
        "Panna Family A",
        "123",
    )

    _create_panna_family(
        db,
        "Panna Family B",
        "987",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 3),
        ),
        _config(False),
    )

    assert result.records == ()


def test_accessors_return_records(db):
    _create_panna_family(
        db,
        "Panna Family A",
        "123",
    )

    _create_panna_family(
        db,
        "Panna Family B",
        "987",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 3),
        ),
        _config(),
    )

    records = get_family_transition_records(
        result,
    )

    assert isinstance(
        records,
        tuple,
    )

    assert records
    assert all(
        isinstance(
            record,
            FamilyTransitionRecord,
        )
        for record in records
    )


def test_feature_names_are_unique(db):
    _create_panna_family(
        db,
        "Panna Family A",
        "123",
    )

    _create_panna_family(
        db,
        "Panna Family B",
        "987",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 4, 5, 6, 7, 8),
        ),
        _observation(
            3,
            date(2026, 1, 3),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_transition_features(
        db,
        _history(
            observations,
            date(2026, 1, 4),
        ),
        _config(),
    )

    names = get_family_transition_feature_names(
        result,
    )

    assert len(names) == len(set(names))


def test_feature_names_are_deterministic(db):
    _create_panna_family(
        db,
        "Panna Family A",
        "123",
    )

    _create_panna_family(
        db,
        "Panna Family B",
        "987",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (9, 8, 7, 4, 5, 6, 7, 8),
        ),
    )

    history = _history(
        observations,
        date(2026, 1, 3),
    )

    first = build_family_transition_features(
        db,
        history,
        _config(),
    )

    second = build_family_transition_features(
        db,
        history,
        _config(),
    )

    assert (
        get_family_transition_feature_names(first)
        == get_family_transition_feature_names(second)
    )


def test_unknown_feature_name_is_rejected(db):
    result = build_family_transition_features(
        db,
        _history(
            (),
            date(2026, 1, 2),
        ),
        _config(),
    )

    with pytest.raises(ValueError):
        get_family_transition_value(
            result,
            "unknown_feature",
        )


def test_invalid_feature_name_type_is_rejected(db):
    result = build_family_transition_features(
        db,
        _history(
            (),
            date(2026, 1, 2),
        ),
        _config(),
    )

    with pytest.raises(TypeError):
        get_family_transition_value(
            result,
            123,
        )


def test_invalid_result_type_is_rejected():
    with pytest.raises(TypeError):
        get_family_transition_records(
            "invalid",
        )


def test_invalid_history_is_rejected(db):
    with pytest.raises(TypeError):
        build_family_transition_features(
            db,
            "invalid",
            _config(),
        )


def test_invalid_config_is_rejected(db):
    with pytest.raises(TypeError):
        build_family_transition_features(
            db,
            _history(
                (),
                date(2026, 1, 2),
            ),
            "invalid",
        )


def test_missing_database_is_rejected():
    with pytest.raises(ValueError):
        build_family_transition_features(
            None,
            _history(
                (),
                date(2026, 1, 2),
            ),
            _config(),
        )


def test_target_date_is_preserved(db):
    target_date = date(2026, 2, 10)

    result = build_family_transition_features(
        db,
        _history(
            (),
            target_date,
        ),
        _config(),
    )

    assert result.target_date == target_date