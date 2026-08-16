"""Deterministic investigation artifacts shared by adapters and agents."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceLink(BaseModel):
    record_id: str
    relevance: str
    authority: Literal["PRIMARY", "SECONDARY", "UNVERIFIED"] = "PRIMARY"
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"


class RelatedCaseMatch(BaseModel):
    case_id: str
    external_id: str | None = None
    relation: Literal["DUPLICATE", "RELATED", "POSSIBLE"]
    similarity: float = Field(ge=0.0, le=1.0)
    rationale: str


class IncidentCorrelation(BaseModel):
    incident_id: str
    service: str
    correlation: Literal["DIRECT", "POSSIBLE"]
    score: float = Field(ge=0.0, le=1.0)
    rationale: str


class RepositorySignal(BaseModel):
    repository: str
    path: str | None = None
    symbol: str | None = None
    commit_sha: str | None = None
    summary: str
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"


class MissingEvidence(BaseModel):
    evidence_type: str
    importance: Literal["CRITICAL", "IMPORTANT", "OPTIONAL"]
    reason: str
    expected_information: str


class InvestigationSummary(BaseModel):
    case_id: str
    tenant_id: str
    evidence_links: list[EvidenceLink] = Field(default_factory=list)
    related_cases: list[RelatedCaseMatch] = Field(default_factory=list)
    incident_correlations: list[IncidentCorrelation] = Field(default_factory=list)
    repository_signals: list[RepositorySignal] = Field(default_factory=list)
    missing_evidence: list[MissingEvidence] = Field(default_factory=list)
    confirmed_findings: list[str] = Field(default_factory=list)
    investigation_status: Literal["READY", "PARTIAL", "BLOCKED"] = "PARTIAL"
    readiness_reason: str = ""
