from __future__ import annotations

from dataclasses import replace

import pytest

from features.feature_config import FeatureConfig
from features.feature_schema import FeatureSchema
from features.feature_versioning import (
    FeatureVersionIdentity,
    build_feature_version_identity,
    build_feature_version_reference_from_identity,
    is_feature_version_reference_consistent,
    validate_feature_version_identity,
    validate_feature_version_reference_against_identity,
)
from features.versioning_contract import (
    FeatureVersionReference,
    build_feature_version_reference,
)


def make_config(
    **overrides,
) -> FeatureConfig:
    values = {
        "feature_version": "v1",
        "positions": (
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "col8",
        ),
        "lag_windows": (1, 2, 3),
        "rolling_windows": (3, 5, 7),
        "frequency_enabled": True,
        "frequency_window": 5,
        "recency_enabled": True,
        "recency_lookback": 10,
        "position_features_enabled": True,
    }

    values.update(
        overrides
    )

    return FeatureConfig(
        **values
    )


def make_schema(
    feature_name: str = "col1_lag_1",
    feature_version: str = "v1",
) -> FeatureSchema:
    return FeatureSchema(
        feature_name=feature_name,
        feature_version=feature_version,
        feature_type="lag",
        source="lag_features",
        position="col1",
        window=None,
        lag=1,
        description="Previous historical value.",
        availability_rule=(
            "Uses only observations strictly before the target date."
        ),
        data_type="integer",
    )


def make_identity(
    feature_version: str = "v1",
) -> FeatureVersionIdentity:
    return build_feature_version_identity(
        make_config(
            feature_version=feature_version
        ),
        (
            make_schema(
                feature_version=feature_version
            ),
        ),
    )


def test_identity_is_valid_before_reference_validation():
    identity = make_identity()

    validate_feature_version_identity(
        identity
    )


def test_reference_can_be_built_from_identity():
    identity = make_identity()

    reference = build_feature_version_reference_from_identity(
        identity
    )

    assert isinstance(
        reference,
        FeatureVersionReference,
    )

    assert reference.feature_version == identity.feature_version
    assert reference.identity == identity.identity
    assert reference.algorithm == identity.algorithm


def test_reference_from_identity_is_consistent():
    identity = make_identity()

    reference = build_feature_version_reference_from_identity(
        identity
    )

    validate_feature_version_reference_against_identity(
        reference,
        identity,
    )


def test_consistency_helper_returns_true():
    identity = make_identity()

    reference = build_feature_version_reference_from_identity(
        identity
    )

    assert is_feature_version_reference_consistent(
        reference,
        identity,
    ) is True


def test_different_feature_version_is_rejected():
    identity = make_identity(
        feature_version="v1"
    )

    reference = build_feature_version_reference(
        feature_version="v2",
        identity=identity.identity,
        algorithm=identity.algorithm,
    )

    with pytest.raises(
        ValueError,
        match="feature version",
    ):
        validate_feature_version_reference_against_identity(
            reference,
            identity,
        )


def test_different_identity_is_rejected():
    identity = make_identity()

    reference = build_feature_version_reference(
        feature_version=identity.feature_version,
        identity="feature-tampered",
        algorithm=identity.algorithm,
    )

    with pytest.raises(
        ValueError,
        match="identity",
    ):
        validate_feature_version_reference_against_identity(
            reference,
            identity,
        )


def test_different_algorithm_is_rejected():
    identity = make_identity()

    reference = build_feature_version_reference(
        feature_version=identity.feature_version,
        identity=identity.identity,
        algorithm="md5",
    )

    with pytest.raises(
        ValueError,
        match="algorithm",
    ):
        validate_feature_version_reference_against_identity(
            reference,
            identity,
        )


def test_invalid_reference_type_is_rejected():
    identity = make_identity()

    with pytest.raises(TypeError):
        validate_feature_version_reference_against_identity(
            object(),
            identity,
        )


def test_invalid_identity_type_is_rejected():
    reference = build_feature_version_reference(
        feature_version="v1",
        identity="feature-abc",
        algorithm="sha256",
    )

    with pytest.raises(TypeError):
        validate_feature_version_reference_against_identity(
            reference,
            object(),
        )


def test_consistency_helper_returns_false_for_invalid_reference():
    identity = make_identity()

    reference = build_feature_version_reference(
        feature_version=identity.feature_version,
        identity="feature-invalid",
        algorithm=identity.algorithm,
    )

    assert is_feature_version_reference_consistent(
        reference,
        identity,
    ) is False


def test_consistency_helper_returns_false_for_invalid_identity():
    identity = make_identity()

    tampered_identity = FeatureVersionIdentity(
        feature_version=identity.feature_version,
        identity="feature-tampered",
        algorithm=identity.algorithm,
        canonical_definition=identity.canonical_definition,
    )

    reference = build_feature_version_reference_from_identity(
        identity
    )

    assert is_feature_version_reference_consistent(
        reference,
        tampered_identity,
    ) is False


def test_tampered_identity_is_rejected_before_matching():
    identity = make_identity()

    tampered_identity = FeatureVersionIdentity(
        feature_version=identity.feature_version,
        identity="feature-tampered",
        algorithm=identity.algorithm,
        canonical_definition=identity.canonical_definition,
    )

    reference = build_feature_version_reference_from_identity(
        identity
    )

    with pytest.raises(ValueError):
        validate_feature_version_reference_against_identity(
            reference,
            tampered_identity,
        )


def test_changed_feature_definition_produces_incompatible_identity():
    identity_a = make_identity()

    identity_b = build_feature_version_identity(
        make_config(
            feature_version="v1",
            lag_windows=(1, 2),
        ),
        (
            make_schema(
                feature_version="v1"
            ),
        ),
    )

    assert identity_a.identity != identity_b.identity

    reference_a = build_feature_version_reference_from_identity(
        identity_a
    )

    assert is_feature_version_reference_consistent(
        reference_a,
        identity_b,
    ) is False


def test_changed_schema_produces_incompatible_identity():
    identity_a = make_identity()

    identity_b = build_feature_version_identity(
        make_config(
            feature_version="v1",
        ),
        (
            make_schema(
                feature_name="col1_lag_2",
                feature_version="v1",
            ),
        ),
    )

    assert identity_a.identity != identity_b.identity

    reference_a = build_feature_version_reference_from_identity(
        identity_a
    )

    assert is_feature_version_reference_consistent(
        reference_a,
        identity_b,
    ) is False


def test_same_definition_remains_compatible():
    identity_a = make_identity()
    identity_b = make_identity()

    reference = build_feature_version_reference_from_identity(
        identity_a
    )

    assert identity_a == identity_b

    validate_feature_version_reference_against_identity(
        reference,
        identity_b,
    )


def test_validation_does_not_modify_reference():
    identity = make_identity()

    reference = build_feature_version_reference_from_identity(
        identity
    )

    original = reference

    validate_feature_version_reference_against_identity(
        reference,
        identity,
    )

    assert reference == original


def test_validation_does_not_modify_identity():
    identity = make_identity()

    reference = build_feature_version_reference_from_identity(
        identity
    )

    original = identity

    validate_feature_version_reference_against_identity(
        reference,
        identity,
    )

    assert identity == original


def test_reference_identity_round_trip_is_deterministic():
    identity = make_identity()

    reference_a = build_feature_version_reference_from_identity(
        identity
    )

    reference_b = build_feature_version_reference_from_identity(
        identity
    )

    assert reference_a == reference_b


def test_feature_version_change_breaks_reference_compatibility():
    identity_v1 = make_identity(
        feature_version="v1"
    )

    identity_v2 = make_identity(
        feature_version="v2"
    )

    reference_v1 = build_feature_version_reference_from_identity(
        identity_v1
    )

    assert (
        is_feature_version_reference_consistent(
            reference_v1,
            identity_v2,
        )
        is False
    )


def test_identity_change_breaks_reference_compatibility():
    identity_v1 = make_identity(
        feature_version="v1"
    )

    identity_changed = build_feature_version_identity(
        make_config(
            feature_version="v1",
            recency_lookback=20,
        ),
        (
            make_schema(
                feature_version="v1"
            ),
        ),
    )

    reference_v1 = build_feature_version_reference_from_identity(
        identity_v1
    )

    assert (
        identity_v1.identity
        != identity_changed.identity
    )

    assert (
        is_feature_version_reference_consistent(
            reference_v1,
            identity_changed,
        )
        is False
    )


def test_identity_algorithm_must_remain_supported():
    identity = make_identity()

    invalid_identity = FeatureVersionIdentity(
        feature_version=identity.feature_version,
        identity=identity.identity,
        algorithm="md5",
        canonical_definition=identity.canonical_definition,
    )

    reference = build_feature_version_reference(
        feature_version=identity.feature_version,
        identity=identity.identity,
        algorithm="md5",
    )

    with pytest.raises(ValueError):
        validate_feature_version_reference_against_identity(
            reference,
            invalid_identity,
        )


def test_reference_validation_rejects_empty_feature_version():
    identity = make_identity()

    reference = FeatureVersionReference(
        feature_version="",
        identity=identity.identity,
        algorithm=identity.algorithm,
    )

    with pytest.raises(ValueError):
        validate_feature_version_reference_against_identity(
            reference,
            identity,
        )


def test_reference_validation_rejects_empty_identity():
    identity = make_identity()

    reference = FeatureVersionReference(
        feature_version=identity.feature_version,
        identity="",
        algorithm=identity.algorithm,
    )

    with pytest.raises(ValueError):
        validate_feature_version_reference_against_identity(
            reference,
            identity,
        )


def test_reference_validation_rejects_empty_algorithm():
    identity = make_identity()

    reference = FeatureVersionReference(
        feature_version=identity.feature_version,
        identity=identity.identity,
        algorithm="",
    )

    with pytest.raises(ValueError):
        validate_feature_version_reference_against_identity(
            reference,
            identity,
        )