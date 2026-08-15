from typing import List, Literal, Optional

from pydantic import BaseModel, Field


GitHubPublishStatus = Literal[
    "PUBLISHED",
    "PARTIALLY_PUBLISHED",
    "BLOCKED",
    "FAILED",
]


GitOperationStatus = Literal[
    "COMPLETED",
    "NOT_STARTED",
    "FAILED",
]


PullRequestStatus = Literal[
    "CREATED",
    "NOT_CREATED",
    "FAILED",
]


class GitCommitResult(BaseModel):
    status: GitOperationStatus = Field(
        description="Whether the Git commit operation completed."
    )

    branch: str = Field(
        default="Not provided",
        description="Branch on which the commit was created."
    )

    commit_hash: Optional[str] = Field(
        default=None,
        description="Commit SHA if a commit was successfully created."
    )

    commit_message: Optional[str] = Field(
        default=None,
        description="Commit message used when creating the commit."
    )


class GitPushResult(BaseModel):
    status: GitOperationStatus = Field(
        description="Whether the branch push operation completed."
    )

    branch: str = Field(
        default="Not provided",
        description="Branch that was pushed."
    )

    remote: str = Field(
        default="origin",
        description="Git remote used for the push."
    )

    remote_branch: str = Field(
        default="Not provided",
        description="Remote branch containing the published changes."
    )


class PullRequestResult(BaseModel):
    status: PullRequestStatus = Field(
        description="Result of the pull request creation operation."
    )

    url: Optional[str] = Field(
        default=None,
        description="URL of the created pull request, if available."
    )

    number: Optional[int] = Field(
        default=None,
        description="Pull request number, if available."
    )

    title: Optional[str] = Field(
        default=None,
        description="Pull request title."
    )

    base_branch: str = Field(
        default="Not provided",
        description="Target branch of the pull request."
    )

    head_branch: str = Field(
        default="Not provided",
        description="Source branch of the pull request."
    )


class GitHubPublishResult(BaseModel):
    """
    Structured result produced by the GitHub Publication Agent.

    Represents the actual outcome of committing, pushing, and creating
    a pull request. It does not represent publication planning.
    """

    status: GitHubPublishStatus = Field(
        description=(
            "Overall result of the GitHub publication operation."
        )
    )

    repository: str = Field(
        description="Repository where publication was attempted."
    )

    commit: GitCommitResult = Field(
        description="Actual result of the Git commit operation."
    )

    push: GitPushResult = Field(
        description="Actual result of pushing the branch to the remote."
    )

    pull_request: PullRequestResult = Field(
        description="Actual result of pull request creation."
    )

    files_published: List[str] = Field(
        default_factory=list,
        description=(
            "Files intentionally included in the published change."
        )
    )

    validation_confirmed: bool = Field(
        description=(
            "Whether successful validation was confirmed before "
            "publication was attempted."
        )
    )

    duplicate_check_confirmed: bool = Field(
        description=(
            "Whether duplicate-work verification passed before "
            "publication was attempted."
        )
    )

    publication_plan_confirmed: bool = Field(
        description=(
            "Whether a valid publication plan was confirmed before "
            "performing GitHub operations."
        )
    )

    pre_publish_checks: List[str] = Field(
        default_factory=list,
        description=(
            "Safety checks confirmed before publication."
        )
    )

    errors: List[str] = Field(
        default_factory=list,
        description=(
            "Errors encountered during commit, push, or pull request "
            "creation."
        )
    )

    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "Non-blocking warnings encountered during publication."
        )
    )

    rollback_required: bool = Field(
        description=(
            "Whether the partial publication state requires cleanup "
            "or rollback."
        )
    )

    rollback_notes: List[str] = Field(
        default_factory=list,
        description=(
            "Actions or considerations required if publication must "
            "be rolled back."
        )
    )

    summary: str = Field(
        description="Concise factual summary of the publication outcome."
    )

    next_action: Literal[
        "REVIEW_PULL_REQUEST",
        "RETRY_PUBLICATION",
        "ROLLBACK",
        "STOP",
    ] = Field(
        description=(
            "Recommended next workflow action after the publication "
            "attempt."
        )
    )