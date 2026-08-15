from typing import List, Literal

from pydantic import BaseModel, Field


RepositoryConfidence = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]


class RepositoryCandidate(BaseModel):
    """
    Represents a repository that may contain the implementation
    related to the support ticket.
    """

    repository: str = Field(
        description=(
            "Repository name or identifier. Use 'Unknown' when the "
            "repository has not been identified."
        )
    )

    source: str = Field(
        description=(
            "Where the repository information came from, such as "
            "ticket metadata, configuration, GitHub, Bitbucket, or "
            "inference."
        )
    )

    confidence: RepositoryConfidence = Field(
        description="Confidence that this is the relevant repository."
    )

    evidence: str = Field(
        description=(
            "Evidence supporting why this repository may contain "
            "the affected implementation."
        )
    )


class CodeLocation(BaseModel):
    """
    Represents a potential code location that should be investigated.
    """

    path: str = Field(
        description=(
            "Potential source path, package, class, or module. "
            "Use 'Unknown' when not available."
        )
    )

    symbol: str = Field(
        default="Unknown",
        description=(
            "Potential class, method, function, or other code symbol."
        )
    )

    reason: str = Field(
        description=(
            "Why this location is relevant to the reported problem."
        )
    )

    confidence: RepositoryConfidence = Field(
        description="Confidence that this is a relevant code location."
    )


class RepositoryAnalysis(BaseModel):
    """
    Structured output produced by the Repository Agent.

    This model identifies where the implementation related to the
    support issue is likely located.
    """

    repository_identified: bool = Field(
        description=(
            "Whether a specific repository has been identified."
        )
    )

    repository_candidates: List[RepositoryCandidate] = Field(
        default_factory=list,
        description=(
            "Repositories that may contain the implementation."
        )
    )

    primary_repository: str = Field(
        default="Unknown",
        description=(
            "Most likely repository containing the affected code."
        )
    )

    affected_service: str = Field(
        default="Unknown",
        description=(
            "Service or application containing the affected functionality."
        )
    )

    affected_module: str = Field(
        default="Unknown",
        description=(
            "Likely module containing the affected functionality."
        )
    )

    likely_code_locations: List[CodeLocation] = Field(
        default_factory=list,
        description=(
            "Potential packages, classes, methods, files, or modules "
            "that should be inspected."
        )
    )

    search_signals: List[str] = Field(
        default_factory=list,
        description=(
            "Signals that should be used to locate the relevant source "
            "code in a repository."
        )
    )

    search_performed: bool = Field(
        default=False,
        description=(
            "Whether an actual repository/source-code search was performed."
        )
    )

    findings: List[str] = Field(
        default_factory=list,
        description=(
            "Repository or source-code findings, if actual repository "
            "search was performed."
        )
    )

    unknowns: List[str] = Field(
        default_factory=list,
        description=(
            "Important repository or source-code information that "
            "remains unknown."
        )
    )

    recommendation: str = Field(
        description=(
            "Recommended next action for downstream SupportMaster agents."
        )
    )