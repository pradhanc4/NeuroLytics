from datetime import date

import pytest

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
from features.historical_family_frequency import (
    HistoricalFamilyFrequencyResult,
    build_historical_family_frequency_features,
    get_historical_family_frequency_feature_names,
    get_historical_family_frequency_feature_value,
    get_historical_family_frequency_feature_values,
)


def _observation(
    result_id: int,
    result_date: date,
    positions: tuple[int, ...],
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=result_date,
        positions=positions,
    )


def _create_family_mappings(db):
    db.add_all(
        [
            PannaReference(
                panna="123",
                digit_1=1,
                digit_2=2,
                digit_3=3,
                panna_type="Panna A",
                is_active=True,
            ),
            PannaReference(
                panna="456",
                digit_1=4,
                digit_2=5,
                digit_3=6,
                panna_type="Panna B",
                is_active=True,
            ),
            JodiFamily(
                family_name="Jodi A",
                is_active=True,
            ),
            JodiFamily(
                family_name="Jodi B",
                is_active=True,
            ),
            PanelFamily(
                family_name="Panel A",
                is_active=True,
            ),
            PanelFamily(
                family_name="Panel B",
                is_active=True,
            ),
        ]
    )
    db.commit()

    jodi_a = db.query(JodiFamily).filter(
        JodiFamily.family_name == "Jodi A"
    ).one()

    jodi_b = db.query(JodiFamily).filter(
        JodiFamily.family_name == "Jodi B"
    ).one()

    panel_a = db.query(PanelFamily).filter(
        PanelFamily.family_name == "Panel A"
    ).one()

    panel_b = db.query(PanelFamily).filter(
        PanelFamily.family_name == "Panel B"
    ).one()

    db.add_all(
        [
            JodiFamilyMember(
                family_id=jodi_a.id,
                jodi="45",
                digit_1=4,
                digit_2=5,
                is_active=True,
            ),
            JodiFamilyMember(
                family_id=jodi_b.id,
                jodi="67",
                digit_1=6,
                digit_2=7,
                is_active=True,
            ),
            PanelFamilyMember(
                family_id=panel_a.id,
                panel="678",
                digit_1=6,
                digit_2=7,
                digit_3=8,
                is_active=True,
            ),
            PanelFamilyMember(
                family_id=panel_b.id,
                panel="901",
                digit_1=9,
                digit_2=0,
                digit_3=1,
                is_active=True,
            ),
        ]
    )
    db.commit()


def test_build_returns_result(db):
    _create_family_mappings(db)

    result = build_historical_family_frequency_features(
        db=db,
        history=(
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    assert isinstance(
        result,
        HistoricalFamilyFrequencyResult,
    )


def test_target_date_is_preserved(db):
    _create_family_mappings(db)

    target_date = date(2026, 1, 5)

    result = build_historical_family_frequency_features(
        db=db,
        history=(),
        target_date=target_date,
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    assert result.target_date == target_date


def test_active_family_universe_is_represented_even_when_zero(
    db,
):
    _create_family_mappings(db)

    result = build_historical_family_frequency_features(
        db=db,
        history=(
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    values = get_historical_family_frequency_feature_values(
        result
    )

    assert (
        values[
            "panna_family_frequency_count_3_Panna A"
        ]
        == 1
    )

    assert (
        values[
            "panna_family_frequency_count_3_Panna B"
        ]
        == 0
    )

    assert (
        values[
            "jodi_family_frequency_count_3_Jodi A"
        ]
        == 1
    )

    assert (
        values[
            "jodi_family_frequency_count_3_Jodi B"
        ]
        == 0
    )

    assert (
        values[
            "panel_family_frequency_count_3_Panel A"
        ]
        == 1
    )

    assert (
        values[
            "panel_family_frequency_count_3_Panel B"
        ]
        == 0
    )


def test_family_frequency_count_is_correct(db):
    _create_family_mappings(db)

    history = (
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
        _observation(
            3,
            date(2026, 1, 3),
            (4, 5, 6, 6, 7, 9, 0, 1),
        ),
    )

    result = build_historical_family_frequency_features(
        db=db,
        history=history,
        target_date=date(2026, 1, 4),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    values = get_historical_family_frequency_feature_values(
        result
    )

    assert (
        values[
            "panna_family_frequency_count_3_Panna A"
        ]
        == 2
    )

    assert (
        values[
            "panna_family_frequency_count_3_Panna B"
        ]
        == 1
    )

    assert (
        values[
            "jodi_family_frequency_count_3_Jodi A"
        ]
        == 2
    )

    assert (
        values[
            "jodi_family_frequency_count_3_Jodi B"
        ]
        == 1
    )

    assert (
        values[
            "panel_family_frequency_count_3_Panel A"
        ]
        == 2
    )

    assert (
        values[
            "panel_family_frequency_count_3_Panel B"
        ]
        == 1
    )


def test_family_frequency_percentage_is_correct(db):
    _create_family_mappings(db)

    history = (
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
        _observation(
            3,
            date(2026, 1, 3),
            (4, 5, 6, 6, 7, 9, 0, 1),
        ),
    )

    result = build_historical_family_frequency_features(
        db=db,
        history=history,
        target_date=date(2026, 1, 4),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    values = get_historical_family_frequency_feature_values(
        result
    )

    assert values[
        "panna_family_frequency_percentage_3_Panna A"
    ] == pytest.approx(66.6666667)

    assert values[
        "panna_family_frequency_percentage_3_Panna B"
    ] == pytest.approx(33.3333333)


def test_window_limits_observations(db):
    _create_family_mappings(db)

    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (4, 5, 6, 6, 7, 9, 0, 1),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            3,
            date(2026, 1, 3),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
    )

    result = build_historical_family_frequency_features(
        db=db,
        history=history,
        target_date=date(2026, 1, 4),
        config=FeatureConfig(
            frequency_windows=(2,),
        ),
    )

    values = get_historical_family_frequency_feature_values(
        result
    )

    assert values[
        "panna_family_frequency_count_2_Panna A"
    ] == 2

    assert values[
        "panna_family_frequency_count_2_Panna B"
    ] == 0


def test_target_date_is_never_used(db):
    _create_family_mappings(db)

    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (4, 5, 6, 6, 7, 9, 0, 1),
        ),
    )

    result = build_historical_family_frequency_features(
        db=db,
        history=history,
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(5,),
        ),
    )

    values = get_historical_family_frequency_feature_values(
        result
    )

    assert values[
        "panna_family_frequency_count_5_Panna A"
    ] == 1

    assert values[
        "panna_family_frequency_count_5_Panna B"
    ] == 0


def test_future_observation_is_never_used(db):
    _create_family_mappings(db)

    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 3),
            (4, 5, 6, 6, 7, 9, 0, 1),
        ),
    )

    result = build_historical_family_frequency_features(
        db=db,
        history=history,
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(5,),
        ),
    )

    values = get_historical_family_frequency_feature_values(
        result
    )

    assert values[
        "panna_family_frequency_count_5_Panna B"
    ] == 0


def test_unmapped_observations_are_excluded_from_denominator(
    db,
):
    _create_family_mappings(db)

    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (9, 9, 9, 9, 9, 9, 9, 9),
        ),
    )

    result = build_historical_family_frequency_features(
        db=db,
        history=history,
        target_date=date(2026, 1, 3),
        config=FeatureConfig(
            frequency_windows=(5,),
        ),
    )

    values = get_historical_family_frequency_feature_values(
        result
    )

    assert values[
        "panna_family_frequency_count_5_Panna A"
    ] == 1

    assert values[
        "panna_family_frequency_percentage_5_Panna A"
    ] == pytest.approx(100.0)


def test_no_history_returns_zero_family_frequencies(db):
    _create_family_mappings(db)

    result = build_historical_family_frequency_features(
        db=db,
        history=(),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(5,),
        ),
    )

    values = get_historical_family_frequency_feature_values(
        result
    )

    for family in (
        "Panna A",
        "Panna B",
    ):
        assert values[
            f"panna_family_frequency_count_5_{family}"
        ] == 0

        assert values[
            f"panna_family_frequency_percentage_5_{family}"
        ] == 0.0


def test_multiple_windows_are_generated(db):
    _create_family_mappings(db)

    history = (
        _observation(
            1,
            date(2026, 1, 1),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        _observation(
            2,
            date(2026, 1, 2),
            (4, 5, 6, 6, 7, 9, 0, 1),
        ),
    )

    result = build_historical_family_frequency_features(
        db=db,
        history=history,
        target_date=date(2026, 1, 3),
        config=FeatureConfig(
            frequency_windows=(3, 5),
        ),
    )

    names = get_historical_family_frequency_feature_names(
        result
    )

    assert (
        "panna_family_frequency_count_3_Panna A"
        in names
    )

    assert (
        "panna_family_frequency_count_5_Panna A"
        in names
    )


def test_zero_digit_components_are_valid_family_values(db):
    _create_family_mappings(db)

    result = build_historical_family_frequency_features(
        db=db,
        history=(
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 9, 0, 1),
            ),
        ),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    values = get_historical_family_frequency_feature_values(
        result
    )

    assert values[
        "panna_family_frequency_count_3_Panna A"
    ] == 1

    assert values[
        "jodi_family_frequency_count_3_Jodi A"
    ] == 1

    assert values[
        "panel_family_frequency_count_3_Panel B"
    ] == 1


def test_inactive_panna_mapping_is_excluded(db):
    _create_family_mappings(db)

    inactive = PannaReference(
        panna="789",
        digit_1=7,
        digit_2=8,
        digit_3=9,
        panna_type="Inactive Panna Family",
        is_active=False,
    )

    db.add(inactive)
    db.commit()

    result = build_historical_family_frequency_features(
        db=db,
        history=(
            _observation(
                1,
                date(2026, 1, 1),
                (7, 8, 9, 4, 5, 6, 7, 8),
            ),
        ),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    names = get_historical_family_frequency_feature_names(
        result
    )

    assert (
        "panna_family_frequency_count_3_Inactive Panna Family"
        not in names
    )


def test_inactive_jodi_family_is_excluded(db):
    _create_family_mappings(db)

    inactive = JodiFamily(
        family_name="Inactive Jodi Family",
        is_active=False,
    )

    db.add(inactive)
    db.commit()

    result = build_historical_family_frequency_features(
        db=db,
        history=(),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    names = get_historical_family_frequency_feature_names(
        result
    )

    assert (
        "jodi_family_frequency_count_3_Inactive Jodi Family"
        not in names
    )


def test_inactive_panel_family_is_excluded(db):
    _create_family_mappings(db)

    inactive = PanelFamily(
        family_name="Inactive Panel Family",
        is_active=False,
    )

    db.add(inactive)
    db.commit()

    result = build_historical_family_frequency_features(
        db=db,
        history=(),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    names = get_historical_family_frequency_feature_names(
        result
    )

    assert (
        "panel_family_frequency_count_3_Inactive Panel Family"
        not in names
    )


def test_feature_names_are_unique(db):
    _create_family_mappings(db)

    result = build_historical_family_frequency_features(
        db=db,
        history=(
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(3, 5),
        ),
    )

    names = get_historical_family_frequency_feature_names(
        result
    )

    assert len(names) == len(set(names))


def test_feature_value_accessor_returns_value(db):
    _create_family_mappings(db)

    result = build_historical_family_frequency_features(
        db=db,
        history=(
            _observation(
                1,
                date(2026, 1, 1),
                (1, 2, 3, 4, 5, 6, 7, 8),
            ),
        ),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    assert get_historical_family_frequency_feature_value(
        result,
        "panna_family_frequency_count_3_Panna A",
    ) == 1


def test_invalid_result_is_rejected_by_accessors():
    with pytest.raises(TypeError):
        get_historical_family_frequency_feature_names(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_historical_family_frequency_feature_values(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_historical_family_frequency_feature_value(
            "invalid",
            "anything",
        )


def test_missing_feature_name_is_rejected(db):
    _create_family_mappings(db)

    result = build_historical_family_frequency_features(
        db=db,
        history=(),
        target_date=date(2026, 1, 2),
        config=FeatureConfig(
            frequency_windows=(3,),
        ),
    )

    with pytest.raises(ValueError):
        get_historical_family_frequency_feature_value(
            result,
            "does_not_exist",
        )


def test_invalid_database_is_rejected():
    with pytest.raises(ValueError):
        build_historical_family_frequency_features(
            db=None,
            history=(),
            target_date=date(2026, 1, 2),
            config=FeatureConfig(
                frequency_windows=(3,),
            ),
        )


def test_invalid_target_date_is_rejected(db):
    with pytest.raises(TypeError):
        build_historical_family_frequency_features(
            db=db,
            history=(),
            target_date="2026-01-02",
            config=FeatureConfig(
                frequency_windows=(3,),
            ),
        )


def test_invalid_history_is_rejected(db):
    with pytest.raises(TypeError):
        build_historical_family_frequency_features(
            db=db,
            history="invalid",
            target_date=date(2026, 1, 2),
            config=FeatureConfig(
                frequency_windows=(3,),
            ),
        )


def test_invalid_config_is_rejected(db):
    with pytest.raises(TypeError):
        build_historical_family_frequency_features(
            db=db,
            history=(),
            target_date=date(2026, 1, 2),
            config="invalid",
        )