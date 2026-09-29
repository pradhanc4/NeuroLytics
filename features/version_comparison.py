from __future__ import annotations

from dataclasses import dataclass

from features.versioning_contract import (
    DatasetVersionReference,
    FeatureVersionReference,
    validate_dataset_version_reference,
    validate_feature_version_reference,
)


UNCHANGED = "UNCHANGED"
CHANGED = "CHANGED"

FEATURE_VERSION_CHANGED = "FEATURE_VERSION_CHANGED"
FEATURE_IDENTITY_CHANGED = "FEATURE_IDENTITY_CHANGED"
DATASET_VERSION_CHANGED = "DATASET_VERSION_CHANGED"
DATASET_IDENTITY_CHANGED = "DATASET_IDENTITY_CHANGED"
ALGORITHM_CHANGED = "ALGORITHM_CHANGED"


@dataclass(frozen=True)
class VersionChange:
    """Immutable description of one detected version change."""

    code: str
    message: str


@dataclass(frozen=True)
class VersionComparisonResult:
    """Immutable result of comparing two version references."""

    status: str
    changes: tuple[VersionChange, ...]

    @property
    def is_changed(self) -> bool:
        """Return whether at least one change was detected."""

        return self.status == CHANGED

    @property
    def is_unchanged(self) -> bool:
        """Return whether no changes were detected."""

        return self.status == UNCHANGED

    @property
    def change_count(self) -> int:
        """Return the number of detected changes."""

        return len(self.changes)


def compare_feature_versions(
    first: FeatureVersionReference,
    second: FeatureVersionReference,
) -> VersionComparisonResult:
    """
    Compare two feature-version references.

    The comparison reports differences in declared feature version,
    deterministic feature identity, and versioning algorithm.

    No identity is recalculated.
    """

    validate_feature_version_reference(first)
    validate_feature_version_reference(second)

    changes: list[VersionChange] = []

    if first.feature_version != second.feature_version:
        changes.append(
            VersionChange(
                code=FEATURE_VERSION_CHANGED,
                message=(
                    "Feature version changed from "
                    f"{first.feature_version!r} to "
                    f"{second.feature_version!r}."
                ),
            )
        )

    if first.identity != second.identity:
        changes.append(
            VersionChange(
                code=FEATURE_IDENTITY_CHANGED,
                message=(
                    "Feature identity changed from "
                    f"{first.identity!r} to "
                    f"{second.identity!r}."
                ),
            )
        )

    if first.algorithm != second.algorithm:
        changes.append(
            VersionChange(
                code=ALGORITHM_CHANGED,
                message=(
                    "Feature versioning algorithm changed from "
                    f"{first.algorithm!r} to "
                    f"{second.algorithm!r}."
                ),
            )
        )

    status = CHANGED if changes else UNCHANGED

    return VersionComparisonResult(
        status=status,
        changes=tuple(changes),
    )


def compare_dataset_versions(
    first: DatasetVersionReference,
    second: DatasetVersionReference,
) -> VersionComparisonResult:
    """
    Compare two dataset-version references.

    The comparison reports differences in dataset version, dataset
    identity, associated feature version, associated feature identity,
    and versioning algorithm.

    No identity is recalculated.
    """

    validate_dataset_version_reference(first)
    validate_dataset_version_reference(second)

    changes: list[VersionChange] = []

    if first.dataset_version != second.dataset_version:
        changes.append(
            VersionChange(
                code=DATASET_VERSION_CHANGED,
                message=(
                    "Dataset version changed from "
                    f"{first.dataset_version!r} to "
                    f"{second.dataset_version!r}."
                ),
            )
        )

    if first.identity != second.identity:
        changes.append(
            VersionChange(
                code=DATASET_IDENTITY_CHANGED,
                message=(
                    "Dataset identity changed from "
                    f"{first.identity!r} to "
                    f"{second.identity!r}."
                ),
            )
        )

    if first.feature_version != second.feature_version:
        changes.append(
            VersionChange(
                code=FEATURE_VERSION_CHANGED,
                message=(
                    "Associated feature version changed from "
                    f"{first.feature_version!r} to "
                    f"{second.feature_version!r}."
                ),
            )
        )

    if first.feature_identity != second.feature_identity:
        changes.append(
            VersionChange(
                code=FEATURE_IDENTITY_CHANGED,
                message=(
                    "Associated feature identity changed from "
                    f"{first.feature_identity!r} to "
                    f"{second.feature_identity!r}."
                ),
            )
        )

    if first.algorithm != second.algorithm:
        changes.append(
            VersionChange(
                code=ALGORITHM_CHANGED,
                message=(
                    "Dataset versioning algorithm changed from "
                    f"{first.algorithm!r} to "
                    f"{second.algorithm!r}."
                ),
            )
        )

    status = CHANGED if changes else UNCHANGED

    return VersionComparisonResult(
        status=status,
        changes=tuple(changes),
    )


def validate_feature_version_comparison(
    first: FeatureVersionReference,
    second: FeatureVersionReference,
) -> VersionComparisonResult:
    """
    Compare two feature versions and raise if a change is detected.
    """

    result = compare_feature_versions(first, second)

    if result.is_changed:
        codes = ", ".join(change.code for change in result.changes)
        raise ValueError(
            f"Feature version comparison detected changes: {codes}"
        )

    return result


def validate_dataset_version_comparison(
    first: DatasetVersionReference,
    second: DatasetVersionReference,
) -> VersionComparisonResult:
    """
    Compare two dataset versions and raise if a change is detected.
    """

    result = compare_dataset_versions(first, second)

    if result.is_changed:
        codes = ", ".join(change.code for change in result.changes)
        raise ValueError(
            f"Dataset version comparison detected changes: {codes}"
        )

    return result


def is_feature_version_unchanged(
    first: FeatureVersionReference,
    second: FeatureVersionReference,
) -> bool:
    """Return whether two feature references are unchanged."""

    return compare_feature_versions(first, second).is_unchanged


def is_dataset_version_unchanged(
    first: DatasetVersionReference,
    second: DatasetVersionReference,
) -> bool:
    """Return whether two dataset references are unchanged."""

    return compare_dataset_versions(first, second).is_unchanged


def is_feature_version_changed(
    first: FeatureVersionReference,
    second: FeatureVersionReference,
) -> bool:
    """Return whether two feature references contain any change."""

    return compare_feature_versions(first, second).is_changed


def is_dataset_version_changed(
    first: DatasetVersionReference,
    second: DatasetVersionReference,
) -> bool:
    """Return whether two dataset references contain any change."""

    return compare_dataset_versions(first, second).is_changed


def get_feature_version_changes(
    first: FeatureVersionReference,
    second: FeatureVersionReference,
) -> tuple[VersionChange, ...]:
    """Return detected feature-version changes."""

    return compare_feature_versions(first, second).changes


def get_dataset_version_changes(
    first: DatasetVersionReference,
    second: DatasetVersionReference,
) -> tuple[VersionChange, ...]:
    """Return detected dataset-version changes."""

    return compare_dataset_versions(first, second).changes


__all__ = [
    "UNCHANGED",
    "CHANGED",
    "FEATURE_VERSION_CHANGED",
    "FEATURE_IDENTITY_CHANGED",
    "DATASET_VERSION_CHANGED",
    "DATASET_IDENTITY_CHANGED",
    "ALGORITHM_CHANGED",
    "VersionChange",
    "VersionComparisonResult",
    "compare_feature_versions",
    "compare_dataset_versions",
    "validate_feature_version_comparison",
    "validate_dataset_version_comparison",
    "is_feature_version_unchanged",
    "is_dataset_version_unchanged",
    "is_feature_version_changed",
    "is_dataset_version_changed",
    "get_feature_version_changes",
    "get_dataset_version_changes",
]