from typing import List, Literal

from pydantic import BaseModel, Field


ImplementationStatus = Literal[
    "READY",
    "BLOCKED",
    "NEEDS_MORE_INFORMATION",
    "IMPLEMENTED",
]

ChangeType = Literal[
    "CREATE",
    "MODIFY",
    "DELETE",
    "REFACTOR",
    "CONFIGURATION",
]


class FileChange(BaseModel):
    """
    Represents a source or configuration file affected by the
    implementation.
    """

    file_path: str = Field(
        description=(
            "Repository-relative path of the file that was actually "
            "created, modified, deleted, refactored, or configured."
        )
    )

    change_type: ChangeType = Field(
        description="Type of change actually performed on the file."
    )

    purpose: str = Field(
        description=(
            "Why this file needed to change in order to address the "
            "approved remediation plan."
        )
    )

    summary: str = Field(
        description=(
            "Concise description of the actual change made to this file."
        )
    )


class ImplementationResult(BaseModel):
    """
    Structured output produced by the Implementation Agent.

    This model records the implementation performed against an approved
    remediation plan. It distinguishes implementation completion from
    validation and review readiness.
    """

    implementation_status: ImplementationStatus = Field(
        description=(
            "Current implementation state. READY means implementation "
            "can proceed or is prepared to proceed, BLOCKED means a "
            "safety gate prevents implementation, NEEDS_MORE_INFORMATION "
            "means required technical information is missing, and "
            "IMPLEMENTED means the approved changes have been made."
        )
    )

    objective: str = Field(
        description=(
            "The specific engineering objective the implementation was "
            "intended to achieve."
        )
    )

    root_cause_addressed: str = Field(
        description=(
            "The established or sufficiently supported root cause that "
            "the implementation is intended to address. Do not invent "
            "or strengthen the root cause beyond the root-cause analysis."
        )
    )

    implementation_summary: str = Field(
        description=(
            "Concise summary of what was actually implemented. If no "
            "changes were made because the agent was blocked, explain "
            "why instead."
        )
    )

    files_changed: List[FileChange] = Field(
        default_factory=list,
        description=(
            "Files that were actually created, modified, deleted, "
            "refactored, or configuration-changed during implementation. "
            "Do not list files merely proposed for future modification."
        )
    )

    code_changes: List[str] = Field(
        default_factory=list,
        description=(
            "Important implementation changes actually made to the "
            "source code. Keep these concise and implementation-focused."
        )
    )

    design_considerations: List[str] = Field(
        default_factory=list,
        description=(
            "Important design decisions made during implementation, "
            "including how the change fits existing repository patterns "
            "and why the selected approach was used."
        )
    )

    tests_added: List[str] = Field(
        default_factory=list,
        description=(
            "Tests that were actually added as part of the implementation. "
            "Do not list tests that were merely recommended."
        )
    )

    tests_modified: List[str] = Field(
        default_factory=list,
        description=(
            "Existing tests that were actually modified as part of the "
            "implementation and the behavior they now validate."
        )
    )

    tests_not_added_reason: str = Field(
        default="None",
        description=(
            "Reason why appropriate tests were not added, when applicable. "
            "Use 'None' when tests were added or no explanation is needed."
        )
    )

    validation_requirements: List[str] = Field(
        default_factory=list,
        description=(
            "Validation that still needs to be performed to demonstrate "
            "that the implementation correctly addresses the original "
            "failure and does not introduce regressions."
        )
    )

    validation_performed: List[str] = Field(
        default_factory=list,
        description=(
            "Validation actions actually performed by the agent, such as "
            "specific test suites or checks. Do not claim success unless "
            "the validation was actually executed."
        )
    )

    validation_results: List[str] = Field(
        default_factory=list,
        description=(
            "Observed results from validation that was actually performed. "
            "Clearly distinguish successful, failed, and inconclusive "
            "validation."
        )
    )

    original_failure_addressed: bool = Field(
        description=(
            "Whether the implementation specifically targets the original "
            "customer-reported failure condition. This does not mean the "
            "fix has been validated."
        )
    )

    implementation_scope_changed: bool = Field(
        description=(
            "Whether the actual implementation scope differs materially "
            "from the approved remediation plan."
        )
    )

    scope_change_reason: str = Field(
        default="None",
        description=(
            "Explanation for any material deviation from the approved "
            "remediation plan. Use 'None' when the implementation stayed "
            "within the approved scope."
        )
    )

    known_risks: List[str] = Field(
        default_factory=list,
        description=(
            "Known technical risks, limitations, or areas requiring "
            "additional review after implementation."
        )
    )

    unresolved_questions: List[str] = Field(
        default_factory=list,
        description=(
            "Important questions that remain unanswered after repository "
            "inspection or implementation."
        )
    )

    patch_ready: bool = Field(
        description=(
            "Whether the implementation is complete enough to be reviewed "
            "as a proposed source-code change. This does not imply that "
            "tests passed or that the change is safe to merge."
        )
    )

    review_required: bool = Field(
        description=(
            "Whether human or downstream engineering review is required "
            "before the change can be published or merged."
        )
    )

    implementation_verified: bool = Field(
        description=(
            "Whether the implementation has been technically validated "
            "against the relevant tests or checks. An implementation can "
            "be complete while this remains false."
        )
    )

    next_action: Literal[
        "RUN_TESTS",
        "REVIEW_IMPLEMENTATION",
        "GATHER_MORE_INFORMATION",
        "STOP",
    ] = Field(
        description=(
            "Recommended next workflow action based on the implementation "
            "state, validation status, and remaining safety concerns."
        )
    )