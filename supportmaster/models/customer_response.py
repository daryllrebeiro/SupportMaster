from typing import List, Literal

from pydantic import BaseModel, Field


ResponseStatus = Literal[
    "RESOLVED",
    "PARTIALLY_RESOLVED",
    "VERIFICATION_REQUIRED",
    "BLOCKED",
    "NOT_RESOLVED",
]


MessageTone = Literal[
    "PROFESSIONAL",
    "REASSURING",
    "INFORMATIONAL",
]


CommunicationType = Literal[
    "RESOLUTION",
    "PROGRESS_UPDATE",
    "VERIFICATION_REQUEST",
    "BLOCKED_UPDATE",
    "NOT_RESOLVED_UPDATE",
]


CustomerConfirmationStatus = Literal[
    "CONFIRMED",
    "NOT_REQUIRED",
    "PENDING",
    "NOT_AVAILABLE",
]


EvidenceStrength = Literal[
    "STRONG",
    "MODERATE",
    "LIMITED",
    "INSUFFICIENT",
]


class CustomerResponse(BaseModel):
    """
    Structured customer-facing communication produced by SupportMaster.

    This model represents communication derived from the verified
    SupportMaster workflow state.

    It must never claim that an issue is resolved, deployed, verified,
    or customer-confirmed unless the underlying workflow evidence
    supports that claim.
    """

    ticket_id: str = Field(
        default="Not provided",
        description=(
            "Support ticket identifier, if available. "
            "Never invent a ticket identifier."
        ),
    )

    response_status: ResponseStatus = Field(
        description=(
            "Current resolution state that can safely be communicated "
            "to the customer."
        ),
    )

    communication_type: CommunicationType = Field(
        description=(
            "Purpose of the customer communication."
        ),
    )

    subject: str = Field(
        description=(
            "Concise customer-facing subject appropriate for the "
            "current response status."
        ),
    )

    summary: str = Field(
        description=(
            "Concise explanation of the original issue and its current "
            "state, using only verified information."
        ),
    )

    resolution: str = Field(
        default="No confirmed resolution to communicate.",
        description=(
            "Customer-facing explanation of what was resolved, if "
            "anything. Must not claim resolution without sufficient "
            "evidence."
        ),
    )

    verification: str = Field(
        default="Verification details are not available.",
        description=(
            "Customer-facing explanation of validation or verification "
            "that actually occurred."
        ),
    )

    customer_impact: str = Field(
        description=(
            "What the current outcome means for the customer."
        ),
    )

    resolution_confidence: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ] = Field(
        description=(
            "Confidence in the communicated resolution status based "
            "on the available technical evidence."
        ),
    )

    evidence_strength: EvidenceStrength = Field(
        description=(
            "Overall strength of the evidence supporting the customer "
            "communication."
        ),
    )

    evidence_basis: List[str] = Field(
        default_factory=list,
        description=(
            "Concise, evidence-backed facts used to construct the "
            "customer response."
        ),
    )

    customer_confirmation_status: CustomerConfirmationStatus = Field(
        description=(
            "Whether customer confirmation exists, is required, is "
            "pending, or is not applicable."
        ),
    )

    customer_confirmation_required: bool = Field(
        description=(
            "Whether customer confirmation is required before the "
            "support issue should be considered fully closed."
        ),
    )

    customer_action_required: bool = Field(
        description=(
            "Whether the customer needs to perform an action."
        ),
    )

    customer_action: str = Field(
        default="No customer action required.",
        description=(
            "Specific action requested from the customer, if any."
        ),
    )

    remaining_work: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete engineering, verification, deployment, or "
            "customer-confirmation work that remains."
        ),
    )

    limitations: List[str] = Field(
        default_factory=list,
        description=(
            "Important limitations or uncertainties that materially "
            "affect what can safely be communicated."
        ),
    )

    next_steps: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete next steps for the customer or support team."
        ),
    )

    tone: MessageTone = Field(
        description="Tone used for the customer-facing response."
    )

    safe_to_send: bool = Field(
        description=(
            "Whether the generated customer response is sufficiently "
            "evidence-based and appropriate to send without additional "
            "human review."
        ),
    )

    requires_human_review: bool = Field(
        description=(
            "Whether a human support or engineering reviewer should "
            "review the response before it is sent."
        ),
    )

    internal_notes: List[str] = Field(
        default_factory=list,
        description=(
            "Internal-only notes explaining important reasoning, "
            "uncertainty, or evidence limitations. These must not be "
            "included in the customer-facing message."
        ),
    )

    unsupported_claims: List[str] = Field(
        default_factory=list,
        description=(
            "Claims that were considered but intentionally excluded "
            "because they were not supported by evidence."
        ),
    )

    full_response: str = Field(
        description=(
            "Complete customer-facing response ready for review or "
            "delivery. It must contain only information appropriate "
            "for the customer."
        ),
    )