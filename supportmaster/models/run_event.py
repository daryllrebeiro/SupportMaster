"""Durable run-event and snapshot contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RunEvent(BaseModel):
    sequence: int
    run_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RunSnapshot(BaseModel):
    run_id: str
    version: int
    state: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
