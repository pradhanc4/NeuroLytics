from dataclasses import dataclass

import pytest

from analytics.markov_models import MarkovConfig, MarkovChain, build_markov_artifact, build_markov_dataset
from analytics.sequence_evaluation import (
    SEQUENCE_EVALUATION_VERSION,
    VALID,
    accuracy,
    brier_score,
    build_sequence_evaluation_dataset,
    build_sequence_evaluation_report,
    calibrate_sequence_model,
    evaluate_sequence_model,
    expected_calibration_error,
    fit_temperature,
    log_loss,
    mean_entropy,
    top_k_accuracy,
    validate_sequence_evaluation_report,
)
from analytics.sequence_framework import SequenceModelRun


def make_run(identity="eval-1"):
    dataset = build_markov_dataset(
        [(0, 1, 2, 3, 4, 5), (5, 4, 3, 2, 1, 0)],
        identity,
        "target",
    )
    model = MarkovChain(MarkovConfig(order=1, smoothing=1.0)).fit(dataset)
    metrics = model.evaluate(dataset)
    artifact = build_markov_artifact(model, dataset)
    return SequenceModelRun(
        "markov", "28.0.0", identity, "target", model, metrics, artifact
    )


def test_version():
    assert SEQUENCE_EVALUATION_VERSION == "34.0.0"


def test_dataset_contract_and_zero():
    dataset = build_sequence_evaluation_dataset([(0, 1, 0, 2)], "d")
    assert dataset.sequences[0][0] == 0


def test_dataset_rejects_empty():
    with pytest.raises(ValueError):
        build_sequence_evaluation_dataset([], "d")


def test_dataset_rejects_bad_digit():
    with pytest.raises(ValueError):
        build_sequence_evaluation_dataset([(0, 10)], "d")


def test_log_loss():
    value = log_loss([(0.7, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)], [0])
    assert value == pytest.approx(-__import__("math").log(0.7))


def test_accuracy():
    row = (0.1, 0.8, 0.1, 0, 0, 0, 0, 0, 0, 0)
    assert accuracy([row], [1]) == 1.0


def test_top_k_accuracy():
    row = (0.4, 0.3, 0.2, 0.1, 0, 0, 0, 0, 0, 0)
    assert top_k_accuracy([row], [2], 3) == 1.0


def test_brier_score_nonnegative():
    row = (1.0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    assert brier_score([row], [0]) == pytest.approx(0.0)


def test_ece_nonnegative():
    row = (1.0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    assert expected_calibration_error([row], [0]) == pytest.approx(0.0)


def test_entropy_uniform():
    row = tuple([0.1] * 10)
    assert mean_entropy([row]) == pytest.approx(__import__("math").log(10))


def test_temperature_is_positive():
    row = (0.7, 0.3, 0, 0, 0, 0, 0, 0, 0, 0)
    assert fit_temperature([row], [0]) > 0


def test_temperature_invalid():
    with pytest.raises(ValueError):
        from analytics.sequence_evaluation import _temperature_scale
        _temperature_scale([(1.0,) + (0.0,) * 9], 0)


def test_evaluate_markov_model():
    run = make_run()
    dataset = build_sequence_evaluation_dataset(
        [(0, 1, 2, 3, 4, 5), (5, 4, 3, 2, 1, 0)], "eval-1"
    )
    result = evaluate_sequence_model(run, dataset, top_k=3)
    assert result.model_kind == "markov"
    assert result.observations == 10
    assert 0 <= result.accuracy <= 1
    assert 0 <= result.top_k_accuracy <= 1
    assert result.brier_score >= 0
    assert result.expected_calibration_error >= 0


def test_evaluate_rejects_identity_mismatch():
    run = make_run("run")
    dataset = build_sequence_evaluation_dataset([(0, 1, 2)], "other")
    with pytest.raises(ValueError):
        evaluate_sequence_model(run, dataset)


def test_evaluate_requires_windows():
    run = make_run()
    dataset = build_sequence_evaluation_dataset([(0,)], "eval-1")
    with pytest.raises(ValueError):
        evaluate_sequence_model(run, dataset)


def test_calibration_result():
    run = make_run()
    dataset = build_sequence_evaluation_dataset(
        [(0, 1, 2, 3, 4, 5), (5, 4, 3, 2, 1, 0)], "eval-1"
    )
    result = calibrate_sequence_model(run, dataset)
    assert result.temperature > 0
    assert result.pre_log_loss >= 0
    assert result.post_log_loss >= 0


def test_calibration_identity_mismatch():
    run = make_run()
    dataset = build_sequence_evaluation_dataset([(0, 1, 2)], "other")
    with pytest.raises(ValueError):
        calibrate_sequence_model(run, dataset)


def test_report_identity_and_validation():
    run = make_run()
    dataset = build_sequence_evaluation_dataset(
        [(0, 1, 2, 3, 4, 5), (5, 4, 3, 2, 1, 0)], "eval-1"
    )
    evaluation = evaluate_sequence_model(run, dataset)
    calibration = calibrate_sequence_model(run, dataset)
    report = build_sequence_evaluation_report(
        dataset, [evaluation], [calibration]
    )
    validation = validate_sequence_evaluation_report(report)
    assert validation.status == VALID
    assert report.report_identity.startswith("sequence-evaluation-")


def test_report_rejects_mismatched_evaluation():
    run = make_run("a")
    dataset_a = build_sequence_evaluation_dataset([(0, 1, 2, 3)], "a")
    dataset_b = build_sequence_evaluation_dataset([(0, 1, 2, 3)], "b")
    evaluation = evaluate_sequence_model(run, dataset_a)
    with pytest.raises(ValueError):
        build_sequence_evaluation_report(dataset_b, [evaluation])


def test_report_requires_evaluations():
    dataset = build_sequence_evaluation_dataset([(0, 1, 2)], "d")
    report = build_sequence_evaluation_report(dataset, [])
    assert validate_sequence_evaluation_report(report).status == "INVALID"


def test_probability_rows_must_have_ten_classes():
    with pytest.raises(ValueError):
        log_loss([(0.5, 0.5)], [0])


def test_probability_rows_must_sum_to_one():
    with pytest.raises(ValueError):
        log_loss([(0.4,) + (0.0,) * 9], [0])


def test_target_range_validation():
    row = (0.1,) * 10
    with pytest.raises(ValueError):
        accuracy([row], [10])


def test_top_k_validation():
    with pytest.raises(ValueError):
        top_k_accuracy([(0.1,) * 10], [0], 0)


def test_ece_bins_validation():
    with pytest.raises(ValueError):
        expected_calibration_error([(0.1,) * 10], [0], 0)


def test_report_version_is_deterministic():
    run = make_run()
    dataset = build_sequence_evaluation_dataset(
        [(0, 1, 2, 3, 4, 5), (5, 4, 3, 2, 1, 0)], "eval-1"
    )
    evaluation = evaluate_sequence_model(run, dataset)
    first = build_sequence_evaluation_report(dataset, [evaluation])
    second = build_sequence_evaluation_report(dataset, [evaluation])
    assert first.report_identity == second.report_identity


def test_calibration_versioned_model_metadata():
    run = make_run()
    dataset = build_sequence_evaluation_dataset(
        [(0, 1, 2, 3, 4, 5), (5, 4, 3, 2, 1, 0)], "eval-1"
    )
    result = calibrate_sequence_model(run, dataset)
    assert result.model_version == "28.0.0"


def test_probability_rows_are_preserved():
    run = make_run()
    dataset = build_sequence_evaluation_dataset(
        [(0, 1, 2, 3, 4, 5), (5, 4, 3, 2, 1, 0)], "eval-1"
    )
    result = evaluate_sequence_model(run, dataset)
    assert len(result.probabilities) == result.observations
    assert len(result.targets) == result.observations


def test_evaluation_target_name_is_independent():
    run = make_run()
    dataset = build_sequence_evaluation_dataset(
        [(0, 1, 2, 3)], "eval-1", "custom_target"
    )
    result = evaluate_sequence_model(run, dataset)
    assert result.dataset_identity == "eval-1"
