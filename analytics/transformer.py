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
TRANSFORMER_VERSION = "32.0.0"
MODEL_KIND = "transformer"


@dataclass(frozen=True)
class TransformerConfig:
    sequence_length: int = 5
    d_model: int = 16
    num_heads: int = 2
    feed_forward_size: int = 32
    learning_rate: float = 0.01
    epochs: int = 20
    batch_size: int = 8
    smoothing: float = 1e-6
    seed: int = 32
    alphabet_size: int = 10
    gradient_clip: float = 5.0
    patience: int = 5


@dataclass(frozen=True)
class TransformerDataset:
    sequences: tuple[tuple[int, ...], ...]
    identity: str
    target_name: str = "target"


@dataclass(frozen=True)
class TransformerMetrics:
    log_loss: float
    accuracy: float
    observations: int


@dataclass(frozen=True)
class TransformerTrainingHistory:
    losses: tuple[float, ...]
    epochs_completed: int
    best_loss: float


@dataclass(frozen=True)
class TransformerArtifact:
    model_kind: str
    model_version: str
    sequence_length: int
    d_model: int
    num_heads: int
    dataset_identity: str
    target_name: str
    artifact_identity: str


@dataclass(frozen=True)
class TransformerValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


@dataclass(frozen=True)
class TransformerBaselineComparison:
    transformer_log_loss: float
    baseline_log_loss: float
    difference: float


@dataclass(frozen=True)
class TransformerReproducibilityResult:
    identical: bool
    first_identity: str
    second_identity: str


@dataclass(frozen=True)
class PositionTransformerModels:
    models: tuple[tuple[str, "TransformerClassifier"], ...]


def validate_transformer_config(config: TransformerConfig) -> None:
    if not isinstance(config, TransformerConfig):
        raise TypeError("config must be a TransformerConfig.")
    ints = ("sequence_length", "d_model", "num_heads", "feed_forward_size",
            "epochs", "batch_size", "patience")
    for name in ints:
        value = getattr(config, name)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")
    if config.d_model % config.num_heads:
        raise ValueError("d_model must be divisible by num_heads.")
    if config.learning_rate <= 0 or not math.isfinite(config.learning_rate):
        raise ValueError("learning_rate must be positive and finite.")
    if config.smoothing < 0 or not math.isfinite(config.smoothing):
        raise ValueError("smoothing must be non-negative and finite.")
    if config.alphabet_size != 10:
        raise ValueError("alphabet_size must be exactly 10 for NeuroLytics digit models.")
    if config.gradient_clip <= 0 or not math.isfinite(config.gradient_clip):
        raise ValueError("gradient_clip must be positive and finite.")


def _validate_sequence(sequence: Sequence[int], alphabet_size: int = 10) -> tuple[int, ...]:
    values = tuple(sequence)
    if not values:
        raise ValueError("sequence cannot be empty.")
    if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) for v in values):
        raise ValueError("sequence values must be integers.")
    values = tuple(int(v) for v in values)
    if any(v < 0 or v >= alphabet_size for v in values):
        raise ValueError("sequence values must be valid digits 0-9.")
    return values


def build_transformer_dataset(
    sequences: Sequence[Sequence[int]], identity: str, target_name: str = "target"
) -> TransformerDataset:
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("identity must be non-empty.")
    if not isinstance(target_name, str) or not target_name.strip():
        raise ValueError("target_name must be non-empty.")
    rows = tuple(_validate_sequence(row) for row in sequences)
    if not rows:
        raise ValueError("at least one sequence is required.")
    return TransformerDataset(rows, identity, target_name)


def validate_transformer_dataset(
    dataset: TransformerDataset, config: TransformerConfig | None = None
) -> None:
    if not isinstance(dataset, TransformerDataset):
        raise TypeError("dataset must be a TransformerDataset.")
    cfg = config or TransformerConfig()
    validate_transformer_config(cfg)
    if not dataset.sequences:
        raise ValueError("dataset must contain sequences.")
    for sequence in dataset.sequences:
        if len(_validate_sequence(sequence, cfg.alphabet_size)) <= cfg.sequence_length:
            raise ValueError("every sequence must contain more observations than sequence_length.")


def prepare_transformer_dataset_from_sequences(
    sequences: Sequence[Sequence[int]], identity: str, target_name: str = "target"
) -> TransformerDataset:
    return build_transformer_dataset(sequences, identity, target_name)


def chronological_transformer_split(
    dataset: TransformerDataset, test_fraction: float = 0.2
) -> tuple[TransformerDataset, TransformerDataset]:
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1.")
    if len(dataset.sequences) < 2:
        raise ValueError("at least two sequences are required for a chronological split.")
    cut = max(1, min(len(dataset.sequences) - 1,
                     int(len(dataset.sequences) * (1 - test_fraction))))
    return (
        TransformerDataset(dataset.sequences[:cut], dataset.identity + ":train", dataset.target_name),
        TransformerDataset(dataset.sequences[cut:], dataset.identity + ":test", dataset.target_name),
    )


def _windows(dataset: TransformerDataset, sequence_length: int) -> tuple[np.ndarray, np.ndarray]:
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


def _layer_norm(x: np.ndarray, eps: float = 1e-5):
    mean = np.mean(x, axis=-1, keepdims=True)
    centered = x - mean
    variance = np.mean(centered * centered, axis=-1, keepdims=True)
    inv = 1.0 / np.sqrt(variance + eps)
    normalized = centered * inv
    return normalized, (normalized, inv, x.shape)


def _layer_norm_backward(dy: np.ndarray, cache) -> np.ndarray:
    normalized, inv, shape = cache
    n = shape[-1]
    return (inv / n) * (
        n * dy
        - np.sum(dy, axis=-1, keepdims=True)
        - normalized * np.sum(dy * normalized, axis=-1, keepdims=True)
    )


def _positional_encoding(length: int, d_model: int) -> np.ndarray:
    result = np.zeros((length, d_model), dtype=float)
    for position in range(length):
        for index in range(0, d_model, 2):
            angle = position / (10000.0 ** (index / d_model))
            result[position, index] = math.sin(angle)
            if index + 1 < d_model:
                result[position, index + 1] = math.cos(angle)
    return result


class TransformerClassifier:
    """Deterministic NumPy Transformer encoder for categorical digit sequences."""

    def __init__(self, config: TransformerConfig = TransformerConfig()) -> None:
        validate_transformer_config(config)
        self.config = config
        self.classes_ = tuple(range(config.alphabet_size))
        self._fitted = False
        self._history: TransformerTrainingHistory | None = None
        self._initialize_parameters()

    def _initialize_parameters(self) -> None:
        rng = np.random.default_rng(self.config.seed)
        d = self.config.d_model
        a = self.config.alphabet_size
        f = self.config.feed_forward_size
        scale = 1.0 / math.sqrt(d)
        self.embedding = rng.normal(0.0, scale, size=(a, d))
        self.Wq = rng.normal(0.0, scale, size=(d, d))
        self.Wk = rng.normal(0.0, scale, size=(d, d))
        self.Wv = rng.normal(0.0, scale, size=(d, d))
        self.Wo = rng.normal(0.0, scale, size=(d, d))
        self.W1 = rng.normal(0.0, scale, size=(d, f))
        self.b1 = np.zeros(f)
        self.W2 = rng.normal(0.0, scale, size=(f, d))
        self.b2 = np.zeros(d)
        self.output = rng.normal(0.0, scale, size=(a, d))
        self.output_bias = np.zeros(a)
        self.positional = _positional_encoding(self.config.sequence_length, d)


    @property
    def fitted(self) -> bool:
        return self._fitted

    @property
    def training_history(self) -> TransformerTrainingHistory | None:
        return self._history

    def _forward(self, window: Sequence[int], training: bool = False):
        values = _validate_sequence(window, self.config.alphabet_size)
        if len(values) != self.config.sequence_length:
            raise ValueError("window length must equal sequence_length.")
        d = self.config.d_model
        heads = self.config.num_heads
        head_dim = d // heads
        x = self.embedding[list(values)] + self.positional
        q = x @ self.Wq
        k = x @ self.Wk
        v = x @ self.Wv
        qh = q.reshape(len(values), heads, head_dim).transpose(1, 0, 2)
        kh = k.reshape(len(values), heads, head_dim).transpose(1, 0, 2)
        vh = v.reshape(len(values), heads, head_dim).transpose(1, 0, 2)
        scores = np.matmul(qh, kh.transpose(0, 2, 1)) / math.sqrt(head_dim)
        weights = np.empty_like(scores)
        contexts = np.empty_like(vh)
        for head in range(heads):
            for row in range(len(values)):
                weights[head, row] = _softmax(scores[head, row])
            contexts[head] = weights[head] @ vh[head]
        context = contexts.transpose(1, 0, 2).reshape(len(values), d)
        attn_linear = context @ self.Wo
        residual1 = x + attn_linear
        norm1, norm1_cache = _layer_norm(residual1)
        ff_pre = norm1 @ self.W1 + self.b1
        ff_act = np.maximum(ff_pre, 0.0)
        ff_out = ff_act @ self.W2 + self.b2
        residual2 = norm1 + ff_out
        norm2, norm2_cache = _layer_norm(residual2)
        final = norm2[-1]
        logits = self.output @ final + self.output_bias
        probabilities = _softmax(logits)
        cache = (
            values, x, qh, kh, vh, weights, contexts, norm1, norm1_cache,
            ff_pre, ff_act, norm2, norm2_cache, final
        )
        return probabilities, cache
    def _zero_grads(self) -> dict[str, np.ndarray]:
        names = (
            "embedding", "Wq", "Wk", "Wv", "Wo",
            "W1", "b1", "W2", "b2", "output", "output_bias"
        )
        return {name: np.zeros_like(getattr(self, name)) for name in names}

    def _backward(self, cache, target: int, probabilities: np.ndarray):
        (
            values, x, qh, kh, vh, weights, contexts, norm1,
            norm1_cache, ff_pre, ff_act, norm2, norm2_cache, final
        ) = cache
        grads = self._zero_grads()
        dlogits = probabilities.copy()
        dlogits[target] -= 1.0
        grads["output"] += np.outer(dlogits, final)
        grads["output_bias"] += dlogits

        dnorm2 = np.zeros_like(norm2)
        dnorm2[-1] = self.output.T @ dlogits
        dresidual2 = _layer_norm_backward(dnorm2, norm2_cache)

        dnorm1 = dresidual2.copy()
        dff = dresidual2
        grads["W2"] += ff_act.T @ dff
        grads["b2"] += np.sum(dff, axis=0)
        dff_act = dff @ self.W2.T
        dff_pre = dff_act * (ff_pre > 0.0)
        grads["W1"] += norm1.T @ dff_pre
        grads["b1"] += np.sum(dff_pre, axis=0)
        dnorm1 += dff_pre @ self.W1.T

        dresidual1 = _layer_norm_backward(dnorm1, norm1_cache)
        dx = dresidual1
        dattn = dresidual1 @ self.Wo.T
        flat_context = contexts.transpose(1, 0, 2).reshape(len(values), -1)
        grads["Wo"] += flat_context.T @ dattn
        dcontexts = dattn.reshape(
            len(values), self.config.num_heads, -1
        ).transpose(1, 0, 2)

        dweights = np.zeros_like(weights)
        dvh = np.zeros_like(vh)
        for head in range(self.config.num_heads):
            dweights[head] = dcontexts[head] @ vh[head].T
            dvh[head] = weights[head].T @ dcontexts[head]

        dscores = np.zeros_like(weights)
        for head in range(self.config.num_heads):
            for row in range(len(values)):
                w = weights[head, row]
                dw = dweights[head, row]
                dscores[head, row] = w * (
                    dw - np.sum(dw * w)
                )

        scale = 1.0 / math.sqrt(
            self.config.d_model // self.config.num_heads
        )
        dqh = np.matmul(dscores, kh) * scale
        dkh = np.matmul(
            dscores.transpose(0, 2, 1), qh
        ) * scale
        dq = dqh.transpose(1, 0, 2).reshape(
            len(values), self.config.d_model
        )
        dk = dkh.transpose(1, 0, 2).reshape(
            len(values), self.config.d_model
        )
        dv = dvh.transpose(1, 0, 2).reshape(
            len(values), self.config.d_model
        )
        grads["Wq"] += x.T @ dq
        grads["Wk"] += x.T @ dk
        grads["Wv"] += x.T @ dv
        dx += dq @ self.Wq.T
        dx += dk @ self.Wk.T
        dx += dv @ self.Wv.T
        for index, value in enumerate(values):
            grads["embedding"][value] += dx[index]
        return grads

    def _train_window(self, window: Sequence[int], target: int) -> float:
        probabilities, cache = self._forward(window, training=True)
        loss = -math.log(
            max(float(probabilities[target]), self.config.smoothing or 1e-15)
        )
        grads = self._backward(cache, target, probabilities)
        norm = math.sqrt(
            sum(float(np.sum(g * g)) for g in grads.values())
        )
        if norm > self.config.gradient_clip:
            factor = self.config.gradient_clip / norm
            grads = {
                name: value * factor
                for name, value in grads.items()
            }
        for name, gradient in grads.items():
            setattr(
                self,
                name,
                getattr(self, name) - self.config.learning_rate * gradient,
            )
        return float(loss)

    def fit(self, dataset: TransformerDataset) -> "TransformerClassifier":
        validate_transformer_dataset(dataset, self.config)
        x, y = _windows(dataset, self.config.sequence_length)
        losses: list[float] = []
        best_loss = float("inf")
        best_state = None
        stale = 0
        for _epoch in range(self.config.epochs):
            epoch_losses = []
            for start in range(0, len(x), self.config.batch_size):
                batch_x = x[start:start + self.config.batch_size]
                batch_y = y[start:start + self.config.batch_size]
                for window, target in zip(batch_x, batch_y):
                    epoch_losses.append(
                        self._train_window(window, int(target))
                    )
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
        self._history = TransformerTrainingHistory(
            tuple(losses), len(losses), best_loss
        )
        return self

    def _state(self) -> tuple[np.ndarray, ...]:
        names = (
            "embedding", "Wq", "Wk", "Wv", "Wo",
            "W1", "b1", "W2", "b2", "output", "output_bias"
        )
        return tuple(
            np.array(getattr(self, name), copy=True)
            for name in names
        )

    def _restore_state(self, state: tuple[np.ndarray, ...]) -> None:
        names = (
            "embedding", "Wq", "Wk", "Wv", "Wo",
            "W1", "b1", "W2", "b2", "output", "output_bias"
        )
        for name, value in zip(names, state):
            setattr(self, name, np.array(value, copy=True))

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise ValueError("Transformer model must be fitted.")

    def predict_proba(
        self, windows: Sequence[Sequence[int]]
    ) -> tuple[tuple[float, ...], ...]:
        self._require_fitted()
        return tuple(
            tuple(float(v) for v in self._forward(window)[0])
            for window in windows
        )

    def predict_next(
        self, window: Sequence[int], top_k: int = 1
    ) -> tuple[int, ...]:
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")
        probabilities = self.predict_proba([window])[0]
        ranked = sorted(
            range(self.config.alphabet_size),
            key=lambda digit: (-probabilities[digit], digit),
        )
        return tuple(
            ranked[:min(top_k, self.config.alphabet_size)]
        )

    def evaluate(self, dataset: TransformerDataset) -> TransformerMetrics:
        validate_transformer_dataset(dataset, self.config)
        x, y = _windows(dataset, self.config.sequence_length)
        probabilities = self.predict_proba(x.tolist())
        losses = [
            -math.log(max(row[int(target)], 1e-15))
            for row, target in zip(probabilities, y)
        ]
        correct = sum(
            int(
                max(
                    range(self.config.alphabet_size),
                    key=lambda digit: (row[digit], -digit),
                ) == int(target)
            )
            for row, target in zip(probabilities, y)
        )
        return TransformerMetrics(
            float(np.mean(losses)),
            correct / len(y),
            len(y),
        )

    def log_likelihood(self, dataset: TransformerDataset) -> float:
        metrics = self.evaluate(dataset)
        return -metrics.log_loss * metrics.observations


def build_position_transformer_models(
    datasets: Mapping[str, TransformerDataset],
    config: TransformerConfig = TransformerConfig(),
) -> PositionTransformerModels:
    validate_transformer_config(config)
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    models = tuple(
        (name, TransformerClassifier(config).fit(datasets[name]))
        for name in sorted(datasets)
    )
    return PositionTransformerModels(models)


def get_position_transformer_model(
    models: PositionTransformerModels, position: str
) -> TransformerClassifier:
    for name, model in models.models:
        if name == position:
            return model
    raise ValueError(f"Position model not found: {position}")


def compare_with_baseline(
    metrics: TransformerMetrics, baseline_log_loss: float
) -> TransformerBaselineComparison:
    if baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    return TransformerBaselineComparison(
        metrics.log_loss,
        float(baseline_log_loss),
        metrics.log_loss - baseline_log_loss,
    )

def build_transformer_artifact(
    model: TransformerClassifier, dataset: TransformerDataset
) -> TransformerArtifact:
    model._require_fitted()
    validate_transformer_dataset(dataset, model.config)
    payload = {
        "model_kind": MODEL_KIND,
        "model_version": TRANSFORMER_VERSION,
        "sequence_length": model.config.sequence_length,
        "d_model": model.config.d_model,
        "num_heads": model.config.num_heads,
        "feed_forward_size": model.config.feed_forward_size,
        "learning_rate": model.config.learning_rate,
        "epochs": model.config.epochs,
        "batch_size": model.config.batch_size,
        "seed": model.config.seed,
        "dataset_identity": dataset.identity,
        "target_name": dataset.target_name,
        "parameters": [
            np.asarray(value).round(12).tolist()
            for value in model._state()
        ],
    }
    identity = "transformer-" + hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return TransformerArtifact(
        MODEL_KIND,
        TRANSFORMER_VERSION,
        model.config.sequence_length,
        model.config.d_model,
        model.config.num_heads,
        dataset.identity,
        dataset.target_name,
        identity,
    )


def validate_transformer_model(
    model: TransformerClassifier,
) -> TransformerValidationResult:
    if not isinstance(model, TransformerClassifier):
        return TransformerValidationResult(
            INVALID, ("INVALID_MODEL_TYPE",)
        )
    issues: list[str] = []
    if not model.fitted:
        issues.append("MODEL_NOT_FITTED")
    expected = {
        "embedding": (
            model.config.alphabet_size,
            model.config.d_model,
        ),
        "Wq": (model.config.d_model, model.config.d_model),
        "Wk": (model.config.d_model, model.config.d_model),
        "Wv": (model.config.d_model, model.config.d_model),
        "Wo": (model.config.d_model, model.config.d_model),
        "W1": (
            model.config.d_model,
            model.config.feed_forward_size,
        ),
        "b1": (model.config.feed_forward_size,),
        "W2": (
            model.config.feed_forward_size,
            model.config.d_model,
        ),
        "b2": (model.config.d_model,),
        "output": (
            model.config.alphabet_size,
            model.config.d_model,
        ),
        "output_bias": (model.config.alphabet_size,),
    }
    for name, shape in expected.items():
        value = getattr(model, name)
        if value.shape != shape:
            issues.append(f"INVALID_{name.upper()}_SHAPE")
        if not np.isfinite(value).all():
            issues.append(f"NONFINITE_{name.upper()}")
    if not np.isfinite(model.positional).all():
        issues.append("NONFINITE_POSITIONAL_ENCODING")
    return TransformerValidationResult(
        VALID if not issues else INVALID,
        tuple(issues),
    )


def save_transformer_model(
    model: TransformerClassifier, path: str | Path
) -> Path:
    model._require_fitted()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, target)
    return target


def load_transformer_model(
    path: str | Path,
) -> TransformerClassifier:
    model = joblib.load(Path(path))
    if not isinstance(model, TransformerClassifier):
        raise ValueError(
            "Stored artifact is not a TransformerClassifier."
        )
    return model


def reproduce_transformer_artifact(
    first: TransformerArtifact,
    second: TransformerArtifact,
) -> TransformerReproducibilityResult:
    if not isinstance(first, TransformerArtifact) or not isinstance(
        second, TransformerArtifact
    ):
        raise TypeError(
            "Both artifacts must be TransformerArtifact instances."
        )
    return TransformerReproducibilityResult(
        first.artifact_identity == second.artifact_identity,
        first.artifact_identity,
        second.artifact_identity,
    )


def validate_transformer_artifact_lineage(
    artifact: TransformerArtifact,
    dataset: TransformerDataset,
    model: TransformerClassifier,
) -> None:
    if (
        artifact.model_kind != MODEL_KIND
        or artifact.model_version != TRANSFORMER_VERSION
    ):
        raise ValueError(
            "Transformer artifact version lineage is invalid."
        )
    if artifact.dataset_identity != dataset.identity:
        raise ValueError(
            "Transformer artifact dataset identity does not match."
        )
    if artifact.sequence_length != model.config.sequence_length:
        raise ValueError(
            "Transformer artifact sequence configuration does not match."
        )
    if (
        artifact.d_model != model.config.d_model
        or artifact.num_heads != model.config.num_heads
    ):
        raise ValueError(
            "Transformer artifact model configuration does not match."
        )


__all__ = [
    "VALID",
    "INVALID",
    "TRANSFORMER_VERSION",
    "MODEL_KIND",
    "TransformerConfig",
    "TransformerDataset",
    "TransformerMetrics",
    "TransformerTrainingHistory",
    "TransformerArtifact",
    "TransformerValidationResult",
    "TransformerBaselineComparison",
    "TransformerReproducibilityResult",
    "PositionTransformerModels",
    "TransformerClassifier",
    "validate_transformer_config",
    "build_transformer_dataset",
    "validate_transformer_dataset",
    "prepare_transformer_dataset_from_sequences",
    "chronological_transformer_split",
    "build_position_transformer_models",
    "get_position_transformer_model",
    "compare_with_baseline",
    "build_transformer_artifact",
    "validate_transformer_model",
    "save_transformer_model",
    "load_transformer_model",
    "reproduce_transformer_artifact",
    "validate_transformer_artifact_lineage",
]

