from __future__ import annotations

from dataclasses import dataclass

from analytics.statistical_baseline_dataset import (
    StatisticalBaselineDataset,
    validate_statistical_baseline_dataset,
)
from analytics.statistical_descriptive import (
    DescriptiveStatistics,
    build_statistical_descriptive_result,
)

VALID = "VALID"
INVALID = "INVALID"


@dataclass(frozen=True)
class CentralTendencyDispersion:
    """Central-tendency and dispersion view for one position."""

    position: str
    count: int
    mean: float | None
    median: float | None
    mode: tuple[int, ...]
    minimum: int | None
    maximum: int | None
    range: int | None
    variance: float | None
    standard_deviation: float | None


@dataclass(frozen=True)
class StatisticalCentralTendencyDispersionBaseline:
    """Immutable Phase 18.7 baseline result."""

    market_id: int
    analysis_version: str
    baseline_version: str
    statistics: tuple[CentralTendencyDispersion, ...]

    @property
    def positions(self) -> tuple[str, ...]:
        return tuple(item.position for item in self.statistics)

    @property
    def position_count(self) -> int:
        return len(self.statistics)


@dataclass(frozen=True)
class StatisticalCentralTendencyDispersionValidationIssue:
    code: str
    message: str


@dataclass(frozen=True)
class StatisticalCentralTendencyDispersionValidationResult:
    status: str
    issues: tuple[
        StatisticalCentralTendencyDispersionValidationIssue, ...
    ]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID

    @property
    def issue_count(self) -> int:
        return len(self.issues)


def _issue(
    code: str,
    message: str,
) -> StatisticalCentralTendencyDispersionValidationIssue:
    return StatisticalCentralTendencyDispersionValidationIssue(
        code=code,
        message=message,
    )


def _from_descriptive(
    statistic: DescriptiveStatistics,
) -> CentralTendencyDispersion:
    return CentralTendencyDispersion(
        position=statistic.column_name,
        count=statistic.count,
        mean=statistic.mean,
        median=statistic.median,
        mode=statistic.mode,
        minimum=statistic.minimum,
        maximum=statistic.maximum,
        range=statistic.range,
        variance=statistic.variance,
        standard_deviation=statistic.standard_deviation,
    )


def build_statistical_central_tendency_dispersion_baseline(
    dataset: StatisticalBaselineDataset,
) -> StatisticalCentralTendencyDispersionBaseline:
    """
    Build Phase 18.7 from the existing Phase 18.3 engine.

    No central-tendency or dispersion calculation is duplicated here.
    """
    validate_statistical_baseline_dataset(dataset)

    descriptive = build_statistical_descriptive_result(dataset)

    statistics = tuple(
        _from_descriptive(item)
        for item in descriptive.statistics
    )

    return StatisticalCentralTendencyDispersionBaseline(
        market_id=descriptive.market_id,
        analysis_version=descriptive.analysis_version,
        baseline_version=descriptive.baseline_version,
        statistics=statistics,
    )


def validate_statistical_central_tendency_dispersion_baseline(
    baseline: StatisticalCentralTendencyDispersionBaseline,
) -> None:
    """Raise when a Phase 18.7 baseline is structurally invalid."""
    if not isinstance(
        baseline,
        StatisticalCentralTendencyDispersionBaseline,
    ):
        raise TypeError(
            "baseline must be a "
            "StatisticalCentralTendencyDispersionBaseline instance."
        )

    if (
        not isinstance(baseline.market_id, int)
        or isinstance(baseline.market_id, bool)
        or baseline.market_id <= 0
    ):
        raise ValueError("market_id must be a positive integer.")

    if (
        not isinstance(baseline.analysis_version, str)
        or not baseline.analysis_version.strip()
    ):
        raise ValueError(
            "analysis_version must be a non-empty string."
        )

    if (
        not isinstance(baseline.baseline_version, str)
        or not baseline.baseline_version.strip()
    ):
        raise ValueError(
            "baseline_version must be a non-empty string."
        )

    if not isinstance(baseline.statistics, tuple):
        raise TypeError("statistics must be a tuple.")

    previous_position = None
    seen: set[str] = set()

    for item in baseline.statistics:
        if not isinstance(item, CentralTendencyDispersion):
            raise TypeError(
                "statistics must contain "
                "CentralTendencyDispersion objects."
            )

        if not item.position.strip():
            raise ValueError("position must be a non-empty string.")

        if item.position in seen:
            raise ValueError("positions must be unique.")

        if (
            previous_position is not None
            and item.position <= previous_position
        ):
            raise ValueError(
                "statistics must be in deterministic order."
            )

        seen.add(item.position)
        previous_position = item.position

        if item.count < 0:
            raise ValueError("count cannot be negative.")

        if item.count == 0:
            if any(
                value is not None
                for value in (
                    item.mean,
                    item.median,
                    item.minimum,
                    item.maximum,
                    item.range,
                    item.variance,
                    item.standard_deviation,
                )
            ):
                raise ValueError(
                    "empty statistics cannot contain numeric values."
                )
            if item.mode:
                raise ValueError(
                    "empty statistics cannot contain a mode."
                )
            continue

        required = (
            item.mean,
            item.median,
            item.minimum,
            item.maximum,
            item.range,
            item.variance,
            item.standard_deviation,
        )
        if any(value is None for value in required):
            raise ValueError(
                "non-empty statistics require all measures."
            )

        if item.minimum < 0 or item.maximum > 9:
            raise ValueError(
                "minimum and maximum must be within 0-9."
            )

        if item.minimum > item.maximum:
            raise ValueError(
                "minimum cannot exceed maximum."
            )

        if item.range != item.maximum - item.minimum:
            raise ValueError(
                "range must equal maximum minus minimum."
            )

        if item.variance < 0:
            raise ValueError("variance cannot be negative.")

        if item.standard_deviation < 0:
            raise ValueError(
                "standard deviation cannot be negative."
            )

        if not item.mode:
            raise ValueError(
                "non-empty statistics require a mode."
            )

        for mode_value in item.mode:
            if mode_value < 0 or mode_value > 9:
                raise ValueError(
                    "mode values must be within 0-9."
                )
def validate_statistical_central_tendency_dispersion_baseline_result(
    baseline: StatisticalCentralTendencyDispersionBaseline,
) -> StatisticalCentralTendencyDispersionValidationResult:
    """Return non-raising validation details."""
    if not isinstance(
        baseline,
        StatisticalCentralTendencyDispersionBaseline,
    ):
        return StatisticalCentralTendencyDispersionValidationResult(
            status=INVALID,
            issues=(
                _issue(
                    "INVALID_BASELINE_TYPE",
                    (
                        "baseline must be a "
                        "StatisticalCentralTendencyDispersionBaseline "
                        "instance."
                    ),
                ),
            ),
        )

    try:
        validate_statistical_central_tendency_dispersion_baseline(
            baseline
        )
    except (TypeError, ValueError) as exc:
        return StatisticalCentralTendencyDispersionValidationResult(
            status=INVALID,
            issues=(
                _issue(
                    "INVALID_BASELINE",
                    str(exc),
                ),
            ),
        )

    return StatisticalCentralTendencyDispersionValidationResult(
        status=VALID,
        issues=(),
    )


def is_statistical_central_tendency_dispersion_baseline_valid(
    baseline: StatisticalCentralTendencyDispersionBaseline,
) -> bool:
    return (
        validate_statistical_central_tendency_dispersion_baseline_result(
            baseline
        ).is_valid
    )


def get_central_tendency_dispersion(
    baseline: StatisticalCentralTendencyDispersionBaseline,
    position: str,
) -> CentralTendencyDispersion:
    """Return the Phase 18.7 statistics for one position."""
    validate_statistical_central_tendency_dispersion_baseline(
        baseline
    )

    for item in baseline.statistics:
        if item.position == position:
            return item

    raise ValueError(
        f"Central tendency and dispersion not found: {position}"
    )


def get_central_tendency_dispersion_positions(
    baseline: StatisticalCentralTendencyDispersionBaseline,
) -> tuple[str, ...]:
    validate_statistical_central_tendency_dispersion_baseline(
        baseline
    )
    return baseline.positions


def get_position_mean(
    baseline: StatisticalCentralTendencyDispersionBaseline,
    position: str,
) -> float | None:
    return get_central_tendency_dispersion(
        baseline,
        position,
    ).mean


def get_position_median(
    baseline: StatisticalCentralTendencyDispersionBaseline,
    position: str,
) -> float | None:
    return get_central_tendency_dispersion(
        baseline,
        position,
    ).median


def get_position_variance(
    baseline: StatisticalCentralTendencyDispersionBaseline,
    position: str,
) -> float | None:
    return get_central_tendency_dispersion(
        baseline,
        position,
    ).variance


def get_position_standard_deviation(
    baseline: StatisticalCentralTendencyDispersionBaseline,
    position: str,
) -> float | None:
    return get_central_tendency_dispersion(
        baseline,
        position,
    ).standard_deviation
