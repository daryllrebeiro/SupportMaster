from typing import List, Literal

from pydantic import BaseModel, Field


MatchConfidence = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]

MatchType = Literal[
    "EXACT",
    "STRONG_SIMILAR",
    "RELATED",
    "NO_MATCH",
    "UNKNOWN",
]

DuplicateStatus = Literal[
    "DUPLICATE_FOUND",
    "RELATED_WORK_FOUND",
    "NO_DUPLICATE_FOUND",
    "INSUFFICIENT_EVIDENCE",
]


class DuplicateCandidate(BaseModel):
    source: str = Field(
        description=(
            "Engineering system where the candidate was found, "
            "such as Jira, Linear, GitHub, or Bitbucket."
        )
    )

    identifier: str = Field(
        description="Identifier of the candidate issue, PR, commit, etc."
    )

    title: str = Field(
        description="Title or short description of the candidate."
    )

    match_type: MatchType = Field(
        description=(
            "Relationship between the candidate and the current issue."
        )
    )

    confidence: MatchConfidence = Field(
        description=(
            "Confidence that the candidate is related to the current issue."
        )
    )

    matching_signals: List[str] = Field(
        default_factory=list,
        description=(
            "Specific technical or semantic signals that connect the "
            "candidate to the current issue."
        )
    )

    reasoning: str = Field(
        description=(
            "Evidence-based explanation of why the candidate is or is "
            "not considered duplicate or related work."
        )
    )


class DuplicateWorkAnalysis(BaseModel):
    """
    Structured output produced by the Duplicate Work Agent.

    This acts as a safety gate before SupportMaster can proceed toward
    autonomous source-code modification.
    """

    duplicate_status: DuplicateStatus = Field(
        description=(
            "Overall duplicate-work determination."
        )
    )

    search_performed: bool = Field(
        description=(
            "Whether actual duplicate-work searches were successfully "
            "performed."
        )
    )

    search_signals_used: List[str] = Field(
        default_factory=list,
        description=(
            "Signals actually used during duplicate-work searches."
        )
    )

    candidates: List[DuplicateCandidate] = Field(
        default_factory=list,
        description=(
            "Potential duplicate or related engineering work discovered."
        )
    )

    strongest_match: str = Field(
        default="None identified",
        description=(
            "Identifier of the strongest matching candidate. "
            "Use 'None identified' when no candidate exists and "
            "'Unknown' when duplicate detection could not be completed."
        )
    )

    conclusion: str = Field(
        description=(
            "Evidence-based conclusion about existing duplicate or "
            "related engineering work."
        )
    )

    recommended_action: str = Field(
        description=(
            "Recommended downstream workflow action based on the "
            "duplicate-work result."
        )
    )

    unresolved_questions: List[str] = Field(
        default_factory=list,
        description=(
            "Relevant questions that prevent a stronger duplicate-work "
            "determination."
        )
    )