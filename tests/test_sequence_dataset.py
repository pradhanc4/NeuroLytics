from datetime import date

import pytest

from features.sequence_dataset import (
    SequenceDataset,
    SequenceDatasetConfig,
    SequenceSample,
    build_sequence_dataset,
    get_sequence_feature_names,
    get_sequence_input_positions,
    get_sequence_sample,
    get_sequence_sample_count,
    get_sequence_target_positions,
    validate_sequence_dataset,
    validate_sequence_dataset_config,
    validate_sequence_sample,
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


def config(**overrides):
    values = {
        "sequence_length": 3,
        "input_positions": POSITIONS,
        "target_positions": POSITIONS,
        "feature_names": (
            "col1_latest_value",
            "col2_latest_value",
        ),
    }

    values.update(
        overrides
    )

    return SequenceDatasetConfig(
        **values
    )


def sample(**overrides):
    values = {
        "sample_index": 0,
        "sequence_start_date": date(
            2026,
            1,
            1,
        ),
        "sequence_end_date": date(
            2026,
            1,
            3,
        ),
        "target_date": date(
            2026,
            1,
            4,
        ),
        "sequence_length": 3,
        "positions": POSITIONS,
        "features": (
            (1, 2),
            (2, 3),
            (3, 4),
        ),
        "target": (
            4,
            5,
            6,
            7,
            8,
            9,
            0,
            1,
        ),
    }

    values.update(
        overrides
    )

    return SequenceSample(
        **values
    )


def test_valid_config():
    validate_sequence_dataset_config(
        config()
    )


def test_config_is_immutable():
    with pytest.raises(AttributeError):
        config().sequence_length = 5


def test_config_rejects_zero_length():
    with pytest.raises(ValueError):
        validate_sequence_dataset_config(
            config(
                sequence_length=0
            )
        )


def test_config_rejects_boolean_length():
    with pytest.raises(TypeError):
        validate_sequence_dataset_config(
            config(
                sequence_length=True
            )
        )


def test_config_rejects_empty_positions():
    with pytest.raises(ValueError):
        validate_sequence_dataset_config(
            config(
                input_positions=()
            )
        )


def test_config_rejects_unknown_position():
    with pytest.raises(ValueError):
        validate_sequence_dataset_config(
            config(
                input_positions=("col9",)
            )
        )


def test_config_rejects_duplicate_positions():
    with pytest.raises(ValueError):
        validate_sequence_dataset_config(
            config(
                input_positions=(
                    "col1",
                    "col1",
                )
            )
        )


def test_config_rejects_duplicate_feature_names():
    with pytest.raises(ValueError):
        validate_sequence_dataset_config(
            config(
                feature_names=(
                    "x",
                    "x",
                )
            )
        )


def test_config_rejects_blank_feature_name():
    with pytest.raises(ValueError):
        validate_sequence_dataset_config(
            config(
                feature_names=(" ",)
            )
        )


def test_config_rejects_invalid_incomplete_flag():
    with pytest.raises(TypeError):
        validate_sequence_dataset_config(
            config(
                allow_incomplete_sequences=1
            )
        )


def test_valid_sample():
    validate_sequence_sample(
        sample()
    )


def test_sample_is_immutable():
    with pytest.raises(AttributeError):
        sample().sample_index = 2


def test_sample_rejects_negative_index():
    with pytest.raises(ValueError):
        validate_sequence_sample(
            sample(
                sample_index=-1
            )
        )


def test_sample_rejects_bad_position():
    with pytest.raises(ValueError):
        validate_sequence_sample(
            sample(
                positions=("col9",)
            )
        )


def test_sample_rejects_feature_row_count():
    with pytest.raises(ValueError):
        validate_sequence_sample(
            sample(
                features=(
                    (1, 2),
                )
            )
        )


def test_sample_rejects_non_tuple_feature_row():
    with pytest.raises(TypeError):
        validate_sequence_sample(
            sample(
                features=(
                    [1, 2],
                    [2, 3],
                    [3, 4],
                )
            )
        )


def test_sample_requires_future_target():
    with pytest.raises(ValueError):
        validate_sequence_sample(
            sample(
                target_date=date(
                    2026,
                    1,
                    3,
                )
            )
        )


def test_invalid_sample_type():
    with pytest.raises(TypeError):
        validate_sequence_sample(
            "invalid"
        )


def test_empty_dataset():
    dataset = build_sequence_dataset(
        config()
    )

    assert isinstance(
        dataset,
        SequenceDataset,
    )

    assert (
        get_sequence_sample_count(
            dataset
        )
        == 0
    )


def test_dataset_preserves_metadata():
    dataset = build_sequence_dataset(
        config()
    )

    assert dataset.sequence_length == 3

    assert (
        dataset.input_positions
        == POSITIONS
    )

    assert (
        dataset.target_positions
        == POSITIONS
    )

    assert (
        dataset.feature_names
        == (
            "col1_latest_value",
            "col2_latest_value",
        )
    )


def test_dataset_accepts_samples():
    dataset = build_sequence_dataset(
        config(),
        (
            sample(
                sample_index=0
            ),
            sample(
                sample_index=1,
                sequence_start_date=date(
                    2026,
                    1,
                    2,
                ),
                sequence_end_date=date(
                    2026,
                    1,
                    4,
                ),
                target_date=date(
                    2026,
                    1,
                    5,
                ),
            ),
        ),
    )

    assert (
        get_sequence_sample_count(
            dataset
        )
        == 2
    )


def test_dataset_rejects_list_samples():
    with pytest.raises(TypeError):
        build_sequence_dataset(
            config(),
            [
                sample()
            ],
        )


def test_dataset_rejects_position_mismatch():
    with pytest.raises(ValueError):
        build_sequence_dataset(
            config(),
            (
                sample(
                    positions=("col1",)
                ),
            ),
        )


def test_dataset_rejects_length_mismatch():
    with pytest.raises(ValueError):
        build_sequence_dataset(
            config(),
            (
                sample(
                    sequence_length=2
                ),
            ),
        )


def test_dataset_rejects_non_increasing_indices():
    with pytest.raises(ValueError):
        build_sequence_dataset(
            config(),
            (
                sample(
                    sample_index=1
                ),
                sample(
                    sample_index=1
                ),
            ),
        )


def test_dataset_validation():
    dataset = build_sequence_dataset(
        config(),
        (
            sample(),
        ),
    )

    validate_sequence_dataset(
        dataset
    )


def test_invalid_dataset_type():
    with pytest.raises(TypeError):
        validate_sequence_dataset(
            "invalid"
        )


def test_get_sample():
    item = sample(
        sample_index=4
    )

    dataset = build_sequence_dataset(
        config(),
        (
            item,
        ),
    )

    assert (
        get_sequence_sample(
            dataset,
            4,
        )
        == item
    )


def test_missing_sample():
    with pytest.raises(ValueError):
        get_sequence_sample(
            build_sequence_dataset(
                config()
            ),
            99,
        )


def test_feature_names_getter():
    assert (
        get_sequence_feature_names(
            build_sequence_dataset(
                config()
            )
        )
        == (
            "col1_latest_value",
            "col2_latest_value",
        )
    )


def test_input_positions_getter():
    assert (
        get_sequence_input_positions(
            build_sequence_dataset(
                config()
            )
        )
        == POSITIONS
    )


def test_target_positions_getter():
    assert (
        get_sequence_target_positions(
            build_sequence_dataset(
                config()
            )
        )
        == POSITIONS
    )


def test_getters_reject_invalid_dataset():
    with pytest.raises(TypeError):
        get_sequence_sample_count(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_sequence_sample(
            "invalid",
            0,
        )

    with pytest.raises(TypeError):
        get_sequence_feature_names(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_sequence_input_positions(
            "invalid"
        )

    with pytest.raises(TypeError):
        get_sequence_target_positions(
            "invalid"
        )


def test_dataset_is_deterministic():
    samples = (
        sample(
            sample_index=0
        ),
    )

    first = build_sequence_dataset(
        config(),
        samples,
    )

    second = build_sequence_dataset(
        config(),
        samples,
    )

    assert first == second


def test_zero_is_preserved():
    assert 0 in sample().target


def test_dataset_is_immutable():
    dataset = build_sequence_dataset(
        config()
    )

    with pytest.raises(AttributeError):
        dataset.sequence_length = 5