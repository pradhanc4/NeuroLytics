import pytest

from analytics.markov_models import MarkovChain, MarkovConfig, build_markov_artifact, build_markov_dataset
from analytics.sequence_evaluation import build_sequence_evaluation_dataset, evaluate_sequence_model
from analytics.sequence_ensemble import (
    ENSEMBLE_METHODS,
    SEQUENCE_ENSEMBLE_VERSION,
    VALID,
    build_sequence_ensemble,
    build_sequence_ensemble_report,
    build_sequence_ensemble_weights,
    compare_sequence_evaluations,
    ensemble_model_versions,
    select_best_ensemble,
    validate_sequence_ensemble,
    validate_sequence_ensemble_report,
    validate_sequence_ensemble_weights,
)
from analytics.sequence_framework import SequenceModelRun


def make_evaluation(identity="ens-1"):
    sequences = ((0, 1, 2, 3, 4, 5), (5, 4, 3, 2, 1, 0))
    model_dataset = build_markov_dataset(sequences, identity, "target")
    model = MarkovChain(MarkovConfig(order=1, smoothing=1.0)).fit(model_dataset)
    metrics = model.evaluate(model_dataset)
    artifact = build_markov_artifact(model, model_dataset)
    run = SequenceModelRun("markov", "28.0.0", identity, "target", model, metrics, artifact)
    eval_dataset = build_sequence_evaluation_dataset(sequences, identity)
    return evaluate_sequence_model(run, eval_dataset)


def make_evaluations():
    first = make_evaluation("ens-1")
    second = make_evaluation("ens-1")
    object.__setattr__(second, "model_kind", "lstm")
    object.__setattr__(second, "model_version", "30.0.0")
    return first, second


def test_version():
    assert SEQUENCE_ENSEMBLE_VERSION == "35.0.0"


def test_methods_are_defined():
    assert ENSEMBLE_METHODS == ("equal_weight", "inverse_log_loss", "softmax_score")


def test_comparison_contract():
    first, second = make_evaluations()
    report = compare_sequence_evaluations([first, second])
    assert len(report.results) == 2
    assert report.dataset_identity == "ens-1"
    assert report.comparison_identity.startswith("sequence-comparison-")


def test_comparison_baselines():
    first, second = make_evaluations()
    report = compare_sequence_evaluations([first, second], first.log_loss, first.accuracy)
    assert report.results[0].log_loss_delta == pytest.approx(0.0)
    assert report.results[0].accuracy_delta == pytest.approx(0.0)


def test_comparison_rejects_mixed_datasets():
    first = make_evaluation("a")
    second = make_evaluation("b")
    with pytest.raises(ValueError):
        compare_sequence_evaluations([first, second])


def test_comparison_rejects_empty():
    with pytest.raises(ValueError):
        compare_sequence_evaluations([])


@pytest.mark.parametrize("method", ENSEMBLE_METHODS)
def test_weight_builder(method):
    first, second = make_evaluations()
    result = build_sequence_ensemble_weights([first, second], method)
    assert result.method == method
    assert sum(result.weights) == pytest.approx(1.0)
    assert len(result.weights) == 2
    assert validate_sequence_ensemble_weights(result).status == VALID


def test_weight_rejects_unknown_method():
    first, _ = make_evaluations()
    with pytest.raises(ValueError):
        build_sequence_ensemble_weights([first], "unknown")


def test_equal_weights():
    first, second = make_evaluations()
    result = build_sequence_ensemble_weights([first, second], "equal_weight")
    assert result.weights == pytest.approx((0.5, 0.5))


def test_inverse_log_loss_is_deterministic():
    first, second = make_evaluations()
    a = build_sequence_ensemble_weights([first, second], "inverse_log_loss")
    b = build_sequence_ensemble_weights([first, second], "inverse_log_loss")
    assert a.weights == b.weights
    assert a.identity == b.identity


def test_ensemble_probability_shape():
    first, second = make_evaluations()
    result = build_sequence_ensemble([first, second], "equal_weight")
    assert result.observations == len(result.targets)
    assert len(result.probabilities) == result.observations
    assert all(len(row) == 10 for row in result.probabilities)
    assert all(sum(row) == pytest.approx(1.0) for row in result.probabilities)


def test_ensemble_metrics():
    first, second = make_evaluations()
    result = build_sequence_ensemble([first, second], "inverse_log_loss")
    assert result.log_loss >= 0
    assert 0 <= result.accuracy <= 1
    assert 0 <= result.top_k_accuracy <= 1
    assert result.brier_score >= 0
    assert result.expected_calibration_error >= 0


def test_ensemble_lineage():
    first, second = make_evaluations()
    result = build_sequence_ensemble([first, second])
    assert result.dataset_identity == "ens-1"
    assert result.model_kinds == ("markov", "lstm")
    assert result.ensemble_identity.startswith("sequence-ensemble-")


def test_ensemble_validation():
    first, second = make_evaluations()
    result = build_sequence_ensemble([first, second])
    assert validate_sequence_ensemble(result).status == VALID


def test_select_best_ensemble():
    first, second = make_evaluations()
    a = build_sequence_ensemble([first, second], "equal_weight")
    b = build_sequence_ensemble([first, second], "inverse_log_loss")
    selected = select_best_ensemble([a, b])
    assert selected.ensemble_identity in {a.ensemble_identity, b.ensemble_identity}


def test_select_rejects_empty():
    with pytest.raises(ValueError):
        select_best_ensemble([])


def test_report_builds_all_methods():
    first, second = make_evaluations()
    report = build_sequence_ensemble_report([first, second])
    assert len(report.ensembles) == 3
    assert report.selected_method in ENSEMBLE_METHODS
    assert report.selected_ensemble_identity.startswith("sequence-ensemble-")


def test_report_validation():
    first, second = make_evaluations()
    report = build_sequence_ensemble_report([first, second])
    assert validate_sequence_ensemble_report(report).status == VALID


def test_report_is_deterministic():
    first, second = make_evaluations()
    a = build_sequence_ensemble_report([first, second])
    b = build_sequence_ensemble_report([first, second])
    assert a.report_identity == b.report_identity


def test_report_accepts_subset_methods():
    first, second = make_evaluations()
    report = build_sequence_ensemble_report([first, second], ("equal_weight",))
    assert len(report.ensembles) == 1
    assert report.selected_method == "equal_weight"


def test_report_rejects_unknown_method():
    first, second = make_evaluations()
    with pytest.raises(ValueError):
        build_sequence_ensemble_report([first, second], ("bad",))


def test_model_versions():
    first, second = make_evaluations()
    assert ensemble_model_versions([first, second]) == (
        ("markov", "28.0.0"),
        ("lstm", "30.0.0"),
    )


def test_weights_identity_is_stable():
    first, second = make_evaluations()
    a = build_sequence_ensemble_weights([first, second], "equal_weight")
    b = build_sequence_ensemble_weights([first, second], "equal_weight")
    assert a.identity == b.identity


def test_probability_blend_changes_with_weight():
    first, second = make_evaluations()
    equal = build_sequence_ensemble([first, second], "equal_weight")
    inverse = build_sequence_ensemble([first, second], "inverse_log_loss")
    assert equal.probabilities == inverse.probabilities or equal.weights != inverse.weights


def test_invalid_weight_validation():
    first, second = make_evaluations()
    weights = build_sequence_ensemble_weights([first, second])
    object.__setattr__(weights, "weights", (1.0, 1.0))
    assert validate_sequence_ensemble_weights(weights).status == "INVALID"


def test_invalid_ensemble_method_validation():
    first, second = make_evaluations()
    ensemble = build_sequence_ensemble([first, second])
    object.__setattr__(ensemble, "method", "bad")
    assert validate_sequence_ensemble(ensemble).status == "INVALID"


def test_invalid_report_selected_identity():
    first, second = make_evaluations()
    report = build_sequence_ensemble_report([first, second])
    object.__setattr__(report, "selected_ensemble_identity", "missing")
    assert validate_sequence_ensemble_report(report).status == "INVALID"


def test_baseline_validation():
    first, second = make_evaluations()
    with pytest.raises(ValueError):
        compare_sequence_evaluations([first, second], -1.0)
    with pytest.raises(ValueError):
        compare_sequence_evaluations([first, second], None, 2.0)
