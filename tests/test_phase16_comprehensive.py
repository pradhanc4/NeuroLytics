from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from features.feature_schema import FeatureSchema
from features.feature_versioning import FeatureVersionIdentity

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)

from features.sequence_dataset import (
    SequenceDataset,
    SequenceDatasetConfig,
    SequenceSample,
)

from features.sequence_dataset_artifact import (
    SequenceArtifactIntegrity,
    build_sequence_dataset_artifact,
    calculate_sequence_artifact_integrity,
    calculate_sequence_dataset_fingerprint,
    is_sequence_artifact_integrity_valid,
    serialize_sequence_dataset_artifact,
    validate_sequence_artifact_integrity,
    validate_sequence_dataset_artifact,
)

from features.sequence_dataset_integration import (
    SequenceDatasetIntegrationResult,
    build_sequence_dataset_integration,
)

from features.sequence_dataset_validator import (
    build_validated_sequence_dataset,
    validate_sequence_dataset,
)

from features.sequence_leakage_validator import (
    CLEAN,
    LEAKAGE,
    DUPLICATE_DATE,
    FUTURE_ROW,
    TARGET_DATE_INCLUDED,
    validate_sequence_components_point_in_time,
    validate_sequence_dataset_point_in_time,
    validate_sequence_sample_point_in_time,
)

from features.sequence_targets import (
    build_sequence_targets,
)

from features.sequence_temporal_split import (
    TemporalSequenceSplit,
    TemporalSplitConfig,
    split_sequence_dataset_temporally,
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


def make_config(
    sequence_length: int = 3,
    feature_names: tuple[str, ...] = (
        "sequence_target_col1",
    ),
) -> SequenceDatasetConfig:
    return SequenceDatasetConfig(
        sequence_length=sequence_length,
        input_positions=POSITIONS,
        target_positions=("col1",),
        feature_names=feature_names,
        allow_incomplete_sequences=False,
    )


def make_observation(
    day: str,
    result_id: int,
    value: int = 1,
) -> HistoricalFeatureObservation:
    return HistoricalFeatureObservation(
        result_id=result_id,
        market_id=1,
        result_date=date.fromisoformat(day),
        positions=(
            value,
            value + 1,
            value + 2,
            value + 3,
            value + 4,
            value + 5,
            value + 6,
            value + 7,
        ),
    )


def make_history(
    count: int = 8,
) -> tuple[HistoricalFeatureObservation, ...]:
    return tuple(
        make_observation(
            f"2026-01-{index:02d}",
            index,
            index,
        )
        for index in range(1, count + 1)
    )


def make_schema(
    name: str = "sequence_target_col1",
    version: str = "sequence-v1",
) -> FeatureSchema:
    return FeatureSchema(
        feature_name=name,
        feature_version=version,
        feature_type="sequence",
        source="sequence_dataset",
        position=None,
        window=3,
        lag=None,
        description="Sequence dataset feature.",
        availability_rule=(
            "Uses only observations strictly before "
            "the target date."
        ),
        data_type="integer",
    )


def make_version_identity() -> FeatureVersionIdentity:
    import hashlib

    canonical_definition = (
        '{"feature_version":"sequence-v1",'
        '"schema":"sequence-dataset-v1"}'
    )

    digest = hashlib.sha256(
        canonical_definition.encode("utf-8")
    ).hexdigest()

    return FeatureVersionIdentity(
        feature_version="sequence-v1",
        identity=f"feature-{digest}",
        algorithm="sha256",
        canonical_definition=canonical_definition,
    )


def build_components(
    observations=None,
    config=None,
):
    if observations is None:
        observations = make_history()

    if config is None:
        config = make_config()

    windows = build_sequence_windows(
        observations,
        config,
    )

    targets = build_sequence_targets(
        windows,
        observations,
        config,
    )

    return windows, targets, config


def build_dataset(
    observations=None,
    config=None,
):
    windows, targets, config = build_components(
        observations,
        config,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        config,
    )

    return (
        dataset,
        observations
        if observations is not None
        else make_history(),
        windows,
        targets,
        config,
    )


def build_integration(
    observations=None,
    config=None,
    split_date_value=None,
):
    if observations is None:
        observations = make_history()

    if config is None:
        config = make_config()

    if split_date_value is None:
        split_date_value = date(
            2026,
            1,
            6,
        )

    split_config = TemporalSplitConfig(
        split_date=split_date_value,
    )

    return build_sequence_dataset_integration(
        observations=observations,
        sequence_config=config,
        temporal_split_config=split_config,
    )


def build_artifact():
    integration = build_integration()

    return build_sequence_dataset_artifact(
        result=integration,
        schemas=(
            make_schema(),
        ),
        feature_version_identity=(
            make_version_identity()
        ),
    )


# ---------------------------------------------------------------------------
# 16.10.1 — Complete pipeline construction
# ---------------------------------------------------------------------------


def test_complete_pipeline_produces_windows():
    integration = build_integration()

    assert integration.window_count > 0


def test_complete_pipeline_produces_targets():
    integration = build_integration()

    assert integration.target_count > 0


def test_complete_pipeline_produces_samples():
    integration = build_integration()

    assert integration.sample_count > 0


def test_complete_pipeline_counts_are_consistent():
    integration = build_integration()

    assert (
        integration.sample_count
        <= integration.window_count
    )

    assert (
        integration.sample_count
        <= integration.target_count
    )


def test_complete_pipeline_is_leakage_free():
    integration = build_integration()

    assert integration.is_leakage_free is True


def test_complete_pipeline_has_train_and_validation_contract():
    integration = build_integration()

    assert (
        integration.train_count
        + integration.validation_count
        == integration.sample_count
    )


def test_complete_pipeline_preserves_sequence_length():
    integration = build_integration()

    assert (
        integration.dataset.sequence_length
        == integration.sequence_config.sequence_length
    )


def test_complete_pipeline_preserves_positions():
    integration = build_integration()

    assert (
        integration.dataset.input_positions
        == POSITIONS
    )

    assert (
        integration.dataset.target_positions
        == ("col1",)
    )


# ---------------------------------------------------------------------------
# 16.10.2 — Sequence contract validation
# ---------------------------------------------------------------------------


def test_all_samples_have_strict_target_boundary():
    integration = build_integration()

    for sample in integration.dataset.samples:
        assert (
            sample.target_date
            > sample.sequence_end_date
        )


def test_all_samples_have_configured_sequence_length():
    integration = build_integration()

    for sample in integration.dataset.samples:
        assert (
            sample.sequence_length
            == integration.sequence_config.sequence_length
        )


def test_sample_indices_are_strictly_increasing():
    integration = build_integration()

    indices = tuple(
        sample.sample_index
        for sample in integration.dataset.samples
    )

    assert indices == tuple(
        sorted(indices)
    )

    assert len(indices) == len(
        set(indices)
    )


def test_sample_target_dates_are_chronological():
    integration = build_integration()

    dates = tuple(
        sample.target_date
        for sample in integration.dataset.samples
    )

    assert dates == tuple(
        sorted(dates)
    )

    assert len(dates) == len(
        set(dates)
    )


# ---------------------------------------------------------------------------
# 16.10.3 — Window / target alignment
# ---------------------------------------------------------------------------


def test_each_target_follows_its_window():
    integration = build_integration()

    windows = integration.windows.windows
    targets = integration.targets.targets

    target_by_index = {
        target.window_index: target
        for target in targets
    }

    for window in windows:
        target = target_by_index.get(
            window.window_index
        )

        if target is None:
            continue

        assert (
            target.target_date
            > window.sequence_end_date
        )


def test_targets_are_not_inside_their_windows():
    integration = build_integration()

    for window in integration.windows.windows:
        target = next(
            (
                item
                for item in integration.targets.targets
                if item.window_index
                == window.window_index
            ),
            None,
        )

        if target is None:
            continue

        assert target.target_date not in (
            window.sequence_start_date,
            window.sequence_end_date,
        )


def test_validated_dataset_matches_window_target_pairing():
    integration = build_integration()

    assert (
        len(integration.dataset.samples)
        == len(integration.targets.targets)
    )


# ---------------------------------------------------------------------------
# 16.10.4 — Point-in-time / leakage stress
# ---------------------------------------------------------------------------


def test_clean_components_are_clean():
    observations = make_history()

    windows, targets, _ = build_components(
        observations
    )

    result = validate_sequence_components_point_in_time(
        windows,
        targets,
        observations,
    )

    assert result.status == CLEAN


def test_clean_dataset_is_leakage_free():
    dataset, observations, _, _, _ = build_dataset()

    result = validate_sequence_dataset_point_in_time(
        dataset,
        observations,
    )

    assert result.status == CLEAN


def test_future_observation_is_detected():
    observations = make_history()

    windows, targets, _ = build_components(
        observations
    )

    future = observations + (
        make_observation(
            "2026-01-20",
            100,
            100,
        ),
    )

    result = validate_sequence_components_point_in_time(
        windows,
        targets,
        future,
    )

    assert result.status == LEAKAGE

    assert any(
        issue.code == FUTURE_ROW
        for issue in result.issues
    )


def test_duplicate_date_is_detected():
    observations = make_history()

    windows, targets, _ = build_components(
        observations
    )

    duplicate = observations + (
        make_observation(
            "2026-01-04",
            100,
            100,
        ),
    )

    result = validate_sequence_components_point_in_time(
        windows,
        targets,
        duplicate,
    )

    assert result.status == LEAKAGE

    assert any(
        issue.code == DUPLICATE_DATE
        for issue in result.issues
    )


def test_target_date_in_sequence_is_rejected():
    observations = make_history()

    sample = SequenceSample(
        sample_index=0,
        sequence_start_date=date(
            2026,
            1,
            1,
        ),
        sequence_end_date=date(
            2026,
            1,
            3,
        ),
        target_date=date(
            2026,
            1,
            3,
        ),
        sequence_length=3,
        positions=POSITIONS,
        features=(
            observations[0].positions,
            observations[1].positions,
            observations[2].positions,
        ),
        target=(4,),
    )

    result = validate_sequence_sample_point_in_time(
        sample,
        observations,
    )

    assert any(
        issue.code == TARGET_DATE_INCLUDED
        for issue in result.issues
    )


# ---------------------------------------------------------------------------
# 16.10.5 — Temporal split stress
# ---------------------------------------------------------------------------


def test_temporal_split_is_disjoint():
    integration = build_integration()

    train_indices = {
        sample.sample_index
        for sample in (
            integration.temporal_split.train_samples
        )
    }

    validation_indices = {
        sample.sample_index
        for sample in (
            integration.temporal_split.validation_samples
        )
    }

    assert train_indices.isdisjoint(
        validation_indices
    )


def test_train_samples_are_on_or_before_cutoff():
    integration = build_integration()

    cutoff = (
        integration.temporal_split.split_date
    )

    for sample in (
        integration.temporal_split.train_samples
    ):
        assert sample.target_date <= cutoff


def test_validation_samples_are_after_cutoff():
    integration = build_integration()

    cutoff = (
        integration.temporal_split.split_date
    )

    for sample in (
        integration.temporal_split.validation_samples
    ):
        assert sample.target_date > cutoff


def test_temporal_split_preserves_all_samples():
    integration = build_integration()

    combined = (
        integration.temporal_split.train_samples
        + integration.temporal_split.validation_samples
    )

    assert {
        sample.sample_index
        for sample in combined
    } == {
        sample.sample_index
        for sample in integration.dataset.samples
    }


def test_split_counts_sum_to_dataset_count():
    integration = build_integration()

    assert (
        integration.temporal_split.train_count
        + integration.temporal_split.validation_count
        == integration.sample_count
    )


def test_split_is_deterministic():
    first = build_integration()
    second = build_integration()

    assert first.temporal_split == (
        second.temporal_split
    )


# ---------------------------------------------------------------------------
# 16.10.6 — Determinism / reproducibility
# ---------------------------------------------------------------------------


def test_windows_are_reproducible():
    first = build_integration()
    second = build_integration()

    assert first.windows == second.windows


def test_targets_are_reproducible():
    first = build_integration()
    second = build_integration()

    assert first.targets == second.targets


def test_datasets_are_reproducible():
    first = build_integration()
    second = build_integration()

    assert first.dataset == second.dataset


def test_integrations_are_reproducible():
    first = build_integration()
    second = build_integration()

    assert first == second


def test_serialized_artifacts_are_reproducible():
    first = build_artifact()
    second = build_artifact()

    assert (
        serialize_sequence_dataset_artifact(
            first
        )
        == serialize_sequence_dataset_artifact(
            second
        )
    )


def test_artifact_fingerprints_are_reproducible():
    first = build_artifact()
    second = build_artifact()

    assert (
        calculate_sequence_dataset_fingerprint(
            first
        )
        == calculate_sequence_dataset_fingerprint(
            second
        )
    )


# ---------------------------------------------------------------------------
# 16.10.7 — Schema / version integration
# ---------------------------------------------------------------------------


def test_artifact_preserves_schema():
    artifact = build_artifact()

    assert artifact.schemas == (
        make_schema(),
    )


def test_artifact_preserves_feature_names():
    artifact = build_artifact()

    assert artifact.feature_names == (
        "sequence_target_col1",
    )


def test_artifact_schema_names_match_feature_names():
    artifact = build_artifact()

    assert tuple(
        schema.feature_name
        for schema in artifact.schemas
    ) == artifact.feature_names


def test_artifact_preserves_version_identity():
    artifact = build_artifact()

    assert (
        artifact.feature_version_identity
        == make_version_identity()
    )


def test_artifact_requires_leakage_free_integration():
    integration = build_integration()

    dirty = replace(
        integration,
        dataset_leakage=replace(
            integration.dataset_leakage,
            status=LEAKAGE,
        ),
    )

    with pytest.raises(ValueError):
        build_sequence_dataset_artifact(
            result=dirty,
            schemas=(
                make_schema(),
            ),
            feature_version_identity=(
                make_version_identity()
            ),
        )


# ---------------------------------------------------------------------------
# 16.10.8 — Artifact integrity
# ---------------------------------------------------------------------------


def test_artifact_validation_passes():
    artifact = build_artifact()

    validate_sequence_dataset_artifact(
        artifact
    )


def test_artifact_integrity_passes():
    artifact = build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    validate_sequence_artifact_integrity(
        artifact,
        integrity,
    )

    assert is_sequence_artifact_integrity_valid(
        artifact,
        integrity,
    )


def test_integrity_digest_matches_fingerprint():
    artifact = build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert (
        integrity.digest
        == artifact.fingerprint
    )


def test_tampered_digest_fails():
    artifact = build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    tampered = SequenceArtifactIntegrity(
        algorithm=integrity.algorithm,
        digest="0" * 64,
        identity=integrity.identity,
    )

    with pytest.raises(ValueError):
        validate_sequence_artifact_integrity(
            artifact,
            tampered,
        )


def test_tampered_identity_fails():
    artifact = build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    tampered = SequenceArtifactIntegrity(
        algorithm=integrity.algorithm,
        digest=integrity.digest,
        identity="sequence-artifact-tampered",
    )

    with pytest.raises(ValueError):
        validate_sequence_artifact_integrity(
            artifact,
            tampered,
        )


# ---------------------------------------------------------------------------
# 16.10.9 — Boundary conditions
# ---------------------------------------------------------------------------


def test_insufficient_history_produces_no_valid_targeted_sample():
    observations = make_history(
        count=3
    )

    config = make_config(
        sequence_length=3
    )

    windows, targets, _ = build_components(
        observations,
        config,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        config,
    )

    assert len(
        dataset.samples
    ) == 0


def test_empty_history_is_handled():
    observations = ()

    config = make_config()

    windows, targets, _ = build_components(
        observations,
        config,
    )

    dataset = build_validated_sequence_dataset(
        windows,
        targets,
        config,
    )

    assert len(windows.windows) == 0
    assert len(targets.targets) == 0
    assert len(dataset.samples) == 0


def test_empty_history_integration_is_deterministic():
    config = make_config()

    first = build_integration(
        observations=(),
        config=config,
    )

    second = build_integration(
        observations=(),
        config=config,
    )

    assert first == second


def test_zero_values_are_preserved():
    observations = tuple(
        HistoricalFeatureObservation(
            result_id=index,
            market_id=1,
            result_date=date(
                2026,
                1,
                index,
            ),
            positions=(
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ),
        )
        for index in range(1, 7)
    )

    integration = build_integration(
        observations=observations
    )

    assert integration.sample_count > 0

    for sample in integration.dataset.samples:
        for row in sample.features:
            assert 0 in row


def test_sequence_target_is_not_confused_with_zero():
    observations = tuple(
        HistoricalFeatureObservation(
            result_id=index,
            market_id=1,
            result_date=date(
                2026,
                1,
                index,
            ),
            positions=(
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
            ),
        )
        for index in range(1, 7)
    )

    integration = build_integration(
        observations=observations
    )

    assert integration.sample_count > 0

    for sample in integration.dataset.samples:
        assert sample.target == (0,)


# ---------------------------------------------------------------------------
# 16.10.10 — Contract immutability / invalid inputs
# ---------------------------------------------------------------------------


def test_sequence_dataset_is_immutable():
    integration = build_integration()

    with pytest.raises(
        AttributeError
    ):
        integration.dataset.sequence_length = 99


def test_temporal_split_is_immutable():
    integration = build_integration()

    with pytest.raises(
        AttributeError
    ):
        integration.temporal_split.split_date = date(
            2030,
            1,
            1,
        )


def test_artifact_is_immutable():
    artifact = build_artifact()

    with pytest.raises(
        AttributeError
    ):
        artifact.fingerprint = "tampered"


def test_invalid_sequence_config_is_rejected():
    observations = make_history()

    with pytest.raises(TypeError):
        build_sequence_windows(
            observations,
            "invalid",
        )


def test_invalid_temporal_split_config_is_rejected():
    dataset, _, _, _, _ = build_dataset()

    with pytest.raises(TypeError):
        split_sequence_dataset_temporally(
            dataset,
            "invalid",
        )


def test_invalid_integration_observations_are_rejected():
    with pytest.raises(TypeError):
        build_sequence_dataset_integration(
            observations=("invalid",),
            sequence_config=make_config(),
            temporal_split_config=(
                TemporalSplitConfig(
                    split_date=date(
                        2026,
                        1,
                        5,
                    )
                )
            ),
        )


# ---------------------------------------------------------------------------
# 16.10.11 — Final end-to-end invariants
# ---------------------------------------------------------------------------


def test_end_to_end_sample_count_matches_train_plus_validation():
    integration = build_integration()

    assert (
        integration.sample_count
        == integration.train_count
        + integration.validation_count
    )


def test_end_to_end_artifact_sample_count_matches_dataset():
    artifact = build_artifact()

    assert (
        artifact.sample_count
        == len(
            artifact.sequence_dataset.samples
        )
    )


def test_end_to_end_artifact_is_leakage_free():
    artifact = build_artifact()

    assert artifact.is_leakage_free


def test_end_to_end_artifact_fingerprint_is_valid():
    artifact = build_artifact()

    assert (
        calculate_sequence_dataset_fingerprint(
            artifact
        )
        == artifact.fingerprint
    )


def test_end_to_end_integrity_is_valid():
    artifact = build_artifact()

    integrity = (
        calculate_sequence_artifact_integrity(
            artifact
        )
    )

    assert is_sequence_artifact_integrity_valid(
        artifact,
        integrity,
    )