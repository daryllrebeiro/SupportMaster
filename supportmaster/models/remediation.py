from typing import List, Literal

from pydantic import BaseModel, Field


Priority = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
]

ChangeType = Literal[
    "CODE",
    "CONFIGURATION",
    "DATABASE",
    "INFRASTRUCTURE",
    "DEPENDENCY",
    "DOCUMENTATION",
    "UNKNOWN",
]


class RemediationStep(BaseModel):
    step: int = Field(
        description="Sequential remediation step number."
    )

    action: str = Field(
        description="High-level action that should be performed."
    )

    change_type: ChangeType = Field(
        description="Type of change required."
    )

    priority: Priority = Field(
        description="Priority of this remediation step."
    )

    rationale: str = Field(
        description="Why this remediation step is necessary."
    )

    expected_result: str = Field(
        description="Expected technical result after the step."
    )

    risk: str = Field(
        description="Potential risk introduced by this change."
    )

    validation: str = Field(
        description="How the change should be validated."
    )


class RemediationPlan(BaseModel):
    """
    Structured output produced by the Remediation Planning Agent.

    This model describes what should be changed and how the change
    should be validated without directly modifying source code.
    """

    remediation_status: Literal[
        "READY",
        "NEEDS_MORE_EVIDENCE",
        "BLOCKED",
        "NO_FIX_REQUIRED",
    ] = Field(
        description="Whether remediation planning can proceed."
    )

    objective: str = Field(
        description="Primary objective of the remediation."
    )

    root_cause: str = Field(
        description="Root cause that the remediation is intended to address."
    )

    proposed_approach: str = Field(
        description=(
            "High-level technical approach for addressing the root cause."
        )
    )

    remediation_steps: List[RemediationStep] = Field(
        default_factory=list,
        description="Ordered remediation steps."
    )

    affected_components: List[str] = Field(
        default_factory=list,
        description="Components expected to be modified."
    )

    files_or_areas_to_review: List[str] = Field(
        default_factory=list,
        description=(
            "Known files, modules, classes, or source areas that should "
            "be reviewed before implementation."
        )
    )

    compatibility_considerations: List[str] = Field(
        default_factory=list,
        description=(
            "Compatibility concerns that implementation should consider."
        )
    )

    performance_considerations: List[str] = Field(
        default_factory=list,
        description=(
            "Performance implications that should be evaluated."
        )
    )

    risks: List[str] = Field(
        default_factory=list,
        description="Known risks associated with the proposed remediation."
    )

    testing_strategy: List[str] = Field(
        default_factory=list,
        description="Tests required to validate the remediation."
    )

    regression_scenarios: List[str] = Field(
        default_factory=list,
        description="Existing behavior that must continue working."
    )

    rollout_considerations: List[str] = Field(
        default_factory=list,
        description="High-level deployment or rollout considerations."
    )

    unresolved_questions: List[str] = Field(
        default_factory=list,
        description=(
            "Questions that must be answered before implementation."
        )
    )

    implementation_allowed: bool = Field(
        description=(
            "Whether downstream implementation may proceed based on the "
            "available evidence and safety gates."
        )
    )

    next_action: Literal[
        "IMPLEMENT_FIX",
        "GATHER_MORE_EVIDENCE",
        "REVIEW_EXISTING_WORK",
        "STOP",
    ] = Field(
        description="Recommended next workflow action."
    )