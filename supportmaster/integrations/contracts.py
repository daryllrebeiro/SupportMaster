"""Typed contracts shared by external production integrations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


IntegrationPermission = Literal[
    "READ_ISSUES",
    "WRITE_ISSUES",
    "READ_REPOSITORY",
    "WRITE_REPOSITORY",
    "READ_CI",
    "TRIGGER_CI",
    "READ_MONITORING",
    "SEND_NOTIFICATIONS",
]


class IssueRecord(BaseModel):
    key: str
    title: str
    status: str = "UNKNOWN"
    url: str | None = None
    labels: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class CIStatus(BaseModel):
    run_id: str
    status: Literal["QUEUED", "RUNNING", "PASSED", "FAILED", "CANCELLED", "UNKNOWN"]
    url: str | None = None
    commit_sha: str | None = None
    details: dict[str, str] = Field(default_factory=dict)


class IncidentRecord(BaseModel):
    incident_id: str
    service: str
    severity: str = "UNKNOWN"
    status: str = "UNKNOWN"
    started_at: datetime | None = None
    summary: str = ""
    url: str | None = None


class MetricSample(BaseModel):
    metric: str
    value: float
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dimensions: dict[str, str] = Field(default_factory=dict)


class IntegrationReadResult(BaseModel):
    """Read result paired with an auditable operation receipt."""

    items: list[Any] = Field(default_factory=list)
    receipt: dict[str, Any] = Field(default_factory=dict)
