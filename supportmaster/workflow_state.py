"""Typed state shared by the SupportMaster orchestration graph.

The existing agents write these values through their ``output_key`` settings.
Keeping the keys in one contract lets orchestration nodes make decisions from
structured state instead of parsing agent prose.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models.audit import WorkflowAudit
from .models.code_change import CodeChangeResult
from .models.customer_response import CustomerResponse
from .models.duplicate_work import DuplicateWorkAnalysis
from .models.evidence import EvidenceAnalysis
from .models.escalation import EscalationAnalysis
from .models.github_publish import GitHubPublishResult
from .models.implementation import ImplementationResult
from .models.investigation import InvestigationPlan
from .models.publish import PublishPlan
from .models.remediation import RemediationPlan
from .models.repository import RepositoryAnalysis
from .models.resolution import ResolutionAnalysis
from .models.review import ReviewAnalysis
from .models.root_cause import RootCauseAnalysis
from .models.test_result import TestResult
from .models.ticket import TicketAnalysis
from .models.validation import ValidationAnalysis
from .models.workflow_control import WorkflowControl
from .models.workflow_summary import WorkflowSummary


GateName = Literal["DUPLICATE_WORK", "REVIEW", "VALIDATION", "AUDIT"]
GateRoute = Literal[
    "CONTINUE",
    "STOP",
    "REQUEST_INFORMATION",
    # Retained for compatibility with older persisted events. New gates
    # never emit this route; blocked automation terminates with SAFETY_STOP.
    "HUMAN_REVIEW_REQUIRED",
    "SAFETY_STOP",
    "READY_FOR_IMPLEMENTATION",
    "READY_FOR_PUBLISH",
    "COMPLETED",
]
TerminalStatus = Literal["COMPLETED", "BLOCKED", "SAFETY_STOP", "HUMAN_REVIEW_REQUIRED"]


class AutonomousStop(BaseModel):
    """Machine-readable terminal result for a fail-closed autonomous run."""

    status: Literal["SAFETY_STOP"] = "SAFETY_STOP"
    gate: GateName
    reason: str
    blocking_reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    evidence_keys: list[str] = Field(default_factory=list)
    autonomous_continuation_allowed: bool = False


OUTPUT_KEY_TO_STATE_FIELD: dict[str, str] = {
    "ticket_analysis": "ticket_analysis",
    "investigation_plan": "investigation_plan",
    "duplicate_work_analysis": "duplicate_work_analysis",
    "evidence_analysis": "evidence_analysis",
    "repository_analysis": "repository_analysis",
    "root_cause_analysis": "root_cause_analysis",
    "remediation_plan": "remediation_plan",
    "review_analysis": "review_analysis",
    "code_change_result": "code_change_result",
    "implementation_result": "implementation_result",
    "validation_analysis": "validation_analysis",
    "test_result": "test_result",
    "publish_plan": "publish_plan",
    "github_publish_result": "github_publish_result",
    "resolution_analysis": "resolution_analysis",
    "customer_response": "customer_response",
    "workflow_audit": "workflow_audit",
    "escalation_analysis": "escalation_analysis",
    "workflow_summary": "workflow_summary",
    "workflow_control": "workflow_control",
    "autonomous_stop": "autonomous_stop",
}


class SupportMasterState(BaseModel):
    """State contract for the agent outputs and orchestration decisions."""

    model_config = ConfigDict(extra="allow")

    ticket_analysis: Optional[TicketAnalysis] = None
    investigation_plan: Optional[InvestigationPlan] = None
    duplicate_work_analysis: Optional[DuplicateWorkAnalysis] = None
    evidence_analysis: Optional[EvidenceAnalysis] = None
    repository_analysis: Optional[RepositoryAnalysis] = None
    root_cause_analysis: Optional[RootCauseAnalysis] = None
    remediation_plan: Optional[RemediationPlan] = None
    review_analysis: Optional[ReviewAnalysis] = None
    code_change_result: Optional[CodeChangeResult] = None
    implementation_result: Optional[ImplementationResult] = None
    validation_analysis: Optional[ValidationAnalysis] = None
    test_result: Optional[TestResult] = None
    publish_plan: Optional[PublishPlan] = None
    github_publish_result: Optional[GitHubPublishResult] = None
    resolution_analysis: Optional[ResolutionAnalysis] = None
    customer_response: Optional[CustomerResponse] = None
    workflow_audit: Optional[WorkflowAudit] = None
    escalation_analysis: Optional[EscalationAnalysis] = None
    workflow_summary: Optional[WorkflowSummary] = None
    workflow_control: Optional[WorkflowControl] = None
    autonomous_stop: Optional[AutonomousStop] = None

    last_gate_decision: Optional["GateDecision"] = Field(default=None)
    terminal_status: Optional[TerminalStatus] = None
    autonomous_best_effort: bool = False
    uncertainty_flags: list[str] = Field(default_factory=list)


class GateDecision(BaseModel):
    """Deterministic routing result emitted by an orchestration gate."""

    gate: GateName
    route: GateRoute
    reason: str
    blocking_reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    evidence_keys: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# Resolve forward references used by SupportMasterState.
SupportMasterState.model_rebuild()
