from __future__ import annotations

import hashlib
import json
import joblib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

VALID = "VALID"
INVALID = "INVALID"
MARKOV_VERSION = "28.0.0"
MODEL_KIND = "markov"

@dataclass(frozen=True)
class MarkovConfig:
    order: int = 1
    smoothing: float = 1.0
    alphabet_size: int = 10

@dataclass(frozen=True)
class MarkovDataset:
    sequences: tuple[tuple[int, ...], ...]
    identity: str
    target_name: str = "target"

@dataclass(frozen=True)
class MarkovMetrics:
    log_loss: float
    accuracy: float
    observations: int

@dataclass(frozen=True)
class MarkovArtifact:
    model_kind: str
    model_version: str
    order: int
    smoothing: float
    dataset_identity: str
    target_name: str
    artifact_identity: str

@dataclass(frozen=True)
class MarkovValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

@dataclass(frozen=True)
class MarkovBaselineComparison:
    markov_log_loss: float
    baseline_log_loss: float
    difference: float

@dataclass(frozen=True)
class MarkovReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str

@dataclass(frozen=True)
class PositionMarkovModels:
    models: tuple[tuple[str, "MarkovChain"], ...]

def validate_markov_config(config: MarkovConfig) -> None:
    if not isinstance(config, MarkovConfig):
        raise TypeError("config must be a MarkovConfig.")
    if isinstance(config.order, bool) or not isinstance(config.order, int) or config.order <= 0:
        raise ValueError("order must be a positive integer.")
    if config.order > 10:
        raise ValueError("order must not exceed 10.")
    if config.smoothing < 0:
        raise ValueError("smoothing cannot be negative.")
    if config.alphabet_size != 10:
        raise ValueError("alphabet_size must be exactly 10 for NeuroLytics digit models.")

def _validate_sequence(sequence: Sequence[int], alphabet_size: int = 10) -> tuple[int, ...]:
    values = tuple(sequence)
    if not values:
        raise ValueError("sequence cannot be empty.")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("sequence values must be integers.")
    if any(v < 0 or v >= alphabet_size for v in values):
        raise ValueError("sequence values must be valid digits 0-9.")
    return values

def build_markov_dataset(
    sequences: Sequence[Sequence[int]],
    identity: str,
    target_name: str = "target",
) -> MarkovDataset:
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("identity must be non-empty.")
    rows = tuple(_validate_sequence(row) for row in sequences)
    if not rows:
        raise ValueError("at least one sequence is required.")
    if not isinstance(target_name, str) or not target_name.strip():
        raise ValueError("target_name must be non-empty.")
    return MarkovDataset(rows, identity, target_name)

def _context(sequence: tuple[int, ...], index: int, order: int) -> tuple[int, ...] | None:
    if index < order:
        return None
    return sequence[index - order:index]

def _transition_counts(
    dataset: MarkovDataset, config: MarkovConfig
) -> dict[tuple[int, ...], list[int]]:
    validate_markov_dataset(dataset, config)
    counts: dict[tuple[int, ...], list[int]] = {}
    for sequence in dataset.sequences:
        for i in range(config.order, len(sequence)):
            context = _context(sequence, i, config.order)
            assert context is not None
            counts.setdefault(context, [0] * config.alphabet_size)[sequence[i]] += 1
    return counts

def validate_markov_dataset(dataset: MarkovDataset, config: MarkovConfig | None = None) -> None:
    if not isinstance(dataset, MarkovDataset):
        raise TypeError("dataset must be a MarkovDataset.")
    if not dataset.sequences:
        raise ValueError("dataset must contain sequences.")
    cfg = config or MarkovConfig()
    validate_markov_config(cfg)
    for sequence in dataset.sequences:
        _validate_sequence(sequence, cfg.alphabet_size)
        if len(sequence) <= cfg.order:
            raise ValueError("every sequence must contain more observations than the Markov order.")

class MarkovChain:
    def __init__(self, config: MarkovConfig = MarkovConfig()) -> None:
        validate_markov_config(config)
        self.config = config
        self._counts: dict[tuple[int, ...], list[int]] = {}
        self._fitted = False
        self.classes_ = tuple(range(config.alphabet_size))

    def fit(self, dataset: MarkovDataset) -> "MarkovChain":
        validate_markov_dataset(dataset, self.config)
        self._counts = _transition_counts(dataset, self.config)
        self._fitted = True
        return self

    @property
    def fitted(self) -> bool:
        return self._fitted

    @property
    def contexts_(self) -> tuple[tuple[int, ...], ...]:
        return tuple(sorted(self._counts))

    def transition_counts(self, context: Sequence[int]) -> tuple[int, ...]:
        self._require_fitted()
        ctx = _validate_sequence(context, self.config.alphabet_size)
        if len(ctx) != self.config.order:
            raise ValueError("context width must equal model order.")
        return tuple(self._counts.get(ctx, [0] * self.config.alphabet_size))

    def transition_probabilities(self, context: Sequence[int]) -> tuple[float, ...]:
        counts = self.transition_counts(context)
        alpha = self.config.smoothing
        denominator = sum(counts) + alpha * self.config.alphabet_size
        if denominator <= 0:
            return tuple(1.0 / self.config.alphabet_size for _ in counts)
        return tuple((count + alpha) / denominator for count in counts)

    def predict_proba(self, contexts: Sequence[Sequence[int]]) -> tuple[tuple[float, ...], ...]:
        self._require_fitted()
        return tuple(self.transition_probabilities(ctx) for ctx in contexts)

    def predict_next(self, context: Sequence[int], top_k: int = 1) -> tuple[int, ...]:
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")
        probabilities = self.transition_probabilities(context)
        ranked = sorted(range(self.config.alphabet_size), key=lambda d: (-probabilities[d], d))
        return tuple(ranked[: min(top_k, self.config.alphabet_size)])

    def log_likelihood(self, dataset: MarkovDataset) -> float:
        validate_markov_dataset(dataset, self.config)
        total = 0.0
        import math
        for sequence in dataset.sequences:
            for i in range(self.config.order, len(sequence)):
                context = sequence[i - self.config.order:i]
                probability = self.transition_probabilities(context)[sequence[i]]
                total += math.log(max(probability, 1e-15))
        return total

    def evaluate(self, dataset: MarkovDataset) -> MarkovMetrics:
        validate_markov_dataset(dataset, self.config)
        import math
        losses = []
        correct = 0
        observations = 0
        for sequence in dataset.sequences:
            for i in range(self.config.order, len(sequence)):
                context = sequence[i - self.config.order:i]
                probabilities = self.transition_probabilities(context)
                target = sequence[i]
                losses.append(-math.log(max(probabilities[target], 1e-15)))
                correct += int(max(range(self.config.alphabet_size), key=lambda d: (probabilities[d], -d)) == target)
                observations += 1
        if observations == 0:
            raise ValueError("dataset has no evaluable transitions.")
        return MarkovMetrics(sum(losses) / observations, correct / observations, observations)

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise ValueError("Markov model must be fitted.")

def prepare_markov_dataset_from_sequences(
    sequences: Sequence[Sequence[int]], identity: str, target_name: str = "target"
) -> MarkovDataset:
    return build_markov_dataset(sequences, identity, target_name)

def build_position_markov_models(
    datasets: Mapping[str, MarkovDataset],
    config: MarkovConfig = MarkovConfig(),
) -> PositionMarkovModels:
    validate_markov_config(config)
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    models = tuple((name, MarkovChain(config).fit(datasets[name])) for name in sorted(datasets))
    return PositionMarkovModels(models)

def get_position_markov_model(models: PositionMarkovModels, position: str) -> MarkovChain:
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")

def compare_with_baseline(metrics: MarkovMetrics, baseline_log_loss: float) -> MarkovBaselineComparison:
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return MarkovBaselineComparison(metrics.log_loss, float(baseline_log_loss), metrics.log_loss - baseline_log_loss)

def build_markov_artifact(model: MarkovChain, dataset: MarkovDataset) -> MarkovArtifact:
    model._require_fitted()
    validate_markov_dataset(dataset, model.config)
    payload = {
        "model_kind": MODEL_KIND,
        "model_version": MARKOV_VERSION,
        "order": model.config.order,
        "smoothing": model.config.smoothing,
        "dataset_identity": dataset.identity,
        "target_name": dataset.target_name,
        "contexts": [
            [list(context), list(model._counts[context])] for context in sorted(model._counts)
        ],
    }
    identity = "markov-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return MarkovArtifact(
        MODEL_KIND, MARKOV_VERSION, model.config.order, model.config.smoothing,
        dataset.identity, dataset.target_name, identity,
    )

def validate_markov_model(model: MarkovChain) -> MarkovValidationResult:
    if not isinstance(model, MarkovChain):
        return MarkovValidationResult(INVALID, ("INVALID_MODEL_TYPE",))
    issues = []
    if not model.fitted:
        issues.append("MODEL_NOT_FITTED")
    for context, counts in model._counts.items():
        if len(context) != model.config.order or len(counts) != model.config.alphabet_size:
            issues.append("INVALID_TRANSITION_SHAPE")
        if any(v < 0 for v in counts):
            issues.append("NEGATIVE_TRANSITION_COUNT")
    return MarkovValidationResult(VALID if not issues else INVALID, tuple(issues))

def save_markov_model(model: MarkovChain, path: str | Path) -> Path:
    model._require_fitted()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target

def load_markov_model(path: str | Path) -> MarkovChain:
    model = joblib.load(Path(path))
    if not isinstance(model, MarkovChain):
        raise ValueError("Stored artifact is not a MarkovChain.")
    return model

def reproduce_markov_artifact(
    first: MarkovArtifact, second: MarkovArtifact
) -> MarkovReproducibilityResult:
    if not isinstance(first, MarkovArtifact) or not isinstance(second, MarkovArtifact):
        raise TypeError("Both artifacts must be MarkovArtifact instances.")
    return MarkovReproducibilityResult(
        first.artifact_identity == second.artifact_identity,
        first.artifact_identity,
        second.artifact_identity,
    )

def validate_markov_artifact_lineage(
    artifact: MarkovArtifact, dataset: MarkovDataset, model: MarkovChain
) -> None:
    if artifact.model_kind != MODEL_KIND or artifact.model_version != MARKOV_VERSION:
        raise ValueError("Markov artifact version lineage is invalid.")
    if artifact.dataset_identity != dataset.identity:
        raise ValueError("Markov artifact dataset identity does not match.")
    if artifact.order != model.config.order or artifact.smoothing != model.config.smoothing:
        raise ValueError("Markov artifact configuration does not match model.")

def stationary_distribution(model: MarkovChain, context: Sequence[int], steps: int = 100) -> tuple[float, ...]:
    if steps <= 0:
        raise ValueError("steps must be positive.")
    probabilities = model.transition_probabilities(context)
    for _ in range(steps - 1):
        weighted = [0.0] * model.config.alphabet_size
        for digit, weight in enumerate(probabilities):
            next_context = (context[1:] + (digit,)) if model.config.order > 1 else (digit,)
            row = model.transition_probabilities(next_context)
            for j, value in enumerate(row):
                weighted[j] += weight * value
        probabilities = tuple(weighted)
    return probabilities

__all__ = [
    "VALID", "INVALID", "MARKOV_VERSION", "MODEL_KIND", "MarkovConfig",
    "MarkovDataset", "MarkovMetrics", "MarkovArtifact", "MarkovValidationResult",
    "MarkovBaselineComparison", "MarkovReproducibilityResult", "PositionMarkovModels",
    "MarkovChain", "validate_markov_config", "build_markov_dataset",
    "validate_markov_dataset", "prepare_markov_dataset_from_sequences",
    "build_position_markov_models", "get_position_markov_model",
    "compare_with_baseline", "build_markov_artifact", "validate_markov_model",
    "save_markov_model", "load_markov_model", "reproduce_markov_artifact",
    "validate_markov_artifact_lineage", "stationary_distribution",
]
