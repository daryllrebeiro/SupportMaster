from typing import List, Literal

from pydantic import BaseModel, Field


PublishStatus = Literal[
    "READY_TO_PUBLISH",
    "BLOCKED",
    "NEEDS_REVIEW",
    "NOT_READY",
]


PublishAction = Literal[
    "CREATE_COMMIT",
    "CREATE_PULL_REQUEST",
    "REQUEST_REVIEW",
    "GATHER_MORE_INFORMATION",
    "STOP",
]


ChangeType = Literal[
    "CREATE",
    "MODIFY",
    "DELETE",
    "REFACTOR",
    "CONFIGURATION",
]


class PlannedFileChange(BaseModel):
    """
    Represents a file expected to be included in the publication.

    This should be derived from the actual implementation/diff rather
    than from the original remediation plan alone.
    """

    file_path: str = Field(
        description=(
            "Repository-relative path of the file expected to be included "
            "in the publication."
        )
    )

    change_type: ChangeType = Field(
        description="Type of change present in the file."
    )

    summary: str = Field(
        description="Concise description of the actual change in the file."
    )

    reason: str = Field(
        description=(
            "Why the file is part of the implementation and how it relates "
            "to the approved remediation."
        )
    )


class CommitPlan(BaseModel):
    """
    Proposed commit information.

    This describes what should be committed; it does not mean that the
    commit has already been created.
    """

    message: str = Field(
        description=(
            "Proposed concise commit message accurately describing the "
            "implemented change."
        )
    )

    summary: str = Field(
        description=(
            "Summary of the changes that should be included in the commit."
        )
    )

    files: List[PlannedFileChange] = Field(
        default_factory=list,
        description=(
            "Files that should be included in the commit based on the "
            "actual implementation."
        )
    )

    scope_verified: bool = Field(
        description=(
            "Whether the proposed commit scope has been checked against "
            "the actual implementation and review findings."
        )
    )


class PullRequestPlan(BaseModel):
    """
    Proposed pull-request metadata.

    This does not mean that a pull request has already been created.
    """

    title: str = Field(
        description="Proposed pull request title."
    )

    body: str = Field(
        description=(
            "Proposed pull request description explaining the problem, "
            "root cause, implementation, testing, and known risks."
        )
    )

    base_branch: str = Field(
        description="Target branch for the pull request."
    )

    head_branch: str = Field(
        description="Source branch containing the implementation."
    )

    testing_summary: str = Field(
        description=(
            "Accurate summary of tests and validation actually performed. "
            "Do not claim unexecuted tests passed."
        )
    )

    risk_summary: str = Field(
        description=(
            "Known risks, limitations, compatibility concerns, and "
            "remaining uncertainty."
        )
    )

    validation_status: str = Field(
        description=(
            "Summary of the final validation state supporting the PR."
        )
    )


class PublishPlan(BaseModel):
    """
    Structured publication gate for SupportMaster.

    This model determines whether an already reviewed implementation is
    safe to turn into a commit and/or pull request.

    It does not itself imply that anything has been committed, pushed,
    or published.
    """

    status: PublishStatus = Field(
        description=(
            "Publication readiness status based on implementation, "
            "validation, review, repository state, and safety checks."
        )
    )

    repository: str = Field(
        default="Not provided",
        description=(
            "Repository containing the implementation."
        )
    )

    branch: str = Field(
        default="Not provided",
        description=(
            "Current working branch containing the implementation."
        )
    )

    implementation_summary: str = Field(
        description=(
            "Concise summary of the implementation being considered "
            "for publication."
        )
    )

    root_cause_summary: str = Field(
        description=(
            "Root cause addressed by the implementation."
        )
    )

    validation_summary: str = Field(
        description=(
            "Summary of the evidence demonstrating whether the original "
            "issue was resolved."
        )
    )

    review_summary: str = Field(
        description=(
            "Summary of the Review Agent's assessment, including any "
            "identified concerns."
        )
    )

    commit: CommitPlan = Field(
        description=(
            "Proposed commit information based on the actual implementation."
        )
    )

    pull_request: PullRequestPlan = Field(
        description="Proposed pull request information."
    )

    safety_checks: List[str] = Field(
        default_factory=list,
        description=(
            "Safety checks that were actually performed before publication."
        )
    )

    passed_checks: List[str] = Field(
        default_factory=list,
        description=(
            "Publication safety checks that passed."
        )
    )

    failed_checks: List[str] = Field(
        default_factory=list,
        description=(
            "Publication safety checks that failed."
        )
    )

    blockers: List[str] = Field(
        default_factory=list,
        description=(
            "Conditions that prevent safe publication."
        )
    )

    required_reviewers: List[str] = Field(
        default_factory=list,
        description=(
            "People, teams, or ownership groups that should review "
            "the change before publication."
        )
    )

    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "Important warnings or residual risks that do not necessarily "
            "block publication."
        )
    )

    uncommitted_changes_present: bool = Field(
        description=(
            "Whether repository changes exist that are not yet represented "
            "by the proposed commit."
        )
    )

    unexpected_changes_present: bool = Field(
        description=(
            "Whether changes exist outside the approved implementation "
            "scope."
        )
    )

    validation_passed: bool = Field(
        description=(
            "Whether the Validation Agent established sufficient evidence "
            "that the implementation solves the original issue."
        )
    )

    review_passed: bool = Field(
        description=(
            "Whether the Review Agent approved the implementation for "
            "publication."
        )
    )

    publication_allowed: bool = Field(
        description=(
            "Final safety gate indicating whether SupportMaster may "
            "proceed toward commit/PR publication."
        )
    )

    recommended_action: PublishAction = Field(
        description=(
            "Next action the workflow should perform."
        )
    )

    recommendation: str = Field(
        description=(
            "Evidence-based explanation of why publication is or is not "
            "allowed."
        )
    )