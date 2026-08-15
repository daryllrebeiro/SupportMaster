from typing import List, Literal

from pydantic import BaseModel, Field


TestStatus = Literal[
    "PASSED",
    "FAILED",
    "PARTIALLY_PASSED",
    "NOT_RUN",
    "BLOCKED",
    "NOT_REQUIRED",
]

TestType = Literal[
    "UNIT",
    "INTEGRATION",
    "REGRESSION",
    "FUNCTIONAL",
    "PERFORMANCE",
    "MEMORY",
    "REPRODUCTION",
    "MANUAL",
    "CI",
    "OTHER",
]


class TestCaseResult(BaseModel):
    name: str = Field(
        description=(
            "Name or concise description of the test that was executed."
        )
    )

    test_type: TestType = Field(
        description="Type of test that was performed."
    )

    status: TestStatus = Field(
        description="Outcome of the individual test."
    )

    description: str = Field(
        description=(
            "What the test was intended to verify."
        )
    )

    result: str = Field(
        description=(
            "Observed result of the test. Must contain only "
            "evidence-supported information."
        )
    )

    failure_reason: str = Field(
        default="None",
        description=(
            "Reason for failure or blocking condition, if applicable."
        )
    )

    evidence: str = Field(
        default="Not provided",
        description=(
            "Evidence supporting the reported test result."
        )
    )


class TestResult(BaseModel):
    """
    Structured post-implementation testing result for SupportMaster.

    This model records what was actually tested after implementation,
    what happened, and whether the evidence supports proceeding toward
    commit, publishing, and resolution.
    """

    ticket_id: str = Field(
        description=(
            "Support ticket identifier, if available."
        )
    )

    overall_status: TestStatus = Field(
        description=(
            "Overall outcome of post-implementation testing."
        )
    )

    tests_executed: bool = Field(
        description=(
            "Whether at least one applicable test was actually executed."
        )
    )

    required_testing_completed: bool = Field(
        description=(
            "Whether all testing required for the implemented change "
            "was completed."
        )
    )

    original_issue_reproduced: bool = Field(
        description=(
            "Whether the original customer-reported failure scenario "
            "was reproduced or otherwise directly verified."
        )
    )

    original_issue_resolved: bool = Field(
        description=(
            "Whether testing provides sufficient evidence that the "
            "original customer-reported issue no longer occurs."
        )
    )

    regression_risk: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
        "UNKNOWN",
    ] = Field(
        description=(
            "Observed or assessed regression risk based only on "
            "available testing evidence."
        )
    )

    test_cases: List[TestCaseResult] = Field(
        default_factory=list,
        description=(
            "Individual tests performed and their observed outcomes."
        )
    )

    passed_tests: List[str] = Field(
        default_factory=list,
        description=(
            "Tests that actually passed."
        )
    )

    failed_tests: List[str] = Field(
        default_factory=list,
        description=(
            "Tests that actually failed."
        )
    )

    blocked_tests: List[str] = Field(
        default_factory=list,
        description=(
            "Tests that could not be executed because of blockers."
        )
    )

    validation_gaps: List[str] = Field(
        default_factory=list,
        description=(
            "Important testing or verification gaps that remain."
        )
    )

    failures: List[str] = Field(
        default_factory=list,
        description=(
            "Important test failures that affect the implementation "
            "or resolution decision."
        )
    )

    evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Evidence supporting the overall test result."
        )
    )

    recommended_next_steps: List[str] = Field(
        default_factory=list,
        description=(
            "Actions required after testing based on the observed result."
        )
    )

    resolution_verifiable: bool = Field(
        description=(
            "Whether the available post-implementation testing evidence "
            "is sufficient to support a resolution claim."
        )
    )