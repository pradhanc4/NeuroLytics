from datetime import date

import pytest

from analytics.statistical_baseline_contract import (
    build_statistical_baseline_contract,
)
from analytics.statistical_baseline_dataset import (
    INVALID,
    VALID,
    StatisticalBaselineDataset,
    StatisticalBaselineDatasetValidationResult,
    build_statistical_baseline_dataset,
    build_statistical_baseline_dataset_from_list,
    get_statistical_baseline_columns,
    get_statistical_baseline_dates,
    get_statistical_baseline_observation_count,
    get_statistical_baseline_observations,
    is_statistical_baseline_dataset_valid,
    validate_statistical_baseline_dataset,
    validate_statistical_baseline_dataset_result,
)
from analytics.statistical_foundation import (
    StatisticalAnalysisRequest,
    StatisticalObservation,
    build_analysis_result,
)


def build_observations():
    return (
        StatisticalObservation(
            record_date=date(2026, 1, 3),
            column_name="col2",
            value=7,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=5,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 2),
            column_name="col1",
            value=0,
        ),
    )


def build_contract(
    observations=None,
):
    if observations is None:
        observations = build_observations()

    request = StatisticalAnalysisRequest(
        market_id=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        analysis_version="v1",
    )

    result = build_analysis_result(
        request,
        observations,
    )

    return build_statistical_baseline_contract(
        result=result,
        observations=observations,
        analysis_columns=("col1", "col2"),
        baseline_version="v18.2",
    )


def test_build_baseline_dataset():
    observations = build_observations()

    dataset = build_statistical_baseline_dataset(
        contract=build_contract(observations),
        observations=observations,
    )

    assert isinstance(
        dataset,
        StatisticalBaselineDataset,
    )

    assert dataset.observation_count == 3


def test_dataset_is_deterministically_sorted():
    dataset = build_statistical_baseline_dataset(
        contract=build_contract(),
        observations=build_observations(),
    )

    assert dataset.observations == (
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=5,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 2),
            column_name="col1",
            value=0,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 3),
            column_name="col2",
            value=7,
        ),
    )


def test_actual_zero_is_preserved():
    dataset = build_statistical_baseline_dataset(
        contract=build_contract(),
        observations=build_observations(),
    )

    zero_observations = tuple(
        observation
        for observation in dataset.observations
        if observation.value == 0
    )

    assert len(zero_observations) == 1
    assert zero_observations[0].column_name == "col1"


def test_dates_are_deterministic_and_unique():
    dataset = build_statistical_baseline_dataset(
        contract=build_contract(),
        observations=build_observations(),
    )

    assert dataset.dates == (
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    )


def test_columns_follow_contract_order():
    dataset = build_statistical_baseline_dataset(
        contract=build_contract(),
        observations=build_observations(),
    )

    assert dataset.columns == (
        "col1",
        "col2",
    )


def test_valid_dataset():
    dataset = build_statistical_baseline_dataset(
        contract=build_contract(),
        observations=build_observations(),
    )

    validate_statistical_baseline_dataset(
        dataset
    )

    assert is_statistical_baseline_dataset_valid(
        dataset
    )


def test_validation_result_is_valid():
    dataset = build_statistical_baseline_dataset(
        contract=build_contract(),
        observations=build_observations(),
    )

    result = validate_statistical_baseline_dataset_result(
        dataset
    )

    assert result.status == VALID
    assert result.is_valid
    assert result.issue_count == 0


def test_list_builder():
    observations = list(
        build_observations()
    )

    dataset = build_statistical_baseline_dataset_from_list(
        contract=build_contract(),
        observations=observations,
    )

    assert dataset.observation_count == 3


def test_list_builder_rejects_tuple():
    with pytest.raises(
        TypeError,
        match="must be a list",
    ):
        build_statistical_baseline_dataset_from_list(
            contract=build_contract(),
            observations=build_observations(),
        )


def test_builder_requires_contract():
    with pytest.raises(
        TypeError,
        match="StatisticalBaselineContract",
    ):
        build_statistical_baseline_dataset(
            contract=object(),
            observations=build_observations(),
        )


def test_builder_requires_tuple():
    with pytest.raises(
        TypeError,
        match="must be a tuple",
    ):
        build_statistical_baseline_dataset(
            contract=build_contract(),
            observations=list(
                build_observations()
            ),
        )


def test_builder_rejects_duplicate_date_column():
    observations = (
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=5,
        ),
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=7,
        ),
    )

    contract = build_contract(
        observations
    )

    with pytest.raises(
        ValueError,
        match="Duplicate statistical observation",
    ):
        build_statistical_baseline_dataset(
            contract=contract,
            observations=observations,
        )


def test_builder_rejects_unsupported_column():
    observations = (
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="invalid",
            value=5,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Unsupported column",
    ):
        build_statistical_baseline_dataset(
            contract=build_contract(
                build_observations()
            ),
            observations=observations,
        )


def test_builder_rejects_invalid_digit():
    observations = (
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=10,
        ),
    )

    with pytest.raises(
        ValueError,
        match="digit range",
    ):
        build_statistical_baseline_dataset(
            contract=build_contract(
                build_observations()
            ),
            observations=observations,
        )


def test_builder_rejects_boolean_value():
    observations = (
        StatisticalObservation(
            record_date=date(2026, 1, 1),
            column_name="col1",
            value=True,
        ),
    )

    with pytest.raises(
        ValueError,
        match="integer",
    ):
        build_statistical_baseline_dataset(
            contract=build_contract(
                build_observations()
            ),
            observations=observations,
        )


def test_builder_rejects_date_before_contract():
    observations = (
        StatisticalObservation(
            record_date=date(2025, 12, 31),
            column_name="col1",
            value=5,
        ),
    )

    contract = build_contract(
        build_observations()
    )

    with pytest.raises(
        ValueError,
        match="before the contract start date",
    ):
        build_statistical_baseline_dataset(
            contract=contract,
            observations=observations,
        )


def test_builder_rejects_date_after_contract():
    observations = (
        StatisticalObservation(
            record_date=date(2026, 1, 11),
            column_name="col1",
            value=5,
        ),
    )

    contract = build_contract(
        build_observations()
    )

    with pytest.raises(
        ValueError,
        match="after the contract end date",
    ):
        build_statistical_baseline_dataset(
            contract=contract,
            observations=observations,
        )


def test_contract_alignment_is_required():
    observations = build_observations()

    contract = build_contract(
        observations
    )

    invalid_contract = type(contract)(
        market_id=contract.market_id,
        analysis_version=contract.analysis_version,
        baseline_version=contract.baseline_version,
        start_date=contract.start_date,
        end_date=contract.end_date,
        analysis_columns=contract.analysis_columns,
        observation_count=contract.observation_count + 1,
        column_observation_counts=contract.column_observation_counts,
    )

    with pytest.raises(
        ValueError,
        match="invalid.*contract",
    ):
        build_statistical_baseline_dataset(
            contract=invalid_contract,
            observations=observations,
        )


def test_getters():
    dataset = build_statistical_baseline_dataset(
        contract=build_contract(),
        observations=build_observations(),
    )

    assert get_statistical_baseline_observation_count(
        dataset
    ) == 3

    assert get_statistical_baseline_observations(
        dataset
    ) == dataset.observations

    assert get_statistical_baseline_dates(
        dataset
    ) == (
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    )

    assert get_statistical_baseline_columns(
        dataset
    ) == (
        "col1",
        "col2",
    )


def test_dataset_validation_rejects_unsorted_observations():
    observations = build_observations()

    dataset = StatisticalBaselineDataset(
        contract=build_contract(
            observations
        ),
        observations=observations,
    )

    with pytest.raises(
        ValueError,
        match="deterministic",
    ):
        validate_statistical_baseline_dataset(
            dataset
        )


def test_dataset_validation_rejects_invalid_contract():
    contract = build_contract()

    invalid_contract = type(contract)(
        market_id=contract.market_id,
        analysis_version=contract.analysis_version,
        baseline_version="",
        start_date=contract.start_date,
        end_date=contract.end_date,
        analysis_columns=contract.analysis_columns,
        observation_count=contract.observation_count,
        column_observation_counts=contract.column_observation_counts,
    )

    dataset = StatisticalBaselineDataset(
        contract=invalid_contract,
        observations=(
            StatisticalObservation(
                record_date=date(2026, 1, 1),
                column_name="col1",
                value=5,
            ),
            StatisticalObservation(
                record_date=date(2026, 1, 2),
                column_name="col1",
                value=0,
            ),
            StatisticalObservation(
                record_date=date(2026, 1, 3),
                column_name="col2",
                value=7,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="contract is invalid",
    ):
        validate_statistical_baseline_dataset(
            dataset
        )


def test_invalid_dataset_returns_validation_result():
    result = validate_statistical_baseline_dataset_result(
        object()
    )

    assert result.status == INVALID
    assert not result.is_valid
    assert result.issue_count == 1
    assert (
        result.issues[0].code
        == "INVALID_DATASET_TYPE"
    )


def test_validation_result_is_immutable():
    result = StatisticalBaselineDatasetValidationResult(
        status=VALID,
        issues=(),
    )

    with pytest.raises(
        AttributeError
    ):
        result.status = INVALID