from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from analytics.gru import (
    GRU_VERSION,
    GRUConfig,
    GRUClassifier,
    build_gru_artifact,
    build_gru_dataset,
)
from analytics.hidden_markov_models import (
    HMM_VERSION,
    HMMConfig,
    HiddenMarkovModel,
    build_hmm_artifact,
    build_hmm_dataset,
)
from analytics.lstm import (
    LSTM_VERSION,
    LSTMConfig,
    LSTMClassifier,
    build_lstm_artifact,
    build_lstm_dataset,
)
from analytics.markov_models import (
    MARKOV_VERSION,
    MarkovConfig,
    MarkovChain,
    build_markov_artifact,
    build_markov_dataset,
)
from analytics.transformer import (
    TRANSFORMER_VERSION,
    TransformerConfig,
    TransformerClassifier,
    build_transformer_artifact,
    build_transformer_dataset,
)

SEQUENCE_FRAMEWORK_VERSION = "33.0.0"
MODEL_KINDS = ("gru", "hidden_markov", "lstm", "markov", "transformer")


@dataclass(frozen=True)
class SequenceFrameworkDataset:
    sequences: tuple[tuple[int, ...], ...]
    identity: str
    target_name: str = "target"


@dataclass(frozen=True)
class SequenceModelSpec:
    model_kind: str
    model_version: str
    model_class: type
    config_class: type
    dataset_builder: Callable[..., Any]
    artifact_builder: Callable[[Any, Any], Any]


@dataclass(frozen=True)
class SequenceModelRun:
    model_kind: str
    model_version: str
    dataset_identity: str
    target_name: str
    model: Any
    metrics: Any
    artifact: Any


@dataclass(frozen=True)
class SequenceModelComparison:
    model_kind: str
    model_version: str
    log_loss: float
    accuracy: float
    observations: int
    log_loss_delta: float
    accuracy_delta: float


@dataclass(frozen=True)
class SequenceFrameworkReport:
    framework_version: str
    dataset_identity: str
    target_name: str
    runs: tuple[SequenceModelRun, ...]
    comparisons: tuple[SequenceModelComparison, ...]
    framework_identity: str


def _validate_sequences(
    sequences: Sequence[Sequence[int]],
) -> tuple[tuple[int, ...], ...]:
    rows = tuple(tuple(row) for row in sequences)
    if not rows:
        raise ValueError("at least one sequence is required.")
    for row in rows:
        if not row:
            raise ValueError("sequence cannot be empty.")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in row):
            raise ValueError("sequence values must be integers.")
        if any(value < 0 or value > 9 for value in row):
            raise ValueError("sequence values must be valid digits 0-9.")
    return rows


def build_sequence_framework_dataset(
    sequences: Sequence[Sequence[int]],
    identity: str,
    target_name: str = "target",
) -> SequenceFrameworkDataset:
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("identity must be non-empty.")
    if not isinstance(target_name, str) or not target_name.strip():
        raise ValueError("target_name must be non-empty.")
    rows = _validate_sequences(sequences)
    return SequenceFrameworkDataset(rows, identity, target_name)


def validate_sequence_framework_dataset(
    dataset: SequenceFrameworkDataset,
    minimum_length: int = 2,
) -> None:
    if not isinstance(dataset, SequenceFrameworkDataset):
        raise TypeError("dataset must be a SequenceFrameworkDataset.")
    if isinstance(minimum_length, bool) or not isinstance(minimum_length, int):
        raise TypeError("minimum_length must be an integer.")
    if minimum_length < 2:
        raise ValueError("minimum_length must be at least 2.")
    if not dataset.sequences:
        raise ValueError("dataset must contain sequences.")
    _validate_sequences(dataset.sequences)
    if any(len(row) < minimum_length for row in dataset.sequences):
        raise ValueError("every sequence must satisfy minimum_length.")


def _build_spec(
    kind: str,
    version: str,
    model_class: type,
    config_class: type,
    dataset_builder: Callable[..., Any],
    artifact_builder: Callable[[Any, Any], Any],
) -> SequenceModelSpec:
    return SequenceModelSpec(
        kind, version, model_class, config_class, dataset_builder, artifact_builder
    )


def build_default_sequence_model_registry() -> "SequenceModelRegistry":
    return SequenceModelRegistry(
        (
            _build_spec("gru", GRU_VERSION, GRUClassifier, GRUConfig, build_gru_dataset, _artifact_adapter(build_gru_artifact)),
            _build_spec("hidden_markov", HMM_VERSION, HiddenMarkovModel, HMMConfig, build_hmm_dataset, _artifact_adapter(build_hmm_artifact)),
            _build_spec("lstm", LSTM_VERSION, LSTMClassifier, LSTMConfig, build_lstm_dataset, _artifact_adapter(build_lstm_artifact)),
            _build_spec("markov", MARKOV_VERSION, MarkovChain, MarkovConfig, build_markov_dataset, _artifact_adapter(build_markov_artifact)),
            _build_spec("transformer", TRANSFORMER_VERSION, TransformerClassifier, TransformerConfig, build_transformer_dataset, _artifact_adapter(build_transformer_artifact)),
        )
    )


def _artifact_adapter(builder: Callable[[Any, Any], Any]) -> Callable[[Any, Any], Any]:
    return builder


class SequenceModelRegistry:
    def __init__(self, specs: Sequence[SequenceModelSpec] = ()) -> None:
        self._specs: dict[str, SequenceModelSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: SequenceModelSpec) -> None:
        if not isinstance(spec, SequenceModelSpec):
            raise TypeError("spec must be a SequenceModelSpec.")
        if spec.model_kind not in MODEL_KINDS:
            raise ValueError(f"unsupported model kind: {spec.model_kind}")
        if spec.model_kind in self._specs:
            raise ValueError(f"model kind already registered: {spec.model_kind}")
        self._specs[spec.model_kind] = spec

    def get(self, model_kind: str) -> SequenceModelSpec:
        if model_kind not in self._specs:
            raise ValueError(f"model kind is not registered: {model_kind}")
        return self._specs[model_kind]

    def kinds(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))

    def __len__(self) -> int:
        return len(self._specs)
def _model_dataset(spec: SequenceModelSpec, dataset: SequenceFrameworkDataset) -> Any:
    return spec.dataset_builder(
        dataset.sequences,
        dataset.identity,
        dataset.target_name,
    )


def _metric_values(metrics: Any) -> tuple[float, float, int]:
    for name in ("log_loss", "accuracy", "observations"):
        if not hasattr(metrics, name):
            raise TypeError(f"model metrics do not expose {name}.")
    return float(metrics.log_loss), float(metrics.accuracy), int(metrics.observations)


def _model_config_kwargs(config: Any) -> dict[str, Any]:
    if config is None:
        return {}
    if hasattr(config, "__dataclass_fields__"):
        return {
            name: getattr(config, name)
            for name in config.__dataclass_fields__
        }
    if isinstance(config, Mapping):
        return dict(config)
    raise TypeError("config must be a dataclass instance, mapping, or None.")


def build_sequence_model(
    model_kind: str,
    config: Any = None,
    registry: SequenceModelRegistry | None = None,
) -> Any:
    active_registry = registry or build_default_sequence_model_registry()
    spec = active_registry.get(model_kind)
    if config is None:
        return spec.model_class()
    if isinstance(config, spec.config_class):
        return spec.model_class(config)
    kwargs = _model_config_kwargs(config)
    return spec.model_class(spec.config_class(**kwargs))


def prepare_model_dataset(
    model_kind: str,
    dataset: SequenceFrameworkDataset,
    registry: SequenceModelRegistry | None = None,
) -> Any:
    validate_sequence_framework_dataset(dataset)
    active_registry = registry or build_default_sequence_model_registry()
    return _model_dataset(active_registry.get(model_kind), dataset)


def train_sequence_model(
    model_kind: str,
    dataset: SequenceFrameworkDataset,
    config: Any = None,
    registry: SequenceModelRegistry | None = None,
) -> SequenceModelRun:
    validate_sequence_framework_dataset(dataset)
    active_registry = registry or build_default_sequence_model_registry()
    spec = active_registry.get(model_kind)
    model_dataset = _model_dataset(spec, dataset)
    model = build_sequence_model(model_kind, config, active_registry)
    model.fit(model_dataset)
    metrics = model.evaluate(model_dataset)
    artifact = spec.artifact_builder(model, model_dataset)
    return SequenceModelRun(
        model_kind,
        spec.model_version,
        dataset.identity,
        dataset.target_name,
        model,
        metrics,
        artifact,
    )


def train_sequence_models(
    dataset: SequenceFrameworkDataset,
    model_kinds: Sequence[str] | None = None,
    configs: Mapping[str, Any] | None = None,
    registry: SequenceModelRegistry | None = None,
) -> tuple[SequenceModelRun, ...]:
    active_registry = registry or build_default_sequence_model_registry()
    kinds = tuple(sorted(model_kinds or active_registry.kinds()))
    unknown = tuple(kind for kind in kinds if kind not in active_registry.kinds())
    if unknown:
        raise ValueError(f"unregistered model kinds: {unknown}")
    supplied = configs or {}
    return tuple(
        train_sequence_model(
            kind,
            dataset,
            supplied.get(kind),
            active_registry,
        )
        for kind in kinds
    )


def compare_sequence_model_runs(
    runs: Sequence[SequenceModelRun],
    baseline_log_loss: float | None = None,
    baseline_accuracy: float | None = None,
) -> tuple[SequenceModelComparison, ...]:
    if not runs:
        raise ValueError("at least one model run is required.")
    if baseline_log_loss is not None and baseline_log_loss < 0:
        raise ValueError("baseline_log_loss cannot be negative.")
    if baseline_accuracy is not None and not 0 <= baseline_accuracy <= 1:
        raise ValueError("baseline_accuracy must be between 0 and 1.")
    comparisons = []
    for run in runs:
        log_loss, accuracy, observations = _metric_values(run.metrics)
        comparisons.append(
            SequenceModelComparison(
                run.model_kind,
                run.model_version,
                log_loss,
                accuracy,
                observations,
                log_loss - baseline_log_loss if baseline_log_loss is not None else 0.0,
                accuracy - baseline_accuracy if baseline_accuracy is not None else 0.0,
            )
        )
    return tuple(comparisons)


def build_sequence_framework_report(
    dataset: SequenceFrameworkDataset,
    runs: Sequence[SequenceModelRun],
    baseline_log_loss: float | None = None,
    baseline_accuracy: float | None = None,
) -> SequenceFrameworkReport:
    validate_sequence_framework_dataset(dataset)
    normalized_runs = tuple(runs)
    for run in normalized_runs:
        if run.dataset_identity != dataset.identity:
            raise ValueError("all runs must reference the supplied dataset identity.")
    comparisons = compare_sequence_model_runs(
        normalized_runs,
        baseline_log_loss,
        baseline_accuracy,
    )
    payload = {
        "framework_version": SEQUENCE_FRAMEWORK_VERSION,
        "dataset_identity": dataset.identity,
        "target_name": dataset.target_name,
        "models": [
            {
                "kind": run.model_kind,
                "version": run.model_version,
                "artifact": run.artifact.artifact_identity,
            }
            for run in normalized_runs
        ],
    }
    identity = "sequence-framework-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SequenceFrameworkReport(
        SEQUENCE_FRAMEWORK_VERSION,
        dataset.identity,
        dataset.target_name,
        normalized_runs,
        comparisons,
        identity,
    )
def predict_next_sequence_model(
    run: SequenceModelRun,
    window: Sequence[int],
    top_k: int = 1,
) -> tuple[int, ...]:
    if not isinstance(run, SequenceModelRun):
        raise TypeError("run must be a SequenceModelRun.")
    if run.model_kind == "hidden_markov":
        return run.model.predict_next(window, top_k)
    return run.model.predict_next(window, top_k)


def validate_sequence_model_run(run: SequenceModelRun) -> None:
    if not isinstance(run, SequenceModelRun):
        raise TypeError("run must be a SequenceModelRun.")
    if run.model_kind not in MODEL_KINDS:
        raise ValueError("run contains an unsupported model kind.")
    if not run.model.fitted:
        raise ValueError("model run contains an unfitted model.")
    _metric_values(run.metrics)
    if not getattr(run.artifact, "artifact_identity", ""):
        raise ValueError("model run artifact identity is required.")


def validate_sequence_framework_report(
    report: SequenceFrameworkReport,
) -> None:
    if not isinstance(report, SequenceFrameworkReport):
        raise TypeError("report must be a SequenceFrameworkReport.")
    if report.framework_version != SEQUENCE_FRAMEWORK_VERSION:
        raise ValueError("framework version is invalid.")
    if not report.dataset_identity:
        raise ValueError("dataset identity is required.")
    for run in report.runs:
        validate_sequence_model_run(run)
        if run.dataset_identity != report.dataset_identity:
            raise ValueError("run dataset identity does not match report.")
    if len(report.runs) != len(report.comparisons):
        raise ValueError("runs and comparisons must have equal length.")
    if not report.framework_identity.startswith("sequence-framework-"):
        raise ValueError("framework identity is invalid.")


def build_position_sequence_models(
    datasets: Mapping[str, SequenceFrameworkDataset],
    model_kind: str,
    config: Any = None,
    registry: SequenceModelRegistry | None = None,
) -> tuple[tuple[str, SequenceModelRun], ...]:
    if not isinstance(datasets, Mapping) or not datasets:
        raise ValueError("datasets must be a non-empty mapping.")
    return tuple(
        (
            position,
            train_sequence_model(model_kind, datasets[position], config, registry),
        )
        for position in sorted(datasets)
    )


def get_position_sequence_model(
    models: Sequence[tuple[str, SequenceModelRun]],
    position: str,
) -> SequenceModelRun:
    for name, run in models:
        if name == position:
            return run
    raise ValueError(f"Position model not found: {position}")


def framework_model_versions(
    registry: SequenceModelRegistry | None = None,
) -> tuple[tuple[str, str], ...]:
    active_registry = registry or build_default_sequence_model_registry()
    return tuple(
        (kind, active_registry.get(kind).model_version)
        for kind in active_registry.kinds()
    )


__all__ = [
    "SEQUENCE_FRAMEWORK_VERSION",
    "MODEL_KINDS",
    "SequenceFrameworkDataset",
    "SequenceModelSpec",
    "SequenceModelRun",
    "SequenceModelComparison",
    "SequenceFrameworkReport",
    "SequenceModelRegistry",
    "build_default_sequence_model_registry",
    "build_sequence_framework_dataset",
    "validate_sequence_framework_dataset",
    "build_sequence_model",
    "prepare_model_dataset",
    "train_sequence_model",
    "train_sequence_models",
    "compare_sequence_model_runs",
    "build_sequence_framework_report",
    "predict_next_sequence_model",
    "validate_sequence_model_run",
    "validate_sequence_framework_report",
    "build_position_sequence_models",
    "get_position_sequence_model",
    "framework_model_versions",
]
