from __future__ import annotations

from datetime import date

import pytest

from features.dataset_versioning import (
    DATASET_VERSION_ALGORITHM,
    DATASET_VERSION_PREFIX,
    DatasetVersionIdentity,
    build_dataset_version_identity,
    build_dataset_version_reference,
    get_canonical_dataset_definition,
    get_dataset_feature_identity,
    get_dataset_feature_version,
    get_dataset_version_algorithm,
    get_dataset_version_identity,
    get_dataset_version_label,
    is_dataset_version_identity_valid,
    is_dataset_version_reproducible,
    validate_dataset_version_identity,
    validate_dataset_version_reference_against_identity,
)
from features.feature_config import FeatureConfig
from features.feature_schema import FeatureSchema
from features.feature_versioning import (
    build_feature_version_identity,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
    UnifiedFeatureRecord,
)
from features.versioning_contract import (
    DatasetVersionReference,
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

    values.update(overrides)

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


def make_feature_identity(
    feature_version: str = "v1",
):
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


def make_dataset(
    *,
    target_date: date = date(2026, 1, 5),
    feature_version: str = "v1",
    first_value: int | float | str | bool | None = 5,
    second_value: int | float | str | bool | None = 10,
):
    return UnifiedFeatureDataset(
        target_date=target_date,
        feature_version=feature_version,
        records=(
            UnifiedFeatureRecord(
                feature_name="col1_lag_1",
                value=first_value,
                feature_type="lag",
                source="lag_features",
            ),
            UnifiedFeatureRecord(
                feature_name="col1_lag_2",
                value=second_value,
                feature_type="lag",
                source="lag_features",
            ),
        ),
    )


def make_identity(
    *,
    dataset_version: str = "dataset-v1",
    target_date: date = date(2026, 1, 5),
    feature_version: str = "v1",
    first_value=5,
    second_value=10,
):
    dataset = make_dataset(
        target_date=target_date,
        feature_version=feature_version,
        first_value=first_value,
        second_value=second_value,
    )

    feature_identity = make_feature_identity(
        feature_version=feature_version
    )

    return build_dataset_version_identity(
        dataset=dataset,
        feature_identity=feature_identity,
        dataset_version=dataset_version,
    )


def test_dataset_version_algorithm():
    assert DATASET_VERSION_ALGORITHM == "sha256"


def test_dataset_version_prefix():
    assert DATASET_VERSION_PREFIX == "dataset-"


def test_dataset_identity_can_be_created():
    identity = make_identity()

    assert isinstance(
        identity,
        DatasetVersionIdentity,
    )


def test_dataset_identity_has_expected_algorithm():
    identity = make_identity()

    assert identity.algorithm == "sha256"


def test_dataset_identity_has_expected_prefix():
    identity = make_identity()

    assert identity.identity.startswith(
        DATASET_VERSION_PREFIX
    )


def test_dataset_identity_preserves_dataset_version():
    identity = make_identity(
        dataset_version="dataset-v7"
    )

    assert identity.dataset_version == "dataset-v7"


def test_dataset_identity_preserves_feature_version():
    identity = make_identity(
        feature_version="v4"
    )

    assert identity.feature_version == "v4"


def test_dataset_identity_preserves_feature_identity():
    identity = make_identity()

    feature_identity = make_feature_identity()

    assert identity.feature_identity == feature_identity.identity


def test_dataset_identity_is_deterministic():
    identity_a = make_identity()
    identity_b = make_identity()

    assert identity_a == identity_b


def test_same_dataset_produces_same_identity():
    identity_a = make_identity()
    identity_b = make_identity()

    assert identity_a.identity == identity_b.identity


def test_different_dataset_version_changes_identity():
    identity_a = make_identity(
        dataset_version="dataset-v1"
    )

    identity_b = make_identity(
        dataset_version="dataset-v2"
    )

    assert identity_a.identity != identity_b.identity


def test_different_target_date_changes_identity():
    identity_a = make_identity(
        target_date=date(2026, 1, 5)
    )

    identity_b = make_identity(
        target_date=date(2026, 1, 6)
    )

    assert identity_a.identity != identity_b.identity


def test_different_feature_value_changes_identity():
    identity_a = make_identity(
        first_value=5
    )

    identity_b = make_identity(
        first_value=6
    )

    assert identity_a.identity != identity_b.identity


def test_different_second_feature_value_changes_identity():
    identity_a = make_identity(
        second_value=10
    )

    identity_b = make_identity(
        second_value=11
    )

    assert identity_a.identity != identity_b.identity


def test_different_feature_version_changes_identity():
    identity_a = make_identity(
        feature_version="v1"
    )

    identity_b = make_identity(
        feature_version="v2"
    )

    assert identity_a.identity != identity_b.identity


def test_different_feature_identity_changes_identity():
    dataset = make_dataset()

    feature_identity_a = make_feature_identity(
        feature_version="v1"
    )

    feature_identity_b = build_feature_version_identity(
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

    identity_a = build_dataset_version_identity(
        dataset,
        feature_identity_a,
        "dataset-v1",
    )

    identity_b = build_dataset_version_identity(
        dataset,
        feature_identity_b,
        "dataset-v1",
    )

    assert identity_a.identity != identity_b.identity


def test_dataset_feature_version_mismatch_is_rejected():
    dataset = make_dataset(
        feature_version="v2"
    )

    feature_identity = make_feature_identity(
        feature_version="v1"
    )

    with pytest.raises(
        ValueError,
        match="feature_version",
    ):
        build_dataset_version_identity(
            dataset,
            feature_identity,
            "dataset-v1",
        )


def test_invalid_dataset_type_is_rejected():
    feature_identity = make_feature_identity()

    with pytest.raises(TypeError):
        build_dataset_version_identity(
            object(),
            feature_identity,
            "dataset-v1",
        )


def test_invalid_feature_identity_type_is_rejected():
    dataset = make_dataset()

    with pytest.raises(TypeError):
        build_dataset_version_identity(
            dataset,
            object(),
            "dataset-v1",
        )


def test_empty_dataset_version_is_rejected():
    dataset = make_dataset()
    feature_identity = make_feature_identity()

    with pytest.raises(ValueError):
        build_dataset_version_identity(
            dataset,
            feature_identity,
            "",
        )


def test_whitespace_dataset_version_is_rejected():
    dataset = make_dataset()
    feature_identity = make_feature_identity()

    with pytest.raises(ValueError):
        build_dataset_version_identity(
            dataset,
            feature_identity,
            "   ",
        )


def test_empty_dataset_is_rejected():
    dataset = UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version="v1",
        records=(),
    )

    feature_identity = make_feature_identity()

    with pytest.raises(
        ValueError,
        match="at least one feature",
    ):
        build_dataset_version_identity(
            dataset,
            feature_identity,
            "dataset-v1",
        )


def test_duplicate_feature_names_are_rejected():
    dataset = UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version="v1",
        records=(
            UnifiedFeatureRecord(
                feature_name="same",
                value=1,
                feature_type="lag",
                source="lag_features",
            ),
            UnifiedFeatureRecord(
                feature_name="same",
                value=2,
                feature_type="lag",
                source="lag_features",
            ),
        ),
    )

    feature_identity = make_feature_identity()

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        build_dataset_version_identity(
            dataset,
            feature_identity,
            "dataset-v1",
        )


def test_invalid_feature_name_is_rejected():
    dataset = UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version="v1",
        records=(
            UnifiedFeatureRecord(
                feature_name="",
                value=1,
                feature_type="lag",
                source="lag_features",
            ),
        ),
    )

    feature_identity = make_feature_identity()

    with pytest.raises(ValueError):
        build_dataset_version_identity(
            dataset,
            feature_identity,
            "dataset-v1",
        )


def test_invalid_feature_type_is_rejected():
    dataset = UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version="v1",
        records=(
            UnifiedFeatureRecord(
                feature_name="col1_lag_1",
                value=1,
                feature_type="",
                source="lag_features",
            ),
        ),
    )

    feature_identity = make_feature_identity()

    with pytest.raises(ValueError):
        build_dataset_version_identity(
            dataset,
            feature_identity,
            "dataset-v1",
        )


def test_invalid_source_is_rejected():
    dataset = UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version="v1",
        records=(
            UnifiedFeatureRecord(
                feature_name="col1_lag_1",
                value=1,
                feature_type="lag",
                source="",
            ),
        ),
    )

    feature_identity = make_feature_identity()

    with pytest.raises(ValueError):
        build_dataset_version_identity(
            dataset,
            feature_identity,
            "dataset-v1",
        )


def test_none_value_is_valid_and_identity_is_deterministic():
    identity_a = make_identity(
        first_value=None
    )

    identity_b = make_identity(
        first_value=None
    )

    assert identity_a == identity_b


def test_zero_value_is_distinct_from_none():
    identity_zero = make_identity(
        first_value=0
    )

    identity_none = make_identity(
        first_value=None
    )

    assert identity_zero.identity != identity_none.identity


def test_false_value_is_distinct_from_zero():
    identity_false = make_identity(
        first_value=False
    )

    identity_zero = make_identity(
        first_value=0
    )

    assert identity_false.identity != identity_zero.identity


def test_string_value_is_preserved_in_identity():
    identity_a = make_identity(
        first_value="005"
    )

    identity_b = make_identity(
        first_value="5"
    )

    assert identity_a.identity != identity_b.identity


def test_record_order_is_part_of_dataset_identity():
    feature_identity = make_feature_identity()

    dataset_a = UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version="v1",
        records=(
            UnifiedFeatureRecord(
                feature_name="a",
                value=1,
                feature_type="lag",
                source="lag",
            ),
            UnifiedFeatureRecord(
                feature_name="b",
                value=2,
                feature_type="lag",
                source="lag",
            ),
        ),
    )

    dataset_b = UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version="v1",
        records=(
            UnifiedFeatureRecord(
                feature_name="b",
                value=2,
                feature_type="lag",
                source="lag",
            ),
            UnifiedFeatureRecord(
                feature_name="a",
                value=1,
                feature_type="lag",
                source="lag",
            ),
        ),
    )

    identity_a = build_dataset_version_identity(
        dataset_a,
        feature_identity,
        "dataset-v1",
    )

    identity_b = build_dataset_version_identity(
        dataset_b,
        feature_identity,
        "dataset-v1",
    )

    assert identity_a.identity != identity_b.identity


def test_feature_type_change_changes_identity():
    feature_identity = make_feature_identity()

    dataset_a = make_dataset()

    dataset_b = UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version="v1",
        records=(
            UnifiedFeatureRecord(
                feature_name="col1_lag_1",
                value=5,
                feature_type="rolling",
                source="lag_features",
            ),
            UnifiedFeatureRecord(
                feature_name="col1_lag_2",
                value=10,
                feature_type="lag",
                source="lag_features",
            ),
        ),
    )

    identity_a = build_dataset_version_identity(
        dataset_a,
        feature_identity,
        "dataset-v1",
    )

    identity_b = build_dataset_version_identity(
        dataset_b,
        feature_identity,
        "dataset-v1",
    )

    assert identity_a.identity != identity_b.identity


def test_source_change_changes_identity():
    feature_identity = make_feature_identity()

    dataset_a = make_dataset()

    dataset_b = UnifiedFeatureDataset(
        target_date=date(2026, 1, 5),
        feature_version="v1",
        records=(
            UnifiedFeatureRecord(
                feature_name="col1_lag_1",
                value=5,
                feature_type="lag",
                source="different_source",
            ),
            UnifiedFeatureRecord(
                feature_name="col1_lag_2",
                value=10,
                feature_type="lag",
                source="lag_features",
            ),
        ),
    )

    identity_a = build_dataset_version_identity(
        dataset_a,
        feature_identity,
        "dataset-v1",
    )

    identity_b = build_dataset_version_identity(
        dataset_b,
        feature_identity,
        "dataset-v1",
    )

    assert identity_a.identity != identity_b.identity


def test_canonical_definition_is_not_empty():
    identity = make_identity()

    assert isinstance(
        identity.canonical_definition,
        str,
    )

    assert identity.canonical_definition


def test_canonical_definition_is_deterministic():
    identity_a = make_identity()
    identity_b = make_identity()

    assert (
        identity_a.canonical_definition
        == identity_b.canonical_definition
    )


def test_validate_identity_accepts_valid_identity():
    identity = make_identity()

    validate_dataset_version_identity(
        identity
    )


def test_tampered_identity_is_rejected():
    identity = make_identity()

    tampered = DatasetVersionIdentity(
        dataset_version=identity.dataset_version,
        identity="dataset-tampered",
        algorithm=identity.algorithm,
        canonical_definition=identity.canonical_definition,
        feature_version=identity.feature_version,
        feature_identity=identity.feature_identity,
    )

    with pytest.raises(ValueError):
        validate_dataset_version_identity(
            tampered
        )


def test_invalid_identity_type_is_rejected():
    with pytest.raises(TypeError):
        validate_dataset_version_identity(
            object()
        )


def test_invalid_identity_algorithm_is_rejected():
    identity = make_identity()

    invalid = DatasetVersionIdentity(
        dataset_version=identity.dataset_version,
        identity=identity.identity,
        algorithm="md5",
        canonical_definition=identity.canonical_definition,
        feature_version=identity.feature_version,
        feature_identity=identity.feature_identity,
    )

    with pytest.raises(ValueError):
        validate_dataset_version_identity(
            invalid
        )


def test_invalid_identity_definition_is_rejected():
    identity = make_identity()

    invalid = DatasetVersionIdentity(
        dataset_version=identity.dataset_version,
        identity=identity.identity,
        algorithm=identity.algorithm,
        canonical_definition="",
        feature_version=identity.feature_version,
        feature_identity=identity.feature_identity,
    )

    with pytest.raises(ValueError):
        validate_dataset_version_identity(
            invalid
        )


def test_dataset_reference_can_be_created():
    identity = make_identity()

    reference = build_dataset_version_reference(
        identity
    )

    assert isinstance(
        reference,
        DatasetVersionReference,
    )

    assert reference.dataset_version == identity.dataset_version
    assert reference.identity == identity.identity
    assert reference.feature_version == identity.feature_version
    assert reference.feature_identity == identity.feature_identity


def test_dataset_reference_matches_identity():
    identity = make_identity()

    reference = build_dataset_version_reference(
        identity
    )

    validate_dataset_version_reference_against_identity(
        reference,
        identity,
    )


def test_reproducibility_returns_true_for_same_dataset():
    identity_a = make_identity()
    identity_b = make_identity()

    assert is_dataset_version_reproducible(
        identity_a,
        identity_b,
    ) is True


def test_reproducibility_returns_false_for_changed_value():
    identity_a = make_identity(
        first_value=5
    )

    identity_b = make_identity(
        first_value=6
    )

    assert is_dataset_version_reproducible(
        identity_a,
        identity_b,
    ) is False


def test_identity_getters():
    identity = make_identity()

    assert (
        get_dataset_version_identity(identity)
        == identity.identity
    )

    assert (
        get_dataset_version_label(identity)
        == identity.dataset_version
    )

    assert (
        get_dataset_version_algorithm(identity)
        == identity.algorithm
    )

    assert (
        get_dataset_feature_version(identity)
        == identity.feature_version
    )

    assert (
        get_dataset_feature_identity(identity)
        == identity.feature_identity
    )

    assert (
        get_canonical_dataset_definition(identity)
        == identity.canonical_definition
    )


def test_validity_helper():
    identity = make_identity()

    assert (
        is_dataset_version_identity_valid(identity)
        is True
    )

    assert (
        is_dataset_version_identity_valid(object())
        is False
    )


def test_dataset_reference_mismatch_is_rejected():
    identity_a = make_identity(
        dataset_version="dataset-v1"
    )

    identity_b = make_identity(
        dataset_version="dataset-v2"
    )

    reference_a = build_dataset_version_reference(
        identity_a
    )

    with pytest.raises(ValueError):
        validate_dataset_version_reference_against_identity(
            reference_a,
            identity_b,
        )


def test_dataset_feature_identity_mismatch_is_rejected():
    identity_a = make_identity()

    feature_identity_b = build_feature_version_identity(
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

    dataset_b = make_dataset()

    identity_b = build_dataset_version_identity(
        dataset_b,
        feature_identity_b,
        "dataset-v1",
    )

    reference_a = build_dataset_version_reference(
        identity_a
    )

    with pytest.raises(ValueError):
        validate_dataset_version_reference_against_identity(
            reference_a,
            identity_b,
        )