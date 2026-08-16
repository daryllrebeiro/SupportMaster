"""Scoped human-review and resume contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from .control import AuthorizationScope


ReviewTaskStatus = Literal["OPEN", "APPROVED", "REJECTED", "EXPIRED", "RESUMED"]
ReviewDecisionType = Literal["APPROVE", "REJECT"]


class HumanReviewDecision(BaseModel):
    """A reviewer decision scoped to specific autonomous capabilities."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    reviewer: str
    decision: ReviewDecisionType
    approved_scopes: list[AuthorizationScope] = Field(default_factory=list)
    comment: str = ""
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HumanReviewTask(BaseModel):
    """Durable pause point for a workflow requiring human action."""

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    status: ReviewTaskStatus = "OPEN"
    reason: str
    blocking_reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    evidence_keys: list[str] = Field(default_factory=list)
    allowed_scopes: list[AuthorizationScope] = Field(default_factory=list)
    resume_condition: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    decision: HumanReviewDecision | None = None
