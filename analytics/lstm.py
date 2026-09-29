from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import joblib
import numpy as np

VALID = "VALID"
INVALID = "INVALID"
LSTM_VERSION = "30.0.0"
MODEL_KIND = "lstm"


@dataclass(frozen=True)
class LSTMConfig:
    sequence_length: int = 5
    hidden_size: int = 16
    learning_rate: float = 0.05
    epochs: int = 25
    batch_size: int = 8
    smoothing: float = 1e-6
    seed: int = 30
    alphabet_size: int = 10
    gradient_clip: float = 5.0
    patience: int = 5


@dataclass(frozen=True)
class LSTMDataset:
    sequences: tuple[tuple[int, ...], ...]
    identity: str
    target_name: str = "target"


@dataclass(frozen=True)
class LSTMMetrics:
    log_loss: float
    accuracy: float
    observations: int


@dataclass(frozen=True)
class LSTMTrainingHistory:
    losses: tuple[float, ...]
    epochs_completed: int
    best_loss: float


@dataclass(frozen=True)
class LSTMArtifact:
    model_kind: str
    model_version: str
    sequence_length: int
    hidden_size: int
    dataset_identity: str
    target_name: str
    artifact_identity: str


@dataclass(frozen=True)
class LSTMValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


@dataclass(frozen=True)
class LSTMBaselineComparison:
    lstm_log_loss: float
    baseline_log_loss: float
    difference: float


@dataclass(frozen=True)
class LSTMReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str


@dataclass(frozen=True)
class PositionLSTMModels:
    models: tuple[tuple[str, "LSTMClassifier"], ...]


def validate_lstm_config(config: LSTMConfig) -> None:
    if not isinstance(config, LSTMConfig):
        raise TypeError("config must be an LSTMConfig.")
    if isinstance(config.sequence_length, bool) or not isinstance(config.sequence_length, int) or config.sequence_length <= 0:
        raise ValueError("sequence_length must be a positive integer.")
    if isinstance(config.hidden_size, bool) or not isinstance(config.hidden_size, int) or config.hidden_size <= 0:
        raise ValueError("hidden_size must be a positive integer.")
    if config.learning_rate <= 0 or not math.isfinite(config.learning_rate):
        raise ValueError("learning_rate must be positive and finite.")
    if isinstance(config.epochs, bool) or not isinstance(config.epochs, int) or config.epochs <= 0:
        raise ValueError("epochs must be a positive integer.")
    if isinstance(config.batch_size, bool) or not isinstance(config.batch_size, int) or config.batch_size <= 0:
        raise ValueError("batch_size must be a positive integer.")
    if config.smoothing < 0 or not math.isfinite(config.smoothing):
        raise ValueError("smoothing must be non-negative and finite.")
    if config.alphabet_size != 10:
        raise ValueError("alphabet_size must be exactly 10 for NeuroLytics digit models.")
    if config.gradient_clip <= 0:
        raise ValueError("gradient_clip must be positive.")
    if isinstance(config.patience, bool) or not isinstance(config.patience, int) or config.patience <= 0:
        raise ValueError("patience must be a positive integer.")


def _validate_sequence(sequence: Sequence[int], alphabet_size: int = 10) -> tuple[int, ...]:
    values = tuple(sequence)
    if not values:
        raise ValueError("sequence cannot be empty.")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("sequence values must be integers.")
    if any(v < 0 or v >= alphabet_size for v in values):
        raise ValueError("sequence values must be valid digits 0-9.")
    return values


def build_lstm_dataset(
    sequences: Sequence[Sequence[int]],
    identity: str,
    target_name: str = "target",
) -> LSTMDataset:
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("identity must be non-empty.")
    if not isinstance(target_name, str) or not target_name.strip():
        raise ValueError("target_name must be non-empty.")
    rows = tuple(_validate_sequence(row) for row in sequences)
    if not rows:
        raise ValueError("at least one sequence is required.")
    return LSTMDataset(rows, identity, target_name)


def validate_lstm_dataset(dataset: LSTMDataset, config: LSTMConfig | None = None) -> None:
    if not isinstance(dataset, LSTMDataset):
        raise TypeError("dataset must be an LSTMDataset.")
    cfg = config or LSTMConfig()
    validate_lstm_config(cfg)
    if not dataset.sequences:
        raise ValueError("dataset must contain sequences.")
    for sequence in dataset.sequences:
        values = _validate_sequence(sequence, cfg.alphabet_size)
        if len(values) <= cfg.sequence_length:
            raise ValueError("every sequence must contain more observations than sequence_length.")


def prepare_lstm_dataset_from_sequences(
    sequences: Sequence[Sequence[int]], identity: str, target_name: str = "target"
) -> LSTMDataset:
    return build_lstm_dataset(sequences, identity, target_name)


def chronological_lstm_split(
    dataset: LSTMDataset, test_fraction: float = 0.2
) -> tuple[LSTMDataset, LSTMDataset]:
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1.")
    if len(dataset.sequences) < 2:
        raise ValueError("at least two sequences are required for a chronological split.")
    cut = max(1, min(len(dataset.sequences) - 1, int(len(dataset.sequences) * (1 - test_fraction))))
    train = LSTMDataset(dataset.sequences[:cut], dataset.identity + ":train", dataset.target_name)
    test = LSTMDataset(dataset.sequences[cut:], dataset.identity + ":test", dataset.target_name)
    return train, test


def _windows(dataset: LSTMDataset, sequence_length: int) -> tuple[np.ndarray, np.ndarray]:
    x_rows: list[list[int]] = []
    y_rows: list[int] = []
    for sequence in dataset.sequences:
        for index in range(sequence_length, len(sequence)):
            x_rows.append(list(sequence[index - sequence_length:index]))
            y_rows.append(sequence[index])
    if not x_rows:
        raise ValueError("dataset has no evaluable sequence windows.")
    return np.asarray(x_rows, dtype=np.int64), np.asarray(y_rows, dtype=np.int64)


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values)
    exp = np.exp(np.clip(shifted, -60.0, 60.0))
    return exp / np.sum(exp)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -60.0, 60.0)))


class LSTMClassifier:
    """Small deterministic categorical LSTM implemented with NumPy."""

    def __init__(self, config: LSTMConfig = LSTMConfig()) -> None:
        validate_lstm_config(config)
        self.config = config
        self.classes_ = tuple(range(config.alphabet_size))
        self._fitted = False
        self._history: LSTMTrainingHistory | None = None
        self._initialize_parameters()

    def _initialize_parameters(self) -> None:
        rng = np.random.default_rng(self.config.seed)
        scale = 1.0 / math.sqrt(self.config.hidden_size)
        h = self.config.hidden_size
        a = self.config.alphabet_size
        self.W = rng.normal(0.0, scale, size=(4 * h, a))
        self.U = rng.normal(0.0, scale, size=(4 * h, h))
        self.b = np.zeros(4 * h, dtype=float)
        self.V = rng.normal(0.0, scale, size=(a, h))
        self.c = np.zeros(a, dtype=float)

    @property
    def fitted(self) -> bool:
        return self._fitted

    @property
    def training_history(self) -> LSTMTrainingHistory | None:
        return self._history

    def _forward(self, window: Sequence[int], training: bool = False):
        h = self.config.hidden_size
        hidden = np.zeros(h, dtype=float)
        cell = np.zeros(h, dtype=float)
        cache = []
        for value in window:
            x = np.zeros(self.config.alphabet_size, dtype=float)
            x[int(value)] = 1.0
            gates = self.W @ x + self.U @ hidden + self.b
            i = _sigmoid(gates[:h])
            f = _sigmoid(gates[h:2*h])
            o = _sigmoid(gates[2*h:3*h])
            g = np.tanh(gates[3*h:])
            cell = f * cell + i * g
            hidden = o * np.tanh(cell)
            if training:
                cache.append((x, hidden.copy(), cell.copy(), i, f, o, g))
        logits = self.V @ hidden + self.c
        return _softmax(logits), hidden, cache

    def _train_window(self, window: Sequence[int], target: int) -> float:
        probabilities, final_hidden, cache = self._forward(window, training=True)
        loss = -math.log(max(float(probabilities[target]), self.config.smoothing or 1e-15))
        dlogits = probabilities.copy()
        dlogits[target] -= 1.0
        dV = np.outer(dlogits, final_hidden)
        dc = dlogits.copy()
        dh = self.V.T @ dlogits
        h = self.config.hidden_size
        dW = np.zeros_like(self.W)
        dU = np.zeros_like(self.U)
        db = np.zeros_like(self.b)
        dcell = np.zeros(h, dtype=float)
        next_hidden = np.zeros(h, dtype=float)
        for t in range(len(cache) - 1, -1, -1):
            x, hidden, cell, i, f, o, g = cache[t]
            prev_hidden = cache[t - 1][1] if t else np.zeros(h, dtype=float)
            prev_cell = cache[t - 1][2] if t else np.zeros(h, dtype=float)
            tanh_cell = np.tanh(cell)
            do = dh * tanh_cell
            dcell_total = dcell + dh * o * (1.0 - tanh_cell * tanh_cell)
            df = dcell_total * prev_cell
            di = dcell_total * g
            dg = dcell_total * i
            dgate = np.concatenate((
                di * i * (1.0 - i),
                df * f * (1.0 - f),
                do * o * (1.0 - o),
                dg * (1.0 - g * g),
            ))
            dW += np.outer(dgate, x)
            dU += np.outer(dgate, prev_hidden)
            db += dgate
            dh = self.U.T @ dgate
            dcell = dcell_total * f
            next_hidden = hidden
        norm = max(1.0, float(np.linalg.norm(dW)))
        clip = self.config.gradient_clip / max(1.0, norm)
        if clip < 1.0:
            dW *= clip
            dU *= clip
            db *= clip
            dV *= clip
            dc *= clip
        lr = self.config.learning_rate
        self.W -= lr * dW
        self.U -= lr * dU
        self.b -= lr * db
        self.V -= lr * dV
        self.c -= lr * dc
        return float(loss)

    def fit(self, dataset: LSTMDataset) -> "LSTMClassifier":
        validate_lstm_dataset(dataset, self.config)
        x, y = _windows(dataset, self.config.sequence_length)
        losses: list[float] = []
        best_loss = float("inf")
        best_state = None
        stale = 0
        for _epoch in range(self.config.epochs):
            epoch_losses = []
            for start in range(0, len(x), self.config.batch_size):
                for window, target in zip(x[start:start + self.config.batch_size], y[start:start + self.config.batch_size]):
                    epoch_losses.append(self._train_window(window, int(target)))
            epoch_loss = float(np.mean(epoch_losses))
            losses.append(epoch_loss)
            if epoch_loss + 1e-12 < best_loss:
                best_loss = epoch_loss
                best_state = self._state()
                stale = 0
            else:
                stale += 1
            if stale >= self.config.patience:
                break
        if best_state is not None:
            self._restore_state(best_state)
        self._fitted = True
        self._history = LSTMTrainingHistory(tuple(losses), len(losses), best_loss)
        return self

    def _state(self) -> tuple[np.ndarray, ...]:
        return tuple(np.array(v, copy=True) for v in (self.W, self.U, self.b, self.V, self.c))

    def _restore_state(self, state: tuple[np.ndarray, ...]) -> None:
        self.W, self.U, self.b, self.V, self.c = tuple(np.array(v, copy=True) for v in state)

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise ValueError("LSTM model must be fitted.")

    def predict_proba(self, windows: Sequence[Sequence[int]]) -> tuple[tuple[float, ...], ...]:
        self._require_fitted()
        results = []
        for window in windows:
            values = _validate_sequence(window, self.config.alphabet_size)
            if len(values) != self.config.sequence_length:
                raise ValueError("each prediction window must equal sequence_length.")
            results.append(tuple(float(v) for v in self._forward(values)[0]))
        return tuple(results)

    def predict_next(self, window: Sequence[int], top_k: int = 1) -> tuple[int, ...]:
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")
        probabilities = self.predict_proba([window])[0]
        ranked = sorted(range(self.config.alphabet_size), key=lambda d: (-probabilities[d], d))
        return tuple(ranked[:min(top_k, self.config.alphabet_size)])

    def evaluate(self, dataset: LSTMDataset) -> LSTMMetrics:
        validate_lstm_dataset(dataset, self.config)
        x, y = _windows(dataset, self.config.sequence_length)
        probabilities = self.predict_proba(x.tolist())
        losses = [-math.log(max(row[int(target)], 1e-15)) for row, target in zip(probabilities, y)]
        correct = sum(int(max(range(self.config.alphabet_size), key=lambda d: (row[d], -d)) == int(target))
                      for row, target in zip(probabilities, y))
        return LSTMMetrics(float(np.mean(losses)), correct / len(y), len(y))

    def log_likelihood(self, dataset: LSTMDataset) -> float:
        metrics = self.evaluate(dataset)
        return -metrics.log_loss * metrics.observations


def build_position_lstm_models(
    datasets: Mapping[str, LSTMDataset],
    config: LSTMConfig = LSTMConfig(),
) -> PositionLSTMModels:
    validate_lstm_config(config)
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    models = tuple((name, LSTMClassifier(config).fit(datasets[name])) for name in sorted(datasets))
    return PositionLSTMModels(models)


def get_position_lstm_model(models: PositionLSTMModels, position: str) -> LSTMClassifier:
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")


def compare_with_baseline(metrics: LSTMMetrics, baseline_log_loss: float) -> LSTMBaselineComparison:
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return LSTMBaselineComparison(metrics.log_loss, float(baseline_log_loss), metrics.log_loss - baseline_log_loss)


def build_lstm_artifact(model: LSTMClassifier, dataset: LSTMDataset) -> LSTMArtifact:
    model._require_fitted()
    validate_lstm_dataset(dataset, model.config)
    payload = {
        "model_kind": MODEL_KIND,
        "model_version": LSTM_VERSION,
        "sequence_length": model.config.sequence_length,
        "hidden_size": model.config.hidden_size,
        "learning_rate": model.config.learning_rate,
        "epochs": model.config.epochs,
        "batch_size": model.config.batch_size,
        "seed": model.config.seed,
        "dataset_identity": dataset.identity,
        "target_name": dataset.target_name,
        "parameters": [np.asarray(v).round(12).tolist() for v in model._state()],
    }
    identity = "lstm-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return LSTMArtifact(
        MODEL_KIND, LSTM_VERSION, model.config.sequence_length, model.config.hidden_size,
        dataset.identity, dataset.target_name, identity,
    )


def validate_lstm_model(model: LSTMClassifier) -> LSTMValidationResult:
    if not isinstance(model, LSTMClassifier):
        return LSTMValidationResult(INVALID, ("INVALID_MODEL_TYPE",))
    issues: list[str] = []
    if not model.fitted:
        issues.append("MODEL_NOT_FITTED")
    expected = {
        "W": (4 * model.config.hidden_size, model.config.alphabet_size),
        "U": (4 * model.config.hidden_size, model.config.hidden_size),
        "b": (4 * model.config.hidden_size,),
        "V": (model.config.alphabet_size, model.config.hidden_size),
        "c": (model.config.alphabet_size,),
    }
    for name, shape in expected.items():
        if getattr(model, name).shape != shape:
            issues.append(f"INVALID_{name.upper()}_SHAPE")
        if not np.isfinite(getattr(model, name)).all():
            issues.append(f"NONFINITE_{name.upper()}")
    return LSTMValidationResult(VALID if not issues else INVALID, tuple(issues))


def save_lstm_model(model: LSTMClassifier, path: str | Path) -> Path:
    model._require_fitted()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_lstm_model(path: str | Path) -> LSTMClassifier:
    model = joblib.load(Path(path))
    if not isinstance(model, LSTMClassifier):
        raise ValueError("Stored artifact is not an LSTMClassifier.")
    return model


def reproduce_lstm_artifact(first: LSTMArtifact, second: LSTMArtifact) -> LSTMReproducibilityResult:
    if not isinstance(first, LSTMArtifact) or not isinstance(second, LSTMArtifact):
        raise TypeError("Both artifacts must be LSTMArtifact instances.")
    return LSTMReproducibilityResult(
        first.artifact_identity == second.artifact_identity,
        first.artifact_identity,
        second.artifact_identity,
    )


def validate_lstm_artifact_lineage(
    artifact: LSTMArtifact, dataset: LSTMDataset, model: LSTMClassifier
) -> None:
    if artifact.model_kind != MODEL_KIND or artifact.model_version != LSTM_VERSION:
        raise ValueError("LSTM artifact version lineage is invalid.")
    if artifact.dataset_identity != dataset.identity:
        raise ValueError("LSTM artifact dataset identity does not match.")
    if artifact.sequence_length != model.config.sequence_length or artifact.hidden_size != model.config.hidden_size:
        raise ValueError("LSTM artifact configuration does not match model.")


__all__ = [
    "VALID", "INVALID", "LSTM_VERSION", "MODEL_KIND", "LSTMConfig",
    "LSTMDataset", "LSTMMetrics", "LSTMTrainingHistory", "LSTMArtifact",
    "LSTMValidationResult", "LSTMBaselineComparison", "LSTMReproducibilityResult",
    "PositionLSTMModels", "LSTMClassifier", "validate_lstm_config",
    "build_lstm_dataset", "validate_lstm_dataset",
    "prepare_lstm_dataset_from_sequences", "chronological_lstm_split",
    "build_position_lstm_models", "get_position_lstm_model",
    "compare_with_baseline", "build_lstm_artifact", "validate_lstm_model",
    "save_lstm_model", "load_lstm_model", "reproduce_lstm_artifact",
    "validate_lstm_artifact_lineage",
]
