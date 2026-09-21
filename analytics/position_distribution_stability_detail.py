from __future__ import annotations

from dataclasses import dataclass

from analytics.position_distribution_volatility import (
    PositionDistributionVolatility,
)


@dataclass(frozen=True)
class PositionDistributionStabilityDetail:
    position: str
    digit: int
    window_count: int
    change_count: int
    total_absolute_change: float
    mean_absolute_change: float
    maximum_absolute_change: float
    minimum_absolute_change: float
    stability_level: str


def _validate_volatility_result(
    position: str,
    result: PositionDistributionVolatility,
) -> None:
    if result.position != position:
        raise ValueError(
            "Volatility result position does not match "
            "the requested position."
        )

    if result.digit < 0 or result.digit > 9:
        raise ValueError(
            "Volatility result digit must be between 0 and 9."
        )

    if result.window_count < 0:
        raise ValueError(
            "Window count must be greater than or equal to zero."
        )

    if result.change_count < 0:
        raise ValueError(
            "Change count must be greater than or equal to zero."
        )

    if result.total_absolute_change < 0:
        raise ValueError(
            "Total absolute change must be greater than or equal to zero."
        )

    if result.mean_absolute_change < 0:
        raise ValueError(
            "Mean absolute change must be greater than or equal to zero."
        )

    if result.maximum_absolute_change < 0:
        raise ValueError(
            "Maximum absolute change must be greater than or equal to zero."
        )

    if result.minimum_absolute_change < 0:
        raise ValueError(
            "Minimum absolute change must be greater than or equal to zero."
        )


def _classify_stability(
    mean_absolute_change: float,
    low_threshold: float,
    high_threshold: float,
) -> str:
    if mean_absolute_change < low_threshold:
        return "STABLE"

    if mean_absolute_change < high_threshold:
        return "MODERATE"

    return "UNSTABLE"


def build_position_distribution_stability_detail(
    position: str,
    result: PositionDistributionVolatility,
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> PositionDistributionStabilityDetail:
    if low_threshold < 0:
        raise ValueError(
            "Low threshold must be greater than or equal to zero."
        )

    if high_threshold < low_threshold:
        raise ValueError(
            "High threshold must be greater than or equal to "
            "the low threshold."
        )

    _validate_volatility_result(
        position=position,
        result=result,
    )

    stability_level = _classify_stability(
        mean_absolute_change=result.mean_absolute_change,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )

    return PositionDistributionStabilityDetail(
        position=result.position,
        digit=result.digit,
        window_count=result.window_count,
        change_count=result.change_count,
        total_absolute_change=result.total_absolute_change,
        mean_absolute_change=result.mean_absolute_change,
        maximum_absolute_change=result.maximum_absolute_change,
        minimum_absolute_change=result.minimum_absolute_change,
        stability_level=stability_level,
    )


def build_all_position_distribution_stability_details(
    position: str,
    results: tuple[PositionDistributionVolatility, ...],
    low_threshold: float = 2.0,
    high_threshold: float = 5.0,
) -> tuple[PositionDistributionStabilityDetail, ...]:
    if low_threshold < 0:
        raise ValueError(
            "Low threshold must be greater than or equal to zero."
        )

    if high_threshold < low_threshold:
        raise ValueError(
            "High threshold must be greater than or equal to "
            "the low threshold."
        )

    details = tuple(
        build_position_distribution_stability_detail(
            position=position,
            result=result,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        )
        for result in results
    )

    return details


def get_position_distribution_stability_detail(
    results: tuple[PositionDistributionStabilityDetail, ...],
    digit: int,
) -> PositionDistributionStabilityDetail | None:
    if digit < 0 or digit > 9:
        raise ValueError(
            "Digit must be between 0 and 9."
        )

    for result in results:
        if result.digit == digit:
            return result

    return None