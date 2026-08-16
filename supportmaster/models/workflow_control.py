from typing import List, Literal

from pydantic import BaseModel, Field


WorkflowDecision = Literal[
    "CONTINUE",
    "STOP",
    "REQUEST_INFORMATION",
    "HUMAN_REVIEW_REQUIRED",
    "SAFETY_STOP",
    "READY_FOR_IMPLEMENTATION",
    "READY_FOR_PUBLISH",
]


WorkflowStage = Literal[
    "TICKET_ANALYSIS",
    "INVESTIGATION",
    "EVIDENCE_ANALYSIS",
    "DUPLICATE_CHECK",
    "REPOSITORY_ANALYSIS",
    "ROOT_CAUSE_ANALYSIS",
    "VALIDATION",
    "IMPLEMENTATION",
    "TESTING",
    "COMMIT_PLANNING",
    "PUBLISHING",
    "PR_CREATION",
    "CUSTOMER_RESPONSE",
    "WORKFLOW_SUMMARY",
    "ESCALATION",
    "COMPLETED",
]


GateStatus = Literal[
    "PASSED",
    "FAILED",
    "NOT_RUN",
    "NOT_REQUIRED",
    "UNKNOWN",
]


AuthorizationLevel = Literal[
    "NONE",
    "INVESTIGATION_ONLY",
    "IMPLEMENTATION",
    "PUBLISH",
    "HUMAN_APPROVAL_REQUIRED",
]


class SafetyGate(BaseModel):
    """
    Structured representation of an individual workflow safety gate.
    """

    name: str = Field(
        description=(
            "Name of the safety gate, such as DUPLICATE_CHECK, "
            "EVIDENCE_CHECK, VALIDATION_CHECK, or PRODUCTION_APPROVAL."
        )
    )

    status: GateStatus = Field(
        description="Current status of the safety gate."
    )

    reason: str = Field(
        description=(
            "Evidence-based explanation for the current gate status."
        )
    )


class WorkflowControl(BaseModel):
    """
    Control-plane decision produced by the SupportMaster Workflow Control
    Agent.

    This is the orchestration contract between the decision layer and
    the workflow executor.

    It determines:

    - where the workflow currently is
    - what should happen next
    - whether autonomous execution is permitted
    - whether implementation is permitted
    - whether publishing is permitted
    - whether human intervention is required
    - which safety gates support the decision
    """

    # ================================================================
    # WORKFLOW POSITION
    # ================================================================

    current_stage: WorkflowStage = Field(
        description=(
            "The workflow stage currently being evaluated."
        )
    )

    next_stage: WorkflowStage = Field(
        description=(
            "The next workflow stage recommended by the control decision."
        )
    )

    # ================================================================
    # PRIMARY DECISION
    # ================================================================

    decision: WorkflowDecision = Field(
        description=(
            "The authoritative control-plane decision. "
            "CONTINUE permits normal progression. "
            "READY_FOR_IMPLEMENTATION explicitly authorizes source-code "
            "modification. "
            "READY_FOR_PUBLISH explicitly authorizes the publishing "
            "stage. "
            "REQUEST_INFORMATION requires additional information. "
            "HUMAN_REVIEW_REQUIRED requires human intervention. "
            "STOP prevents autonomous continuation."
        )
    )

    reason: str = Field(
        description=(
            "Concise, evidence-based explanation of the decision."
        )
    )

    # ================================================================
    # AUTHORIZATION
    # ================================================================

    authorization: AuthorizationLevel = Field(
        description=(
            "Highest level of autonomous action currently authorized."
        )
    )

    autonomous_continuation_allowed: bool = Field(
        description=(
            "Whether the workflow may proceed automatically to the "
            "recommended next stage."
        )
    )

    autonomous_modification_allowed: bool = Field(
        default=False,
        description=(
            "Whether autonomous source-code modification is explicitly "
            "authorized."
        )
    )

    autonomous_publish_allowed: bool = Field(
        default=False,
        description=(
            "Whether autonomous commit, push, publish, or pull-request "
            "creation is explicitly authorized."
        )
    )

    human_review_required: bool = Field(
        default=False,
        description=(
            "Whether human review or approval is required before the "
            "workflow may continue."
        )
    )

    # ================================================================
    # SAFETY GATES
    # ================================================================

    safety_gates: List[SafetyGate] = Field(
        default_factory=list,
        description=(
            "Individual safety gates evaluated for the current "
            "workflow decision."
        )
    )

    safety_checks_passed: List[str] = Field(
        default_factory=list,
        description=(
            "Safety conditions explicitly confirmed by available "
            "evidence."
        )
    )

    safety_checks_failed: List[str] = Field(
        default_factory=list,
        description=(
            "Safety conditions that failed or could not be established."
        )
    )

    # ================================================================
    # BLOCKERS AND ACTIONS
    # ================================================================

    blocking_reasons: List[str] = Field(
        default_factory=list,
        description=(
            "Specific evidence-based conditions preventing autonomous "
            "continuation."
        )
    )

    required_actions: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete actions that must occur before the blocked "
            "workflow can safely continue."
        )
    )

    unresolved_questions: List[str] = Field(
        default_factory=list,
        description=(
            "Material unanswered questions that affect the current "
            "workflow decision."
        )
    )

    # ================================================================
    # WORKFLOW PROGRESS
    # ================================================================

    completed_stages: List[WorkflowStage] = Field(
        default_factory=list,
        description=(
            "Workflow stages for which successful completion is "
            "supported by evidence."
        )
    )

    pending_stages: List[WorkflowStage] = Field(
        default_factory=list,
        description=(
            "Workflow stages that remain before the workflow can "
            "reach completion."
        )
    )

    # ================================================================
    # TRACEABILITY
    # ================================================================

    evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Important evidence supporting the control-plane decision."
        )
    )

    confidence: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ] = Field(
        description=(
            "Confidence in the control decision based on the quality "
            "and completeness of available evidence."
        )
    )
