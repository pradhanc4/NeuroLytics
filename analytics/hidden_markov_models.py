from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import joblib

VALID = "VALID"
INVALID = "INVALID"
HMM_VERSION = "29.0.0"
MODEL_KIND = "hidden_markov"


@dataclass(frozen=True)
class HMMConfig:
    n_states: int = 10
    n_observations: int = 10
    smoothing: float = 1.0
    max_iterations: int = 25
    tolerance: float = 1e-6
    random_seed: int = 29


@dataclass(frozen=True)
class HMMDataset:
    sequences: tuple[tuple[int, ...], ...]
    identity: str
    target_name: str = "target"


@dataclass(frozen=True)
class HMMMetrics:
    log_loss: float
    accuracy: float
    observations: int


@dataclass(frozen=True)
class HMMTrainingResult:
    log_likelihood: float
    iterations: int
    converged: bool


@dataclass(frozen=True)
class HMMArtifact:
    model_kind: str
    model_version: str
    n_states: int
    n_observations: int
    smoothing: float
    dataset_identity: str
    target_name: str
    artifact_identity: str


@dataclass(frozen=True)
class HMMValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


@dataclass(frozen=True)
class HMMBaselineComparison:
    hmm_log_loss: float
    baseline_log_loss: float
    difference: float


@dataclass(frozen=True)
class HMMReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str


@dataclass(frozen=True)
class PositionHMMModels:
    models: tuple[tuple[str, "HiddenMarkovModel"], ...]


def validate_hmm_config(config: HMMConfig) -> None:
    if not isinstance(config, HMMConfig):
        raise TypeError("config must be an HMMConfig.")
    if isinstance(config.n_states, bool) or not isinstance(config.n_states, int) or config.n_states <= 0:
        raise ValueError("n_states must be a positive integer.")
    if config.n_states > 50:
        raise ValueError("n_states must not exceed 50.")
    if config.n_observations != 10:
        raise ValueError("n_observations must be exactly 10 for NeuroLytics digit models.")
    if config.smoothing < 0:
        raise ValueError("smoothing cannot be negative.")
    if isinstance(config.max_iterations, bool) or not isinstance(config.max_iterations, int) or config.max_iterations <= 0:
        raise ValueError("max_iterations must be a positive integer.")
    if config.tolerance < 0:
        raise ValueError("tolerance cannot be negative.")
    if isinstance(config.random_seed, bool) or not isinstance(config.random_seed, int):
        raise TypeError("random_seed must be an integer.")


def _validate_sequence(sequence: Sequence[int], n_observations: int = 10) -> tuple[int, ...]:
    values = tuple(sequence)
    if not values:
        raise ValueError("sequence cannot be empty.")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("sequence values must be integers.")
    if any(v < 0 or v >= n_observations for v in values):
        raise ValueError("sequence values must be valid digits 0-9.")
    return values


def build_hmm_dataset(
    sequences: Sequence[Sequence[int]],
    identity: str,
    target_name: str = "target",
) -> HMMDataset:
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("identity must be non-empty.")
    if not isinstance(target_name, str) or not target_name.strip():
        raise ValueError("target_name must be non-empty.")
    rows = tuple(_validate_sequence(row) for row in sequences)
    if not rows:
        raise ValueError("at least one sequence is required.")
    return HMMDataset(rows, identity, target_name)


def validate_hmm_dataset(dataset: HMMDataset, config: HMMConfig | None = None) -> None:
    if not isinstance(dataset, HMMDataset):
        raise TypeError("dataset must be an HMMDataset.")
    if not dataset.sequences:
        raise ValueError("dataset must contain sequences.")
    cfg = config or HMMConfig()
    validate_hmm_config(cfg)
    for sequence in dataset.sequences:
        _validate_sequence(sequence, cfg.n_observations)


def _normalize(values: Sequence[float]) -> tuple[float, ...]:
    total = sum(values)
    if total <= 0:
        return tuple(1.0 / len(values) for _ in values)
    return tuple(v / total for v in values)


def _deterministic_rng(seed: int):
    import random
    return random.Random(seed)


def _initial_parameters(config: HMMConfig) -> tuple[tuple[float, ...], tuple[tuple[float, ...], ...], tuple[float, ...]]:
    rng = _deterministic_rng(config.random_seed)
    initial = [1.0 + rng.random() for _ in range(config.n_states)]
    transition = []
    emission = []
    for _ in range(config.n_states):
        transition.append(_normalize([1.0 + rng.random() for _ in range(config.n_states)]))
        emission.append(_normalize([1.0 + rng.random() for _ in range(config.n_observations)]))
    return _normalize(initial), tuple(transition), tuple(emission)


def _safe_log(value: float) -> float:
    return math.log(max(value, 1e-300))


class HiddenMarkovModel:
    def __init__(self, config: HMMConfig = HMMConfig()) -> None:
        validate_hmm_config(config)
        self.config = config
        self.initial_probabilities: tuple[float, ...] = ()
        self.transition_matrix: tuple[tuple[float, ...], ...] = ()
        self.emission_matrix: tuple[tuple[float, ...], ...] = ()
        self._fitted = False
        self.classes_ = tuple(range(config.n_observations))
        self.training_result: HMMTrainingResult | None = None

    @property
    def fitted(self) -> bool:
        return self._fitted

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise ValueError("Hidden Markov model must be fitted.")

    def _initialize(self) -> None:
        self.initial_probabilities, self.transition_matrix, self.emission_matrix = _initial_parameters(self.config)

    def _forward(self, sequence: tuple[int, ...]):
        n = len(sequence)
        s = self.config.n_states
        alpha = [[0.0] * s for _ in range(n)]
        scales = [0.0] * n
        for state in range(s):
            alpha[0][state] = self.initial_probabilities[state] * self.emission_matrix[state][sequence[0]]
        scales[0] = sum(alpha[0])
        if scales[0] <= 0:
            scales[0] = 1e-300
        alpha[0] = [v / scales[0] for v in alpha[0]]
        for t in range(1, n):
            for state in range(s):
                alpha[t][state] = self.emission_matrix[state][sequence[t]] * sum(
                    alpha[t - 1][previous] * self.transition_matrix[previous][state]
                    for previous in range(s)
                )
            scales[t] = sum(alpha[t])
            if scales[t] <= 0:
                scales[t] = 1e-300
            alpha[t] = [v / scales[t] for v in alpha[t]]
        log_likelihood = sum(_safe_log(v) for v in scales)
        return alpha, scales, log_likelihood

    def _backward(self, sequence: tuple[int, ...], scales: Sequence[float]):
        n = len(sequence)
        s = self.config.n_states
        beta = [[0.0] * s for _ in range(n)]
        beta[-1] = [1.0] * s
        for t in range(n - 2, -1, -1):
            for state in range(s):
                beta[t][state] = sum(
                    self.transition_matrix[state][next_state]
                    * self.emission_matrix[next_state][sequence[t + 1]]
                    * beta[t + 1][next_state]
                    for next_state in range(s)
                ) / max(scales[t + 1], 1e-300)
        return beta

    def _expectation(self, sequence: tuple[int, ...]):
        alpha, scales, log_likelihood = self._forward(sequence)
        beta = self._backward(sequence, scales)
        n = len(sequence)
        s = self.config.n_states
        gamma = [[0.0] * s for _ in range(n)]
        xi = [[[0.0] * s for _ in range(s)] for _ in range(max(0, n - 1))]
        for t in range(n):
            gamma[t] = list(_normalize([alpha[t][state] * beta[t][state] for state in range(s)]))
        for t in range(n - 1):
            values = []
            for i in range(s):
                for j in range(s):
                    values.append(
                        alpha[t][i]
                        * self.transition_matrix[i][j]
                        * self.emission_matrix[j][sequence[t + 1]]
                        * beta[t + 1][j]
                    )
            normalized = _normalize(values)
            index = 0
            for i in range(s):
                for j in range(s):
                    xi[t][i][j] = normalized[index]
                    index += 1
        return gamma, xi, log_likelihood

    def fit(self, dataset: HMMDataset) -> "HiddenMarkovModel":
        validate_hmm_dataset(dataset, self.config)
        self._initialize()
        previous = None
        converged = False
        final_ll = float("-inf")
        iterations = 0
        s = self.config.n_states
        o = self.config.n_observations
        for iteration in range(1, self.config.max_iterations + 1):
            initial_counts = [self.config.smoothing] * s
            transition_counts = [[self.config.smoothing] * s for _ in range(s)]
            transition_denominators = [self.config.smoothing * s for _ in range(s)]
            emission_counts = [[self.config.smoothing] * o for _ in range(s)]
            emission_denominators = [self.config.smoothing * o for _ in range(s)]
            total_ll = 0.0
            for sequence in dataset.sequences:
                gamma, xi, ll = self._expectation(sequence)
                total_ll += ll
                for state in range(s):
                    initial_counts[state] += gamma[0][state]
                for t in range(len(sequence) - 1):
                    for i in range(s):
                        for j in range(s):
                            transition_counts[i][j] += xi[t][i][j]
                            transition_denominators[i] += xi[t][i][j]
                for t, observation in enumerate(sequence):
                    for state in range(s):
                        emission_counts[state][observation] += gamma[t][state]
                        emission_denominators[state] += gamma[t][state]
            self.initial_probabilities = _normalize(initial_counts)
            self.transition_matrix = tuple(
                _normalize(row) for row in transition_counts
            )
            self.emission_matrix = tuple(
                _normalize(row) for row in emission_counts
            )
            final_ll = total_ll
            iterations = iteration
            if previous is not None and abs(total_ll - previous) <= self.config.tolerance:
                converged = True
                break
            previous = total_ll
        self._fitted = True
        self.training_result = HMMTrainingResult(final_ll, iterations, converged)
        return self

    def log_likelihood(self, dataset: HMMDataset) -> float:
        self._require_fitted()
        validate_hmm_dataset(dataset, self.config)
        return sum(self._forward(sequence)[2] for sequence in dataset.sequences)

    def predict_state_proba(self, sequence: Sequence[int]) -> tuple[tuple[float, ...], ...]:
        self._require_fitted()
        values = _validate_sequence(sequence, self.config.n_observations)
        alpha, _, _ = self._forward(values)
        return tuple(tuple(row) for row in alpha)

    def posterior_state_proba(self, sequence: Sequence[int]) -> tuple[tuple[float, ...], ...]:
        self._require_fitted()
        values = _validate_sequence(sequence, self.config.n_observations)
        gamma, _, _ = self._expectation(values)
        return tuple(tuple(row) for row in gamma)

    def viterbi(self, sequence: Sequence[int]) -> tuple[int, ...]:
        self._require_fitted()
        values = _validate_sequence(sequence, self.config.n_observations)
        n = len(values)
        s = self.config.n_states
        delta = [[float("-inf")] * s for _ in range(n)]
        back = [[0] * s for _ in range(n)]
        for state in range(s):
            delta[0][state] = _safe_log(self.initial_probabilities[state]) + _safe_log(
                self.emission_matrix[state][values[0]]
            )
        for t in range(1, n):
            for state in range(s):
                candidates = [
                    delta[t - 1][previous] + _safe_log(self.transition_matrix[previous][state])
                    for previous in range(s)
                ]
                best = max(range(s), key=lambda x: (candidates[x], -x))
                delta[t][state] = candidates[best] + _safe_log(self.emission_matrix[state][values[t]])
                back[t][state] = best
        last = max(range(s), key=lambda x: (delta[-1][x], -x))
        path = [last]
        for t in range(n - 1, 0, -1):
            path.append(back[t][path[-1]])
        return tuple(reversed(path))

    def predict_next_proba(self, sequence: Sequence[int]) -> tuple[float, ...]:
        self._require_fitted()
        values = _validate_sequence(sequence, self.config.n_observations)
        posterior = self.posterior_state_proba(values)[-1]
        result = [0.0] * self.config.n_observations
        for state, weight in enumerate(posterior):
            for observation in range(self.config.n_observations):
                result[observation] += weight * self.emission_matrix[state][observation]
        return _normalize(result)

    def predict_next(self, sequence: Sequence[int], top_k: int = 1) -> tuple[int, ...]:
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")
        probabilities = self.predict_next_proba(sequence)
        ranked = sorted(
            range(self.config.n_observations),
            key=lambda digit: (-probabilities[digit], digit),
        )
        return tuple(ranked[: min(top_k, self.config.n_observations)])

    def evaluate(self, dataset: HMMDataset) -> HMMMetrics:
        self._require_fitted()
        validate_hmm_dataset(dataset, self.config)
        losses = []
        correct = 0
        observations = 0
        for sequence in dataset.sequences:
            if len(sequence) < 2:
                continue
            for index in range(1, len(sequence)):
                probabilities = self.predict_next_proba(sequence[:index])
                target = sequence[index]
                losses.append(-_safe_log(probabilities[target]))
                correct += int(max(range(self.config.n_observations), key=lambda d: (probabilities[d], -d)) == target)
                observations += 1
        if observations == 0:
            raise ValueError("dataset has no evaluable next-observation transitions.")
        return HMMMetrics(sum(losses) / observations, correct / observations, observations)


def prepare_hmm_dataset_from_sequences(
    sequences: Sequence[Sequence[int]], identity: str, target_name: str = "target"
) -> HMMDataset:
    return build_hmm_dataset(sequences, identity, target_name)


def build_position_hmm_models(
    datasets: Mapping[str, HMMDataset],
    config: HMMConfig = HMMConfig(),
) -> PositionHMMModels:
    validate_hmm_config(config)
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    return PositionHMMModels(
        tuple(
            (name, HiddenMarkovModel(config).fit(datasets[name]))
            for name in sorted(datasets)
        )
    )


def get_position_hmm_model(models: PositionHMMModels, position: str) -> HiddenMarkovModel:
    if not isinstance(models, PositionHMMModels):
        raise TypeError("models must be PositionHMMModels.")
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")


def compare_hmm_with_baseline(
    metrics: HMMMetrics, baseline_log_loss: float
) -> HMMBaselineComparison:
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return HMMBaselineComparison(
        metrics.log_loss, float(baseline_log_loss), metrics.log_loss - baseline_log_loss
    )


def build_hmm_artifact(model: HiddenMarkovModel, dataset: HMMDataset) -> HMMArtifact:
    model._require_fitted()
    validate_hmm_dataset(dataset, model.config)
    payload = {
        "model_kind": MODEL_KIND,
        "model_version": HMM_VERSION,
        "n_states": model.config.n_states,
        "n_observations": model.config.n_observations,
        "smoothing": model.config.smoothing,
        "dataset_identity": dataset.identity,
        "target_name": dataset.target_name,
        "initial": list(model.initial_probabilities),
        "transition": [list(row) for row in model.transition_matrix],
        "emission": [list(row) for row in model.emission_matrix],
    }
    identity = "hmm-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return HMMArtifact(
        MODEL_KIND,
        HMM_VERSION,
        model.config.n_states,
        model.config.n_observations,
        model.config.smoothing,
        dataset.identity,
        dataset.target_name,
        identity,
    )


def validate_hmm_model(model: HiddenMarkovModel) -> HMMValidationResult:
    if not isinstance(model, HiddenMarkovModel):
        return HMMValidationResult(INVALID, ("INVALID_MODEL_TYPE",))
    issues = []
    if not model.fitted:
        issues.append("MODEL_NOT_FITTED")
        return HMMValidationResult(INVALID, tuple(issues))
    if len(model.initial_probabilities) != model.config.n_states:
        issues.append("INVALID_INITIAL_SHAPE")
    if len(model.transition_matrix) != model.config.n_states:
        issues.append("INVALID_TRANSITION_SHAPE")
    if len(model.emission_matrix) != model.config.n_states:
        issues.append("INVALID_EMISSION_SHAPE")
    if model.initial_probabilities and not math.isclose(sum(model.initial_probabilities), 1.0, abs_tol=1e-8):
        issues.append("INITIAL_NOT_NORMALIZED")
    for row in model.transition_matrix:
        if len(row) != model.config.n_states or not math.isclose(sum(row), 1.0, abs_tol=1e-8):
            issues.append("TRANSITION_NOT_NORMALIZED")
        if any(value < 0 for value in row):
            issues.append("NEGATIVE_TRANSITION")
    for row in model.emission_matrix:
        if len(row) != model.config.n_observations or not math.isclose(sum(row), 1.0, abs_tol=1e-8):
            issues.append("EMISSION_NOT_NORMALIZED")
        if any(value < 0 for value in row):
            issues.append("NEGATIVE_EMISSION")
    return HMMValidationResult(VALID if not issues else INVALID, tuple(dict.fromkeys(issues)))


def save_hmm_model(model: HiddenMarkovModel, path: str | Path) -> Path:
    model._require_fitted()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_hmm_model(path: str | Path) -> HiddenMarkovModel:
    model = joblib.load(Path(path))
    if not isinstance(model, HiddenMarkovModel):
        raise ValueError("Stored artifact is not a HiddenMarkovModel.")
    return model


def reproduce_hmm_artifact(
    first: HMMArtifact, second: HMMArtifact
) -> HMMReproducibilityResult:
    if not isinstance(first, HMMArtifact) or not isinstance(second, HMMArtifact):
        raise TypeError("Both artifacts must be HMMArtifact instances.")
    return HMMReproducibilityResult(
        first.artifact_identity == second.artifact_identity,
        first.artifact_identity,
        second.artifact_identity,
    )


def validate_hmm_artifact_lineage(
    artifact: HMMArtifact, dataset: HMMDataset, model: HiddenMarkovModel
) -> None:
    if artifact.model_kind != MODEL_KIND or artifact.model_version != HMM_VERSION:
        raise ValueError("HMM artifact version lineage is invalid.")
    if artifact.dataset_identity != dataset.identity:
        raise ValueError("HMM artifact dataset identity does not match.")
    if (
        artifact.n_states != model.config.n_states
        or artifact.n_observations != model.config.n_observations
        or artifact.smoothing != model.config.smoothing
    ):
        raise ValueError("HMM artifact configuration does not match model.")


__all__ = [
    "VALID", "INVALID", "HMM_VERSION", "MODEL_KIND",
    "HMMConfig", "HMMDataset", "HMMMetrics", "HMMTrainingResult",
    "HMMArtifact", "HMMValidationResult", "HMMBaselineComparison",
    "HMMReproducibilityResult", "PositionHMMModels", "HiddenMarkovModel",
    "validate_hmm_config", "build_hmm_dataset", "validate_hmm_dataset",
    "prepare_hmm_dataset_from_sequences", "build_position_hmm_models",
    "get_position_hmm_model", "compare_hmm_with_baseline", "build_hmm_artifact",
    "validate_hmm_model", "save_hmm_model", "load_hmm_model",
    "reproduce_hmm_artifact", "validate_hmm_artifact_lineage",
]
