from typing import List, Literal

from pydantic import BaseModel, Field


ValidationStatus = Literal[
    "PASSED",
    "FAILED",
    "BLOCKED",
    "NEEDS_MORE_INFORMATION",
]


ValidationType = Literal[
    "UNIT",
    "INTEGRATION",
    "REGRESSION",
    "FUNCTIONAL",
    "PERFORMANCE",
    "MEMORY",
    "CONFIGURATION",
    "STATIC_ANALYSIS",
]


EvidenceStrength = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]


class ValidationCheck(BaseModel):
    """
    Represents one concrete validation check performed against the
    implementation.
    """

    name: str = Field(
        description=(
            "Short, specific name of the validation check. "
            "Examples: 'Original large-dataset reproduction', "
            "'Regression test suite', or 'Export output correctness'."
        )
    )

    validation_type: ValidationType = Field(
        description=(
            "Category of validation represented by this check."
        )
    )

    objective: str = Field(
        description=(
            "Specific behavior, requirement, root-cause mechanism, "
            "or regression condition this check is intended to verify."
        )
    )

    expected_result: str = Field(
        description=(
            "Observable result that should occur if the implementation "
            "is correct."
        )
    )

    actual_result: str = Field(
        default="Not executed",
        description=(
            "Actual observed result from the validation. "
            "Use 'Not executed' when the check was only planned and "
            "has not actually been performed."
        )
    )

    status: ValidationStatus = Field(
        description=(
            "Outcome of this validation check. "
            "PASSED means the check was executed and the expected result "
            "was observed. FAILED means it was executed and the expected "
            "result was not observed. BLOCKED means execution was prevented "
            "by a technical or environmental constraint. "
            "NEEDS_MORE_INFORMATION means available evidence is insufficient "
            "to determine the result."
        )
    )

    evidence_strength: EvidenceStrength = Field(
        description=(
            "Strength of the evidence supporting the validation result."
        )
    )

    evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete evidence supporting the validation result. "
            "Include test names, execution results, logs, measurements, "
            "reproduction outcomes, or other observable evidence. "
            "Never invent evidence."
        )
    )

    issues: List[str] = Field(
        default_factory=list,
        description=(
            "Problems, failures, discrepancies, or limitations discovered "
            "during this validation check."
        )
    )

    blocking: bool = Field(
        default=False,
        description=(
            "Whether failure, blockage, or missing evidence from this "
            "validation prevents the implementation from being considered "
            "successfully validated."
        )
    )


class ValidationAnalysis(BaseModel):
    """
    Structured validation result produced by the Validation Agent.

    This model provides an evidence-based assessment of whether an
    implementation resolves the original support issue, addresses the
    established root cause, satisfies relevant acceptance criteria, and
    avoids unacceptable regressions.

    The model intentionally distinguishes implementation completion from
    successful validation.
    """

    overall_status: ValidationStatus = Field(
        description=(
            "Overall validation outcome. PASSED requires sufficient "
            "evidence that the original problem is resolved and no "
            "unacceptable regression was identified. FAILED means the "
            "implementation demonstrably does not satisfy an important "
            "requirement. BLOCKED means validation could not proceed due "
            "to an environmental or technical blocker. "
            "NEEDS_MORE_INFORMATION means important evidence is missing."
        )
    )

    validation_confidence: EvidenceStrength = Field(
        description=(
            "Overall confidence in the validation conclusion based on "
            "the quality, completeness, and directness of the available "
            "validation evidence."
        )
    )

    implementation_ready_for_review: bool = Field(
        description=(
            "Whether validation evidence is sufficient for the implementation "
            "to proceed to engineering review. This must not be true merely "
            "because code compiles or tests were added."
        )
    )

    original_problem: str = Field(
        description=(
            "Precise description of the original customer-support problem "
            "that the implementation is expected to resolve."
        )
    )

    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete behavioral criteria that must be satisfied for the "
            "original issue to be considered resolved."
        )
    )

    expected_behavior: str = Field(
        description=(
            "Expected system behavior after the implementation, including "
            "the behavior required under the original failure condition."
        )
    )

    observed_behavior: str = Field(
        default="Not validated",
        description=(
            "Observed post-implementation behavior based only on actual "
            "validation evidence. Use 'Not validated' when the relevant "
            "scenario was not executed or otherwise observed."
        )
    )

    original_failure_reproduced: bool = Field(
        default=False,
        description=(
            "Whether the original customer failure condition, or a "
            "technically equivalent reproduction, was actually executed "
            "after implementation."
        )
    )

    original_failure_resolved: bool = Field(
        default=False,
        description=(
            "Whether validation evidence demonstrates that the original "
            "failure no longer occurs under the relevant conditions."
        )
    )

    root_cause_addressed: bool = Field(
        description=(
            "Whether available validation evidence demonstrates that the "
            "implementation addresses the identified root-cause mechanism."
        )
    )

    root_cause_validation_summary: str = Field(
        description=(
            "Evidence-based explanation of why the implementation does or "
            "does not address the established root cause."
        )
    )

    regression_detected: bool = Field(
        description=(
            "Whether validation identified an actual regression in existing "
            "supported behavior."
        )
    )

    regression_summary: str = Field(
        default="No regression identified.",
        description=(
            "Summary of regression evidence. Distinguish between an "
            "observed regression and a regression risk that has not been "
            "demonstrated."
        )
    )

    checks: List[ValidationCheck] = Field(
        default_factory=list,
        description=(
            "Individual validation checks performed, blocked, or identified "
            "as necessary for the issue."
        )
    )

    tests_executed: List[str] = Field(
        default_factory=list,
        description=(
            "Tests that were actually executed. Do not include merely "
            "planned or recommended tests."
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

    tests_not_executed: List[str] = Field(
        default_factory=list,
        description=(
            "Relevant tests that were planned or expected but were not "
            "actually executed."
        )
    )

    validation_evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Strongest concrete evidence supporting the overall validation "
            "decision. Prefer direct reproduction results, automated test "
            "results, integration results, and measured runtime behavior."
        )
    )

    missing_validation: List[str] = Field(
        default_factory=list,
        description=(
            "Specific validation evidence still required before the "
            "implementation can be considered sufficiently verified."
        )
    )

    blockers: List[str] = Field(
        default_factory=list,
        description=(
            "Technical, environmental, repository, test, or data-access "
            "blockers that prevented required validation."
        )
    )

    performance_validated: bool = Field(
        default=False,
        description=(
            "Whether performance behavior was actually validated with "
            "relevant evidence. Do not infer this from code inspection."
        )
    )

    performance_evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Measured or directly observed performance evidence, including "
            "workload, execution time, throughput, CPU, database load, or "
            "other relevant measurements. Do not invent measurements."
        )
    )

    memory_behavior_validated: bool = Field(
        default=False,
        description=(
            "Whether memory behavior was actually validated for a "
            "memory-sensitive issue."
        )
    )

    memory_evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete memory-related validation evidence such as successful "
            "large-dataset reproduction, heap measurements, object retention "
            "evidence, or runtime memory observations."
        )
    )

    configuration_validated: bool = Field(
        default=False,
        description=(
            "Whether relevant configuration changes were actually validated, "
            "when configuration is part of the implementation."
        )
    )

    risks: List[str] = Field(
        default_factory=list,
        description=(
            "Remaining risks or limitations that are relevant to the "
            "validation conclusion and supported by available evidence."
        )
    )

    unresolved_questions: List[str] = Field(
        default_factory=list,
        description=(
            "Important unanswered questions that prevent a stronger "
            "validation conclusion."
        )
    )

    recommendation: str = Field(
        description=(
            "Evidence-based recommendation for the next workflow action. "
            "Clearly state whether the implementation should proceed to "
            "review, requires additional testing/evidence, is blocked, "
            "or should be rejected."
        )
    )

    next_action: Literal[
        "APPROVE_FOR_REVIEW",
        "RUN_MORE_TESTS",
        "GATHER_MORE_INFORMATION",
        "FIX_IMPLEMENTATION",
        "STOP",
    ] = Field(
        description=(
            "Recommended next workflow action based strictly on the "
            "validation evidence."
        )
    )