from __future__ import annotations

from dataclasses import dataclass

from analytics.statistical_baseline_validation import (
    validate_complete_statistical_baseline,
)
from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)
from features.version_compatibility import check_feature_version_compatibility
from features.versioning_contract import (
    DatasetVersionReference,
    FeatureVersionReference,
    VersionLineageReference,
    build_version_lineage_reference,
    validate_dataset_version_reference,
    validate_feature_version_reference,
    validate_version_lineage_reference,
)

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class StatisticalBaselineVersionIntegration:
    baseline_version: str
    feature_reference: FeatureVersionReference
    dataset_reference: DatasetVersionReference
    lineage: VersionLineageReference


@dataclass(frozen=True)
class StatisticalBaselineVersionIntegrationValidation:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def build_statistical_baseline_version_integration(
    dataset: StatisticalBaselineDataset,
    feature_reference: FeatureVersionReference,
    dataset_reference: DatasetVersionReference,
) -> StatisticalBaselineVersionIntegration:
    validate_statistical_baseline_dataset(dataset)
    validate_feature_version_reference(feature_reference)
    validate_dataset_version_reference(dataset_reference)

    compatibility = check_feature_version_compatibility(
        feature_reference,
        dataset_reference,
    )
    if not compatibility.is_compatible:
        raise ValueError(
            "Feature and dataset versions are incompatible."
        )

    report = validate_complete_statistical_baseline(dataset)
    if not report.is_valid:
        raise ValueError(
            "Statistical baseline is invalid: "
            + "; ".join(report.issues)
        )

    if dataset.contract.baseline_version != dataset_reference.dataset_version:
        raise ValueError(
            "Dataset version reference must match the baseline dataset version."
        )

    lineage = build_version_lineage_reference(
        feature_version=feature_reference.feature_version,
        feature_identity=feature_reference.identity,
        dataset_version=dataset_reference.dataset_version,
        dataset_identity=dataset_reference.identity,
    )

    return StatisticalBaselineVersionIntegration(
        baseline_version=dataset.contract.baseline_version,
        feature_reference=feature_reference,
        dataset_reference=dataset_reference,
        lineage=lineage,
    )


def validate_statistical_baseline_version_integration(
    integration: StatisticalBaselineVersionIntegration,
) -> None:
    if not isinstance(
        integration,
        StatisticalBaselineVersionIntegration,
    ):
        raise TypeError(
            "integration must be a StatisticalBaselineVersionIntegration instance."
        )
    if not integration.baseline_version.strip():
        raise ValueError("baseline_version must be non-empty.")
    validate_feature_version_reference(integration.feature_reference)
    validate_dataset_version_reference(integration.dataset_reference)
    validate_version_lineage_reference(integration.lineage)

    compatibility = check_feature_version_compatibility(
        integration.feature_reference,
        integration.dataset_reference,
    )
    if not compatibility.is_compatible:
        raise ValueError("feature and dataset versions are incompatible.")

    if integration.lineage.feature_version != integration.feature_reference.feature_version:
        raise ValueError("lineage feature version does not match.")
    if integration.lineage.dataset_version != integration.dataset_reference.dataset_version:
        raise ValueError("lineage dataset version does not match.")


def validate_statistical_baseline_version_integration_result(
    integration: StatisticalBaselineVersionIntegration,
) -> StatisticalBaselineVersionIntegrationValidation:
    try:
        validate_statistical_baseline_version_integration(integration)
    except (TypeError, ValueError) as exc:
        return StatisticalBaselineVersionIntegrationValidation(
            INVALID,
            (str(exc),),
        )
    return StatisticalBaselineVersionIntegrationValidation(VALID, ())


def is_statistical_baseline_version_integration_valid(
    integration: StatisticalBaselineVersionIntegration,
) -> bool:
    return validate_statistical_baseline_version_integration_result(
        integration
    ).is_valid
