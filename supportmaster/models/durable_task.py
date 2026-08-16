"""Durable task, lease, checkpoint, and replay contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


TaskStatus = Literal[
    "PENDING",
    "RUNNING",
    "RETRY_WAIT",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
]
RunControlStatus = Literal[
    "RUNNABLE",
    "RUNNING",
    "PAUSED",
    "CANCEL_REQUESTED",
    "CANCELLED",
    "COMPLETED",
    "FAILED",
]
WorkerOutcome = Literal["SUCCEEDED", "FAILED", "RETRY_WAIT", "PAUSED", "CANCELLED"]


class DurableTask(BaseModel):
    """A resumable unit of work claimed by one worker lease at a time."""

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    task_name: str
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = "PENDING"
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    available_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    last_error: str | None = None
    result: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunControl(BaseModel):
    """Operator-controlled lifecycle state for a durable run."""

    run_id: str
    status: RunControlStatus = "RUNNABLE"
    reason: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskCheckpoint(BaseModel):
    """A resumable checkpoint emitted by a running task."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    run_id: str
    sequence: int = Field(ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReplayPlan(BaseModel):
    """Read-only replay metadata; replay never authorizes mutations."""

    replay_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    source_version: int
    event_sequences: list[int] = Field(default_factory=list)
    dry_run: bool = True
    mutating_replay_allowed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkerTaskResult(BaseModel):
    """Worker outcome returned to a scheduler or API layer."""

    task_id: str
    run_id: str
    outcome: WorkerOutcome
    attempt_count: int = Field(ge=0)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
