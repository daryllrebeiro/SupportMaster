from typing import List, Literal

from pydantic import BaseModel, Field


RootCauseConfidence = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]

RootCauseClassification = Literal[
    "CONFIRMED",
    "STRONGLY_SUPPORTED",
    "POSSIBLE",
    "REJECTED",
    "UNKNOWN",
]


class RootCauseHypothesis(BaseModel):
    hypothesis: str = Field(
        description="The proposed underlying root cause."
    )

    classification: RootCauseClassification = Field(
        description=(
            "Evidence-based classification of the hypothesis: "
            "CONFIRMED, STRONGLY_SUPPORTED, POSSIBLE, REJECTED, or UNKNOWN."
        )
    )

    confidence: RootCauseConfidence = Field(
        description="Confidence in the assessment."
    )

    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence supporting this root-cause hypothesis."
    )

    contradicting_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence that contradicts or weakens the hypothesis."
    )

    verification_gaps: List[str] = Field(
        default_factory=list,
        description=(
            "Evidence still required before the hypothesis can be "
            "considered confirmed."
        )
    )


class RootCauseAnalysis(BaseModel):
    """
    Structured output produced by the Root Cause Analysis Agent.

    This model represents the current evidence-based understanding
    of the underlying cause of the support issue.
    """

    root_cause_determined: bool = Field(
        description=(
            "Whether the available evidence is sufficient to determine "
            "the root cause."
        )
    )

    primary_root_cause: str = Field(
        default="Unknown",
        description=(
            "The most likely root cause. Use 'Unknown' when evidence "
            "is insufficient."
        )
    )

    confidence: RootCauseConfidence = Field(
        default="LOW",
        description="Confidence in the primary root-cause assessment."
    )

    classification: RootCauseClassification = Field(
        default="UNKNOWN",
        description=(
            "Evidence-based classification of the primary root cause."
        )
    )

    explanation: str = Field(
        description=(
            "Concise explanation connecting the observed behavior "
            "to the identified root cause."
        )
    )

    hypotheses: List[RootCauseHypothesis] = Field(
        default_factory=list,
        description=(
            "Root-cause hypotheses considered during the analysis."
        )
    )

    confirmed_facts: List[str] = Field(
        default_factory=list,
        description="Facts directly supported by available evidence."
    )

    inferred_facts: List[str] = Field(
        default_factory=list,
        description="Reasonable conclusions derived from the evidence."
    )

    rejected_hypotheses: List[str] = Field(
        default_factory=list,
        description="Hypotheses weakened or rejected by available evidence."
    )

    remaining_unknowns: List[str] = Field(
        default_factory=list,
        description=(
            "Important questions that remain unanswered and prevent "
            "stronger root-cause confidence."
        )
    )

    recommended_verification: List[str] = Field(
        default_factory=list,
        description=(
            "Additional technical checks required to confirm the "
            "root cause, if necessary."
        )
    )

    recommended_next_agent: Literal[
        "FIX_PLANNING_AGENT",
        "EVIDENCE_AGENT",
        "MORE_INFORMATION_REQUIRED",
        "HUMAN_REVIEW",
    ] = Field(
        description=(
            "The next agent or workflow stage that should receive "
            "the investigation."
        )
    )