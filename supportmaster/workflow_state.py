"""Typed state shared by the SupportMaster orchestration graph.

The existing agents write these values through their ``output_key`` settings.
Keeping the keys in one contract lets orchestration nodes make decisions from
structured state instead of parsing agent prose.
"""

from __future__ import annotations

from typing import Optional

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

    last_gate_decision: Optional["GateDecision"] = Field(default=None)
    terminal_status: Optional["TerminalStatus"] = None


from typing import Literal

GateName = Literal["DUPLICATE_WORK", "REVIEW", "VALIDATION", "AUDIT"]
GateRoute = Literal[
    "CONTINUE",
    "STOP",
    "REQUEST_INFORMATION",
    "HUMAN_REVIEW_REQUIRED",
    "READY_FOR_IMPLEMENTATION",
    "READY_FOR_PUBLISH",
    "COMPLETED",
]
TerminalStatus = Literal["COMPLETED", "BLOCKED", "HUMAN_REVIEW_REQUIRED"]


class GateDecision(BaseModel):
    """Deterministic routing result emitted by an orchestration gate."""

    gate: GateName
    route: GateRoute
    reason: str
    blocking_reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    evidence_keys: list[str] = Field(default_factory=list)


# Resolve forward references used by SupportMasterState.
SupportMasterState.model_rebuild()
