from typing import List, Literal

from pydantic import BaseModel, Field


EscalationStatus = Literal[
    "NO_ESCALATION_REQUIRED",
    "HUMAN_REVIEW_REQUIRED",
    "WORKFLOW_BLOCKED",
    "SAFETY_STOP",
]


EscalationReason = Literal[
    "NONE",
    "DUPLICATE_WORK_FOUND",
    "DUPLICATE_VERIFICATION_INCOMPLETE",
    "INSUFFICIENT_EVIDENCE",
    "CONFLICTING_EVIDENCE",
    "ROOT_CAUSE_UNCERTAIN",
    "REPOSITORY_UNAVAILABLE",
    "VALIDATION_FAILED",
    "VALIDATION_INCOMPLETE",
    "HIGH_RISK_CHANGE",
    "SECURITY_CONCERN",
    "DATA_INTEGRITY_RISK",
    "PRODUCTION_ACTION_REQUIRED",
    "DEPLOYMENT_REQUIRED",
    "IMPLEMENTATION_BLOCKED",
    "PUBLISH_BLOCKED",
    "CUSTOMER_INFORMATION_REQUIRED",
    "HUMAN_APPROVAL_REQUIRED",
    "WORKFLOW_INCONSISTENCY",
    "OTHER",
]


EscalationPriority = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
]


WorkflowStage = Literal[
    "TICKET_ANALYSIS",
    "INVESTIGATION",
    "EVIDENCE",
    "DUPLICATE_WORK",
    "REPOSITORY",
    "VALIDATION",
    "IMPLEMENTATION",
    "PUBLISH",
    "PULL_REQUEST",
    "RESOLUTION",
    "AUDIT",
    "CUSTOMER_RESPONSE",
    "WORKFLOW_SUMMARY",
    "HUMAN_REVIEW",
]


class EscalationAction(BaseModel):
    """
    A concrete action that must be performed by a human before
    autonomous processing can safely continue.
    """

    action: str = Field(
        description=(
            "Specific action required from the human engineer, "
            "support owner, reviewer, or release owner."
        )
    )

    reason: str = Field(
        description=(
            "Evidence-based explanation of why the action is required."
        )
    )

    priority: EscalationPriority = Field(
        description="Priority of the required human action."
    )

    required_role: str = Field(
        default="Engineering",
        description=(
            "Role best suited to perform the action, such as "
            "Engineering, Support, QA, Security, or Release Engineering."
        )
    )

    blocking: bool = Field(
        default=True,
        description=(
            "Whether this action must be completed before the "
            "autonomous workflow may continue."
        )
    )


class EscalationAnalysis(BaseModel):
    """
    Final escalation and autonomous-continuation decision for the
    SupportMaster workflow.

    This model acts as the safety boundary between autonomous
    engineering execution and human intervention.
    """

    ticket_id: str = Field(
        default="Not provided",
        description=(
            "Support ticket identifier associated with the escalation."
        )
    )

    escalation_status: EscalationStatus = Field(
        description=(
            "Overall escalation decision for the current workflow state."
        )
    )

    reason: EscalationReason = Field(
        description=(
            "Primary evidence-based reason for the escalation decision. "
            "Use NONE when no escalation is required."
        )
    )

    priority: EscalationPriority = Field(
        description=(
            "Overall priority of the escalation decision."
        )
    )

    summary: str = Field(
        description=(
            "Concise explanation of the escalation decision and its "
            "impact on autonomous workflow execution."
        )
    )

    safety_gate_passed: bool = Field(
        description=(
            "Whether all mandatory safety conditions required for "
            "autonomous continuation have passed."
        )
    )

    autonomous_continuation_allowed: bool = Field(
        description=(
            "Whether downstream autonomous agents are permitted to "
            "continue execution."
        )
    )

    blocking_factors: List[str] = Field(
        default_factory=list,
        description=(
            "Specific evidence-based conditions preventing autonomous "
            "continuation."
        )
    )

    required_human_actions: List[EscalationAction] = Field(
        default_factory=list,
        description=(
            "Concrete actions that a human must or should perform "
            "before the workflow can safely continue."
        )
    )

    unresolved_questions: List[str] = Field(
        default_factory=list,
        description=(
            "Important unanswered questions that materially affect "
            "the safety or correctness of the workflow."
        )
    )

    affected_workflow_stages: List[WorkflowStage] = Field(
        default_factory=list,
        description=(
            "Workflow stages affected by the escalation decision."
        )
    )

    evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Specific evidence supporting the escalation decision. "
            "Evidence must come from previous workflow outputs and "
            "must not be invented."
        )
    )

    confidence: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ] = Field(
        description=(
            "Confidence that the escalation decision accurately "
            "reflects the available workflow evidence."
        )
    )

    recommended_next_stage: WorkflowStage = Field(
        description=(
            "Next workflow stage that should execute if the workflow "
            "is allowed to proceed."
        )
    )

    resume_condition: str = Field(
        description=(
            "Condition that must be satisfied before the workflow may "
            "resume autonomous execution. Use 'None required' when "
            "autonomous continuation is allowed."
        )
    )

    final_recommendation: str = Field(
        description=(
            "Concise recommendation for how SupportMaster should "
            "proceed from the current workflow state."
        )
    )