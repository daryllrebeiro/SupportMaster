"""Typed control-plane contracts for authorized SupportMaster actions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


PolicyDisposition = Literal["ALLOW", "DENY", "PAUSE", "REQUEST_INFORMATION"]
ActionType = Literal[
    "INVESTIGATION",
    "IMPLEMENTATION",
    "PUBLISH",
    "PRODUCTION",
    "CUSTOMER_RESPONSE",
    "CLOSE_TICKET",
]
AuthorizationScope = Literal[
    "INVESTIGATION",
    "IMPLEMENTATION",
    "PUBLISH",
    "PRODUCTION",
    "CUSTOMER_RESPONSE",
    "CLOSE_TICKET",
]
TerminalOutcome = Literal[
    "COMPLETED",
    "PAUSED_FOR_HUMAN_REVIEW",
    "BLOCKED",
    "SAFETY_STOP",
    "EXECUTION_FAILED",
]


class PolicyDecision(BaseModel):
    """Deterministic authorization result for one high-impact action."""

    action: ActionType
    disposition: PolicyDisposition
    reason: str
    blocking_reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    evidence_keys: list[str] = Field(default_factory=list)
    policy_version: str = "v1"


class AuthorizationGrant(BaseModel):
    """Scoped permission issued by deterministic policy, never by an LLM."""

    grant_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str | None = None
    scope: AuthorizationScope
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    policy_version: str = "v1"
    gate_decision_id: str | None = None
    evidence_keys: list[str] = Field(default_factory=list)
    human_approval_id: str | None = None
    active: bool = True


class GateDecisionRecord(BaseModel):
    """Append-only audit record for a deterministic gate evaluation."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    gate: str
    route: str
    reason: str
    blocking_reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    evidence_keys: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    policy_version: str = "v1"


class ExternalOperationReceipt(BaseModel):
    """Evidence returned by a real external executor."""

    operation_id: str = Field(default_factory=lambda: str(uuid4()))
    operation_type: str
    requested_action: str
    status: Literal["SUCCEEDED", "FAILED", "PARTIAL", "BLOCKED"]
    external_id: str | None = None
    details: dict[str, str] = Field(default_factory=dict)
    error: str | None = None
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
