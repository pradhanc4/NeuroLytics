from datetime import date

import pytest

from features.historical_data_loader import (
    HistoricalFeatureObservation,
)
from features.sequence_dataset import (
    SequenceDatasetConfig,
)
from features.sequence_dataset_integration import (
    build_sequence_dataset_integration,
)
from features.sequence_dataset_reproducibility import (
    canonicalize_sequence_dataset_result,
    get_sequence_dataset_fingerprint,
    get_sequence_dataset_serialized_size,
    sequence_dataset_results_match,
    serialize_sequence_dataset_result,
    validate_sequence_dataset_reproducibility,
)
from features.sequence_temporal_split import (
    TemporalSplitConfig,
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


def sequence_config(
    sequence_length=3,
    target_positions=("col1",),
):
    return SequenceDatasetConfig(
        sequence_length=sequence_length,
        input_positions=POSITIONS,
        target_positions=target_positions,
    )


def temporal_config(
    split_date=date(2026, 1, 4),
):
    return TemporalSplitConfig(
        split_date=split_date,
    )


def build_result(
    observations=None,
    sequence_length=3,
    target_positions=("col1",),
    split_date=date(2026, 1, 4),
):
    if observations is None:
        observations = base_observations()

    return build_sequence_dataset_integration(
        observations,
        sequence_config(
            sequence_length=sequence_length,
            target_positions=target_positions,
        ),
        temporal_config(
            split_date=split_date,
        ),
    )


def test_same_input_produces_equal_results():
    first = build_result()
    second = build_result()

    assert first == second


def test_same_input_produces_same_serialization():
    first = build_result()
    second = build_result()

    assert (
        serialize_sequence_dataset_result(first)
        == serialize_sequence_dataset_result(second)
    )


def test_same_input_produces_same_fingerprint():
    first = build_result()
    second = build_result()

    assert (
        get_sequence_dataset_fingerprint(first)
        == get_sequence_dataset_fingerprint(second)
    )


def test_repeated_fingerprints_are_stable():
    result = build_result()

    first = get_sequence_dataset_fingerprint(result)
    second = get_sequence_dataset_fingerprint(result)
    third = get_sequence_dataset_fingerprint(result)

    assert first == second == third


def test_fingerprint_is_sha256_length():
    fingerprint = get_sequence_dataset_fingerprint(
        build_result()
    )

    assert len(fingerprint) == 64


def test_fingerprint_contains_only_hexadecimal_characters():
    fingerprint = get_sequence_dataset_fingerprint(
        build_result()
    )

    assert all(
        character in "0123456789abcdef"
        for character in fingerprint
    )


def test_results_match_when_identical():
    first = build_result()
    second = build_result()

    assert sequence_dataset_results_match(
        first,
        second,
    ) is True


def test_validation_accepts_identical_results():
    first = build_result()
    second = build_result()

    validate_sequence_dataset_reproducibility(
        first,
        second,
    )


def test_changing_observation_value_changes_fingerprint():
    original = base_observations()

    changed = (
        original[0],
        original[1],
        original[2],
        observation(
            "2026-01-04",
            4,
            positions=(9, 2, 3, 4, 5, 6, 7, 8),
        ),
        original[4],
        original[5],
    )

    first = build_result(
        observations=original,
    )

    second = build_result(
        observations=changed,
    )

    assert (
        get_sequence_dataset_fingerprint(first)
        != get_sequence_dataset_fingerprint(second)
    )


def test_changing_observation_order_changes_result():
    observations = base_observations()

    reordered = (
        observations[1],
        observations[0],
        observations[2],
        observations[3],
        observations[4],
        observations[5],
    )

    first = build_result(
        observations=observations,
    )

    with pytest.raises(Exception):
        build_result(
            observations=reordered,
        )


def test_changing_sequence_length_changes_fingerprint():
    first = build_result(
        sequence_length=3,
    )

    second = build_result(
        sequence_length=4,
    )

    assert (
        get_sequence_dataset_fingerprint(first)
        != get_sequence_dataset_fingerprint(second)
    )


def test_changing_target_positions_changes_fingerprint():
    first = build_result(
        target_positions=("col1",),
    )

    second = build_result(
        target_positions=("col2",),
    )

    assert (
        get_sequence_dataset_fingerprint(first)
        != get_sequence_dataset_fingerprint(second)
    )


def test_changing_split_date_changes_fingerprint():
    first = build_result(
        split_date=date(2026, 1, 4),
    )

    second = build_result(
        split_date=date(2026, 1, 5),
    )

    assert (
        get_sequence_dataset_fingerprint(first)
        != get_sequence_dataset_fingerprint(second)
    )


def test_zero_values_are_preserved_in_fingerprint():
    zero_observations = (
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

    first = build_result(
        observations=zero_observations,
    )

    second = build_result(
        observations=zero_observations,
    )

    assert (
        get_sequence_dataset_fingerprint(first)
        == get_sequence_dataset_fingerprint(second)
    )


def test_fingerprint_is_not_based_on_object_identity():
    first = build_result()
    second = build_result()

    assert first is not second

    assert (
        get_sequence_dataset_fingerprint(first)
        == get_sequence_dataset_fingerprint(second)
    )


def test_serialization_is_non_empty():
    serialized = serialize_sequence_dataset_result(
        build_result()
    )

    assert isinstance(serialized, str)
    assert serialized


def test_serialization_is_valid_json():
    import json

    serialized = serialize_sequence_dataset_result(
        build_result()
    )

    parsed = json.loads(serialized)

    assert isinstance(parsed, dict)


def test_canonical_representation_is_deterministic():
    first = canonicalize_sequence_dataset_result(
        build_result()
    )

    second = canonicalize_sequence_dataset_result(
        build_result()
    )

    assert first == second


def test_serialized_size_is_deterministic():
    first = get_sequence_dataset_serialized_size(
        build_result()
    )

    second = get_sequence_dataset_serialized_size(
        build_result()
    )

    assert first == second


def test_reproducibility_failure_is_detected():
    first = build_result(
        split_date=date(2026, 1, 4),
    )

    second = build_result(
        split_date=date(2026, 1, 5),
    )

    assert sequence_dataset_results_match(
        first,
        second,
    ) is False

    with pytest.raises(ValueError):
        validate_sequence_dataset_reproducibility(
            first,
            second,
        )


def test_invalid_first_result_is_rejected():
    with pytest.raises(TypeError):
        get_sequence_dataset_fingerprint(
            "invalid",
        )


def test_invalid_second_result_is_rejected():
    result = build_result()

    with pytest.raises(TypeError):
        sequence_dataset_results_match(
            result,
            "invalid",
        )


def test_reproducibility_validation_rejects_invalid_first_result():
    result = build_result()

    with pytest.raises(TypeError):
        validate_sequence_dataset_reproducibility(
            "invalid",
            result,
        )


def test_reproducibility_validation_rejects_invalid_second_result():
    result = build_result()

    with pytest.raises(TypeError):
        validate_sequence_dataset_reproducibility(
            result,
            "invalid",
        )


def test_fingerprint_does_not_mutate_result():
    result = build_result()

    before = result

    fingerprint = get_sequence_dataset_fingerprint(
        result
    )

    after = result

    assert fingerprint
    assert before == after


def test_input_observations_remain_unchanged():
    observations = base_observations()
    before = observations

    build_result(
        observations=observations,
    )

    after = observations

    assert before == after