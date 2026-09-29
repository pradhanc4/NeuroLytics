
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
GRU_VERSION = "31.0.0"
MODEL_KIND = "gru"


@dataclass(frozen=True)
class GRUConfig:
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
class GRUDataset:
    sequences: tuple[tuple[int, ...], ...]
    identity: str
    target_name: str = "target"


@dataclass(frozen=True)
class GRUMetrics:
    log_loss: float
    accuracy: float
    observations: int


@dataclass(frozen=True)
class GRUTrainingHistory:
    losses: tuple[float, ...]
    epochs_completed: int
    best_loss: float


@dataclass(frozen=True)
class GRUArtifact:
    model_kind: str
    model_version: str
    sequence_length: int
    hidden_size: int
    dataset_identity: str
    target_name: str
    artifact_identity: str


@dataclass(frozen=True)
class GRUValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


@dataclass(frozen=True)
class GRUBaselineComparison:
    gru_log_loss: float
    baseline_log_loss: float
    difference: float


@dataclass(frozen=True)
class GRUReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str


@dataclass(frozen=True)
class PositionGRUModels:
    models: tuple[tuple[str, "GRUClassifier"], ...]


def validate_gru_config(config: GRUConfig) -> None:
    if not isinstance(config, GRUConfig):
        raise TypeError("config must be an GRUConfig.")
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


def build_gru_dataset(
    sequences: Sequence[Sequence[int]],
    identity: str,
    target_name: str = "target",
) -> GRUDataset:
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("identity must be non-empty.")
    if not isinstance(target_name, str) or not target_name.strip():
        raise ValueError("target_name must be non-empty.")
    rows = tuple(_validate_sequence(row) for row in sequences)
    if not rows:
        raise ValueError("at least one sequence is required.")
    return GRUDataset(rows, identity, target_name)


def validate_gru_dataset(dataset: GRUDataset, config: GRUConfig | None = None) -> None:
    if not isinstance(dataset, GRUDataset):
        raise TypeError("dataset must be an GRUDataset.")
    cfg = config or GRUConfig()
    validate_gru_config(cfg)
    if not dataset.sequences:
        raise ValueError("dataset must contain sequences.")
    for sequence in dataset.sequences:
        values = _validate_sequence(sequence, cfg.alphabet_size)
        if len(values) <= cfg.sequence_length:
            raise ValueError("every sequence must contain more observations than sequence_length.")


def prepare_gru_dataset_from_sequences(
    sequences: Sequence[Sequence[int]], identity: str, target_name: str = "target"
) -> GRUDataset:
    return build_gru_dataset(sequences, identity, target_name)


def chronological_gru_split(
    dataset: GRUDataset, test_fraction: float = 0.2
) -> tuple[GRUDataset, GRUDataset]:
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1.")
    if len(dataset.sequences) < 2:
        raise ValueError("at least two sequences are required for a chronological split.")
    cut = max(1, min(len(dataset.sequences) - 1, int(len(dataset.sequences) * (1 - test_fraction))))
    train = GRUDataset(dataset.sequences[:cut], dataset.identity + ":train", dataset.target_name)
    test = GRUDataset(dataset.sequences[cut:], dataset.identity + ":test", dataset.target_name)
    return train, test


def _windows(dataset: GRUDataset, sequence_length: int) -> tuple[np.ndarray, np.ndarray]:
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


class GRUClassifier:
    """Small deterministic categorical GRU implemented with NumPy."""

    def __init__(self, config: GRUConfig = GRUConfig()) -> None:
        validate_gru_config(config)
        self.config = config
        self.classes_ = tuple(range(config.alphabet_size))
        self._fitted = False
        self._history: GRUTrainingHistory | None = None
        self._initialize_parameters()

    def _initialize_parameters(self) -> None:
        rng = np.random.default_rng(self.config.seed)
        scale = 1.0 / math.sqrt(self.config.hidden_size)
        h = self.config.hidden_size
        a = self.config.alphabet_size
        self.W = rng.normal(0.0, scale, size=(3 * h, a))
        self.U = rng.normal(0.0, scale, size=(3 * h, h))
        self.b = np.zeros(3 * h, dtype=float)
        self.V = rng.normal(0.0, scale, size=(a, h))
        self.c = np.zeros(a, dtype=float)

    @property
    def fitted(self) -> bool:
        return self._fitted

    @property
    def training_history(self) -> GRUTrainingHistory | None:
        return self._history

    def _forward(self, window: Sequence[int], training: bool = False):
        hsize = self.config.hidden_size
        hidden = np.zeros(hsize, dtype=float)
        cache = []
        for value in window:
            x = np.zeros(self.config.alphabet_size, dtype=float)
            x[int(value)] = 1.0
            z = _sigmoid(self.W[:hsize] @ x + self.U[:hsize] @ hidden + self.b[:hsize])
            r = _sigmoid(self.W[hsize:2*hsize] @ x + self.U[hsize:2*hsize] @ hidden + self.b[hsize:2*hsize])
            n = np.tanh(self.W[2*hsize:] @ x + self.U[2*hsize:] @ (r * hidden) + self.b[2*hsize:])
            prev_hidden = hidden.copy()
            hidden = (1.0 - z) * hidden + z * n
            if training:
                cache.append((x, prev_hidden, hidden.copy(), z, r, n))
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
        hsize = self.config.hidden_size
        dW = np.zeros_like(self.W)
        dU = np.zeros_like(self.U)
        db = np.zeros_like(self.b)
        for t in range(len(cache) - 1, -1, -1):
            x, prev_hidden, hidden, z, r, n = cache[t]
            dz = dh * (n - prev_hidden)
            dn = dh * z
            dprev = dh * (1.0 - z)
            dn_pre = dn * (1.0 - n * n)
            dW[2*hsize:] += np.outer(dn_pre, x)
            dU[2*hsize:] += np.outer(dn_pre, r * prev_hidden)
            db[2*hsize:] += dn_pre
            dr_prev = self.U[2*hsize:].T @ dn_pre
            dr = dr_prev * prev_hidden
            dprev += dr_prev * r
            dr_pre = dr * r * (1.0 - r)
            dW[hsize:2*hsize] += np.outer(dr_pre, x)
            dU[hsize:2*hsize] += np.outer(dr_pre, prev_hidden)
            db[hsize:2*hsize] += dr_pre
            dz_pre = dz * z * (1.0 - z)
            dW[:hsize] += np.outer(dz_pre, x)
            dU[:hsize] += np.outer(dz_pre, prev_hidden)
            db[:hsize] += dz_pre
            dprev += self.U[:hsize].T @ dz_pre
            dprev += self.U[hsize:2*hsize].T @ dr_pre
            dh = dprev
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

    def fit(self, dataset: GRUDataset) -> "GRUClassifier":
        validate_gru_dataset(dataset, self.config)
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
        self._history = GRUTrainingHistory(tuple(losses), len(losses), best_loss)
        return self

    def _state(self) -> tuple[np.ndarray, ...]:
        return tuple(np.array(v, copy=True) for v in (self.W, self.U, self.b, self.V, self.c))

    def _restore_state(self, state: tuple[np.ndarray, ...]) -> None:
        self.W, self.U, self.b, self.V, self.c = tuple(np.array(v, copy=True) for v in state)

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise ValueError("GRU model must be fitted.")

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

    def evaluate(self, dataset: GRUDataset) -> GRUMetrics:
        validate_gru_dataset(dataset, self.config)
        x, y = _windows(dataset, self.config.sequence_length)
        probabilities = self.predict_proba(x.tolist())
        losses = [-math.log(max(row[int(target)], 1e-15)) for row, target in zip(probabilities, y)]
        correct = sum(int(max(range(self.config.alphabet_size), key=lambda d: (row[d], -d)) == int(target))
                      for row, target in zip(probabilities, y))
        return GRUMetrics(float(np.mean(losses)), correct / len(y), len(y))

    def log_likelihood(self, dataset: GRUDataset) -> float:
        metrics = self.evaluate(dataset)
        return -metrics.log_loss * metrics.observations


def build_position_gru_models(
    datasets: Mapping[str, GRUDataset],
    config: GRUConfig = GRUConfig(),
) -> PositionGRUModels:
    validate_gru_config(config)
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    models = tuple((name, GRUClassifier(config).fit(datasets[name])) for name in sorted(datasets))
    return PositionGRUModels(models)


def get_position_gru_model(models: PositionGRUModels, position: str) -> GRUClassifier:
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")


def compare_with_baseline(metrics: GRUMetrics, baseline_log_loss: float) -> GRUBaselineComparison:
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return GRUBaselineComparison(metrics.log_loss, float(baseline_log_loss), metrics.log_loss - baseline_log_loss)


def build_gru_artifact(model: GRUClassifier, dataset: GRUDataset) -> GRUArtifact:
    model._require_fitted()
    validate_gru_dataset(dataset, model.config)
    payload = {
        "model_kind": MODEL_KIND,
        "model_version": GRU_VERSION,
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
    identity = "gru-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return GRUArtifact(
        MODEL_KIND, GRU_VERSION, model.config.sequence_length, model.config.hidden_size,
        dataset.identity, dataset.target_name, identity,
    )


def validate_gru_model(model: GRUClassifier) -> GRUValidationResult:
    if not isinstance(model, GRUClassifier):
        return GRUValidationResult(INVALID, ("INVALID_MODEL_TYPE",))
    issues: list[str] = []
    if not model.fitted:
        issues.append("MODEL_NOT_FITTED")
    expected = {
        "W": (3 * model.config.hidden_size, model.config.alphabet_size),
        "U": (3 * model.config.hidden_size, model.config.hidden_size),
        "b": (3 * model.config.hidden_size,),
        "V": (model.config.alphabet_size, model.config.hidden_size),
        "c": (model.config.alphabet_size,),
    }
    for name, shape in expected.items():
        if getattr(model, name).shape != shape:
            issues.append(f"INVALID_{name.upper()}_SHAPE")
        if not np.isfinite(getattr(model, name)).all():
            issues.append(f"NONFINITE_{name.upper()}")
    return GRUValidationResult(VALID if not issues else INVALID, tuple(issues))


def save_gru_model(model: GRUClassifier, path: str | Path) -> Path:
    model._require_fitted()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_gru_model(path: str | Path) -> GRUClassifier:
    model = joblib.load(Path(path))
    if not isinstance(model, GRUClassifier):
        raise ValueError("Stored artifact is not an GRUClassifier.")
    return model


def reproduce_gru_artifact(first: GRUArtifact, second: GRUArtifact) -> GRUReproducibilityResult:
    if not isinstance(first, GRUArtifact) or not isinstance(second, GRUArtifact):
        raise TypeError("Both artifacts must be GRUArtifact instances.")
    return GRUReproducibilityResult(
        first.artifact_identity == second.artifact_identity,
        first.artifact_identity,
        second.artifact_identity,
    )


def validate_gru_artifact_lineage(
    artifact: GRUArtifact, dataset: GRUDataset, model: GRUClassifier
) -> None:
    if artifact.model_kind != MODEL_KIND or artifact.model_version != GRU_VERSION:
        raise ValueError("GRU artifact version lineage is invalid.")
    if artifact.dataset_identity != dataset.identity:
        raise ValueError("GRU artifact dataset identity does not match.")
    if artifact.sequence_length != model.config.sequence_length or artifact.hidden_size != model.config.hidden_size:
        raise ValueError("GRU artifact configuration does not match model.")


__all__ = [
    "VALID", "INVALID", "GRU_VERSION", "MODEL_KIND", "GRUConfig",
    "GRUDataset", "GRUMetrics", "GRUTrainingHistory", "GRUArtifact",
    "GRUValidationResult", "GRUBaselineComparison", "GRUReproducibilityResult",
    "PositionGRUModels", "GRUClassifier", "validate_gru_config",
    "build_gru_dataset", "validate_gru_dataset",
    "prepare_gru_dataset_from_sequences", "chronological_gru_split",
    "build_position_gru_models", "get_position_gru_model",
    "compare_with_baseline", "build_gru_artifact", "validate_gru_model",
    "save_gru_model", "load_gru_model", "reproduce_gru_artifact",
    "validate_gru_artifact_lineage",
]
