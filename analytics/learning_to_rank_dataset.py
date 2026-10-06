from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from typing import Sequence

LEARNING_TO_RANK_DATASET_VERSION = "40.0.0"
VALID = "VALID"
INVALID = "INVALID"
SPLIT_TRAIN = "train"
SPLIT_VALIDATION = "validation"
SPLIT_TEST = "test"
VALID_SPLITS = (SPLIT_TRAIN, SPLIT_VALIDATION, SPLIT_TEST)


@dataclass(frozen=True)
class LearningToRankDatasetConfig:
    feature_names: tuple[str, ...]
    validation_start_date: date
    test_start_date: date
    candidate_digits: tuple[int, ...] = tuple(range(10))
    target_position: str = "close"
    label_policy: str = "binary_actual_digit"


@dataclass(frozen=True)
class LearningToRankCandidateInput:
    candidate_digit: int
    feature_values: tuple[float, ...]
    feature_available_date: date
    panel_family_id: str | None = None
    jodi_family_id: str | None = None


@dataclass(frozen=True)
class LearningToRankObservationInput:
    group_id: str
    target_date: date
    target_position: str
    actual_digit: int
    candidates: tuple[LearningToRankCandidateInput, ...]
    source_observation_identity: str = ""


@dataclass(frozen=True)
class LearningToRankRow:
    group_id: str
    target_date: date
    target_position: str
    candidate_id: str
    candidate_digit: int
    relevance_label: int
    feature_names: tuple[str, ...]
    feature_values: tuple[float, ...]
    feature_available_date: date
    panel_family_id: str | None
    jodi_family_id: str | None
    relationship_key: str
    split: str


@dataclass(frozen=True)
class LearningToRankGroup:
    group_id: str
    target_date: date
    target_position: str
    candidate_ids: tuple[str, ...]
    row_start: int
    row_end: int
    split: str
    actual_digit: int


@dataclass(frozen=True)
class LearningToRankDataset:
    version: str
    source_dataset_identity: str
    feature_schema_identity: str
    config: LearningToRankDatasetConfig
    rows: tuple[LearningToRankRow, ...]
    groups: tuple[LearningToRankGroup, ...]
    train_group_ids: tuple[str, ...]
    validation_group_ids: tuple[str, ...]
    test_group_ids: tuple[str, ...]
    dataset_identity: str


@dataclass(frozen=True)
class LearningToRankValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.status == VALID


def _check_date(value: date, name: str) -> None:
    if not isinstance(value, date):
        raise TypeError(f"{name} must be a datetime.date instance.")


def _check_digits(digits: Sequence[int]) -> tuple[int, ...]:
    values = tuple(digits)
    if values != tuple(range(10)):
        raise ValueError("candidate_digits must contain exactly digits 0 through 9.")
    return values


def validate_learning_to_rank_config(
    config: LearningToRankDatasetConfig,
) -> None:
    if not isinstance(config, LearningToRankDatasetConfig):
        raise TypeError("config must be a LearningToRankDatasetConfig.")
    if not config.feature_names:
        raise ValueError("feature_names must not be empty.")
    if len(set(config.feature_names)) != len(config.feature_names):
        raise ValueError("feature_names must be unique.")
    if any(not isinstance(name, str) or not name.strip() for name in config.feature_names):
        raise ValueError("feature_names must contain non-empty strings.")
    _check_date(config.validation_start_date, "validation_start_date")
    _check_date(config.test_start_date, "test_start_date")
    if config.validation_start_date >= config.test_start_date:
        raise ValueError("validation_start_date must be before test_start_date.")
    _check_digits(config.candidate_digits)
    if not config.target_position.strip():
        raise ValueError("target_position must be non-empty.")
    if config.label_policy != "binary_actual_digit":
        raise ValueError("unsupported label_policy.")


def _candidate_id(position: str, digit: int) -> str:
    return f"{position}:digit:{digit}"


def _relationship_key(panel: str | None, jodi: str | None) -> str:
    return f"panel={panel or 'NONE'}|jodi={jodi or 'NONE'}"


def _split_for_date(target_date: date, config: LearningToRankDatasetConfig) -> str:
    if target_date < config.validation_start_date:
        return SPLIT_TRAIN
    if target_date < config.test_start_date:
        return SPLIT_VALIDATION
    return SPLIT_TEST


def _validate_candidate_input(
    candidate: LearningToRankCandidateInput,
    feature_count: int,
    target_date: date,
) -> None:
    if not isinstance(candidate.candidate_digit, int) or isinstance(candidate.candidate_digit, bool):
        raise TypeError("candidate_digit must be an integer.")
    if candidate.candidate_digit not in range(10):
        raise ValueError("candidate_digit must be between 0 and 9.")
    if len(candidate.feature_values) != feature_count:
        raise ValueError("candidate feature count does not match feature_names.")
    _check_date(candidate.feature_available_date, "feature_available_date")
    if candidate.feature_available_date >= target_date:
        raise ValueError("features must be available strictly before target_date.")
    for value in candidate.feature_values:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            raise ValueError("feature values must be finite numeric values.")


def _validate_observation_input(
    observation: LearningToRankObservationInput,
    config: LearningToRankDatasetConfig,
) -> None:
    if not isinstance(observation, LearningToRankObservationInput):
        raise TypeError("observations must contain LearningToRankObservationInput objects.")
    if not observation.group_id.strip():
        raise ValueError("group_id must be non-empty.")
    _check_date(observation.target_date, "target_date")
    if observation.target_position != config.target_position:
        raise ValueError("observation target_position does not match config.")
    if observation.actual_digit not in range(10):
        raise ValueError("actual_digit must be between 0 and 9.")
    if len(observation.candidates) != 10:
        raise ValueError("each ranking group must contain exactly ten candidates.")
    for candidate in observation.candidates:
        _validate_candidate_input(candidate, len(config.feature_names), observation.target_date)
    digits = tuple(candidate.candidate_digit for candidate in observation.candidates)
    if digits != tuple(range(10)):
        raise ValueError("each group must contain each candidate digit 0 through 9 exactly once.")


def _identity(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "learning-to-rank-dataset-" + hashlib.sha256(encoded).hexdigest()


def build_learning_to_rank_dataset(
    observations: Sequence[LearningToRankObservationInput],
    config: LearningToRankDatasetConfig,
    source_dataset_identity: str,
    feature_schema_identity: str,
) -> LearningToRankDataset:
    validate_learning_to_rank_config(config)
    if not source_dataset_identity:
        raise ValueError("source_dataset_identity must be non-empty.")
    if not feature_schema_identity:
        raise ValueError("feature_schema_identity must be non-empty.")
    materialized = tuple(observations)
    if not materialized:
        raise ValueError("at least one ranking observation is required.")
    for observation in materialized:
        _validate_observation_input(observation, config)
    group_ids = [item.group_id for item in materialized]
    if len(set(group_ids)) != len(group_ids):
        raise ValueError("group_id values must be unique.")
    ordered = tuple(sorted(materialized, key=lambda item: (item.target_date, item.group_id)))
    rows: list[LearningToRankRow] = []
    groups: list[LearningToRankGroup] = []
    for observation in ordered:
        split = _split_for_date(observation.target_date, config)
        start = len(rows)
        candidates = sorted(observation.candidates, key=lambda item: item.candidate_digit)
        for candidate in candidates:
            rows.append(
                LearningToRankRow(
                    group_id=observation.group_id,
                    target_date=observation.target_date,
                    target_position=observation.target_position,
                    candidate_id=_candidate_id(observation.target_position, candidate.candidate_digit),
                    candidate_digit=candidate.candidate_digit,
                    relevance_label=int(candidate.candidate_digit == observation.actual_digit),
                    feature_names=config.feature_names,
                    feature_values=tuple(float(value) for value in candidate.feature_values),
                    feature_available_date=candidate.feature_available_date,
                    panel_family_id=candidate.panel_family_id,
                    jodi_family_id=candidate.jodi_family_id,
                    relationship_key=_relationship_key(candidate.panel_family_id, candidate.jodi_family_id),
                    split=split,
                )
            )
        groups.append(
            LearningToRankGroup(
                group_id=observation.group_id,
                target_date=observation.target_date,
                target_position=observation.target_position,
                candidate_ids=tuple(row.candidate_id for row in rows[start:start + 10]),
                row_start=start,
                row_end=len(rows) - 1,
                split=split,
                actual_digit=observation.actual_digit,
            )
        )
    split_groups = {
        split: tuple(group.group_id for group in groups if group.split == split)
        for split in VALID_SPLITS
    }
    if any(not split_groups[split] for split in VALID_SPLITS):
        raise ValueError("train, validation, and test splits must each contain at least one group.")
    identity_payload = {
        "version": LEARNING_TO_RANK_DATASET_VERSION,
        "source_dataset_identity": source_dataset_identity,
        "feature_schema_identity": feature_schema_identity,
        "config": config,
        "rows": rows,
        "groups": groups,
    }
    return LearningToRankDataset(
        version=LEARNING_TO_RANK_DATASET_VERSION,
        source_dataset_identity=source_dataset_identity,
        feature_schema_identity=feature_schema_identity,
        config=config,
        rows=tuple(rows),
        groups=tuple(groups),
        train_group_ids=split_groups[SPLIT_TRAIN],
        validation_group_ids=split_groups[SPLIT_VALIDATION],
        test_group_ids=split_groups[SPLIT_TEST],
        dataset_identity=_identity(identity_payload),
    )


def validate_learning_to_rank_dataset(
    dataset: LearningToRankDataset,
) -> LearningToRankValidationResult:
    if not isinstance(dataset, LearningToRankDataset):
        return LearningToRankValidationResult(INVALID, ("INVALID_DATASET_TYPE",))
    issues: list[str] = []
    try:
        validate_learning_to_rank_config(dataset.config)
    except (TypeError, ValueError) as exc:
        issues.append("INVALID_CONFIG:" + str(exc))
    if dataset.version != LEARNING_TO_RANK_DATASET_VERSION:
        issues.append("INVALID_VERSION")
    if not dataset.source_dataset_identity:
        issues.append("MISSING_SOURCE_DATASET_IDENTITY")
    if not dataset.feature_schema_identity:
        issues.append("MISSING_FEATURE_SCHEMA_IDENTITY")
    if not dataset.rows:
        issues.append("NO_ROWS")
    if not dataset.groups:
        issues.append("NO_GROUPS")
    if len(dataset.rows) != len(dataset.groups) * 10:
        issues.append("INVALID_ROW_GROUP_CARDINALITY")
    seen_groups: set[str] = set()
    for group in dataset.groups:
        if group.group_id in seen_groups:
            issues.append("DUPLICATE_GROUP_ID")
        seen_groups.add(group.group_id)
        if group.row_end - group.row_start + 1 != 10:
            issues.append("INVALID_GROUP_ROW_RANGE")
        if group.actual_digit not in range(10):
            issues.append("INVALID_GROUP_TARGET")
        if group.split not in VALID_SPLITS:
            issues.append("INVALID_GROUP_SPLIT")
        group_rows = dataset.rows[group.row_start:group.row_end + 1]
        if len(group_rows) != 10 or any(row.group_id != group.group_id for row in group_rows):
            issues.append("GROUP_ROW_ALIGNMENT_ERROR")
        digits = tuple(row.candidate_digit for row in group_rows)
        if digits != tuple(range(10)):
            issues.append("GROUP_CANDIDATE_SET_ERROR")
        labels = tuple(row.relevance_label for row in group_rows)
        if labels.count(1) != 1 or labels[group.actual_digit] != 1:
            issues.append("GROUP_LABEL_ERROR")
        for row in group_rows:
            if row.feature_names != dataset.config.feature_names:
                issues.append("FEATURE_SCHEMA_MISMATCH")
            if len(row.feature_values) != len(dataset.config.feature_names):
                issues.append("FEATURE_VECTOR_LENGTH_ERROR")
            if row.feature_available_date >= row.target_date:
                issues.append("FEATURE_TEMPORAL_LEAKAGE")
            if row.split != group.split:
                issues.append("ROW_SPLIT_MISMATCH")
            if row.candidate_id != _candidate_id(row.target_position, row.candidate_digit):
                issues.append("CANDIDATE_ID_ERROR")
            if row.relationship_key != _relationship_key(row.panel_family_id, row.jodi_family_id):
                issues.append("RELATIONSHIP_KEY_ERROR")
            if any(not math.isfinite(float(value)) for value in row.feature_values):
                issues.append("NON_FINITE_FEATURE")
    train_dates = [group.target_date for group in dataset.groups if group.split == SPLIT_TRAIN]
    validation_dates = [group.target_date for group in dataset.groups if group.split == SPLIT_VALIDATION]
    test_dates = [group.target_date for group in dataset.groups if group.split == SPLIT_TEST]
    if train_dates and max(train_dates) >= dataset.config.validation_start_date:
        issues.append("TRAIN_CROSSES_VALIDATION_BOUNDARY")
    if validation_dates and (min(validation_dates) < dataset.config.validation_start_date or max(validation_dates) >= dataset.config.test_start_date):
        issues.append("VALIDATION_CROSSES_BOUNDARY")
    if test_dates and min(test_dates) < dataset.config.test_start_date:
        issues.append("TEST_CROSSES_TEST_BOUNDARY")
    if len(set(dataset.train_group_ids) & set(dataset.validation_group_ids)):
        issues.append("TRAIN_VALIDATION_GROUP_OVERLAP")
    if len(set(dataset.train_group_ids) & set(dataset.test_group_ids)):
        issues.append("TRAIN_TEST_GROUP_OVERLAP")
    if len(set(dataset.validation_group_ids) & set(dataset.test_group_ids)):
        issues.append("VALIDATION_TEST_GROUP_OVERLAP")
    if not dataset.dataset_identity.startswith("learning-to-rank-dataset-"):
        issues.append("INVALID_DATASET_IDENTITY")
    return LearningToRankValidationResult(
        VALID if not issues else INVALID,
        tuple(sorted(set(issues))),
    )


def get_learning_to_rank_split_rows(
    dataset: LearningToRankDataset,
    split: str,
) -> tuple[LearningToRankRow, ...]:
    validation = validate_learning_to_rank_dataset(dataset)
    if not validation.is_valid:
        raise ValueError("dataset is invalid: " + ",".join(validation.issues))
    if split not in VALID_SPLITS:
        raise ValueError("unsupported split.")
    return tuple(row for row in dataset.rows if row.split == split)


def get_learning_to_rank_group(
    dataset: LearningToRankDataset,
    group_id: str,
) -> LearningToRankGroup:
    validation = validate_learning_to_rank_dataset(dataset)
    if not validation.is_valid:
        raise ValueError("dataset is invalid: " + ",".join(validation.issues))
    for group in dataset.groups:
        if group.group_id == group_id:
            return group
    raise ValueError(f"ranking group not found: {group_id}")


def learning_to_rank_group_sizes(
    dataset: LearningToRankDataset,
) -> tuple[int, int, int]:
    return (
        len(dataset.train_group_ids),
        len(dataset.validation_group_ids),
        len(dataset.test_group_ids),
    )


def learning_to_rank_summary(
    dataset: LearningToRankDataset,
) -> dict[str, object]:
    validation = validate_learning_to_rank_dataset(dataset)
    return {
        "status": validation.status,
        "version": dataset.version,
        "groups": len(dataset.groups),
        "rows": len(dataset.rows),
        "train_groups": len(dataset.train_group_ids),
        "validation_groups": len(dataset.validation_group_ids),
        "test_groups": len(dataset.test_group_ids),
        "features": len(dataset.config.feature_names),
        "candidate_count_per_group": 10,
        "target_position": dataset.config.target_position,
        "dataset_identity": dataset.dataset_identity,
    }


__all__ = [
    "LEARNING_TO_RANK_DATASET_VERSION",
    "VALID",
    "INVALID",
    "SPLIT_TRAIN",
    "SPLIT_VALIDATION",
    "SPLIT_TEST",
    "LearningToRankDatasetConfig",
    "LearningToRankCandidateInput",
    "LearningToRankObservationInput",
    "LearningToRankRow",
    "LearningToRankGroup",
    "LearningToRankDataset",
    "LearningToRankValidationResult",
    "validate_learning_to_rank_config",
    "build_learning_to_rank_dataset",
    "validate_learning_to_rank_dataset",
    "get_learning_to_rank_split_rows",
    "get_learning_to_rank_group",
    "learning_to_rank_group_sizes",
    "learning_to_rank_summary",
]
