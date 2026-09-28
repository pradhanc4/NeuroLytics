from datetime import date

import pytest

from features.sequence_dataset import (
    SequenceDataset,
    SequenceDatasetConfig,
    SequenceSample,
)
from features.sequence_temporal_split import (
    TemporalSequenceSplit,
    TemporalSplitConfig,
    get_total_split_count,
    get_train_count,
    get_train_samples,
    get_validation_count,
    get_validation_samples,
    split_sequence_dataset_temporally,
    validate_temporal_split_config,
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


def config():
    return SequenceDatasetConfig(
        sequence_length=3,
        input_positions=POSITIONS,
        target_positions=("col1",),
        feature_names=(),
        allow_incomplete_sequences=False,
    )


def sample(
    index,
    start_date,
    end_date,
    target_date,
):
    return SequenceSample(
        sample_index=index,
        sequence_start_date=date.fromisoformat(
            start_date
        ),
        sequence_end_date=date.fromisoformat(
            end_date
        ),
        target_date=date.fromisoformat(
            target_date
        ),
        sequence_length=3,
        positions=POSITIONS,
        features=(
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
            (1, 2, 3, 4, 5, 6, 7, 8),
        ),
        target=(1,),
    )


def dataset_with_samples():
    samples = (
        sample(
            0,
            "2026-01-01",
            "2026-01-03",
            "2026-01-04",
        ),
        sample(
            1,
            "2026-01-02",
            "2026-01-04",
            "2026-01-05",
        ),
        sample(
            2,
            "2026-01-03",
            "2026-01-05",
            "2026-01-06",
        ),
        sample(
            3,
            "2026-01-04",
            "2026-01-06",
            "2026-01-07",
        ),
        sample(
            4,
            "2026-01-05",
            "2026-01-07",
            "2026-01-08",
        ),
    )

    return SequenceDataset(
        sequence_length=3,
        input_positions=POSITIONS,
        target_positions=("col1",),
        feature_names=(),
        samples=samples,
    )


def test_temporal_split_respects_cutoff():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert [
        sample.target_date
        for sample in split.train_samples
    ] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]

    assert [
        sample.target_date
        for sample in split.validation_samples
    ] == [
        date(2026, 1, 7),
        date(2026, 1, 8),
    ]


def test_split_date_belongs_to_training_side():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert split.train_samples[-1].target_date == date(
        2026,
        1,
        6,
    )


def test_validation_starts_strictly_after_split_date():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert all(
        sample.target_date
        > split.split_date
        for sample in split.validation_samples
    )


def test_train_and_validation_do_not_overlap():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    train_indices = {
        sample.sample_index
        for sample in split.train_samples
    }

    validation_indices = {
        sample.sample_index
        for sample in split.validation_samples
    }

    assert train_indices.isdisjoint(
        validation_indices
    )


def test_all_samples_are_preserved():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert (
        split.total_count
        == len(dataset.samples)
    )


def test_sample_order_is_preserved():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert [
        sample.sample_index
        for sample in split.train_samples
    ] == [0, 1, 2]

    assert [
        sample.sample_index
        for sample in split.validation_samples
    ] == [3, 4]


def test_split_is_deterministic():
    dataset = dataset_with_samples()

    config_value = TemporalSplitConfig(
        split_date=date(2026, 1, 6)
    )

    first = split_sequence_dataset_temporally(
        dataset,
        config_value,
    )

    second = split_sequence_dataset_temporally(
        dataset,
        config_value,
    )

    assert first == second


def test_train_count_is_correct():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert split.train_count == 3


def test_validation_count_is_correct():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert split.validation_count == 2


def test_total_count_is_correct():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert split.total_count == 5


def test_accessor_functions_return_expected_values():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert get_train_samples(split) == (
        split.train_samples
    )

    assert get_validation_samples(split) == (
        split.validation_samples
    )

    assert get_train_count(split) == 3
    assert get_validation_count(split) == 2
    assert get_total_split_count(split) == 5


def test_all_training_samples_are_on_or_before_cutoff():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert all(
        sample.target_date
        <= date(2026, 1, 6)
        for sample in split.train_samples
    )


def test_empty_dataset_produces_empty_split():
    dataset = SequenceDataset(
        sequence_length=3,
        input_positions=POSITIONS,
        target_positions=("col1",),
        feature_names=(),
        samples=(),
    )

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert split.train_samples == ()
    assert split.validation_samples == ()
    assert split.train_count == 0
    assert split.validation_count == 0
    assert split.total_count == 0


def test_cutoff_before_all_samples_creates_empty_train_set():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 1)
        ),
    )

    assert split.train_samples == ()
    assert len(split.validation_samples) == 5


def test_cutoff_after_all_samples_creates_empty_validation_set():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 31)
        ),
    )

    assert len(split.train_samples) == 5
    assert split.validation_samples == ()


def test_invalid_config_type_is_rejected():
    with pytest.raises(TypeError):
        validate_temporal_split_config(
            "invalid"
        )


def test_invalid_dataset_type_is_rejected():
    with pytest.raises(TypeError):
        split_sequence_dataset_temporally(
            "invalid",
            TemporalSplitConfig(
                split_date=date(2026, 1, 6)
            ),
        )


def test_invalid_config_is_rejected():
    with pytest.raises(TypeError):
        split_sequence_dataset_temporally(
            dataset_with_samples(),
            "invalid",
        )


def test_invalid_sample_order_is_rejected():
    dataset = SequenceDataset(
        sequence_length=3,
        input_positions=POSITIONS,
        target_positions=("col1",),
        feature_names=(),
        samples=(
            sample(
                0,
                "2026-01-02",
                "2026-01-04",
                "2026-01-05",
            ),
            sample(
                1,
                "2026-01-01",
                "2026-01-03",
                "2026-01-04",
            ),
        ),
    )

    with pytest.raises(ValueError):
        split_sequence_dataset_temporally(
            dataset,
            TemporalSplitConfig(
                split_date=date(2026, 1, 5)
            ),
        )


def test_result_is_immutable():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    assert isinstance(
        split,
        TemporalSequenceSplit,
    )

    with pytest.raises(
        AttributeError
    ):
        split.train_samples = ()


def test_no_randomization_is_used():
    dataset = dataset_with_samples()

    split = split_sequence_dataset_temporally(
        dataset,
        TemporalSplitConfig(
            split_date=date(2026, 1, 6)
        ),
    )

    combined = (
        split.train_samples
        + split.validation_samples
    )

    assert [
        sample.sample_index
        for sample in combined
    ] == [0, 1, 2, 3, 4]