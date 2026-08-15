from typing import List, Literal

from pydantic import BaseModel, Field


ChangeExecutionStatus = Literal[
    "COMPLETED",
    "PARTIALLY_COMPLETED",
    "BLOCKED",
    "FAILED",
    "NOT_STARTED",
]


ChangeType = Literal[
    "CREATE",
    "MODIFY",
    "DELETE",
    "REFACTOR",
    "CONFIGURATION",
]


TestExecutionStatus = Literal[
    "PASSED",
    "FAILED",
    "BLOCKED",
    "NOT_RUN",
]


class ChangedFile(BaseModel):
    """
    Represents a file that was actually changed by the Code Change Agent.
    """

    file_path: str = Field(
        description=(
            "Repository-relative path of the file that was actually "
            "created, modified, deleted, or refactored."
        )
    )

    change_type: ChangeType = Field(
        description=(
            "Type of change actually performed on the file."
        )
    )

    summary: str = Field(
        description=(
            "Concise description of the concrete change made to the file."
        )
    )

    reason: str = Field(
        description=(
            "Why this file needed to be changed and how the change "
            "relates to the approved remediation."
        )
    )


class TestExecution(BaseModel):
    """
    Represents one test or validation command actually attempted
    during implementation.
    """

    name: str = Field(
        description=(
            "Name or identifier of the test, test suite, build check, "
            "or validation command."
        )
    )

    status: TestExecutionStatus = Field(
        description=(
            "Observed execution status of the test."
        )
    )

    result: str = Field(
        description=(
            "Observed result of the test execution. Never claim a test "
            "passed unless it was actually executed and passed."
        )
    )

    scope: str = Field(
        description=(
            "Scope covered by the test, such as unit, integration, "
            "regression, or targeted functionality."
        )
    )

    relevant_to_fix: bool = Field(
        description=(
            "Whether this test provides meaningful evidence for the "
            "implemented remediation."
        )
    )


class CodeChangeResult(BaseModel):
    """
    Structured result produced by the Code Change Agent.

    This model records what was actually changed in the repository and
    what implementation-time tests were actually executed.

    It does NOT establish that the implementation is correct or that
    the original customer issue has been resolved. Final correctness
    belongs to the Validation and Review stages.
    """

    status: ChangeExecutionStatus = Field(
        description=(
            "Overall execution status of the requested implementation."
        )
    )

    repository: str = Field(
        default="Not provided",
        description=(
            "Repository in which the implementation was attempted."
        )
    )

    branch: str = Field(
        default="Not provided",
        description=(
            "Branch on which the implementation was performed."
        )
    )

    working_tree_state: Literal[
        "CLEAN",
        "CHANGES_PRESENT",
        "UNKNOWN",
    ] = Field(
        description=(
            "State of the repository working tree after implementation. "
            "This describes repository state only and does not imply "
            "that the changes are correct."
        )
    )

    changed_files: List[ChangedFile] = Field(
        default_factory=list,
        description=(
            "Files that were actually changed. Do not include files that "
            "were merely inspected or planned for modification."
        )
    )

    implementation_summary: str = Field(
        description=(
            "Concise summary of the implementation actually performed."
        )
    )

    root_cause_addressed: str = Field(
        default="Not independently validated",
        description=(
            "Description of the root-cause mechanism the implementation "
            "was intended to address. This is an implementation record, "
            "not proof that the root cause was successfully resolved."
        )
    )

    remediation_followed: bool = Field(
        description=(
            "Whether the implementation substantially followed the "
            "approved remediation plan."
        )
    )

    deviations_from_plan: List[str] = Field(
        default_factory=list,
        description=(
            "Meaningful deviations from the approved remediation plan. "
            "Do not report harmless implementation details as deviations."
        )
    )

    implementation_changes: List[str] = Field(
        default_factory=list,
        description=(
            "Important concrete code, configuration, database, or "
            "structural changes performed during implementation."
        )
    )

    design_considerations: List[str] = Field(
        default_factory=list,
        description=(
            "Important design decisions made while implementing the "
            "approved remediation."
        )
    )

    tests_added: List[str] = Field(
        default_factory=list,
        description=(
            "Tests actually added or modified as part of the implementation."
        )
    )

    tests: List[TestExecution] = Field(
        default_factory=list,
        description=(
            "Tests or validation checks actually attempted during "
            "implementation, including their observed results."
        )
    )

    tests_run: List[str] = Field(
        default_factory=list,
        description=(
            "Names of tests that were actually executed. "
            "Do not include planned but unexecuted tests."
        )
    )

    tests_passed: List[str] = Field(
        default_factory=list,
        description=(
            "Tests that were actually executed and passed."
        )
    )

    tests_failed: List[str] = Field(
        default_factory=list,
        description=(
            "Tests that were actually executed and failed."
        )
    )

    tests_blocked: List[str] = Field(
        default_factory=list,
        description=(
            "Tests that could not be executed because of an environment "
            "or technical blocker."
        )
    )

    test_results: List[str] = Field(
        default_factory=list,
        description=(
            "Observed test execution results. Include only actual "
            "results and never fabricate measurements or outcomes."
        )
    )

    validation_requirements: List[str] = Field(
        default_factory=list,
        description=(
            "Important validation that remains for the downstream "
            "Validation Agent. These are requirements, not claims that "
            "validation has already occurred."
        )
    )

    unresolved_issues: List[str] = Field(
        default_factory=list,
        description=(
            "Known implementation issues that remain unresolved."
        )
    )

    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "Important implementation-time warnings or risks discovered "
            "while making the change."
        )
    )

    scope_expanded: bool = Field(
        default=False,
        description=(
            "Whether implementation required changes beyond the "
            "originally identified scope."
        )
    )

    scope_expansion_reason: str = Field(
        default="None",
        description=(
            "Reason for any necessary scope expansion. Use 'None' when "
            "the implementation remained within the approved scope."
        )
    )

    implementation_complete: bool = Field(
        description=(
            "Whether all intended implementation changes were completed "
            "without a known implementation blocker."
        )
    )

    ready_for_validation: bool = Field(
        description=(
            "Whether the repository is in a state where the Validation "
            "Agent can meaningfully validate the implementation."
        )
    )

    validation_boundary: str = Field(
        default=(
            "Implementation completion does not establish correctness. "
            "The Validation Agent must independently verify the original "
            "problem, root-cause behavior, regression safety, and relevant "
            "runtime behavior."
        ),
        description=(
            "Explicit boundary between implementation evidence and "
            "downstream validation."
        )
    )

    next_action: Literal[
        "VALIDATE_IMPLEMENTATION",
        "COMPLETE_IMPLEMENTATION",
        "REVIEW_IMPLEMENTATION",
        "GATHER_MORE_INFORMATION",
        "STOP",
    ] = Field(
        description=(
            "Recommended next workflow action based on the actual "
            "implementation state."
        )
    )