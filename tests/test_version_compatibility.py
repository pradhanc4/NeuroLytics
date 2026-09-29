from __future__ import annotations

from dataclasses import replace

import pytest

from features.feature_config import FeatureConfig
from features.feature_schema import FeatureSchema
from features.feature_versioning import (
    build_feature_version_identity,
)
from features.dataset_versioning import (
    build_dataset_version_identity,
    build_dataset_version_reference,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
    UnifiedFeatureRecord,
)
from features.version_compatibility import (
    COMPATIBLE,
    INCOMPATIBLE,
    VersionCompatibilityResult,
    check_feature_version_compatibility,
    get_compatibility_issues,
    get_compatibility_status,
    is_feature_version_compatible,
    is_version_compatibility_valid,
    validate_feature_version_compatibility,
)
from features.versioning_contract import (
    build_feature_version_reference,
)


def make_config(
    feature_version: str = "v1",
    lag_windows: tuple[int, ...] = (1, 2, 3),
) -> FeatureConfig:
    return FeatureConfig(
        feature_version=feature_version,
        positions=(
            "col1",
            "col2",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "col8",
        ),
        lag_windows=lag_windows,
        rolling_windows=(3, 5, 7),
        frequency_enabled=True,
        frequency_window=5,
        recency_enabled=True,
        recency_lookback=10,
        position_features_enabled=True,
    )


def make_schema(
    feature_version: str = "v1",
) -> FeatureSchema:
    return FeatureSchema(
        feature_name="col1_lag_1",
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
    lag_windows: tuple[int, ...] = (1, 2, 3),
):
    return build_feature_version_identity(
        make_config(
            feature_version=feature_version,
            lag_windows=lag_windows,
        ),
        (
            make_schema(
                feature_version=feature_version
            ),
        ),
    )


def make_dataset(
    feature_version: str = "v1",
) -> UnifiedFeatureDataset:
    return UnifiedFeatureDataset(
        target_date=__import__(
            "datetime"
        ).date(
            2026,
            1,
            5,
        ),
        feature_version=feature_version,
        records=(
            UnifiedFeatureRecord(
                feature_name="col1_lag_1",
                value=5,
                feature_type="lag",
                source="lag_features",
            ),
        ),
    )


def make_references(
    feature_version: str = "v1",
    lag_windows: tuple[int, ...] = (1, 2, 3),
    dataset_version: str = "dataset-v1",
):
    feature_identity = make_feature_identity(
        feature_version=feature_version,
        lag_windows=lag_windows,
    )

    feature_reference = build_feature_version_reference(
    feature_version=feature_identity.feature_version,
    identity=feature_identity.identity,
    algorithm=feature_identity.algorithm,
)

    dataset = make_dataset(
        feature_version=feature_version
    )

    dataset_identity = build_dataset_version_identity(
        dataset=dataset,
        feature_identity=feature_identity,
        dataset_version=dataset_version,
    )

    dataset_reference = build_dataset_version_reference(
        dataset_identity
    )

    return (
        feature_reference,
        dataset_reference,
    )


def test_compatible_versions_return_compatible():
    feature_reference, dataset_reference = (
        make_references()
    )

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    assert result.status == COMPATIBLE
    assert result.is_compatible is True
    assert result.issue_count == 0


def test_compatible_versions_have_no_issues():
    feature_reference, dataset_reference = (
        make_references()
    )

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    assert result.issues == ()


def test_incompatible_feature_version_is_detected():
    feature_reference, dataset_reference = (
        make_references()
    )

    incompatible_feature_reference = replace(
        feature_reference,
        feature_version="v2",
    )

    result = check_feature_version_compatibility(
        incompatible_feature_reference,
        dataset_reference,
    )

    assert result.status == INCOMPATIBLE
    assert result.is_compatible is False
    assert any(
        issue.code == "FEATURE_VERSION_MISMATCH"
        for issue in result.issues
    )


def test_incompatible_feature_identity_is_detected():
    feature_reference, dataset_reference = (
        make_references()
    )

    incompatible_feature_reference = replace(
        feature_reference,
        identity="feature-tampered",
    )

    result = check_feature_version_compatibility(
        incompatible_feature_reference,
        dataset_reference,
    )

    assert result.status == INCOMPATIBLE
    assert any(
        issue.code == "FEATURE_IDENTITY_MISMATCH"
        for issue in result.issues
    )


def test_incompatible_algorithm_is_detected():
    feature_reference, dataset_reference = (
        make_references()
    )

    incompatible_feature_reference = replace(
        feature_reference,
        algorithm="different",
    )

    result = check_feature_version_compatibility(
        incompatible_feature_reference,
        dataset_reference,
    )

    assert result.status == INCOMPATIBLE
    assert any(
        issue.code == "IDENTITY_ALGORITHM_MISMATCH"
        for issue in result.issues
    )


def test_multiple_compatibility_issues_can_be_reported():
    feature_reference, dataset_reference = (
        make_references()
    )

    incompatible_feature_reference = replace(
        feature_reference,
        feature_version="v2",
        identity="feature-tampered",
        algorithm="different",
    )

    result = check_feature_version_compatibility(
        incompatible_feature_reference,
        dataset_reference,
    )

    assert result.status == INCOMPATIBLE
    assert result.issue_count == 3

    codes = {
        issue.code
        for issue in result.issues
    }

    assert codes == {
        "FEATURE_VERSION_MISMATCH",
        "FEATURE_IDENTITY_MISMATCH",
        "IDENTITY_ALGORITHM_MISMATCH",
    }


def test_validation_function_accepts_compatible_versions():
    feature_reference, dataset_reference = (
        make_references()
    )

    validate_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )


def test_validation_function_rejects_incompatible_versions():
    feature_reference, dataset_reference = (
        make_references()
    )

    incompatible_feature_reference = replace(
        feature_reference,
        identity="feature-tampered",
    )

    with pytest.raises(
        ValueError,
        match="incompatible",
    ):
        validate_feature_version_compatibility(
            incompatible_feature_reference,
            dataset_reference,
        )


def test_boolean_helper_returns_true():
    feature_reference, dataset_reference = (
        make_references()
    )

    assert (
        is_feature_version_compatible(
            feature_reference,
            dataset_reference,
        )
        is True
    )


def test_boolean_helper_returns_false():
    feature_reference, dataset_reference = (
        make_references()
    )

    incompatible_feature_reference = replace(
        feature_reference,
        identity="feature-tampered",
    )

    assert (
        is_feature_version_compatible(
            incompatible_feature_reference,
            dataset_reference,
        )
        is False
    )


def test_invalid_feature_reference_type_is_rejected():
    _, dataset_reference = make_references()

    with pytest.raises(TypeError):
        check_feature_version_compatibility(
            object(),
            dataset_reference,
        )


def test_invalid_dataset_reference_type_is_rejected():
    feature_reference, _ = make_references()

    with pytest.raises(TypeError):
        check_feature_version_compatibility(
            feature_reference,
            object(),
        )


def test_invalid_feature_reference_content_is_reported():
    feature_reference, dataset_reference = (
        make_references()
    )

    invalid_reference = replace(
        feature_reference,
        feature_version="",
    )

    result = check_feature_version_compatibility(
        invalid_reference,
        dataset_reference,
    )

    assert result.status == INCOMPATIBLE
    assert any(
        issue.code == "INVALID_FEATURE_REFERENCE"
        for issue in result.issues
    )


def test_invalid_dataset_reference_content_is_reported():
    feature_reference, dataset_reference = (
        make_references()
    )

    invalid_reference = replace(
        dataset_reference,
        dataset_version="",
    )

    result = check_feature_version_compatibility(
        feature_reference,
        invalid_reference,
    )

    assert result.status == INCOMPATIBLE
    assert any(
        issue.code == "INVALID_DATASET_REFERENCE"
        for issue in result.issues
    )


def test_invalid_feature_and_dataset_references_are_both_reported():
    feature_reference, dataset_reference = (
        make_references()
    )

    invalid_feature_reference = replace(
        feature_reference,
        feature_version="",
    )

    invalid_dataset_reference = replace(
        dataset_reference,
        dataset_version="",
    )

    result = check_feature_version_compatibility(
        invalid_feature_reference,
        invalid_dataset_reference,
    )

    assert result.status == INCOMPATIBLE

    codes = {
        issue.code
        for issue in result.issues
    }

    assert "INVALID_FEATURE_REFERENCE" in codes
    assert "INVALID_DATASET_REFERENCE" in codes


def test_result_is_immutable():
    feature_reference, dataset_reference = (
        make_references()
    )

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    with pytest.raises(
        AttributeError
    ):
        result.status = INCOMPATIBLE


def test_issue_count_matches_issue_tuple():
    feature_reference, dataset_reference = (
        make_references()
    )

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    assert result.issue_count == len(
        result.issues
    )


def test_status_getter():
    feature_reference, dataset_reference = (
        make_references()
    )

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    assert (
        get_compatibility_status(result)
        == COMPATIBLE
    )


def test_issue_getter():
    feature_reference, dataset_reference = (
        make_references()
    )

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    assert (
        get_compatibility_issues(result)
        == ()
    )


def test_validity_helper():
    feature_reference, dataset_reference = (
        make_references()
    )

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    assert (
        is_version_compatibility_valid(result)
        is True
    )


def test_invalid_result_type_is_rejected():
    with pytest.raises(TypeError):
        get_compatibility_status(
            object()
        )


def test_invalid_issue_result_type_is_rejected():
    with pytest.raises(TypeError):
        get_compatibility_issues(
            object()
        )


def test_invalid_validity_result_type_is_rejected():
    with pytest.raises(TypeError):
        is_version_compatibility_valid(
            object()
        )


def test_feature_definition_change_is_incompatible():
    feature_reference, dataset_reference = (
        make_references()
    )

    changed_feature_identity = make_feature_identity(
        feature_version="v1",
        lag_windows=(1, 2),
    )

    changed_reference = build_feature_version_reference(
    feature_version=changed_feature_identity.feature_version,
    identity=changed_feature_identity.identity,
    algorithm=changed_feature_identity.algorithm,
)

    result = check_feature_version_compatibility(
        changed_reference,
        dataset_reference,
    )

    assert result.status == INCOMPATIBLE
    assert any(
        issue.code == "FEATURE_IDENTITY_MISMATCH"
        for issue in result.issues
    )


def test_dataset_version_label_does_not_determine_feature_compatibility():
    feature_reference, dataset_reference = (
        make_references(
            dataset_version="dataset-v999"
        )
    )

    result = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    assert result.status == COMPATIBLE


def test_same_feature_identity_with_different_dataset_identity_is_compatible():
    feature_reference, dataset_reference_a = (
        make_references(
            dataset_version="dataset-v1"
        )
    )

    _, dataset_reference_b = make_references(
        dataset_version="dataset-v2"
    )

    result_a = check_feature_version_compatibility(
        feature_reference,
        dataset_reference_a,
    )

    result_b = check_feature_version_compatibility(
        feature_reference,
        dataset_reference_b,
    )

    assert result_a.is_compatible is True
    assert result_b.is_compatible is True


def test_compatibility_is_deterministic():
    feature_reference, dataset_reference = (
        make_references()
    )

    result_a = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    result_b = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )

    assert result_a == result_b