"""Typed contracts for bounded fork/join execution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


BranchStatus = Literal[
    "SUCCEEDED",
    "FAILED",
    "TIMED_OUT",
    "CANCELLED",
    "SKIPPED",
]
ForkJoinStatus = Literal["COMPLETED", "PARTIAL", "BLOCKED"]


class TaskSpec(BaseModel):
    """One read-only branch in a fork group."""

    name: str
    required: bool = True
    read_only: bool = True
    timeout_seconds: float = Field(default=60.0, gt=0)
    dependencies: list[str] = Field(default_factory=list)


class ForkGroupSpec(BaseModel):
    """A bounded dependency-aware set of read-only tasks."""

    name: str
    tasks: list[TaskSpec] = Field(min_length=1)
    max_concurrency: int = Field(default=4, ge=1, le=32)
    timeout_seconds: float = Field(default=180.0, gt=0)


class BranchResult(BaseModel):
    """Observable outcome of one fork branch."""

    task_name: str
    status: BranchStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: int = Field(default=0, ge=0)


class ForkJoinResult(BaseModel):
    """Deterministic fan-in decision and merged read-only output."""

    group_name: str
    status: ForkJoinStatus
    branches: list[BranchResult] = Field(default_factory=list)
    merged_output: dict[str, Any] = Field(default_factory=dict)
    conflicts: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

