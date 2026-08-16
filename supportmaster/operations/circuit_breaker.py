"""Dependency circuit breaker for external adapters."""

from __future__ import annotations

from enum import Enum
from threading import Lock
from time import monotonic


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 3, recovery_seconds: float = 30.0) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least one.")
        if recovery_seconds <= 0:
            raise ValueError("recovery_seconds must be positive.")
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at: float | None = None
        self._probe_in_flight = False
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._transition_if_ready()
            return self._state

    @property
    def failures(self) -> int:
        with self._lock:
            return self._failures

    def allow_request(self) -> bool:
        with self._lock:
            self._transition_if_ready()
            if self._state == CircuitState.OPEN:
                return False
            if self._state == CircuitState.HALF_OPEN:
                if self._probe_in_flight:
                    return False
                self._probe_in_flight = True
                return True
            return True

    def record_success(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._opened_at = None
            self._probe_in_flight = False

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = monotonic()
                self._probe_in_flight = False

    def _transition_if_ready(self) -> None:
        if self._state == CircuitState.OPEN and self._opened_at is not None and monotonic() - self._opened_at >= self.recovery_seconds:
            self._state = CircuitState.HALF_OPEN
            self._probe_in_flight = False
