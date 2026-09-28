from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from features.sequence_dataset_integration import (
    SequenceDatasetIntegrationResult,
)


def _canonicalize(value: Any) -> Any:
    """
    Convert supported NeuroLytics sequence objects into a deterministic
    JSON-compatible representation.

    Dictionary keys are sorted during JSON serialization, while tuples,
    dataclasses, dates, enums, and primitive values are represented
    explicitly and deterministically.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (str, int, float)):
        return value

    if isinstance(value, date):
        return {
            "__type__": "date",
            "value": value.isoformat(),
        }

    if isinstance(value, datetime):
        return {
            "__type__": "datetime",
            "value": value.isoformat(),
        }

    if isinstance(value, Enum):
        return {
            "__type__": "enum",
            "class": (
                f"{value.__class__.__module__}."
                f"{value.__class__.__qualname__}"
            ),
            "value": _canonicalize(value.value),
        }

    if is_dataclass(value):
        return {
            "__type__": "dataclass",
            "class": (
                f"{value.__class__.__module__}."
                f"{value.__class__.__qualname__}"
            ),
            "fields": {
                field.name: _canonicalize(
                    getattr(value, field.name)
                )
                for field in fields(value)
            },
        }

    if isinstance(value, tuple):
        return {
            "__type__": "tuple",
            "items": [
                _canonicalize(item)
                for item in value
            ],
        }

    if isinstance(value, list):
        return {
            "__type__": "list",
            "items": [
                _canonicalize(item)
                for item in value
            ],
        }

    if isinstance(value, dict):
        return {
            "__type__": "dict",
            "items": [
                (
                    _canonicalize(key),
                    _canonicalize(item),
                )
                for key, item in sorted(
                    value.items(),
                    key=lambda pair: repr(pair[0]),
                )
            ],
        }

    raise TypeError(
        "Unsupported value type for deterministic serialization: "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def canonicalize_sequence_dataset_result(
    result: SequenceDatasetIntegrationResult,
) -> Any:
    """
    Return the canonical representation of an integrated sequence result.
    """

    if not isinstance(
        result,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "result must be a SequenceDatasetIntegrationResult."
        )

    return _canonicalize(result)


def serialize_sequence_dataset_result(
    result: SequenceDatasetIntegrationResult,
) -> str:
    """
    Serialize an integrated sequence result using canonical JSON.

    The output is deterministic for the same logical result.
    """

    canonical = canonicalize_sequence_dataset_result(
        result
    )

    return json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def get_sequence_dataset_fingerprint(
    result: SequenceDatasetIntegrationResult,
) -> str:
    """
    Return the deterministic SHA-256 fingerprint of an integrated
    sequence dataset result.
    """

    serialized = serialize_sequence_dataset_result(
        result
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def sequence_dataset_results_match(
    first: SequenceDatasetIntegrationResult,
    second: SequenceDatasetIntegrationResult,
) -> bool:
    """
    Determine whether two integrated sequence results have identical
    deterministic fingerprints.
    """

    if not isinstance(
        first,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "first must be a SequenceDatasetIntegrationResult."
        )

    if not isinstance(
        second,
        SequenceDatasetIntegrationResult,
    ):
        raise TypeError(
            "second must be a SequenceDatasetIntegrationResult."
        )

    return (
        get_sequence_dataset_fingerprint(first)
        == get_sequence_dataset_fingerprint(second)
    )


def validate_sequence_dataset_reproducibility(
    first: SequenceDatasetIntegrationResult,
    second: SequenceDatasetIntegrationResult,
) -> None:
    """
    Raise ValueError when two integrated sequence results are not
    reproducible.
    """

    if not sequence_dataset_results_match(
        first,
        second,
    ):
        raise ValueError(
            "Sequence dataset results are not reproducible: "
            "their deterministic fingerprints differ."
        )


def get_sequence_dataset_serialized_size(
    result: SequenceDatasetIntegrationResult,
) -> int:
    """
    Return the UTF-8 byte size of the canonical serialized result.
    """

    serialized = serialize_sequence_dataset_result(
        result
    )

    return len(
        serialized.encode("utf-8")
    )