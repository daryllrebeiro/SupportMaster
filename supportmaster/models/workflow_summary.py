from typing import List, Literal

from pydantic import BaseModel, Field


WorkflowStatus = Literal[
    "COMPLETED",
    "BLOCKED",
    "REQUIRES_HUMAN_REVIEW",
    "SAFETY_STOP",
    "FAILED",
]


ResolutionStatus = Literal[
    "RESOLVED",
    "PARTIALLY_RESOLVED",
    "NOT_RESOLVED",
    "VERIFICATION_REQUIRED",
    "BLOCKED",
    "NOT_ATTEMPTED",
    "UNKNOWN",
]


Confidence = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
    "UNKNOWN",
]


DuplicateWorkStatus = Literal[
    "NO_DUPLICATE_FOUND",
    "RELATED_WORK_FOUND",
    "DUPLICATE_FOUND",
    "INSUFFICIENT_EVIDENCE",
    "NOT_CHECKED",
    "UNKNOWN",
]


RepositoryStatus = Literal[
    "IDENTIFIED",
    "ANALYZED",
    "NOT_FOUND",
    "ACCESS_BLOCKED",
    "NOT_CHECKED",
    "UNKNOWN",
]


ValidationStatus = Literal[
    "PASSED",
    "PARTIALLY_PASSED",
    "FAILED",
    "INCOMPLETE",
    "NOT_RUN",
    "BLOCKED",
    "UNKNOWN",
]


ImplementationStatus = Literal[
    "IMPLEMENTED",
    "PARTIALLY_IMPLEMENTED",
    "NOT_IMPLEMENTED",
    "NOT_ATTEMPTED",
    "UNKNOWN",
]


CommitStatus = Literal[
    "CREATED",
    "NOT_CREATED",
    "FAILED",
    "NOT_ATTEMPTED",
    "UNKNOWN",
]


PublicationStatus = Literal[
    "PUBLISHED",
    "PARTIALLY_PUBLISHED",
    "BLOCKED",
    "FAILED",
    "NOT_ATTEMPTED",
    "UNKNOWN",
]


PullRequestStatus = Literal[
    "CREATED",
    "NOT_CREATED",
    "FAILED",
    "NOT_ATTEMPTED",
    "UNKNOWN",
]


AuditStatus = Literal[
    "APPROVED",
    "APPROVED_WITH_WARNINGS",
    "BLOCKED",
]


CustomerResponseStatus = Literal[
    "GENERATED",
    "NOT_GENERATED",
    "REQUIRES_REVIEW",
    "BLOCKED",
]


class WorkflowDecision(BaseModel):
    """
    Final machine-readable decision produced by the SupportMaster
    workflow.
    """

    decision: Literal[
        "COMPLETE",
        "STOP",
        "REQUIRES_HUMAN_REVIEW",
        "RETRY",
    ] = Field(
        description=(
            "Final action the workflow should take. COMPLETE means "
            "the workflow may return its result. STOP means it must "
            "not proceed further. REQUIRES_HUMAN_REVIEW means a human "
            "must decide. RETRY means a failed or blocked stage may "
            "be retried."
        )
    )

    reason: str = Field(
        description=(
            "Evidence-based explanation supporting the final workflow "
            "decision."
        )
    )

    confidence: Confidence = Field(
        description="Confidence in the final workflow decision."
    )


class EngineeringOutcome(BaseModel):
    """
    Consolidated engineering outcome of the investigation and
    implementation stages.
    """

    resolution_status: ResolutionStatus = Field(
        description=(
            "Current resolution state of the customer-support issue."
        )
    )

    summary: str = Field(
        description=(
            "Concise evidence-based summary of the engineering outcome."
        )
    )

    root_cause: str = Field(
        default="Not confirmed",
        description=(
            "Confirmed root cause, if established. Hypotheses must "
            "not be presented as confirmed."
        )
    )

    root_cause_confidence: Confidence = Field(
        default="UNKNOWN",
        description=(
            "Confidence in the root-cause determination."
        )
    )

    implementation_status: ImplementationStatus = Field(
        description=(
            "Current state of the implementation."
        )
    )

    fix_summary: str = Field(
        default="No verified fix implemented",
        description=(
            "Summary of the implemented engineering change, if any."
        )
    )


class PullRequestSummary(BaseModel):
    """
    Actual pull-request execution result.

    This represents what happened, not what was merely planned.
    """

    status: PullRequestStatus = Field(
        description=(
            "Actual pull-request creation result."
        )
    )

    identifier: str = Field(
        default="Not available",
        description=(
            "Pull request number or identifier, if actually created."
        )
    )

    title: str = Field(
        default="Not available",
        description="Actual pull request title, if available."
    )

    url: str = Field(
        default="Not available",
        description=(
            "URL of the pull request, only when creation succeeded "
            "and the URL is known."
        )
    )

    base_branch: str = Field(
        default="Not available",
        description="Target branch of the pull request."
    )

    head_branch: str = Field(
        default="Not available",
        description="Source branch of the pull request."
    )


class CommitSummary(BaseModel):
    """
    Actual Git commit result.

    This must describe executed Git operations rather than planned
    operations.
    """

    status: CommitStatus = Field(
        description="Actual commit operation result."
    )

    branch: str = Field(
        default="Not available",
        description="Branch on which the commit was created."
    )

    commit_hash: str = Field(
        default="Not available",
        description="Commit SHA, if a commit was successfully created."
    )

    commit_message: str = Field(
        default="Not available",
        description="Actual commit message used."
    )


class PublicationSummary(BaseModel):
    """
    Consolidated Git publication result.
    """

    status: PublicationStatus = Field(
        description=(
            "Actual publication state of the implementation."
        )
    )

    repository: str = Field(
        default="Not available",
        description="Repository used for publication."
    )

    branch: str = Field(
        default="Not available",
        description="Branch used for publication."
    )

    commit: CommitSummary = Field(
        default_factory=CommitSummary,
        description="Actual Git commit result."
    )

    pull_request: PullRequestSummary = Field(
        default_factory=PullRequestSummary,
        description="Actual pull-request result."
    )

    files_published: List[str] = Field(
        default_factory=list,
        description=(
            "Files actually included in the publication."
        )
    )


class WorkflowSummary(BaseModel):
    """
    Final structured contract for the SupportMaster workflow.

    This model consolidates investigation, implementation, validation,
    publication, resolution, customer communication, and final audit
    results into a single downstream-consumable result.

    The model describes actual workflow outcomes and verified evidence.
    Planned operations must not be represented as completed operations.
    """

    workflow_status: WorkflowStatus = Field(
        description=(
            "Overall lifecycle state of the SupportMaster workflow."
        )
    )

    ticket_id: str = Field(
        default="Not provided",
        description=(
            "Support ticket identifier, if available."
        )
    )

    customer_goal: str = Field(
        description=(
            "What the customer was trying to accomplish."
        )
    )

    problem_summary: str = Field(
        description=(
            "Concise description of the original customer problem."
        )
    )

    customer_impact: str = Field(
        description=(
            "Impact of the reported issue on the customer."
        )
    )

    engineering_outcome: EngineeringOutcome = Field(
        description=(
            "Consolidated engineering and resolution outcome."
        )
    )

    duplicate_work_status: DuplicateWorkStatus = Field(
        description=(
            "Actual result of duplicate-work verification."
        )
    )

    repository_status: RepositoryStatus = Field(
        description=(
            "Actual state of repository/source-code investigation."
        )
    )

    validation_status: ValidationStatus = Field(
        description=(
            "Actual validation/testing state."
        )
    )

    implementation_status: ImplementationStatus = Field(
        description=(
            "Actual implementation state."
        )
    )

    implementation_summary: str = Field(
        default="No verified implementation",
        description=(
            "Concise summary of the engineering implementation."
        )
    )

    publication: PublicationSummary = Field(
        default_factory=PublicationSummary,
        description=(
            "Actual Git publication and pull-request outcome."
        )
    )

    audit_status: AuditStatus = Field(
        description=(
            "Final safety-audit disposition."
        )
    )

    customer_response_status: CustomerResponseStatus = Field(
        description=(
            "State of the customer-facing response."
        )
    )

    customer_response: str = Field(
        default="Not generated",
        description=(
            "Final customer-facing response, if generated and "
            "supported by the workflow evidence."
        )
    )

    workflow_decision: WorkflowDecision = Field(
        description=(
            "Final machine-readable decision for the workflow."
        )
    )

    completed_stages: List[str] = Field(
        default_factory=list,
        description=(
            "Workflow stages that actually completed successfully."
        )
    )

    blocked_stages: List[str] = Field(
        default_factory=list,
        description=(
            "Workflow stages that were blocked or could not complete."
        )
    )

    important_findings: List[str] = Field(
        default_factory=list,
        description=(
            "Important evidence-based technical or workflow findings."
        )
    )

    remaining_unknowns: List[str] = Field(
        default_factory=list,
        description=(
            "Important information that remains unknown or unverified."
        )
    )

    remaining_work: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete work that remains before the issue or workflow "
            "can be considered fully complete."
        )
    )

    recommended_next_steps: List[str] = Field(
        default_factory=list,
        description=(
            "Recommended actions following the final workflow outcome."
        )
    )

    evidence_references: List[str] = Field(
        default_factory=list,
        description=(
            "Important evidence references supporting the final "
            "workflow summary."
        )
    )

    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "Non-blocking warnings or limitations that should be "
            "surfaced to downstream consumers."
        )
    )
