"""Validated environment-backed limits for production operation."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class OperationSettings(BaseModel):
    """Safety limits that prevent an operator mistake from becoming a flood."""

    max_active_runs: int = Field(default=4, ge=1, le=1_000)
    max_issue_bytes: int = Field(default=250_000, ge=1_024, le=10_000_000)
    max_queue_depth: int = Field(default=100, ge=1, le=100_000)
    circuit_failure_threshold: int = Field(default=3, ge=1, le=100)
    circuit_recovery_seconds: float = Field(default=30.0, ge=0.1, le=86_400.0)


def _integer(environ: dict[str, str], key: str, default: int) -> int:
    raw = environ.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as error:
        raise ValueError(f"{key} must be an integer.") from error


def _number(environ: dict[str, str], key: str, default: float) -> float:
    raw = environ.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as error:
        raise ValueError(f"{key} must be numeric.") from error


def load_operation_settings(environ: dict[str, str] | None = None) -> OperationSettings:
    values = dict(environ or os.environ)
    return OperationSettings(
        max_active_runs=_integer(values, "SUPPORTMASTER_MAX_ACTIVE_RUNS", 4),
        max_issue_bytes=_integer(values, "SUPPORTMASTER_MAX_ISSUE_BYTES", 250_000),
        max_queue_depth=_integer(values, "SUPPORTMASTER_MAX_QUEUE_DEPTH", 100),
        circuit_failure_threshold=_integer(values, "SUPPORTMASTER_CIRCUIT_FAILURE_THRESHOLD", 3),
        circuit_recovery_seconds=_number(values, "SUPPORTMASTER_CIRCUIT_RECOVERY_SECONDS", 30.0),
    )
