from typing import List, Literal

from pydantic import BaseModel, Field


Confidence = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]

Priority = Literal[
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW",
]

NextAgent = Literal[
    "DUPLICATE_WORK_AGENT",
    "REPOSITORY_AGENT",
    "EVIDENCE_AGENT",
    "MORE_INFORMATION_REQUIRED",
]


class Hypothesis(BaseModel):
    description: str = Field(
        description="The possible root-cause explanation."
    )

    confidence: Confidence = Field(
        description="Confidence that this is a plausible hypothesis."
    )

    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence supporting the hypothesis."
    )

    evidence_against: List[str] = Field(
        default_factory=list,
        description="Evidence that weakens or contradicts the hypothesis."
    )

    what_to_inspect: List[str] = Field(
        default_factory=list,
        description="Evidence or implementation details that should be inspected."
    )

    confirmation_criteria: List[str] = Field(
        default_factory=list,
        description="Evidence that would confirm the hypothesis."
    )

    rejection_criteria: List[str] = Field(
        default_factory=list,
        description="Evidence that would reject the hypothesis."
    )


class InvestigationArea(BaseModel):
    area: str = Field(
        description="Investigation area, such as APPLICATION_CODE, MEMORY, DATABASE, or CONFIGURATION."
    )

    what_to_inspect: List[str] = Field(
        default_factory=list,
        description="Things that should be inspected in this area."
    )

    why: str = Field(
        description="Why this investigation area is relevant."
    )

    expected_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence expected from investigating this area."
    )


class SearchPlan(BaseModel):
    search_target: str = Field(
        description="System or source to search, such as Jira, GitHub, Bitbucket, or source code."
    )

    search_signals: List[str] = Field(
        default_factory=list,
        description="Signals that should be used when performing the search."
    )

    purpose: str = Field(
        description="Purpose of performing this search."
    )

    expected_useful_result: str = Field(
        description="What useful information the search may reveal."
    )


class InvestigationStep(BaseModel):
    priority: Priority = Field(
        description="Priority of this investigation action."
    )

    action: str = Field(
        description="Specific investigation action to perform."
    )

    reason: str = Field(
        description="Why this action should be performed."
    )

    expected_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence expected from this investigation step."
    )

    hypotheses_tested: List[str] = Field(
        default_factory=list,
        description="Hypotheses that this step helps confirm or reject."
    )


class InvestigationPlan(BaseModel):
    """
    Structured output produced by the Investigation Agent.

    This model acts as the contract between the Investigation Agent
    and downstream SupportMaster agents.
    """

    investigation_objective: str = Field(
        description="The primary question that the investigation must answer."
    )

    confirmed: List[str] = Field(
        default_factory=list,
        description="Facts confirmed by the Ticket Analysis Agent."
    )

    inferred: List[str] = Field(
        default_factory=list,
        description="Reasonable conclusions derived from confirmed evidence."
    )

    unknown: List[str] = Field(
        default_factory=list,
        description="Important information that is currently unknown."
    )

    likely_execution_path: List[str] = Field(
        default_factory=list,
        description="Likely conceptual execution flow of the affected functionality."
    )

    hypotheses: List[Hypothesis] = Field(
        default_factory=list,
        description="Focused root-cause hypotheses."
    )

    investigation_areas: List[InvestigationArea] = Field(
        default_factory=list,
        description="Technical areas that should be investigated."
    )

    search_plan: List[SearchPlan] = Field(
        default_factory=list,
        description="Planned searches for prior work and technical evidence."
    )

    critical_missing_information: List[str] = Field(
        default_factory=list,
        description="Missing information that blocks reliable investigation."
    )

    important_missing_information: List[str] = Field(
        default_factory=list,
        description="Missing information that reduces investigation confidence."
    )

    optional_missing_information: List[str] = Field(
        default_factory=list,
        description="Useful but non-essential missing information."
    )

    investigation_steps: List[InvestigationStep] = Field(
        default_factory=list,
        description="Prioritized sequence of investigation actions."
    )

    recommended_next_agent: NextAgent = Field(
        description="The single downstream agent that should execute next."
    )

    recommendation_reason: str = Field(
        description="Why the recommended next agent should execute next."
    )