from typing import List, Literal, Optional

from pydantic import BaseModel, Field


ResolutionStatus = Literal[
    "RESOLVED",
    "PARTIALLY_RESOLVED",
    "VERIFICATION_REQUIRED",
    "BLOCKED",
    "NOT_RESOLVED",
]


Confidence = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]


VerificationResult = Literal[
    "PASSED",
    "FAILED",
    "NOT_RUN",
    "BLOCKED",
    "UNKNOWN",
]


EvidenceClassification = Literal[
    "CONFIRMED",
    "STRONGLY_SUPPORTED",
    "INFERRED",
    "CONTRADICTED",
    "UNKNOWN",
]


ResolutionGateStatus = Literal[
    "PASSED",
    "FAILED",
    "NOT_APPLICABLE",
    "UNKNOWN",
]


RecommendedAction = Literal[
    "CLOSE_TICKET",
    "REQUEST_CUSTOMER_CONFIRMATION",
    "RUN_ADDITIONAL_VALIDATION",
    "REVIEW_IMPLEMENTATION",
    "CONTINUE_INVESTIGATION",
    "REVIEW_PUBLICATION",
    "BLOCK",
]


class VerificationCheck(BaseModel):
    """
    Individual verification performed as part of final resolution
    assessment.
    """

    name: str = Field(
        description="Name of the verification check."
    )

    objective: str = Field(
        description="What the check was intended to verify."
    )

    result: VerificationResult = Field(
        description=(
            "Actual result of the verification: PASSED, FAILED, "
            "NOT_RUN, BLOCKED, or UNKNOWN."
        )
    )

    expected_result: str = Field(
        description="Expected result if the issue is correctly resolved."
    )

    actual_result: str = Field(
        default="Not available",
        description="Observed result of the verification."
    )

    evidence: List[str] = Field(
        default_factory=list,
        description="Evidence supporting the verification result."
    )

    confidence: Confidence = Field(
        description="Confidence in the verification result."
    )

    blocking: bool = Field(
        default=False,
        description=(
            "Whether failure or absence of this verification prevents "
            "the issue from being considered resolved."
        )
    )


class ResolutionEvidence(BaseModel):
    """
    Evidence used to determine whether the customer issue is actually
    resolved.
    """

    source: str = Field(
        description=(
            "Source of evidence, such as automated tests, CI, runtime "
            "verification, logs, code inspection, commit, pull request, "
            "or customer confirmation."
        )
    )

    evidence: str = Field(
        description="Specific evidence supporting or contradicting resolution."
    )

    classification: EvidenceClassification = Field(
        description=(
            "Strength and direction of the evidence regarding resolution."
        )
    )

    relevant_to: str = Field(
        description=(
            "What aspect of resolution this evidence supports, such as "
            "root cause, implementation, regression safety, or customer "
            "behavior."
        )
    )


class ResolutionGate(BaseModel):
    """
    High-level safety gate used to determine whether the issue can be
    considered resolved.
    """

    name: str = Field(
        description="Name of the resolution gate."
    )

    status: ResolutionGateStatus = Field(
        description="Status of the resolution gate."
    )

    evidence: List[str] = Field(
        default_factory=list,
        description="Evidence supporting the gate decision."
    )

    blocking: bool = Field(
        default=False,
        description=(
            "Whether failure or uncertainty in this gate prevents "
            "resolution."
        )
    )


class ResolutionAnalysis(BaseModel):
    """
    Final resolution assessment produced by the SupportMaster
    Resolution Agent.

    This model determines whether the original support issue can be
    considered resolved based on implementation, validation,
    publication, regression, and customer-impact evidence.

    It represents an assessment only. It does not itself close or
    modify the support ticket.
    """

    ticket_id: Optional[str] = Field(
        default=None,
        description="Support ticket identifier, if available."
    )

    resolution_status: ResolutionStatus = Field(
        description="Overall status of the customer-support issue."
    )

    summary: str = Field(
        description=(
            "Concise evidence-based explanation of the final resolution "
            "status."
        )
    )

    original_problem: str = Field(
        description="The original customer problem being addressed."
    )

    root_cause: str = Field(
        description="Established or best-supported root cause."
    )

    implemented_change: str = Field(
        description=(
            "Summary of the implementation that was actually performed."
        )
    )

    expected_resolution: str = Field(
        description=(
            "Observable behavior that should occur when the issue is "
            "successfully resolved."
        )
    )

    observed_behavior: str = Field(
        default="Not verified",
        description=(
            "Observed behavior after implementation and validation."
        )
    )

    implementation_gate: ResolutionGate = Field(
        description=(
            "Whether the intended implementation was actually completed "
            "and matches the approved remediation."
        )
    )

    validation_gate: ResolutionGate = Field(
        description=(
            "Whether sufficient technical validation demonstrates that "
            "the implementation works."
        )
    )

    publication_gate: ResolutionGate = Field(
        description=(
            "Whether the validated implementation was safely published, "
            "when publication is required."
        )
    )

    regression_gate: ResolutionGate = Field(
        description=(
            "Whether available evidence indicates that unacceptable "
            "regressions were not introduced."
        )
    )

    customer_impact_gate: ResolutionGate = Field(
        description=(
            "Whether the expected customer-facing behavior has been "
            "verified or sufficiently established."
        )
    )

    verification_checks: List[VerificationCheck] = Field(
        default_factory=list,
        description="Detailed verification checks and their results."
    )

    resolution_evidence: List[ResolutionEvidence] = Field(
        default_factory=list,
        description=(
            "Evidence supporting or contradicting the final resolution."
        )
    )

    blocking_issues: List[str] = Field(
        default_factory=list,
        description=(
            "Issues that prevent the support case from being considered "
            "resolved."
        )
    )

    remaining_risks: List[str] = Field(
        default_factory=list,
        description=(
            "Known risks or limitations that remain after the change."
        )
    )

    remaining_work: List[str] = Field(
        default_factory=list,
        description=(
            "Work that must still be completed before the issue can "
            "be considered fully resolved."
        )
    )

    regression_concerns: List[str] = Field(
        default_factory=list,
        description=(
            "Observed or credible regression concerns supported by "
            "available evidence."
        )
    )

    customer_impact_after_change: str = Field(
        description=(
            "Expected or verified customer impact after the implementation."
        )
    )

    customer_confirmation_required: bool = Field(
        default=False,
        description=(
            "Whether customer confirmation is required before the "
            "ticket can be considered fully resolved."
        )
    )

    confidence: Confidence = Field(
        description=(
            "Overall confidence that the original customer issue has "
            "actually been resolved."
        )
    )

    recommended_action: RecommendedAction = Field(
        description=(
            "Next workflow action based on the final resolution evidence."
        )
    )

    ticket_closure_allowed: bool = Field(
        description=(
            "Whether the available evidence is sufficient for the "
            "SupportMaster workflow to consider the ticket eligible "
            "for closure."
        )
    )