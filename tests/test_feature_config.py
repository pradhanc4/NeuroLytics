from dataclasses import replace

import pytest

from features.feature_config import (
    FeatureConfig,
    POSITIONS,
    get_feature_positions,
    get_feature_version,
    get_lag_windows,
    get_rolling_windows,
    validate_feature_config,
)


def test_default_feature_config_is_valid():
    config = FeatureConfig()

    validate_feature_config(config)

    assert config.feature_version == "v1"
    assert config.positions == POSITIONS
    assert config.lag_windows == (1, 2, 3)
    assert config.rolling_windows == (3, 5, 7)
    assert config.frequency_enabled is True
    assert config.frequency_window == 5
    assert config.recency_enabled is True
    assert config.recency_lookback == 10
    assert config.position_features_enabled is True

    # Phase 15 defaults
    assert config.phase15_enabled is True
    assert config.panna_panel_features_enabled is True
    assert config.jodi_family_features_enabled is True
    assert config.position_family_relationships_enabled is True
    assert config.cross_position_relationships_enabled is True
    assert config.family_frequency_features_enabled is True
    assert config.family_recency_features_enabled is True
    assert config.family_transition_features_enabled is True
    assert config.position_transition_features_enabled is True
    assert config.transition_frequency_features_enabled is True
    assert config.transition_stability_features_enabled is True
    assert config.relationship_change_trend_features_enabled is True


def test_feature_version_getter():
    config = FeatureConfig(
        feature_version="v2",
    )

    assert get_feature_version(config) == "v2"


def test_feature_positions_getter():
    config = FeatureConfig(
        positions=("col1", "col2"),
    )

    assert get_feature_positions(config) == (
        "col1",
        "col2",
    )


def test_lag_windows_getter():
    config = FeatureConfig(
        lag_windows=(1, 3, 5),
    )

    assert get_lag_windows(config) == (
        1,
        3,
        5,
    )


def test_rolling_windows_getter():
    config = FeatureConfig(
        rolling_windows=(3, 7),
    )

    assert get_rolling_windows(config) == (
        3,
        7,
    )


def test_feature_config_must_be_correct_type():
    with pytest.raises(
        TypeError,
        match="FeatureConfig",
    ):
        validate_feature_config(object())


def test_feature_version_is_required():
    config = replace(
        FeatureConfig(),
        feature_version="",
    )

    with pytest.raises(
        ValueError,
        match="feature_version",
    ):
        validate_feature_config(config)


def test_positions_must_not_be_empty():
    config = replace(
        FeatureConfig(),
        positions=(),
    )

    with pytest.raises(
        ValueError,
        match="position",
    ):
        validate_feature_config(config)


def test_duplicate_positions_are_rejected():
    config = replace(
        FeatureConfig(),
        positions=("col1", "col1"),
    )

    with pytest.raises(
        ValueError,
        match="duplicates",
    ):
        validate_feature_config(config)


def test_unknown_position_is_rejected():
    config = replace(
        FeatureConfig(),
        positions=("col1", "col9"),
    )

    with pytest.raises(
        ValueError,
        match="Unsupported position",
    ):
        validate_feature_config(config)


def test_lag_windows_must_not_be_empty():
    config = replace(
        FeatureConfig(),
        lag_windows=(),
    )

    with pytest.raises(
        ValueError,
        match="lag window",
    ):
        validate_feature_config(config)


def test_lag_window_must_be_positive_integer():
    config = replace(
        FeatureConfig(),
        lag_windows=(0,),
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        validate_feature_config(config)


def test_lag_window_boolean_is_rejected():
    config = replace(
        FeatureConfig(),
        lag_windows=(True,),
    )

    with pytest.raises(
        ValueError,
        match="integers",
    ):
        validate_feature_config(config)


def test_duplicate_lag_windows_are_rejected():
    config = replace(
        FeatureConfig(),
        lag_windows=(1, 1),
    )

    with pytest.raises(
        ValueError,
        match="duplicates",
    ):
        validate_feature_config(config)


def test_rolling_windows_must_not_be_empty():
    config = replace(
        FeatureConfig(),
        rolling_windows=(),
    )

    with pytest.raises(
        ValueError,
        match="rolling window",
    ):
        validate_feature_config(config)


def test_rolling_window_must_be_positive_integer():
    config = replace(
        FeatureConfig(),
        rolling_windows=(0,),
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        validate_feature_config(config)


def test_rolling_window_boolean_is_rejected():
    config = replace(
        FeatureConfig(),
        rolling_windows=(True,),
    )

    with pytest.raises(
        ValueError,
        match="integers",
    ):
        validate_feature_config(config)


def test_duplicate_rolling_windows_are_rejected():
    config = replace(
        FeatureConfig(),
        rolling_windows=(3, 3),
    )

    with pytest.raises(
        ValueError,
        match="duplicates",
    ):
        validate_feature_config(config)


def test_frequency_window_must_be_positive():
    config = replace(
        FeatureConfig(),
        frequency_window=0,
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        validate_feature_config(config)


def test_frequency_window_boolean_is_rejected():
    config = replace(
        FeatureConfig(),
        frequency_window=True,
    )

    with pytest.raises(
        ValueError,
        match="integer",
    ):
        validate_feature_config(config)


def test_frequency_enabled_must_be_boolean():
    config = replace(
        FeatureConfig(),
        frequency_enabled=1,
    )

    with pytest.raises(
        ValueError,
        match="boolean",
    ):
        validate_feature_config(config)


def test_recency_lookback_must_be_positive():
    config = replace(
        FeatureConfig(),
        recency_lookback=0,
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        validate_feature_config(config)


def test_recency_lookback_boolean_is_rejected():
    config = replace(
        FeatureConfig(),
        recency_lookback=True,
    )

    with pytest.raises(
        ValueError,
        match="integer",
    ):
        validate_feature_config(config)


def test_recency_enabled_must_be_boolean():
    config = replace(
        FeatureConfig(),
        recency_enabled=1,
    )

    with pytest.raises(
        ValueError,
        match="boolean",
    ):
        validate_feature_config(config)


def test_position_features_enabled_must_be_boolean():
    config = replace(
        FeatureConfig(),
        position_features_enabled=1,
    )

    with pytest.raises(
        ValueError,
        match="boolean",
    ):
        validate_feature_config(config)


def test_custom_valid_configuration():
    config = FeatureConfig(
        feature_version="v3",
        positions=("col1", "col4", "col8"),
        lag_windows=(1, 2, 5),
        rolling_windows=(3, 10),
        frequency_enabled=False,
        frequency_window=7,
        recency_enabled=False,
        recency_lookback=20,
        position_features_enabled=True,
    )

    validate_feature_config(config)

    assert get_feature_version(config) == "v3"
    assert get_feature_positions(config) == (
        "col1",
        "col4",
        "col8",
    )
    assert get_lag_windows(config) == (
        1,
        2,
        5,
    )
    assert get_rolling_windows(config) == (
        3,
        10,
    )


# ============================================================================
# Phase 15 - Configuration Contract Tests
# ============================================================================


def test_phase15_can_be_disabled():
    config = replace(
        FeatureConfig(),
        phase15_enabled=False,
    )

    validate_feature_config(config)

    assert config.phase15_enabled is False


@pytest.mark.parametrize(
    "field_name",
    [
        "panna_panel_features_enabled",
        "jodi_family_features_enabled",
        "position_family_relationships_enabled",
        "cross_position_relationships_enabled",
        "family_frequency_features_enabled",
        "family_recency_features_enabled",
        "family_transition_features_enabled",
        "position_transition_features_enabled",
        "transition_frequency_features_enabled",
        "transition_stability_features_enabled",
        "relationship_change_trend_features_enabled",
    ],
)
def test_phase15_feature_flags_accept_false(field_name):
    config = replace(
        FeatureConfig(),
        **{field_name: False},
    )

    validate_feature_config(config)

    assert getattr(config, field_name) is False


@pytest.mark.parametrize(
    "field_name",
    [
        "phase15_enabled",
        "panna_panel_features_enabled",
        "jodi_family_features_enabled",
        "position_family_relationships_enabled",
        "cross_position_relationships_enabled",
        "family_frequency_features_enabled",
        "family_recency_features_enabled",
        "family_transition_features_enabled",
        "position_transition_features_enabled",
        "transition_frequency_features_enabled",
        "transition_stability_features_enabled",
        "relationship_change_trend_features_enabled",
    ],
)
def test_phase15_boolean_flags_accept_true(field_name):
    config = replace(
        FeatureConfig(),
        **{field_name: True},
    )

    validate_feature_config(config)

    assert getattr(config, field_name) is True


@pytest.mark.parametrize(
    "field_name",
    [
        "phase15_enabled",
        "panna_panel_features_enabled",
        "jodi_family_features_enabled",
        "position_family_relationships_enabled",
        "cross_position_relationships_enabled",
        "family_frequency_features_enabled",
        "family_recency_features_enabled",
        "family_transition_features_enabled",
        "position_transition_features_enabled",
        "transition_frequency_features_enabled",
        "transition_stability_features_enabled",
        "relationship_change_trend_features_enabled",
    ],
)
@pytest.mark.parametrize(
    "invalid_value",
    [
        0,
        1,
        "true",
        "false",
        None,
        [],
    ],
)
def test_phase15_boolean_flags_reject_non_boolean_values(
    field_name,
    invalid_value,
):
    config = replace(
        FeatureConfig(),
        **{field_name: invalid_value},
    )

    with pytest.raises(
        ValueError,
        match="boolean",
    ):
        validate_feature_config(config)


def test_phase15_configuration_can_disable_all_feature_families():
    config = FeatureConfig(
        phase15_enabled=False,
        panna_panel_features_enabled=False,
        jodi_family_features_enabled=False,
        position_family_relationships_enabled=False,
        cross_position_relationships_enabled=False,
        family_frequency_features_enabled=False,
        family_recency_features_enabled=False,
        family_transition_features_enabled=False,
        position_transition_features_enabled=False,
        transition_frequency_features_enabled=False,
        transition_stability_features_enabled=False,
        relationship_change_trend_features_enabled=False,
    )

    validate_feature_config(config)

    assert config.phase15_enabled is False
    assert config.panna_panel_features_enabled is False
    assert config.jodi_family_features_enabled is False
    assert config.position_family_relationships_enabled is False
    assert config.cross_position_relationships_enabled is False
    assert config.family_frequency_features_enabled is False
    assert config.family_recency_features_enabled is False
    assert config.family_transition_features_enabled is False
    assert config.position_transition_features_enabled is False
    assert config.transition_frequency_features_enabled is False
    assert config.transition_stability_features_enabled is False
    assert config.relationship_change_trend_features_enabled is False


def test_phase15_configuration_can_mix_enabled_and_disabled_features():
    config = FeatureConfig(
        phase15_enabled=True,
        panna_panel_features_enabled=True,
        jodi_family_features_enabled=False,
        position_family_relationships_enabled=True,
        cross_position_relationships_enabled=False,
        family_frequency_features_enabled=True,
        family_recency_features_enabled=False,
        family_transition_features_enabled=True,
        position_transition_features_enabled=False,
        transition_frequency_features_enabled=True,
        transition_stability_features_enabled=False,
        relationship_change_trend_features_enabled=True,
    )

    validate_feature_config(config)

    assert config.phase15_enabled is True
    assert config.panna_panel_features_enabled is True
    assert config.jodi_family_features_enabled is False
    assert config.position_family_relationships_enabled is True
    assert config.cross_position_relationships_enabled is False
    assert config.family_frequency_features_enabled is True
    assert config.family_recency_features_enabled is False
    assert config.family_transition_features_enabled is True
    assert config.position_transition_features_enabled is False
    assert config.transition_frequency_features_enabled is True
    assert config.transition_stability_features_enabled is False
    assert config.relationship_change_trend_features_enabled is True