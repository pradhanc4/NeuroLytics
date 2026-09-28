from datetime import date

import pytest

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.sequence_dataset import (
    SequenceDatasetConfig,
    SequenceSample,
)
from features.sequence_leakage_validator import (
    CLEAN,
    LEAKAGE,
    DUPLICATE_DATE,
    FUTURE_ROW,
    SEQUENCE_DATE_MISMATCH,
    SEQUENCE_TARGET_MISMATCH,
    TARGET_DATE_INCLUDED,
    TARGET_IN_SEQUENCE,
    TEMPORAL_ORDER,
    get_sequence_leakage_issue_count,
    get_sequence_leakage_issues,
    get_sequence_leakage_status,
    is_sequence_leakage_free,
    validate_sequence_components_point_in_time,
    validate_sequence_dataset_point_in_time,
    validate_sequence_sample_point_in_time,
)
from features.sequence_targets import (
    SequenceTargetDataset,
    build_sequence_targets,
)
from features.sequence_windows import (
    build_sequence_windows,
)


POSITIONS = (
    "col1",
    "col2",
    "col3",
    "col4",
    "col5",
    "col6",
    "col7",
    "col8",
)


def config(
    sequence_length=3,
    input_positions=POSITIONS,
    target_positions=("col1",),
    feature_names=(),
    allow_incomplete_sequences=False,
):
    return SequenceDatasetConfig(
        sequence_length=sequence_length,
        input_positions=input_positions,
        target_positions=target_positions,
        feature_names=feature_names,
        allow_incomplete_sequences=allow_incomplete_sequences,
    )


def observation(
    day,
    result_id,
    market_id=1,
    positions=(1, 2, 3, 4, 5, 6, 7, 8),
):
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=market_id,
        result_date=date.fromisoformat(day),
        positions=positions,
    )


def base_observations():
    return (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-03", 3),
        observation("2026-01-04", 4),
        observation("2026-01-05", 5),
        observation("2026-01-06", 6),
    )


def build_components(
    observations=None,
    cfg=None,
):
    observations = (
        base_observations()
        if observations is None
        else observations
    )

    cfg = (
        config()
        if cfg is None
        else cfg
    )

    windows = build_sequence_windows(
        observations,
        cfg,
    )

    targets = build_sequence_targets(
        windows,
        observations,
        cfg,
    )

    return windows, targets, cfg


def build_clean_dataset():
    observations = base_observations()

    cfg = config(
        sequence_length=3,
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    from features.sequence_dataset_validator import (
        build_validated_sequence_dataset,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    return dataset, observations, windows, targets


# ---------------------------------------------------------------------------
# Clean validation
# ---------------------------------------------------------------------------


def test_clean_sequence_sample_has_no_leakage():
    dataset, observations, _, _ = build_clean_dataset()

    sample = dataset.samples[0]

    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    assert result.status == CLEAN
    assert result.is_clean is True
    assert result.issue_count == 0
    assert result.issues == ()


def test_clean_sequence_dataset_is_clean():
    dataset, observations, _, _ = build_clean_dataset()

    result = validate_sequence_dataset_point_in_time(
        dataset,
        observations,
    )

    assert result.status == CLEAN
    assert result.is_clean is True
    assert result.issue_count == 0
    assert result.issues == ()


def test_clean_sequence_components_are_clean():
    _, observations, windows, targets = build_clean_dataset()

    result = validate_sequence_components_point_in_time(
        windows,
        targets,
        observations,
    )

    assert result.status == CLEAN
    assert result.is_clean is True
    assert result.issue_count == 0
    assert result.issues == ()


def test_clean_result_accessors():
    dataset, observations, _, _ = build_clean_dataset()

    result = validate_sequence_dataset_point_in_time(
        dataset,
        observations,
    )

    assert get_sequence_leakage_status(result) == CLEAN
    assert get_sequence_leakage_issues(result) == ()
    assert get_sequence_leakage_issue_count(result) == 0
    assert is_sequence_leakage_free(result) is True


# ---------------------------------------------------------------------------
# Target / temporal leakage
# ---------------------------------------------------------------------------


def test_target_date_inside_sequence_is_detected():
    observations = base_observations()

    sample = SequenceSample(
        sample_index=0,
        sequence_start_date=date(2026, 1, 1),
        sequence_end_date=date(2026, 1, 3),
        target_date=date(2026, 1, 3),
        sequence_length=3,
        positions=POSITIONS,
        features=(
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        target=(1,),
    )

    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert TARGET_DATE_INCLUDED in codes
    assert TARGET_IN_SEQUENCE in codes


def test_future_observation_inside_sequence_is_detected():
    observations = base_observations()

    sample = SequenceSample(
        sample_index=0,
        sequence_start_date=date(2026, 1, 2),
        sequence_end_date=date(2026, 1, 5),
        target_date=date(2026, 1, 4),
        sequence_length=3,
        positions=POSITIONS,
        features=(
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        target=(1,),
    )

    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert FUTURE_ROW in codes


def test_duplicate_dates_are_detected():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-02", 2),
        observation("2026-01-02", 3),
        observation("2026-01-03", 4),
    )

    sample = SequenceSample(
        sample_index=0,
        sequence_start_date=date(2026, 1, 1),
        sequence_end_date=date(2026, 1, 2),
        target_date=date(2026, 1, 3),
        sequence_length=2,
        positions=POSITIONS,
        features=(
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        target=(1,),
    )

    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert DUPLICATE_DATE in codes


def test_temporal_order_violation_is_detected():
    observations = (
        observation("2026-01-01", 1),
        observation("2026-01-03", 2),
        observation("2026-01-02", 3),
        observation("2026-01-04", 4),
    )

    sample = SequenceSample(
        sample_index=0,
        sequence_start_date=date(2026, 1, 1),
        sequence_end_date=date(2026, 1, 2),
        target_date=date(2026, 1, 4),
        sequence_length=3,
        positions=POSITIONS,
        features=(
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        target=(1,),
    )

    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert TEMPORAL_ORDER in codes


def test_sequence_start_date_mismatch_is_detected():
    observations = base_observations()

    sample = SequenceSample(
        sample_index=0,
        sequence_start_date=date(2026, 1, 2),
        sequence_end_date=date(2026, 1, 3),
        target_date=date(2026, 1, 4),
        sequence_length=3,
        positions=POSITIONS,
        features=(
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        target=(1,),
    )

    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert SEQUENCE_DATE_MISMATCH in codes


def test_sequence_end_date_mismatch_is_detected():
    observations = base_observations()

    sample = SequenceSample(
        sample_index=0,
        sequence_start_date=date(2026, 1, 1),
        sequence_end_date=date(2026, 1, 2),
        target_date=date(2026, 1, 4),
        sequence_length=3,
        positions=POSITIONS,
        features=(
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        target=(1,),
    )

    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert SEQUENCE_DATE_MISMATCH in codes


# ---------------------------------------------------------------------------
# Target history / target relationship
# ---------------------------------------------------------------------------


def test_target_date_not_in_history_is_detected():
    observations = base_observations()

    sample = SequenceSample(
        sample_index=0,
        sequence_start_date=date(2026, 1, 1),
        sequence_end_date=date(2026, 1, 3),
        target_date=date(2026, 1, 10),
        sequence_length=3,
        positions=POSITIONS,
        features=(
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        target=(1,),
    )

    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    codes = {
        issue.code
        for issue in result.issues
    }

    assert SEQUENCE_TARGET_MISMATCH in codes


def test_zero_values_are_not_treated_as_leakage():
    observations = (
        observation(
            "2026-01-01",
            1,
            positions=(0, 0, 0, 0, 0, 0, 0, 0),
        ),
        observation(
            "2026-01-02",
            2,
            positions=(0, 0, 0, 0, 0, 0, 0, 0),
        ),
        observation(
            "2026-01-03",
            3,
            positions=(0, 0, 0, 0, 0, 0, 0, 0),
        ),
        observation(
            "2026-01-04",
            4,
            positions=(0, 0, 0, 0, 0, 0, 0, 0),
        ),
    )

    cfg = config(
        sequence_length=3,
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    from features.sequence_dataset_validator import (
        build_validated_sequence_dataset,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    result = validate_sequence_dataset_point_in_time(
        dataset,
        observations,
    )

    assert result.is_clean is True


# ---------------------------------------------------------------------------
# Dataset behavior
# ---------------------------------------------------------------------------


def test_multiple_samples_are_validated():
    dataset, observations, _, _ = build_clean_dataset()

    result = validate_sequence_dataset_point_in_time(
        dataset,
        observations,
    )

    assert result.sample_count == len(
        dataset.samples
    )


def test_repeated_validation_is_deterministic():
    dataset, observations, _, _ = build_clean_dataset()

    first = validate_sequence_dataset_point_in_time(
        dataset,
        observations,
    )

    second = validate_sequence_dataset_point_in_time(
        dataset,
        observations,
    )

    assert first == second


def test_empty_dataset_is_clean():
    cfg = config()

    from features.sequence_dataset import (
        build_sequence_dataset,
    )

    dataset = build_sequence_dataset(
        cfg,
        (),
    )

    result = validate_sequence_dataset_point_in_time(
        dataset,
        (),
    )

    assert result.status == CLEAN
    assert result.is_clean is True
    assert result.sample_count == 0
    assert result.issues == ()


def test_empty_components_are_clean():
    cfg = config()

    windows = build_sequence_windows(
        (),
        cfg,
    )

    targets = SequenceTargetDataset(
        target_positions=cfg.target_positions,
        targets=(),
    )

    result = validate_sequence_components_point_in_time(
        windows,
        targets,
        (),
    )

    assert result.status == CLEAN
    assert result.is_clean is True
    assert result.sample_count == 0
    assert result.issues == ()


# ---------------------------------------------------------------------------
# Type validation
# ---------------------------------------------------------------------------


def test_invalid_sample_type_is_rejected():
    with pytest.raises(TypeError):
        validate_sequence_sample_point_in_time(
            "invalid",
            (),
        )


def test_invalid_dataset_type_is_rejected():
    with pytest.raises(TypeError):
        validate_sequence_dataset_point_in_time(
            "invalid",
            (),
        )


def test_invalid_windows_type_is_rejected():
    cfg = config()

    targets = SequenceTargetDataset(
        target_positions=cfg.target_positions,
        targets=(),
    )

    with pytest.raises(TypeError):
        validate_sequence_components_point_in_time(
            "invalid",
            targets,
            (),
        )


def test_invalid_targets_type_is_rejected():
    cfg = config()

    windows = build_sequence_windows(
        (),
        cfg,
    )

    with pytest.raises(TypeError):
        validate_sequence_components_point_in_time(
            windows,
            "invalid",
            (),
        )


def test_invalid_observation_type_is_rejected():
    dataset, _, _, _ = build_clean_dataset()

    with pytest.raises(TypeError):
        validate_sequence_dataset_point_in_time(
            dataset,
            ("invalid",),
        )


# ---------------------------------------------------------------------------
# Contract violations
# ---------------------------------------------------------------------------


def test_sequence_target_date_equal_to_end_is_leakage():
    observations = base_observations()

    sample = SequenceSample(
        sample_index=0,
        sequence_start_date=date(2026, 1, 1),
        sequence_end_date=date(2026, 1, 3),
        target_date=date(2026, 1, 3),
        sequence_length=3,
        positions=POSITIONS,
        features=(
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        target=(1,),
    )

    # SequenceSample itself is allowed to be instantiated directly.
    # The PIT validator must report the contract violation without
    # requiring build_sequence_dataset(), because that constructor
    # correctly rejects the invalid sample earlier.
    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    assert result.status == LEAKAGE
    assert any(
        issue.code == TARGET_DATE_INCLUDED
        for issue in result.issues
    )


# ---------------------------------------------------------------------------
# Component-level future / duplicate history
# ---------------------------------------------------------------------------


def test_future_rows_are_rejected_in_component_validation():
    observations = base_observations()

    cfg = config(
        sequence_length=3,
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    # The latest valid target in the components is 2026-01-06.
    # 2026-01-10 is therefore a future historical row relative
    # to the component validation horizon.
    future_observations = observations + (
        observation(
            "2026-01-10",
            100,
        ),
    )

    result = validate_sequence_components_point_in_time(
        windows,
        targets,
        future_observations,
    )

    assert result.status == LEAKAGE
    assert any(
        issue.code == FUTURE_ROW
        for issue in result.issues
    )


def test_duplicate_dates_are_rejected_in_component_validation():
    observations = base_observations()

    cfg = config(
        sequence_length=3,
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    duplicate_observations = observations + (
        observation(
            "2026-01-03",
            100,
        ),
    )

    result = validate_sequence_components_point_in_time(
        windows,
        targets,
        duplicate_observations,
    )

    assert result.status == LEAKAGE
    assert any(
        issue.code == DUPLICATE_DATE
        for issue in result.issues
    )


# ---------------------------------------------------------------------------
# Result metadata
# ---------------------------------------------------------------------------


def test_result_contains_correct_target_date():
    dataset, observations, _, _ = build_clean_dataset()

    result = validate_sequence_dataset_point_in_time(
        dataset,
        observations,
    )

    assert result.target_date == date(
        2026,
        1,
        6,
    )


def test_issue_count_matches_issue_collection():
    observations = base_observations()

    cfg = config(
        sequence_length=3,
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    from features.sequence_dataset_validator import (
        build_validated_sequence_dataset,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    # Introduce a duplicate historical date without changing
    # the valid SequenceDataset contract.
    invalid_observations = observations + (
        observation(
            "2026-01-03",
            100,
        ),
    )

    result = validate_sequence_dataset_point_in_time(
        dataset,
        invalid_observations,
    )

    assert result.status == LEAKAGE
    assert get_sequence_leakage_issue_count(result) == len(
        get_sequence_leakage_issues(result)
    )
    assert result.issue_count > 0


def test_leakage_result_status_is_not_clean_when_issue_exists():
    observations = base_observations()

    cfg = config(
        sequence_length=3,
    )

    windows, targets, _ = build_components(
        observations,
        cfg,
    )

    from features.sequence_dataset_validator import (
        build_validated_sequence_dataset,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        cfg,
    )

    invalid_observations = observations + (
        observation(
            "2026-01-03",
            100,
        ),
    )

    result = validate_sequence_dataset_point_in_time(
        dataset,
        invalid_observations,
    )

    assert result.status == LEAKAGE
    assert result.is_clean is False
    assert len(result.issues) > 0