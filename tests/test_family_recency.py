from datetime import date

import pytest

from database.jodi_service import JodiFamilyService
from database.models import PannaReference
from database.panel_service import PanelFamilyService
from features.feature_config import FeatureConfig
from features.family_recency import (
    FamilyRecencyRecord,
    FamilyRecencyResult,
    build_family_recency_features,
    get_family_recency_feature_names,
    get_family_recency_record,
    get_family_recency_records,
    get_family_recency_value,
)
from features.point_in_time import (
    HistoricalFeatureObservation,
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


def _create_panna_family(
    db,
    family_name="Panna Family A",
    panna="123",
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
    family_name="Jodi Family A",
    jodi="45",
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
    family_name="Panel Family A",
    panel="678",
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


def test_result_type_is_correct(db):
    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert isinstance(
        result,
        FamilyRecencyResult,
    )


def test_record_type_is_correct(db):
    _create_panna_family(db)

    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    record = get_family_recency_record(
        result,
        "panna_family_recency_Panna Family A",
    )

    assert isinstance(
        record,
        FamilyRecencyRecord,
    )


def test_active_family_is_represented_even_without_history(db):
    _create_panna_family(db)

    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_recency_Panna Family A",
        )
        is None
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_seen_within_lookback_3_Panna Family A",
        )
        is False
    )


def test_recency_counts_observations_since_last_seen(db):
    _create_panna_family(
        db,
        panna="123",
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
            (9, 9, 9, 4, 5, 6, 7, 8),
        ),
        _observation(
            3,
            date(2026, 1, 3),
            (8, 8, 8, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 4),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_recency_Panna Family A",
        )
        == 2
    )


def test_latest_family_occurrence_has_zero_recency(db):
    _create_panna_family(
        db,
        panna="123",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (9, 9, 9, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 3),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_recency_Panna Family A",
        )
        == 0
    )


def test_seen_within_lookback_is_true_when_recency_is_inside_window(db):
    _create_panna_family(
        db,
        panna="123",
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
            (9, 9, 9, 4, 5, 6, 7, 8),
        ),
        _observation(
            3,
            date(2026, 1, 3),
            (8, 8, 8, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 4),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_seen_within_lookback_3_Panna Family A",
        )
        is True
    )


def test_seen_within_lookback_is_false_at_boundary(db):
    _create_panna_family(
        db,
        panna="123",
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
            (9, 9, 9, 4, 5, 6, 7, 8),
        ),
        _observation(
            3,
            date(2026, 1, 3),
            (8, 8, 8, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 4),
        ),
        FeatureConfig(
            recency_lookbacks=(2,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_seen_within_lookback_2_Panna Family A",
        )
        is False
    )


def test_target_date_is_never_used(db):
    _create_panna_family(
        db,
        panna="123",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (9, 9, 9, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 2),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_recency_Panna Family A",
        )
        is None
    )


def test_future_observation_is_never_used(db):
    _create_panna_family(
        db,
        panna="123",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (9, 9, 9, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 3),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 2),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_recency_Panna Family A",
        )
        is None
    )


def test_unmapped_observations_do_not_create_family_recency(db):
    _create_panna_family(
        db,
        panna="123",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (9, 9, 9, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 2),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_recency_Panna Family A",
        )
        is None
    )


def test_zero_digits_are_valid_for_family_mapping(db):
    _create_panna_family(
        db,
        panna="005",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (0, 0, 5, 4, 5, 6, 7, 8),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 2),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panna_family_recency_Panna Family A",
        )
        == 0
    )


def test_multiple_lookbacks_are_generated(db):
    _create_panna_family(db)

    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        FeatureConfig(
            recency_lookbacks=(3, 5, 7),
        ),
    )

    names = get_family_recency_feature_names(
        result,
    )

    assert (
        "panna_family_seen_within_lookback_3_Panna Family A"
        in names
    )

    assert (
        "panna_family_seen_within_lookback_5_Panna Family A"
        in names
    )

    assert (
        "panna_family_seen_within_lookback_7_Panna Family A"
        in names
    )


def test_jodi_family_recency_is_generated(db):
    _create_jodi_family(
        db,
        family_name="Jodi Family A",
        jodi="05",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 0, 5, 6, 7, 8),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 2),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "jodi_family_recency_Jodi Family A",
        )
        == 0
    )


def test_panel_family_recency_is_generated(db):
    _create_panel_family(
        db,
        family_name="Panel Family A",
        panel="005",
    )

    observations = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 0, 0, 5),
        ),
    )

    result = build_family_recency_features(
        db,
        _history(
            observations,
            date(2026, 1, 2),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        get_family_recency_value(
            result,
            "panel_family_recency_Panel Family A",
        )
        == 0
    )


def test_inactive_panna_family_is_excluded(db):
    reference = PannaReference(
        panna="123",
        digit_1=1,
        digit_2=2,
        digit_3=3,
        panna_type="Inactive Family",
        is_active=False,
    )

    db.add(reference)
    db.commit()

    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert (
        "panna_family_recency_Inactive Family"
        not in get_family_recency_feature_names(
            result
        )
    )


def test_accessors_return_records(db):
    _create_panna_family(db)

    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    records = get_family_recency_records(
        result,
    )

    assert isinstance(records, tuple)
    assert records
    assert all(
        isinstance(
            record,
            FamilyRecencyRecord,
        )
        for record in records
    )


def test_feature_names_are_unique(db):
    _create_panna_family(db)

    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        FeatureConfig(
            recency_lookbacks=(3, 5),
        ),
    )

    names = get_family_recency_feature_names(
        result,
    )

    assert len(names) == len(set(names))


def test_feature_names_are_deterministic(db):
    _create_panna_family(
        db,
        family_name="Family B",
        panna="456",
    )

    _create_panna_family(
        db,
        family_name="Family A",
        panna="123",
    )

    history = _history(
        (),
        date(2026, 1, 5),
    )

    config = FeatureConfig(
        recency_lookbacks=(3, 5),
    )

    first = build_family_recency_features(
        db,
        history,
        config,
    )

    second = build_family_recency_features(
        db,
        history,
        config,
    )

    assert (
        get_family_recency_feature_names(first)
        == get_family_recency_feature_names(second)
    )


def test_disabled_feature_returns_empty_result(db):
    _create_panna_family(db)

    config = FeatureConfig(
        family_recency_features_enabled=False,
        recency_lookbacks=(3,),
    )

    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        config,
    )

    assert result.records == ()


def test_invalid_db_is_rejected():
    with pytest.raises(TypeError):
        build_family_recency_features(
            None,
            _history(
                (),
                date(2026, 1, 5),
            ),
            FeatureConfig(
                recency_lookbacks=(3,),
            ),
        )


def test_invalid_history_is_rejected(db):
    with pytest.raises(TypeError):
        build_family_recency_features(
            db,
            "invalid",
            FeatureConfig(
                recency_lookbacks=(3,),
            ),
        )


def test_invalid_config_is_rejected(db):
    with pytest.raises(TypeError):
        build_family_recency_features(
            db,
            _history(
                (),
                date(2026, 1, 5),
            ),
            "invalid",
        )


def test_unknown_feature_name_is_rejected(db):
    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    with pytest.raises(ValueError):
        get_family_recency_value(
            result,
            "unknown_feature",
        )


def test_invalid_feature_name_type_is_rejected(db):
    result = build_family_recency_features(
        db,
        _history(
            (),
            date(2026, 1, 5),
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    with pytest.raises(TypeError):
        get_family_recency_value(
            result,
            123,
        )


def test_invalid_result_type_is_rejected():
    with pytest.raises(TypeError):
        get_family_recency_records(
            "invalid",
        )


def test_target_date_is_preserved(db):
    target_date = date(2026, 2, 10)

    result = build_family_recency_features(
        db,
        _history(
            (),
            target_date,
        ),
        FeatureConfig(
            recency_lookbacks=(3,),
        ),
    )

    assert result.target_date == target_date