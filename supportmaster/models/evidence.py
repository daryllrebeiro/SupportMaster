from typing import List, Literal

from pydantic import BaseModel, Field


EvidenceClassification = Literal[
    "CONFIRMED",
    "INFERRED",
    "HYPOTHESIS",
    "UNKNOWN",
]

EvidenceConfidence = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]


class EvidenceItem(BaseModel):
    """
    Represents a single piece of technical evidence available to
    the SupportMaster investigation.
    """

    category: str = Field(
        description=(
            "Category of evidence, such as LOG, STACK_TRACE, HEAP_DUMP, "
            "THREAD_DUMP, SCREENSHOT, METRIC, CONFIGURATION, SOURCE_CODE, "
            "REPRODUCTION, ERROR, DATABASE, ZIP_ARCHIVE, or ATTACHMENT."
        )
    )

    name: str = Field(
        description=(
            "Name or short identifier of the evidence."
        )
    )

    value: str = Field(
        description=(
            "The actual evidence or a concise representation of it. "
            "Sensitive information such as credentials, tokens, secrets, "
            "or personally identifiable information must not be reproduced."
        )
    )

    source: str = Field(
        description=(
            "Where the evidence originated, such as ticket, comment, "
            "attachment, log file, screenshot, repository, monitoring "
            "system, or another engineering system."
        )
    )

    classification: EvidenceClassification = Field(
        description=(
            "Classification of the evidence: CONFIRMED, INFERRED, "
            "HYPOTHESIS, or UNKNOWN."
        )
    )

    confidence: EvidenceConfidence = Field(
        description=(
            "Confidence that the evidence is accurate, relevant, and "
            "correctly interpreted."
        )
    )

    relevance: str = Field(
        description=(
            "Why this evidence matters to the current investigation."
        )
    )


class EvidenceGap(BaseModel):
    """
    Represents evidence that is missing and could materially affect
    the investigation.
    """

    evidence_type: str = Field(
        description=(
            "Type of missing evidence, such as complete stack trace, "
            "application logs, heap dump, thread dump, configuration, "
            "source code, metrics, reproduction data, or environment details."
        )
    )

    importance: Literal[
        "CRITICAL",
        "IMPORTANT",
        "OPTIONAL",
    ] = Field(
        description=(
            "Importance of obtaining this evidence."
        )
    )

    reason: str = Field(
        description=(
            "Why this evidence is needed for the investigation."
        )
    )

    expected_information: str = Field(
        description=(
            "What this evidence is expected to reveal or help confirm."
        )
    )


class EvidenceFinding(BaseModel):
    """
    Represents a conclusion derived from available evidence.
    """

    finding: str = Field(
        description=(
            "Concise evidence-based finding."
        )
    )

    classification: EvidenceClassification = Field(
        description=(
            "Whether the finding is CONFIRMED, INFERRED, HYPOTHESIS, "
            "or UNKNOWN."
        )
    )

    supporting_evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Evidence items or evidence identifiers supporting this finding."
        )
    )

    confidence: EvidenceConfidence = Field(
        description=(
            "Confidence in the finding."
        )
    )


class EvidenceSource(BaseModel):
    """
    Represents a source from which evidence was obtained or should
    be obtained.
    """

    source_type: str = Field(
        description=(
            "Type of source, such as TICKET, ATTACHMENT, LOG_FILE, "
            "SCREENSHOT, REPOSITORY, MONITORING_SYSTEM, DATABASE, "
            "CONFIGURATION, or ENGINEERING_SYSTEM."
        )
    )

    source_name: str = Field(
        description=(
            "Name or identifier of the evidence source."
        )
    )

    available: bool = Field(
        description=(
            "Whether this evidence source is actually available."
        )
    )

    inspected: bool = Field(
        default=False,
        description=(
            "Whether the source was actually inspected during this stage."
        )
    )

    notes: str = Field(
        default="",
        description=(
            "Relevant information about the source, including access "
            "limitations or important observations."
        )
    )


class EvidenceAnalysis(BaseModel):
    """
    Structured output produced by the SupportMaster Evidence Agent.

    This model acts as the contract between evidence collection and
    downstream duplicate detection, repository investigation, and
    root-cause analysis agents.
    """

    evidence_available: bool = Field(
        description=(
            "Whether meaningful technical evidence is currently available."
        )
    )

    evidence_collection_performed: bool = Field(
        default=False,
        description=(
            "Whether the agent actually collected or inspected evidence "
            "using an available evidence or attachment tool."
        )
    )

    evidence_sources: List[EvidenceSource] = Field(
        default_factory=list,
        description=(
            "Sources from which evidence was obtained or is expected "
            "to be obtained."
        )
    )

    evidence_items: List[EvidenceItem] = Field(
        default_factory=list,
        description=(
            "Concrete technical evidence currently available to the "
            "investigation."
        )
    )

    findings: List[EvidenceFinding] = Field(
        default_factory=list,
        description=(
            "Evidence-based findings derived from the available evidence."
        )
    )

    evidence_gaps: List[EvidenceGap] = Field(
        default_factory=list,
        description=(
            "Important evidence that is currently missing."
        )
    )

    strongest_evidence: List[str] = Field(
        default_factory=list,
        description=(
            "The strongest pieces of evidence currently available and "
            "most useful for downstream investigation."
        )
    )

    root_cause_readiness: Literal[
        "READY_FOR_ROOT_CAUSE_ANALYSIS",
        "PARTIALLY_READY",
        "INSUFFICIENT_EVIDENCE",
    ] = Field(
        description=(
            "Assessment of whether the currently available evidence "
            "is sufficient for meaningful root-cause analysis."
        )
    )

    sensitive_data_detected: bool = Field(
        default=False,
        description=(
            "Whether potentially sensitive information was detected in "
            "the evidence. The actual secret or sensitive value must never "
            "be included in the structured output."
        )
    )

    redactions_performed: bool = Field(
        default=False,
        description=(
            "Whether sensitive information was removed or masked before "
            "the evidence was passed downstream."
        )
    )

    confidence_summary: str = Field(
        description=(
            "Overall assessment of the quality, completeness, and "
            "reliability of the available evidence."
        )
    )

    recommendation: str = Field(
        description=(
            "Recommended next action for downstream SupportMaster agents."
        )
    )