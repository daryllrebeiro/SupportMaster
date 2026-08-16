"""Configurable organization context used by functional workflow decisions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkflowPolicy(BaseModel):
    """Organization policy inputs; deterministic gates still enforce safety."""

    required_evidence_sources: list[str] = Field(default_factory=list)
    require_duplicate_check: bool = True
    require_implementation_approval: bool = True
    require_publication_approval: bool = True
    require_production_approval: bool = True
    allow_autonomous_code_change: bool = False
    allowed_external_actions: list[str] = Field(default_factory=list)
    escalation_thresholds: dict[str, str] = Field(default_factory=dict)


class OrganizationProfile(BaseModel):
    """A tenant's support vocabulary, routing, and workflow preferences."""

    organization_id: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=300)
    status: Literal["ACTIVE", "SUSPENDED"] = "ACTIVE"
    products: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    environments: list[str] = Field(default_factory=lambda: ["development", "staging", "production"])
    severity_levels: list[str] = Field(default_factory=lambda: ["low", "medium", "high", "critical"])
    priority_levels: list[str] = Field(default_factory=lambda: ["low", "normal", "high", "urgent"])
    escalation_rules: dict[str, list[str]] = Field(default_factory=dict)
    ownership_rules: dict[str, str] = Field(default_factory=dict)
    repository_mappings: dict[str, str] = Field(default_factory=dict)
    terminology: dict[str, str] = Field(default_factory=dict)
    response_style: Literal["CONCISE", "STANDARD", "DETAILED"] = "STANDARD"
    workflow_policy: WorkflowPolicy = Field(default_factory=WorkflowPolicy)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
