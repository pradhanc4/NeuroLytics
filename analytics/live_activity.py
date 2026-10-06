"""Live processing state for the NeuroLytics dashboard.

This module is intentionally dependency-free and process-local. It provides a
small thread-safe event/state surface that can be populated by Excel processing,
website data entry, prediction, evaluation, and retraining workflows.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import RLock
from typing import Any


class LiveActivity:
    """Thread-safe live state and bounded event history."""

    def __init__(self, max_events: int = 250) -> None:
        if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 10:
            raise ValueError("max_events must be an integer >= 10.")
        self._lock = RLock()
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._sequence = 0
        self._state: dict[str, Any] = {
            "status": "IDLE",
            "source": None,
            "current_date": None,
            "stage": None,
            "operation": "Waiting",
            "prediction": None,
            "actual": None,
            "result": None,
            "model_version": None,
            "accuracy": None,
            "total_predictions": 0,
            "correct_predictions": 0,
            "incorrect_predictions": 0,
            "retraining_events": 0,
            "processed_entries": 0,
            "updated_at": self._now(),
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def emit(self, message: str, **updates: Any) -> dict[str, Any]:
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be non-empty.")
        with self._lock:
            self._sequence += 1
            self._state.update(updates)
            self._state["updated_at"] = self._now()
            event = {
                "sequence": self._sequence,
                "timestamp": self._state["updated_at"],
                "message": message.strip(),
                "state": dict(self._state),
            }
            self._events.append(event)
            return dict(event)

    def reset(self, *, source: str | None = None) -> dict[str, Any]:
        with self._lock:
            self._state.update({
                "status": "RUNNING",
                "source": source,
                "current_date": None,
                "stage": None,
                "operation": "Starting",
                "prediction": None,
                "actual": None,
                "result": None,
                "model_version": None,
                "accuracy": None,
                "total_predictions": 0,
                "correct_predictions": 0,
                "incorrect_predictions": 0,
                "retraining_events": 0,
                "processed_entries": 0,
            })
            return self.emit("Processing started")

    def set_status(self, status: str, message: str) -> dict[str, Any]:
        return self.emit(message, status=status)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "status": "VALID",
                "state": dict(self._state),
                "events": list(self._events),
                "last_sequence": self._sequence,
            }

    def events_since(self, sequence: int = 0) -> dict[str, Any]:
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise ValueError("sequence must be a non-negative integer.")
        with self._lock:
            events = [event for event in self._events if event["sequence"] > sequence]
            return {
                "status": "VALID",
                "events": events,
                "last_sequence": self._sequence,
                "state": dict(self._state),
            }


live_activity = LiveActivity()

__all__ = ["LiveActivity", "live_activity"]
