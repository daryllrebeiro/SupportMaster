from typing import List, Literal

from pydantic import BaseModel, Field


Classification = Literal[
    "CONFIRMED",
    "INFERRED",
    "HYPOTHESIS",
    "UNKNOWN",
]

Confidence = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]


class TechnicalSignal(BaseModel):
    category: str = Field(
        description=(
            "Category of the technical signal, such as ERROR, EXCEPTION, "
            "STACK_TRACE, API, SERVICE, DATABASE, CONFIGURATION, VERSION, "
            "or ENVIRONMENT."
        )
    )

    value: str = Field(
        description="The exact or normalized technical signal."
    )

    classification: Classification = Field(
        description=(
            "How strongly the signal is supported: "
            "CONFIRMED, INFERRED, HYPOTHESIS, or UNKNOWN."
        )
    )


class AffectedComponent(BaseModel):
    component: str = Field(
        description="Name of the affected or potentially affected component."
    )

    confidence: Confidence = Field(
        description="Confidence that this component is involved."
    )

    evidence: str = Field(
        description="Evidence supporting the component identification."
    )

    classification: Classification = Field(
        description=(
            "Whether the component identification is confirmed, inferred, "
            "a hypothesis, or unknown."
        )
    )


class TicketAnalysis(BaseModel):
    """
    Structured output produced by the Ticket Analysis Agent.

    This model acts as the contract between the Ticket Analysis Agent
    and downstream SupportMaster agents.
    """

    ticket_id: str = Field(
        description="Support ticket identifier, if available."
    )

    customer_goal: str = Field(
        description="What the customer was attempting to accomplish."
    )

    expected_behavior: str = Field(
        description="What should have happened."
    )

    actual_behavior: str = Field(
        description="What actually happened."
    )

    customer_impact: str = Field(
        description="The impact of the problem on the customer."
    )

    reproducibility: str = Field(
        description=(
            "Whether the issue is deterministic, intermittent, "
            "or unknown."
        )
    )

    product: str = Field(
        default="Not provided",
        description="Product affected by the issue."
    )

    priority: str = Field(
        default="Not provided",
        description="Ticket priority."
    )

    severity: str = Field(
        default="Not provided",
        description="Ticket severity."
    )

    environment: str = Field(
        default="Not provided",
        description="Environment where the issue occurs."
    )

    application_version: str = Field(
        default="Not provided",
        description="Application/product version."
    )

    runtime_version: str = Field(
        default="Not provided",
        description="Runtime/JDK/platform version."
    )

    confirmed_evidence: List[str] = Field(
        default_factory=list,
        description="Facts directly supported by the ticket."
    )

    technical_signals: List[TechnicalSignal] = Field(
        default_factory=list,
        description="Technical signals extracted from the ticket."
    )

    affected_components: List[AffectedComponent] = Field(
        default_factory=list,
        description="Components potentially affected by the issue."
    )

    reproduction_steps: List[str] = Field(
        default_factory=list,
        description="Known steps required to reproduce the issue."
    )

    missing_information: List[str] = Field(
        default_factory=list,
        description="Information required for further investigation."
    )

    search_signals: List[str] = Field(
        default_factory=list,
        description=(
            "Signals that downstream agents can use to search for "
            "related issues, PRs, commits, or source code."
        )
    )