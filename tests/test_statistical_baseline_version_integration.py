from datetime import date

import pytest

from analytics.statistical_baseline_contract import build_statistical_baseline_contract
from analytics.statistical_baseline_dataset import build_statistical_baseline_dataset
from analytics.statistical_baseline_version_integration import (
    VALID,
    build_statistical_baseline_version_integration,
    is_statistical_baseline_version_integration_valid,
    validate_statistical_baseline_version_integration,
    validate_statistical_baseline_version_integration_result,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)
from features.versioning_contract import (
    build_dataset_version_reference,
    build_feature_version_reference,
)


def dataset():
    observations = (
        StatisticalObservation(date(2026, 1, 1), "col1", 0),
        StatisticalObservation(date(2026, 1, 2), "col1", 1),
    )
    request = StatisticalAnalysisRequest(
        1, date(2026, 1, 1), date(2026, 1, 2), "v1"
    )
    result = build_analysis_result(request, observations)
    contract = build_statistical_baseline_contract(
        result, observations, ("col1",), "ds-1"
    )
    return build_statistical_baseline_dataset(contract, observations)


def refs():
    feature = build_feature_version_reference("f1", "feature-id", "sha256")
    dataset_ref = build_dataset_version_reference(
        "ds-1", "dataset-id", "sha256", "f1", "feature-id"
    )
    return feature, dataset_ref


def test_build_and_validate():
    integration = build_statistical_baseline_version_integration(
        dataset(), *refs()
    )
    validate_statistical_baseline_version_integration(integration)
    result = validate_statistical_baseline_version_integration_result(
        integration
    )
    assert result.status == VALID
    assert result.is_valid
    assert is_statistical_baseline_version_integration_valid(integration)


def test_lineage_matches_references():
    integration = build_statistical_baseline_version_integration(
        dataset(), *refs()
    )
    assert integration.lineage.feature_version == "f1"
    assert integration.lineage.dataset_version == "ds-1"


def test_mismatched_versions_rejected():
    feature, dataset_ref = refs()
    mismatched = build_dataset_version_reference(
        "ds-1", "dataset-id", "sha256", "other", "other-id"
    )
    with pytest.raises(ValueError, match="incompatible"):
        build_statistical_baseline_version_integration(
            dataset(), feature, mismatched
        )


def test_invalid_result_type():
    result = validate_statistical_baseline_version_integration_result(object())
    assert not result.is_valid
