from __future__ import annotations

from dataclasses import replace

import pytest

from features.version_comparison import (
    ALGORITHM_CHANGED,
    CHANGED,
    DATASET_IDENTITY_CHANGED,
    DATASET_VERSION_CHANGED,
    FEATURE_IDENTITY_CHANGED,
    FEATURE_VERSION_CHANGED,
    UNCHANGED,
    VersionChange,
    VersionComparisonResult,
    compare_dataset_versions,
    compare_feature_versions,
    get_dataset_version_changes,
    get_feature_version_changes,
    is_dataset_version_changed,
    is_dataset_version_unchanged,
    is_feature_version_changed,
    is_feature_version_unchanged,
    validate_dataset_version_comparison,
    validate_feature_version_comparison,
)
from features.versioning_contract import (
    build_dataset_version_reference,
    build_feature_version_reference,
)


def make_feature_reference(
    feature_version: str = "v1",
    identity: str = "feature-aaa",
    algorithm: str = "sha256",
):
    return build_feature_version_reference(
        feature_version=feature_version,
        identity=identity,
        algorithm=algorithm,
    )


def make_dataset_reference(
    dataset_version: str = "dataset-v1",
    identity: str = "dataset-aaa",
    algorithm: str = "sha256",
    feature_version: str = "v1",
    feature_identity: str = "feature-aaa",
):
    return build_dataset_version_reference(
        dataset_version=dataset_version,
        identity=identity,
        algorithm=algorithm,
        feature_version=feature_version,
        feature_identity=feature_identity,
    )


def test_identical_feature_versions_are_unchanged():
    reference = make_feature_reference()

    result = compare_feature_versions(reference, reference)

    assert result.status == UNCHANGED
    assert result.is_unchanged is True
    assert result.is_changed is False
    assert result.changes == ()
    assert result.change_count == 0


def test_feature_version_change_is_detected():
    first = make_feature_reference(feature_version="v1")
    second = make_feature_reference(feature_version="v2")

    result = compare_feature_versions(first, second)

    assert result.status == CHANGED
    assert FEATURE_VERSION_CHANGED in {
        change.code for change in result.changes
    }


def test_feature_identity_change_is_detected():
    first = make_feature_reference(identity="feature-aaa")
    second = make_feature_reference(identity="feature-bbb")

    result = compare_feature_versions(first, second)

    assert result.status == CHANGED
    assert result.changes[0].code == FEATURE_IDENTITY_CHANGED


def test_feature_algorithm_change_is_detected():
    first = make_feature_reference(algorithm="sha256")
    second = make_feature_reference(algorithm="sha512")

    result = compare_feature_versions(first, second)

    assert result.status == CHANGED
    assert result.changes[0].code == ALGORITHM_CHANGED


def test_multiple_feature_changes_are_reported():
    first = make_feature_reference(
        feature_version="v1",
        identity="feature-aaa",
        algorithm="sha256",
    )
    second = make_feature_reference(
        feature_version="v2",
        identity="feature-bbb",
        algorithm="sha512",
    )

    result = compare_feature_versions(first, second)

    assert result.status == CHANGED
    assert result.change_count == 3
    assert {
        change.code for change in result.changes
    } == {
        FEATURE_VERSION_CHANGED,
        FEATURE_IDENTITY_CHANGED,
        ALGORITHM_CHANGED,
    }


def test_feature_change_messages_are_deterministic():
    first = make_feature_reference(
        feature_version="v1",
        identity="feature-aaa",
        algorithm="sha256",
    )
    second = make_feature_reference(
        feature_version="v2",
        identity="feature-bbb",
        algorithm="sha512",
    )

    first_result = compare_feature_versions(first, second)
    second_result = compare_feature_versions(first, second)

    assert first_result == second_result


def test_feature_change_objects_are_immutable():
    change = VersionChange(
        code=FEATURE_VERSION_CHANGED,
        message="changed",
    )

    with pytest.raises(AttributeError):
        change.code = "other"


def test_feature_comparison_result_is_immutable():
    result = VersionComparisonResult(
        status=UNCHANGED,
        changes=(),
    )

    with pytest.raises(AttributeError):
        result.status = CHANGED


def test_feature_change_getter_returns_tuple():
    first = make_feature_reference(feature_version="v1")
    second = make_feature_reference(feature_version="v2")

    changes = get_feature_version_changes(first, second)

    assert isinstance(changes, tuple)
    assert len(changes) == 1
    assert changes[0].code == FEATURE_VERSION_CHANGED


def test_feature_boolean_helpers():
    first = make_feature_reference(feature_version="v1")
    second = make_feature_reference(feature_version="v2")
    same = make_feature_reference(feature_version="v1")

    assert is_feature_version_changed(first, second) is True
    assert is_feature_version_unchanged(first, second) is False
    assert is_feature_version_changed(first, same) is False
    assert is_feature_version_unchanged(first, same) is True


def test_feature_validation_accepts_unchanged_versions():
    reference = make_feature_reference()

    result = validate_feature_version_comparison(
        reference,
        reference,
    )

    assert result.status == UNCHANGED


def test_feature_validation_rejects_changed_versions():
    first = make_feature_reference(feature_version="v1")
    second = make_feature_reference(feature_version="v2")

    with pytest.raises(ValueError, match="FEATURE_VERSION_CHANGED"):
        validate_feature_version_comparison(first, second)


def test_identical_dataset_versions_are_unchanged():
    reference = make_dataset_reference()

    result = compare_dataset_versions(reference, reference)

    assert result.status == UNCHANGED
    assert result.is_unchanged is True
    assert result.is_changed is False
    assert result.changes == ()
    assert result.change_count == 0


def test_dataset_version_change_is_detected():
    first = make_dataset_reference(dataset_version="dataset-v1")
    second = make_dataset_reference(dataset_version="dataset-v2")

    result = compare_dataset_versions(first, second)

    assert result.status == CHANGED
    assert DATASET_VERSION_CHANGED in {
        change.code for change in result.changes
    }


def test_dataset_identity_change_is_detected():
    first = make_dataset_reference(identity="dataset-aaa")
    second = make_dataset_reference(identity="dataset-bbb")

    result = compare_dataset_versions(first, second)

    assert result.status == CHANGED
    assert result.changes[0].code == DATASET_IDENTITY_CHANGED


def test_dataset_feature_version_change_is_detected():
    first = make_dataset_reference(feature_version="v1")
    second = make_dataset_reference(feature_version="v2")

    result = compare_dataset_versions(first, second)

    assert result.status == CHANGED
    assert FEATURE_VERSION_CHANGED in {
        change.code for change in result.changes
    }


def test_dataset_feature_identity_change_is_detected():
    first = make_dataset_reference(feature_identity="feature-aaa")
    second = make_dataset_reference(feature_identity="feature-bbb")

    result = compare_dataset_versions(first, second)

    assert result.status == CHANGED
    assert FEATURE_IDENTITY_CHANGED in {
        change.code for change in result.changes
    }


def test_dataset_algorithm_change_is_detected():
    first = make_dataset_reference(algorithm="sha256")
    second = make_dataset_reference(algorithm="sha512")

    result = compare_dataset_versions(first, second)

    assert result.status == CHANGED
    assert result.changes[0].code == ALGORITHM_CHANGED


def test_multiple_dataset_changes_are_reported():
    first = make_dataset_reference(
        dataset_version="dataset-v1",
        identity="dataset-aaa",
        algorithm="sha256",
        feature_version="v1",
        feature_identity="feature-aaa",
    )
    second = make_dataset_reference(
        dataset_version="dataset-v2",
        identity="dataset-bbb",
        algorithm="sha512",
        feature_version="v2",
        feature_identity="feature-bbb",
    )

    result = compare_dataset_versions(first, second)

    assert result.status == CHANGED
    assert result.change_count == 5
    assert {
        change.code for change in result.changes
    } == {
        DATASET_VERSION_CHANGED,
        DATASET_IDENTITY_CHANGED,
        FEATURE_VERSION_CHANGED,
        FEATURE_IDENTITY_CHANGED,
        ALGORITHM_CHANGED,
    }


def test_dataset_change_messages_are_deterministic():
    first = make_dataset_reference(
        dataset_version="dataset-v1",
        identity="dataset-aaa",
        feature_version="v1",
        feature_identity="feature-aaa",
    )
    second = make_dataset_reference(
        dataset_version="dataset-v2",
        identity="dataset-bbb",
        feature_version="v2",
        feature_identity="feature-bbb",
    )

    first_result = compare_dataset_versions(first, second)
    second_result = compare_dataset_versions(first, second)

    assert first_result == second_result


def test_dataset_change_getter_returns_tuple():
    first = make_dataset_reference(dataset_version="dataset-v1")
    second = make_dataset_reference(dataset_version="dataset-v2")

    changes = get_dataset_version_changes(first, second)

    assert isinstance(changes, tuple)
    assert len(changes) == 1
    assert changes[0].code == DATASET_VERSION_CHANGED


def test_dataset_boolean_helpers():
    first = make_dataset_reference(dataset_version="dataset-v1")
    second = make_dataset_reference(dataset_version="dataset-v2")
    same = make_dataset_reference(dataset_version="dataset-v1")

    assert is_dataset_version_changed(first, second) is True
    assert is_dataset_version_unchanged(first, second) is False
    assert is_dataset_version_changed(first, same) is False
    assert is_dataset_version_unchanged(first, same) is True


def test_dataset_validation_accepts_unchanged_versions():
    reference = make_dataset_reference()

    result = validate_dataset_version_comparison(
        reference,
        reference,
    )

    assert result.status == UNCHANGED


def test_dataset_validation_rejects_changed_versions():
    first = make_dataset_reference(dataset_version="dataset-v1")
    second = make_dataset_reference(dataset_version="dataset-v2")

    with pytest.raises(ValueError, match="DATASET_VERSION_CHANGED"):
        validate_dataset_version_comparison(first, second)


def test_invalid_feature_reference_is_rejected():
    valid = make_feature_reference()

    with pytest.raises(TypeError):
        compare_feature_versions("invalid", valid)


def test_invalid_dataset_reference_is_rejected():
    valid = make_dataset_reference()

    with pytest.raises(TypeError):
        compare_dataset_versions("invalid", valid)


def test_feature_comparison_does_not_mutate_references():
    first = make_feature_reference()
    second = make_feature_reference()

    before_first = first
    before_second = second

    compare_feature_versions(first, second)

    assert first == before_first
    assert second == before_second


def test_dataset_comparison_does_not_mutate_references():
    first = make_dataset_reference()
    second = make_dataset_reference()

    before_first = first
    before_second = second

    compare_dataset_versions(first, second)

    assert first == before_first
    assert second == before_second


def test_feature_comparison_uses_directional_values():
    first = make_feature_reference(feature_version="v1")
    second = make_feature_reference(feature_version="v2")

    result = compare_feature_versions(first, second)

    assert "v1" in result.changes[0].message
    assert "v2" in result.changes[0].message


def test_dataset_comparison_uses_directional_values():
    first = make_dataset_reference(dataset_version="dataset-v1")
    second = make_dataset_reference(dataset_version="dataset-v2")

    result = compare_dataset_versions(first, second)

    assert "dataset-v1" in result.changes[0].message
    assert "dataset-v2" in result.changes[0].message


def test_feature_identity_can_change_without_feature_version_label_change():
    first = make_feature_reference(
        feature_version="v1",
        identity="feature-aaa",
    )
    second = make_feature_reference(
        feature_version="v1",
        identity="feature-bbb",
    )

    result = compare_feature_versions(first, second)

    assert result.status == CHANGED
    assert result.change_count == 1
    assert result.changes[0].code == FEATURE_IDENTITY_CHANGED


def test_dataset_identity_can_change_without_dataset_version_label_change():
    first = make_dataset_reference(
        dataset_version="dataset-v1",
        identity="dataset-aaa",
    )
    second = make_dataset_reference(
        dataset_version="dataset-v1",
        identity="dataset-bbb",
    )

    result = compare_dataset_versions(first, second)

    assert result.status == CHANGED
    assert result.change_count == 1
    assert result.changes[0].code == DATASET_IDENTITY_CHANGED


def test_same_dataset_identity_with_different_feature_identity_is_changed():
    first = make_dataset_reference(
        identity="dataset-aaa",
        feature_identity="feature-aaa",
    )
    second = make_dataset_reference(
        identity="dataset-aaa",
        feature_identity="feature-bbb",
    )

    result = compare_dataset_versions(first, second)

    assert result.status == CHANGED
    assert result.change_count == 1
    assert result.changes[0].code == FEATURE_IDENTITY_CHANGED