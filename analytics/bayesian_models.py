from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import comb, sqrt
from typing import Iterable

from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)

VALID = "VALID"
INVALID = "INVALID"
BAYESIAN_VERSION = "bayesian-v1"
MODEL_KIND = "conjugate-dirichlet-beta"

@dataclass(frozen=True)
class BayesianPrior:
    concentration: tuple[int, ...]
    version: str = BAYESIAN_VERSION

@dataclass(frozen=True)
class BayesianLikelihood:
    counts: tuple[int, ...]
    total: int

@dataclass(frozen=True)
class BayesianPosterior:
    concentration: tuple[int, ...]
    total: int
    version: str = BAYESIAN_VERSION

@dataclass(frozen=True)
class BayesianPositionPosterior:
    position: str
    posterior: BayesianPosterior

@dataclass(frozen=True)
class BayesianConditionalPosterior:
    condition_position: str
    target_position: str
    condition_digit: int
    posterior: BayesianPosterior

@dataclass(frozen=True)
class BayesianPredictiveDistribution:
    probabilities: tuple[float, ...]
    sample_size: int
    version: str = BAYESIAN_VERSION

@dataclass(frozen=True)
class BayesianCredibleInterval:
    lower: float
    upper: float
    level: float

@dataclass(frozen=True)
class BayesianValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

@dataclass(frozen=True)
class BayesianBaselineComparison:
    position: str
    max_probability_change: float
    changed: bool

@dataclass(frozen=True)
class BayesianArtifact:
    model_kind: str
    bayesian_version: str
    market_id: int
    baseline_version: str
    dataset_identity: str
    canonical_payload: str

@dataclass(frozen=True)
class BayesianReproducibilityResult:
    identical: bool
    first_payload: str
    second_payload: str

def _validate_digit_counts(counts: tuple[int, ...]) -> None:
    if not isinstance(counts, tuple) or len(counts) != 10:
        raise ValueError("counts must be a tuple containing exactly 10 values.")
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in counts):
        raise ValueError("counts must contain non-negative integers.")

def build_uniform_prior(concentration: int = 1) -> BayesianPrior:
    if isinstance(concentration, bool) or not isinstance(concentration, int):
        raise TypeError("concentration must be an integer.")
    if concentration <= 0:
        raise ValueError("concentration must be positive.")
    return BayesianPrior((concentration,) * 10)

def build_prior_from_probabilities(
    probabilities: tuple[float, ...],
    concentration: int = 10,
) -> BayesianPrior:
    if len(probabilities) != 10:
        raise ValueError("probabilities must contain 10 values.")
    if concentration <= 0:
        raise ValueError("concentration must be positive.")
    if any(p < 0.0 or p > 1.0 for p in probabilities):
        raise ValueError("probabilities must be between 0 and 1.")
    total = sum(probabilities)
    if abs(total - 1.0) > 1e-9:
        raise ValueError("probabilities must sum to 1.")
    raw = [max(1, round(p * concentration)) for p in probabilities]
    return BayesianPrior(tuple(raw))

def build_likelihood(counts: tuple[int, ...]) -> BayesianLikelihood:
    _validate_digit_counts(counts)
    return BayesianLikelihood(counts=counts, total=sum(counts))

def update_posterior(
    prior: BayesianPrior,
    likelihood: BayesianLikelihood,
) -> BayesianPosterior:
    if not isinstance(prior, BayesianPrior):
        raise TypeError("prior must be a BayesianPrior.")
    _validate_digit_counts(prior.concentration)
    if not isinstance(likelihood, BayesianLikelihood):
        raise TypeError("likelihood must be a BayesianLikelihood.")
    _validate_digit_counts(likelihood.counts)
    concentration = tuple(
        a + n for a, n in zip(prior.concentration, likelihood.counts)
    )
    return BayesianPosterior(
        concentration=concentration,
        total=sum(concentration),
    )

def _counts_for_position(
    dataset: StatisticalBaselineDataset,
    position: str,
) -> tuple[int, ...]:
    counts = [0] * 10
    for observation in dataset.observations:
        if observation.column_name == position:
            counts[observation.value] += 1
    return tuple(counts)

def build_bayesian_position_model(
    dataset: StatisticalBaselineDataset,
    prior: BayesianPrior | None = None,
) -> tuple[BayesianPositionPosterior, ...]:
    validate_statistical_baseline_dataset(dataset)
    prior = prior or build_uniform_prior()
    return tuple(
        BayesianPositionPosterior(
            position=position,
            posterior=update_posterior(
                prior,
                build_likelihood(_counts_for_position(dataset, position)),
            ),
        )
        for position in dataset.columns
    )

def build_bayesian_conditional_model(
    dataset: StatisticalBaselineDataset,
    condition_position: str,
    target_position: str,
    prior: BayesianPrior | None = None,
) -> tuple[BayesianConditionalPosterior, ...]:
    validate_statistical_baseline_dataset(dataset)
    if condition_position == target_position:
        raise ValueError("Condition and target positions must differ.")
    if condition_position not in dataset.columns or target_position not in dataset.columns:
        raise ValueError("Condition and target positions must be declared.")
    prior = prior or build_uniform_prior()
    rows: dict[date, dict[str, int]] = {}
    for obs in dataset.observations:
        rows.setdefault(obs.record_date, {})[obs.column_name] = obs.value
    result = []
    for condition_digit in range(10):
        counts = [0] * 10
        for row in rows.values():
            if row.get(condition_position) == condition_digit and target_position in row:
                counts[row[target_position]] += 1
        result.append(
            BayesianConditionalPosterior(
                condition_position=condition_position,
                target_position=target_position,
                condition_digit=condition_digit,
                posterior=update_posterior(
                    prior,
                    build_likelihood(tuple(counts)),
                ),
            )
        )
    return tuple(result)

def posterior_probabilities(posterior: BayesianPosterior) -> tuple[float, ...]:
    if not isinstance(posterior, BayesianPosterior):
        raise TypeError("posterior must be a BayesianPosterior.")
    if posterior.total <= 0:
        raise ValueError("posterior total must be positive.")
    return tuple(a / posterior.total for a in posterior.concentration)

def posterior_mean(posterior: BayesianPosterior, digit: int) -> float:
    if digit not in range(10):
        raise ValueError("digit must be in the range 0-9.")
    return posterior_probabilities(posterior)[digit]

def _beta_cdf(x: float, a: int, b: int) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    n = a + b - 1
    return sum(comb(n, j) * x**j * (1.0 - x)**(n - j) for j in range(a, n + 1))

def beta_quantile(probability: float, a: int, b: int, iterations: int = 80) -> float:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1.")
    if a <= 0 or b <= 0:
        raise ValueError("Beta parameters must be positive.")
    if probability == 0.0:
        return 0.0
    if probability == 1.0:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(iterations):
        mid = (low + high) / 2.0
        if _beta_cdf(mid, a, b) < probability:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0

def credible_interval(
    posterior: BayesianPosterior,
    digit: int,
    level: float = 0.95,
) -> BayesianCredibleInterval:
    if digit not in range(10):
        raise ValueError("digit must be in the range 0-9.")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be between 0 and 1.")
    a = posterior.concentration[digit]
    b = posterior.total - a
    if b <= 0:
        return BayesianCredibleInterval(1.0, 1.0, level)
    tail = (1.0 - level) / 2.0
    return BayesianCredibleInterval(
        lower=beta_quantile(tail, a, b),
        upper=beta_quantile(1.0 - tail, a, b),
        level=level,
    )

def posterior_predictive(
    posterior: BayesianPosterior,
    sample_size: int = 1,
) -> BayesianPredictiveDistribution:
    if isinstance(sample_size, bool) or not isinstance(sample_size, int) or sample_size <= 0:
        raise ValueError("sample_size must be a positive integer.")
    return BayesianPredictiveDistribution(
        probabilities=posterior_probabilities(posterior),
        sample_size=sample_size,
    )

def update_bayesian_model(
    prior: BayesianPrior,
    new_counts: tuple[int, ...],
) -> BayesianPosterior:
    return update_posterior(prior, build_likelihood(new_counts))

def compare_bayesian_baselines(
    first: tuple[BayesianPositionPosterior, ...],
    second: tuple[BayesianPositionPosterior, ...],
    tolerance: float = 1e-12,
) -> tuple[BayesianBaselineComparison, ...]:
    if tolerance < 0:
        raise ValueError("tolerance cannot be negative.")
    first_map = {item.position: item.posterior for item in first}
    second_map = {item.position: item.posterior for item in second}
    if set(first_map) != set(second_map):
        raise ValueError("Bayesian baselines must contain the same positions.")
    return tuple(
        BayesianBaselineComparison(
            position=position,
            max_probability_change=max(
                abs(a - b)
                for a, b in zip(
                    posterior_probabilities(first_map[position]),
                    posterior_probabilities(second_map[position]),
                )
            ),
            changed=max(
                abs(a - b)
                for a, b in zip(
                    posterior_probabilities(first_map[position]),
                    posterior_probabilities(second_map[position]),
                )
            ) > tolerance,
        )
        for position in sorted(first_map)
    )

def validate_bayesian_model(
    model: tuple[BayesianPositionPosterior, ...],
) -> BayesianValidationResult:
    issues = []
    previous = None
    for item in model:
        if not isinstance(item, BayesianPositionPosterior):
            issues.append("INVALID_POSITION_POSTERIOR")
            continue
        if previous is not None and item.position <= previous:
            issues.append("NON_DETERMINISTIC_POSITION_ORDER")
        previous = item.position
        try:
            _validate_digit_counts(item.posterior.concentration)
            if item.posterior.total != sum(item.posterior.concentration):
                issues.append("POSTERIOR_TOTAL_MISMATCH")
            if item.posterior.total <= 0:
                issues.append("NON_POSITIVE_POSTERIOR_TOTAL")
        except (TypeError, ValueError):
            issues.append("INVALID_POSTERIOR")
    return BayesianValidationResult(VALID if not issues else INVALID, tuple(issues))

def build_bayesian_artifact(
    model: tuple[BayesianPositionPosterior, ...],
    dataset: StatisticalBaselineDataset,
    dataset_identity: str,
) -> BayesianArtifact:
    import json
    validate_statistical_baseline_dataset(dataset)
    validation = validate_bayesian_model(model)
    if not validation.is_valid:
        raise ValueError("Cannot build an artifact from an invalid Bayesian model.")
    if not isinstance(dataset_identity, str) or not dataset_identity.strip():
        raise ValueError("dataset_identity must be non-empty.")
    payload = {
        "baseline_version": dataset.contract.baseline_version,
        "dataset_identity": dataset_identity,
        "market_id": dataset.contract.market_id,
        "model_kind": MODEL_KIND,
        "positions": [
            {"position": item.position, "concentration": list(item.posterior.concentration)}
            for item in model
        ],
        "version": BAYESIAN_VERSION,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return BayesianArtifact(
        model_kind=MODEL_KIND,
        bayesian_version=BAYESIAN_VERSION,
        market_id=dataset.contract.market_id,
        baseline_version=dataset.contract.baseline_version,
        dataset_identity=dataset_identity,
        canonical_payload=canonical,
    )

def reproduce_bayesian_artifact(
    first: BayesianArtifact,
    second: BayesianArtifact,
) -> BayesianReproducibilityResult:
    if not isinstance(first, BayesianArtifact) or not isinstance(second, BayesianArtifact):
        raise TypeError("Both artifacts must be BayesianArtifact instances.")
    return BayesianReproducibilityResult(
        identical=first.canonical_payload == second.canonical_payload,
        first_payload=first.canonical_payload,
        second_payload=second.canonical_payload,
    )

__all__ = [
    "VALID", "INVALID", "BAYESIAN_VERSION", "MODEL_KIND",
    "BayesianPrior", "BayesianLikelihood", "BayesianPosterior",
    "BayesianPositionPosterior", "BayesianConditionalPosterior",
    "BayesianPredictiveDistribution", "BayesianCredibleInterval",
    "BayesianValidationResult", "BayesianBaselineComparison",
    "BayesianArtifact", "BayesianReproducibilityResult",
    "build_uniform_prior", "build_prior_from_probabilities",
    "build_likelihood", "update_posterior", "update_bayesian_model",
    "build_bayesian_position_model", "build_bayesian_conditional_model",
    "posterior_probabilities", "posterior_mean", "beta_quantile",
    "credible_interval", "posterior_predictive", "compare_bayesian_baselines",
    "validate_bayesian_model", "build_bayesian_artifact",
    "reproduce_bayesian_artifact",
]


def prepare_bayesian_dataset(
    dataset: StatisticalBaselineDataset,
) -> StatisticalBaselineDataset:
    """Validate and return the existing Phase 18 dataset as Bayesian input."""
    validate_statistical_baseline_dataset(dataset)
    return dataset

def validate_bayesian_dataset_version_reference(
    dataset: StatisticalBaselineDataset,
    dataset_reference,
) -> None:
    """Integrate Bayesian artifacts with the existing Phase 17 dataset reference."""
    from features.versioning_contract import validate_dataset_version_reference
    validate_statistical_baseline_dataset(dataset)
    validate_dataset_version_reference(dataset_reference)
    if dataset_reference.feature_version != dataset.contract.analysis_version:
        raise ValueError(
            "Dataset reference feature_version must match the Bayesian dataset analysis_version."
        )
    if dataset_reference.dataset_version != dataset.contract.baseline_version:
        raise ValueError(
            "Dataset reference dataset_version must match the Bayesian baseline_version."
        )

def build_versioned_bayesian_artifact(
    model: tuple[BayesianPositionPosterior, ...],
    dataset: StatisticalBaselineDataset,
    dataset_reference,
) -> BayesianArtifact:
    """Build a Bayesian artifact only after Phase 17 version compatibility validation."""
    validate_bayesian_dataset_version_reference(dataset, dataset_reference)
    return build_bayesian_artifact(
        model=model,
        dataset=dataset,
        dataset_identity=dataset_reference.identity,
    )
