from pathlib import Path

import numpy as np
import pytest

from analytics.sequence_framework import (
    MODEL_KINDS,
    SEQUENCE_FRAMEWORK_VERSION,
    SequenceFrameworkDataset,
    SequenceFrameworkReport,
    SequenceModelRun,
    build_default_sequence_model_registry,
    build_position_sequence_models,
    build_sequence_framework_dataset,
    build_sequence_framework_report,
    build_sequence_model,
    compare_sequence_model_runs,
    framework_model_versions,
    get_position_sequence_model,
    predict_next_sequence_model,
    prepare_model_dataset,
    train_sequence_model,
    train_sequence_models,
    validate_sequence_framework_dataset,
    validate_sequence_framework_report,
    validate_sequence_model_run,
)
from analytics.transformer import TransformerConfig
from analytics.gru import GRUConfig
from analytics.lstm import LSTMConfig


def sequences():
    return [
        [0, 1, 2, 3, 4, 5],
        [1, 2, 3, 4, 5, 6],
        [2, 3, 4, 5, 6, 7],
        [3, 4, 5, 6, 7, 8],
    ]


def dataset():
    return build_sequence_framework_dataset(
        sequences(),
        "phase33-fixture",
        target_name="col1",
    )


def fast_configs():
    return {
        "lstm": LSTMConfig(
            sequence_length=3, hidden_size=4, epochs=2,
            batch_size=4, seed=330, patience=2,
        ),
        "gru": GRUConfig(
            sequence_length=3, hidden_size=4, epochs=2,
            batch_size=4, seed=331, patience=2,
        ),
        "transformer": TransformerConfig(
            sequence_length=3, d_model=8, num_heads=2,
            feed_forward_size=16, epochs=2, batch_size=4,
            seed=332, patience=2,
        ),
    }


def test_version_and_model_kinds():
    assert SEQUENCE_FRAMEWORK_VERSION == "33.0.0"
    assert MODEL_KINDS == (
        "gru", "hidden_markov", "lstm", "markov", "transformer"
    )


def test_dataset_contract():
    ds = dataset()
    assert isinstance(ds, SequenceFrameworkDataset)
    assert ds.identity == "phase33-fixture"
    assert ds.target_name == "col1"
    assert 0 in ds.sequences[0]


def test_dataset_validation():
    validate_sequence_framework_dataset(dataset())


@pytest.mark.parametrize(
    "bad",
    [
        [],
        [[0, 1, 2], []],
        [[0, 1, 10]],
        [[0, True, 2]],
    ],
)
def test_invalid_sequences_rejected(bad):
    with pytest.raises(ValueError):
        build_sequence_framework_dataset(bad, "bad")


def test_invalid_identity_rejected():
    with pytest.raises(ValueError):
        build_sequence_framework_dataset(sequences(), "")


def test_registry_contains_all_sequence_families():
    registry = build_default_sequence_model_registry()
    assert len(registry) == 5
    assert registry.kinds() == tuple(sorted(MODEL_KINDS))


def test_registry_lookup_rejects_unknown_kind():
    registry = build_default_sequence_model_registry()
    with pytest.raises(ValueError):
        registry.get("unknown")


def test_registry_duplicate_rejected():
    registry = build_default_sequence_model_registry()
    with pytest.raises(ValueError):
        registry.register(registry.get("lstm"))


def test_framework_versions():
    assert framework_model_versions() == (
        ("gru", "31.0.0"),
        ("hidden_markov", "29.0.0"),
        ("lstm", "30.0.0"),
        ("markov", "28.0.0"),
        ("transformer", "32.0.0"),
    )


@pytest.mark.parametrize("kind", ["lstm", "gru", "transformer", "markov", "hidden_markov"])
def test_build_model(kind):
    model = build_sequence_model(kind)
    assert model.fitted is False


@pytest.mark.parametrize("kind", ["lstm", "gru", "transformer", "markov", "hidden_markov"])
def test_prepare_model_dataset(kind):
    prepared = prepare_model_dataset(kind, dataset())
    assert prepared.identity == dataset().identity
    assert prepared.target_name == dataset().target_name


def test_train_lstm_through_framework():
    run = train_sequence_model("lstm", dataset(), fast_configs()["lstm"])
    assert isinstance(run, SequenceModelRun)
    assert run.model_kind == "lstm"
    assert run.model_version == "30.0.0"
    assert run.model.fitted
    assert run.metrics.observations > 0
    assert run.artifact.artifact_identity.startswith("lstm-")


def test_train_gru_through_framework():
    run = train_sequence_model("gru", dataset(), fast_configs()["gru"])
    assert run.model_kind == "gru"
    assert run.model.fitted
    assert run.artifact.artifact_identity.startswith("gru-")


def test_train_transformer_through_framework():
    run = train_sequence_model(
        "transformer", dataset(), fast_configs()["transformer"]
    )
    assert run.model_kind == "transformer"
    assert run.model.fitted
    assert run.artifact.artifact_identity.startswith("transformer-")


def test_train_markov_through_framework():
    run = train_sequence_model("markov", dataset())
    assert run.model_kind == "markov"
    assert run.model.fitted
    assert run.metrics.observations > 0
    assert run.artifact.artifact_identity.startswith("markov-")


def test_train_hmm_through_framework():
    run = train_sequence_model(
        "hidden_markov",
        dataset(),
        {"n_states": 3, "max_iterations": 2, "random_seed": 333},
    )
    assert run.model_kind == "hidden_markov"
    assert run.model.fitted
    assert run.metrics.observations > 0
    assert run.artifact.artifact_identity.startswith("hmm-")


def test_train_multiple_models_deterministic_order():
    runs = train_sequence_models(
        dataset(),
        ["transformer", "lstm", "gru"],
        fast_configs(),
    )
    assert [run.model_kind for run in runs] == ["gru", "lstm", "transformer"]


def test_compare_runs():
    runs = train_sequence_models(
        dataset(),
        ["lstm", "gru"],
        fast_configs(),
    )
    comparisons = compare_sequence_model_runs(
        runs, baseline_log_loss=2.3, baseline_accuracy=0.1
    )
    assert len(comparisons) == 2
    assert all(item.observations > 0 for item in comparisons)
    assert comparisons[0].log_loss_delta == pytest.approx(
        comparisons[0].log_loss - 2.3
    )


def test_report_identity_and_validation():
    runs = train_sequence_models(
        dataset(), ["lstm", "gru"], fast_configs()
    )
    report = build_sequence_framework_report(
        dataset(), runs, baseline_log_loss=2.3, baseline_accuracy=0.1
    )
    assert isinstance(report, SequenceFrameworkReport)
    assert report.framework_identity.startswith("sequence-framework-")
    validate_sequence_framework_report(report)


def test_report_rejects_mismatched_dataset_identity():
    run = train_sequence_model("lstm", dataset(), fast_configs()["lstm"])
    other = build_sequence_framework_dataset(sequences(), "other")
    with pytest.raises(ValueError):
        build_sequence_framework_report(other, [run])


def test_run_validation():
    run = train_sequence_model("gru", dataset(), fast_configs()["gru"])
    validate_sequence_model_run(run)


def test_run_validation_rejects_unfitted():
    model = build_sequence_model("gru", fast_configs()["gru"])
    with pytest.raises(ValueError):
        validate_sequence_model_run(
            SequenceModelRun(
                "gru", "31.0.0", dataset().identity,
                dataset().target_name, model, object(), object()
            )
        )


def test_prediction_adapter():
    run = train_sequence_model("markov", dataset())
    prediction = predict_next_sequence_model(run, [1], 3)
    assert len(prediction) == 3
    assert all(0 <= digit <= 9 for digit in prediction)


def test_position_sequence_models():
    models = build_position_sequence_models(
        {"col1": dataset(), "col2": dataset()},
        "gru",
        fast_configs()["gru"],
    )
    assert [name for name, _ in models] == ["col1", "col2"]
    assert get_position_sequence_model(models, "col1").model.fitted


def test_position_model_missing():
    models = build_position_sequence_models(
        {"col1": dataset()}, "lstm", fast_configs()["lstm"]
    )
    with pytest.raises(ValueError):
        get_position_sequence_model(models, "col9")


def test_framework_rejects_invalid_baseline():
    with pytest.raises(ValueError):
        compare_sequence_model_runs(
            [train_sequence_model("markov", dataset())],
            baseline_log_loss=-1,
        )


def test_framework_dataset_minimum_length():
    with pytest.raises(ValueError):
        validate_sequence_framework_dataset(dataset(), minimum_length=7)


def test_numpy_values_are_supported_by_model_window():
    run = train_sequence_model("transformer", dataset(), fast_configs()["transformer"])
    window = np.asarray([4, 5, 6], dtype=np.int64)
    assert len(run.model.predict_next(window, 3)) == 3
