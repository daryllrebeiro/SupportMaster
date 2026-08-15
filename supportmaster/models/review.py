from typing import List, Literal

from pydantic import BaseModel, Field


ReviewStatus = Literal[
    "APPROVED",
    "APPROVED_WITH_WARNINGS",
    "NEEDS_MORE_VALIDATION",
    "NEEDS_IMPLEMENTATION_CHANGES",
    "BLOCKED",
    "REJECTED",
]


ReviewDecision = Literal[
    "PROCEED_TO_HUMAN_REVIEW",
    "RUN_MORE_VALIDATION",
    "RETURN_TO_IMPLEMENTATION",
    "GATHER_MORE_INFORMATION",
    "STOP",
]


ReviewSeverity = Literal[
    "INFO",
    "WARNING",
    "HIGH",
    "CRITICAL",
]


class ReviewFinding(BaseModel):
    """
    Represents a significant finding identified during final review.
    """

    area: str = Field(
        description=(
            "Area being reviewed, such as ROOT_CAUSE, IMPLEMENTATION, "
            "VALIDATION, REGRESSION, SECURITY, PERFORMANCE, SCOPE, "
            "DUPLICATE_WORK, or TESTING."
        )
    )

    finding: str = Field(
        description=(
            "Concise description of the review finding."
        )
    )

    severity: ReviewSeverity = Field(
        description=(
            "Severity of the finding."
        )
    )

    evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete evidence supporting the finding."
        )
    )

    requires_action: bool = Field(
        default=False,
        description=(
            "Whether the finding requires action before the workflow "
            "can proceed."
        )
    )


class ReviewAnalysis(BaseModel):
    """
    Structured output produced by the SupportMaster Review Agent.

    This is the final engineering safety and quality gate before a
    validated implementation can proceed to human review or publication.

    The Review Agent does not modify source code and does not publish
    changes.
    """

    review_status: ReviewStatus = Field(
        description=(
            "Overall result of the final implementation review."
        )
    )

    decision: ReviewDecision = Field(
        description=(
            "Recommended next workflow action based on the complete "
            "investigation, implementation, and validation evidence."
        )
    )

    review_confidence: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ] = Field(
        description=(
            "Confidence in the review decision based on the completeness "
            "and quality of available evidence."
        )
    )

    original_problem: str = Field(
        description=(
            "The original customer-support problem that the workflow "
            "was intended to resolve."
        )
    )

    root_cause_reviewed: str = Field(
        description=(
            "Root cause considered during final review."
        )
    )

    root_cause_sufficiently_established: bool = Field(
        description=(
            "Whether the evidence establishes the root cause strongly "
            "enough to justify the implementation."
        )
    )

    remediation_alignment: bool = Field(
        description=(
            "Whether the implementation aligns with the approved "
            "remediation plan and addresses the established root cause."
        )
    )

    implementation_scope_acceptable: bool = Field(
        description=(
            "Whether the implementation appears appropriately scoped "
            "and avoids unrelated changes."
        )
    )

    duplicate_work_safety_passed: bool = Field(
        description=(
            "Whether duplicate-work verification provides sufficient "
            "confidence that the implementation does not unnecessarily "
            "duplicate existing engineering work."
        )
    )

    validation_sufficient: bool = Field(
        description=(
            "Whether validation evidence is sufficient to support "
            "the implementation's correctness."
        )
    )

    original_problem_resolved: bool = Field(
        description=(
            "Whether available evidence demonstrates that the original "
            "customer problem has been resolved."
        )
    )

    regression_risk_acceptable: bool = Field(
        description=(
            "Whether known regression risks are sufficiently controlled "
            "for the implementation to proceed."
        )
    )

    implementation_reviewable: bool = Field(
        description=(
            "Whether the implementation is complete and sufficiently "
            "documented to undergo human engineering review."
        )
    )

    findings: List[ReviewFinding] = Field(
        default_factory=list,
        description=(
            "Important findings identified during final review."
        )
    )

    strengths: List[str] = Field(
        default_factory=list,
        description=(
            "Important aspects of the investigation, implementation, "
            "or validation that were done correctly."
        )
    )

    blocking_issues: List[str] = Field(
        default_factory=list,
        description=(
            "Issues that prevent the implementation from safely "
            "proceeding."
        )
    )

    required_actions: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete actions required before the workflow can proceed."
        )
    )

    unresolved_risks: List[str] = Field(
        default_factory=list,
        description=(
            "Remaining risks that should be considered during human "
            "review or before publication."
        )
    )

    evidence_summary: List[str] = Field(
        default_factory=list,
        description=(
            "Strongest evidence supporting the final review decision."
        )
    )

    review_summary: str = Field(
        description=(
            "Concise overall assessment of the implementation and "
            "whether it is ready to proceed."
        )
    )

    recommendation: str = Field(
        description=(
            "Detailed recommendation for the next workflow stage."
        )
    )