"""Bounded run admission with idempotent leases."""

from __future__ import annotations

from contextlib import contextmanager
from threading import Lock
from typing import Iterator, Literal

from pydantic import BaseModel


class AdmissionDecision(BaseModel):
    status: Literal["ACCEPTED", "REJECTED"]
    run_id: str
    active_runs: int
    max_active_runs: int
    reason: str | None = None


class RunAdmissionController:
    def __init__(self, max_active_runs: int = 4) -> None:
        if max_active_runs < 1:
            raise ValueError("max_active_runs must be at least one.")
        self.max_active_runs = max_active_runs
        self._active: set[str] = set()
        self._lock = Lock()

    def admit(self, run_id: str) -> AdmissionDecision:
        if not run_id.strip():
            raise ValueError("run_id must not be empty.")
        with self._lock:
            if run_id in self._active:
                return AdmissionDecision(status="ACCEPTED", run_id=run_id, active_runs=len(self._active), max_active_runs=self.max_active_runs, reason="Run admission is idempotent.")
            if len(self._active) >= self.max_active_runs:
                return AdmissionDecision(status="REJECTED", run_id=run_id, active_runs=len(self._active), max_active_runs=self.max_active_runs, reason="Maximum active SupportMaster runs reached.")
            self._active.add(run_id)
            return AdmissionDecision(status="ACCEPTED", run_id=run_id, active_runs=len(self._active), max_active_runs=self.max_active_runs)

    def release(self, run_id: str) -> bool:
        with self._lock:
            if run_id not in self._active:
                return False
            self._active.remove(run_id)
            return True

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    @contextmanager
    def lease(self, run_id: str) -> Iterator[AdmissionDecision]:
        decision = self.admit(run_id)
        if decision.status != "ACCEPTED":
            raise RuntimeError(decision.reason or "Run admission rejected.")
        try:
            yield decision
        finally:
            self.release(run_id)
