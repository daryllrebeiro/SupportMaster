from typing import List, Literal

from pydantic import BaseModel, Field


AuditStatus = Literal[
    "APPROVED",
    "APPROVED_WITH_WARNINGS",
    "BLOCKED",
]


AuditSeverity = Literal[
    "INFO",
    "WARNING",
    "CRITICAL",
]


AuditCategory = Literal[
    "SAFETY",
    "EVIDENCE",
    "VALIDATION",
    "DUPLICATE",
    "IMPLEMENTATION",
    "PUBLICATION",
    "RESOLUTION",
    "CUSTOMER_RESPONSE",
    "WORKFLOW",
    "CONSISTENCY",
    "TRACEABILITY",
]


AuditFindingType = Literal[
    "MISSING_EVIDENCE",
    "CONTRADICTION",
    "UNSUPPORTED_CLAIM",
    "FAILED_GATE",
    "INCOMPLETE_STAGE",
    "SCOPE_MISMATCH",
    "INVALID_STATUS",
    "MISSING_INFORMATION",
    "RISK",
    "OTHER",
]


EvidenceQuality = Literal[
    "STRONG",
    "SUFFICIENT",
    "LIMITED",
    "INSUFFICIENT",
    "UNKNOWN",
]


class AuditFinding(BaseModel):
    """
    A single finding identified during the final SupportMaster audit.
    """

    category: AuditCategory = Field(
        description=(
            "High-level category of the audit finding."
        )
    )

    finding_type: AuditFindingType = Field(
        description=(
            "Specific type of problem or observation identified "
            "during the audit."
        )
    )

    severity: AuditSeverity = Field(
        description=(
            "Severity of the finding. CRITICAL findings indicate "
            "that the workflow is unsafe to complete."
        )
    )

    finding: str = Field(
        description=(
            "Clear description of the issue, inconsistency, "
            "risk, or observation."
        )
    )

    evidence: str = Field(
        description=(
            "Specific evidence from the available workflow outputs "
            "supporting this finding. Do not invent evidence."
        )
    )

    affected_stage: str = Field(
        default="Unknown",
        description=(
            "Workflow stage or output affected by this finding, "
            "such as validation_analysis, publish_plan, "
            "resolution_analysis, or customer_response."
        )
    )

    blocking: bool = Field(
        description=(
            "Whether this finding prevents the workflow from being "
            "safely completed."
        )
    )

    required_action: str = Field(
        default="None",
        description=(
            "Action required to address the finding before the "
            "workflow can safely continue, if any."
        )
    )


class WorkflowAudit(BaseModel):
    """
    Final safety, evidence, consistency, and publication audit for
    the SupportMaster workflow.

    This model represents the audit agent's independent assessment
    of whether the workflow has earned the right to return its
    claimed outcome.
    """

    ticket_id: str = Field(
        default="Not provided",
        description=(
            "Support ticket identifier, if available."
        )
    )

    audit_status: AuditStatus = Field(
        description=(
            "Overall audit disposition. BLOCKED means the workflow "
            "must not be considered safely complete."
        )
    )

    evidence_quality: EvidenceQuality = Field(
        description=(
            "Overall quality of the evidence supporting the final "
            "workflow outcome."
        )
    )

    workflow_complete: bool = Field(
        description=(
            "Whether all workflow stages required for the claimed "
            "outcome have completed sufficiently."
        )
    )

    duplicate_gate_passed: bool = Field(
        description=(
            "Whether duplicate-work verification provides sufficient "
            "evidence to safely continue."
        )
    )

    validation_gate_passed: bool = Field(
        description=(
            "Whether the available validation evidence is sufficient "
            "to support the claimed implementation outcome."
        )
    )

    implementation_supported: bool = Field(
        description=(
            "Whether there is sufficient evidence that the claimed "
            "implementation actually exists."
        )
    )

    publication_gate_passed: bool = Field(
        description=(
            "Whether publication-related claims and operations are "
            "supported by available evidence and are consistent "
            "with the workflow state."
        )
    )

    resolution_supported: bool = Field(
        description=(
            "Whether the claimed resolution status is consistent "
            "with the available implementation and verification "
            "evidence."
        )
    )

    customer_response_supported: bool = Field(
        description=(
            "Whether the customer-facing response contains only "
            "claims supported by the workflow evidence."
        )
    )

    traceability_complete: bool = Field(
        description=(
            "Whether important claims can be traced back to the "
            "available ticket, investigation, implementation, "
            "validation, publication, or resolution evidence."
        )
    )

    findings: List[AuditFinding] = Field(
        default_factory=list,
        description=(
            "All material findings identified during the final audit."
        )
    )

    blocked_reasons: List[str] = Field(
        default_factory=list,
        description=(
            "Specific reasons the workflow cannot safely complete. "
            "Should be populated when audit_status is BLOCKED."
        )
    )

    warnings: List[str] = Field(
        default_factory=list,
        description=(
            "Non-blocking limitations or risks that should be surfaced "
            "to downstream workflow stages."
        )
    )

    verified_claims: List[str] = Field(
        default_factory=list,
        description=(
            "Important workflow claims directly supported by evidence."
        )
    )

    unsupported_claims: List[str] = Field(
        default_factory=list,
        description=(
            "Claims made or implied by workflow outputs that cannot "
            "be sufficiently supported by available evidence."
        )
    )

    required_actions: List[str] = Field(
        default_factory=list,
        description=(
            "Concrete actions required before a blocked or incomplete "
            "workflow can safely proceed."
        )
    )

    audit_scope: List[str] = Field(
        default_factory=list,
        description=(
            "Workflow outputs or safety areas actually reviewed during "
            "the audit."
        )
    )

    critical_findings_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of CRITICAL audit findings."
        )
    )

    warning_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of WARNING audit findings."
        )
    )

    final_recommendation: str = Field(
        description=(
            "Clear final recommendation describing whether the "
            "workflow should be returned, returned with warnings, "
            "or stopped for remediation."
        )
    )