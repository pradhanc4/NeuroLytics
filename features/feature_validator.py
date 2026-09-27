from __future__ import annotations

from dataclasses import dataclass

from features.feature_schema import (
    FeatureSchema,
    validate_feature_schema,
)
from features.feature_schema_builder import (
    build_feature_schema_from_record,
)
from features.unified_dataset import (
    UnifiedFeatureDataset,
)


VALID = "VALID"
WARNING = "WARNING"
INVALID = "INVALID"


@dataclass(frozen=True)
class FeatureValidationIssue:
    """One feature validation issue."""

    code: str
    message: str
    feature_name: str | None
    severity: str


@dataclass(frozen=True)
class FeatureValidationResult:
    """Complete validation result for one unified feature dataset."""

    status: str
    feature_count: int
    schema_count: int
    issues: tuple[FeatureValidationIssue, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _validate_status(
    status: str,
) -> None:
    if status not in (
        VALID,
        WARNING,
        INVALID,
    ):
        raise ValueError(
            f"Unsupported validation status: {status}"
        )


def _build_issue(
    code: str,
    message: str,
    feature_name: str | None,
    severity: str,
) -> FeatureValidationIssue:
    if severity not in (
        VALID,
        WARNING,
        INVALID,
    ):
        raise ValueError(
            f"Unsupported issue severity: {severity}"
        )

    return FeatureValidationIssue(
        code=code,
        message=message,
        feature_name=feature_name,
        severity=severity,
    )


def _build_schemas_safely(
    dataset: UnifiedFeatureDataset,
) -> tuple[
    tuple[FeatureSchema, ...],
    tuple[FeatureValidationIssue, ...],
]:
    """
    Build schemas while converting schema-builder failures
    into validation issues instead of allowing validation to crash.
    """

    schemas: list[FeatureSchema] = []
    issues: list[FeatureValidationIssue] = []

    seen_names: set[str] = set()

    for record in dataset.records:
        if record.feature_name in seen_names:
            issues.append(
                _build_issue(
                    code="DUPLICATE_FEATURE_NAMES",
                    message=(
                        "Duplicate feature name detected."
                    ),
                    feature_name=record.feature_name,
                    severity=INVALID,
                )
            )
            continue

        seen_names.add(
            record.feature_name
        )

        try:
            schema = build_feature_schema_from_record(
                record,
                dataset.feature_version,
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            issues.append(
                _build_issue(
                    code="INVALID_FEATURE_SCHEMA",
                    message=str(exc),
                    feature_name=record.feature_name,
                    severity=INVALID,
                )
            )
            continue

        schemas.append(schema)

    return (
        tuple(schemas),
        tuple(issues),
    )


def _validate_feature_count(
    dataset: UnifiedFeatureDataset,
    schemas: tuple[FeatureSchema, ...],
) -> list[FeatureValidationIssue]:
    issues: list[FeatureValidationIssue] = []

    if dataset.feature_count != len(schemas):
        issues.append(
            _build_issue(
                code="FEATURE_SCHEMA_COUNT_MISMATCH",
                message=(
                    "Feature count does not match schema count."
                ),
                feature_name=None,
                severity=INVALID,
            )
        )

    return issues


def _validate_feature_names(
    dataset: UnifiedFeatureDataset,
    schemas: tuple[FeatureSchema, ...],
) -> list[FeatureValidationIssue]:
    issues: list[FeatureValidationIssue] = []

    feature_names = dataset.feature_names
    schema_names = tuple(
        schema.feature_name
        for schema in schemas
    )

    feature_name_counts: dict[str, int] = {}

    for feature_name in feature_names:
        feature_name_counts[feature_name] = (
            feature_name_counts.get(
                feature_name,
                0,
            )
            + 1
        )

    for feature_name, count in sorted(
        feature_name_counts.items()
    ):
        if count > 1:
            issues.append(
                _build_issue(
                    code="DUPLICATE_FEATURE_NAMES",
                    message=(
                        "Duplicate feature name detected."
                    ),
                    feature_name=feature_name,
                    severity=INVALID,
                )
            )

    schema_name_counts: dict[str, int] = {}

    for schema_name in schema_names:
        schema_name_counts[schema_name] = (
            schema_name_counts.get(
                schema_name,
                0,
            )
            + 1
        )

    for schema_name, count in sorted(
        schema_name_counts.items()
    ):
        if count > 1:
            issues.append(
                _build_issue(
                    code="DUPLICATE_SCHEMA_NAMES",
                    message=(
                        "Duplicate schema name detected."
                    ),
                    feature_name=schema_name,
                    severity=INVALID,
                )
            )

    feature_name_set = set(
        feature_names
    )

    schema_name_set = set(
        schema_names
    )

    for feature_name in sorted(
        feature_name_set - schema_name_set
    ):
        issues.append(
            _build_issue(
                code="MISSING_FEATURE_SCHEMA",
                message=(
                    "Feature does not have a "
                    "corresponding schema."
                ),
                feature_name=feature_name,
                severity=INVALID,
            )
        )

    for feature_name in sorted(
        schema_name_set - feature_name_set
    ):
        issues.append(
            _build_issue(
                code="ORPHAN_FEATURE_SCHEMA",
                message=(
                    "Feature schema does not have "
                    "a corresponding feature."
                ),
                feature_name=feature_name,
                severity=INVALID,
            )
        )

    return issues


def _validate_schema_versions(
    dataset: UnifiedFeatureDataset,
    schemas: tuple[FeatureSchema, ...],
) -> list[FeatureValidationIssue]:
    issues: list[FeatureValidationIssue] = []

    for schema in schemas:
        if schema.feature_version != (
            dataset.feature_version
        ):
            issues.append(
                _build_issue(
                    code="FEATURE_VERSION_MISMATCH",
                    message=(
                        "Feature schema version does not "
                        "match the unified dataset version."
                    ),
                    feature_name=schema.feature_name,
                    severity=INVALID,
                )
            )

    return issues


def _validate_schema_definitions(
    schemas: tuple[FeatureSchema, ...],
) -> list[FeatureValidationIssue]:
    issues: list[FeatureValidationIssue] = []

    for schema in schemas:
        try:
            validate_feature_schema(
                schema
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            issues.append(
                _build_issue(
                    code="INVALID_FEATURE_SCHEMA",
                    message=str(exc),
                    feature_name=schema.feature_name,
                    severity=INVALID,
                )
            )

    return issues


def _validate_feature_values(
    dataset: UnifiedFeatureDataset,
) -> list[FeatureValidationIssue]:
    issues: list[FeatureValidationIssue] = []

    for record in dataset.records:
        value = record.value

        if value is None:
            continue

        if isinstance(
            value,
            bool,
        ):
            continue

        if isinstance(
            value,
            int,
        ):
            continue

        if isinstance(
            value,
            float,
        ):
            continue

        if isinstance(
            value,
            str,
        ):
            continue

        issues.append(
            _build_issue(
                code="UNSUPPORTED_FEATURE_VALUE_TYPE",
                message=(
                    "Feature contains an unsupported "
                    "value type."
                ),
                feature_name=record.feature_name,
                severity=INVALID,
            )
        )

    return issues


def _validate_schema_order(
    dataset: UnifiedFeatureDataset,
    schemas: tuple[FeatureSchema, ...],
) -> list[FeatureValidationIssue]:
    issues: list[FeatureValidationIssue] = []

    feature_names = dataset.feature_names

    schema_names = tuple(
        schema.feature_name
        for schema in schemas
    )

    if feature_names != schema_names:
        issues.append(
            _build_issue(
                code="FEATURE_SCHEMA_ORDER_MISMATCH",
                message=(
                    "Feature and schema ordering "
                    "does not match."
                ),
                feature_name=None,
                severity=INVALID,
            )
        )

    return issues


def _determine_status(
    issues: tuple[FeatureValidationIssue, ...],
) -> str:
    if any(
        issue.severity == INVALID
        for issue in issues
    ):
        return INVALID

    if any(
        issue.severity == WARNING
        for issue in issues
    ):
        return WARNING

    return VALID


def validate_feature_dataset(
    dataset: UnifiedFeatureDataset,
) -> FeatureValidationResult:
    """
    Validate a unified feature dataset and its schemas.

    Validation failures are returned as structured issues.
    They are not raised as exceptions unless the input object
    itself is of an invalid type.
    """

    if not isinstance(
        dataset,
        UnifiedFeatureDataset,
    ):
        raise TypeError(
            "dataset must be a UnifiedFeatureDataset instance."
        )

    schemas, schema_build_issues = (
        _build_schemas_safely(
            dataset
        )
    )

    issues: list[FeatureValidationIssue] = []

    issues.extend(
        schema_build_issues
    )

    issues.extend(
        _validate_feature_count(
            dataset,
            schemas,
        )
    )

    issues.extend(
        _validate_feature_names(
            dataset,
            schemas,
        )
    )

    issues.extend(
        _validate_schema_versions(
            dataset,
            schemas,
        )
    )

    issues.extend(
        _validate_schema_definitions(
            schemas,
        )
    )

    issues.extend(
        _validate_feature_values(
            dataset,
        )
    )

    issues.extend(
        _validate_schema_order(
            dataset,
            schemas,
        )
    )

    final_issues = tuple(
        issues
    )

    status = _determine_status(
        final_issues
    )

    _validate_status(
        status
    )

    return FeatureValidationResult(
        status=status,
        feature_count=dataset.feature_count,
        schema_count=len(schemas),
        issues=final_issues,
    )


def get_validation_status(
    result: FeatureValidationResult,
) -> str:
    if not isinstance(
        result,
        FeatureValidationResult,
    ):
        raise TypeError(
            "result must be a FeatureValidationResult instance."
        )

    return result.status


def get_validation_issues(
    result: FeatureValidationResult,
) -> tuple[FeatureValidationIssue, ...]:
    if not isinstance(
        result,
        FeatureValidationResult,
    ):
        raise TypeError(
            "result must be a FeatureValidationResult instance."
        )

    return result.issues


def get_validation_issue_count(
    result: FeatureValidationResult,
) -> int:
    if not isinstance(
        result,
        FeatureValidationResult,
    ):
        raise TypeError(
            "result must be a FeatureValidationResult instance."
        )

    return result.issue_count


def is_feature_dataset_valid(
    result: FeatureValidationResult,
) -> bool:
    if not isinstance(
        result,
        FeatureValidationResult,
    ):
        raise TypeError(
            "result must be a FeatureValidationResult instance."
        )

    return result.is_valid