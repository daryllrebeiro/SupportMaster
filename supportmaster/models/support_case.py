"""Organization-neutral support case contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


CaseStatus = Literal[
    "RECEIVED",
    "NORMALIZED",
    "IN_PROGRESS",
    "WAITING_FOR_INFORMATION",
    "RESOLVED",
    "ESCALATED",
    "CLOSED",
]


class CaseAttachment(BaseModel):
    name: str
    uri: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = None


class SupportCase(BaseModel):
    """Canonical case consumed by all future intake adapters."""

    case_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = "default"
    source_system: str = "MANUAL"
    external_id: str | None = None
    status: CaseStatus = "RECEIVED"
    title: str = Field(min_length=1, max_length=2_000)
    description: str = Field(min_length=1, max_length=1_000_000)
    requester: str | None = None
    customer_account: str | None = None
    priority: str | None = None
    severity: str | None = None
    product: str | None = None
    service: str | None = None
    environment: str | None = None
    application_version: str | None = None
    reproduction_steps: list[str] = Field(default_factory=list)
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    customer_impact: str | None = None
    attachments: list[CaseAttachment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def workflow_text(self) -> str:
        """Render a stable, source-neutral prompt for existing agents."""
        sections = [f"Title: {self.title}", f"Description:\n{self.description}"]
        optional = (
            ("Priority", self.priority),
            ("Severity", self.severity),
            ("Product", self.product),
            ("Service", self.service),
            ("Environment", self.environment),
            ("Expected behavior", self.expected_behavior),
            ("Actual behavior", self.actual_behavior),
            ("Customer impact", self.customer_impact),
        )
        sections.extend(f"{label}: {value}" for label, value in optional if value)
        if self.reproduction_steps:
            sections.append("Reproduction steps:\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(self.reproduction_steps, 1)))
        return "\n\n".join(sections)
