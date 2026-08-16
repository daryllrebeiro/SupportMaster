"""Evidence provenance records produced by deterministic ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel):
    """One sanitized, hash-addressed source artifact."""

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    source_uri: str
    source_type: str
    name: str
    content: str
    content_hash: str
    size_bytes: int = Field(ge=0)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    classification: Literal["CONFIRMED", "INFERRED", "HYPOTHESIS", "UNKNOWN"] = "CONFIRMED"
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = "HIGH"
    sensitive_data_detected: bool = False
    redactions_performed: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class EvidenceBundle(BaseModel):
    """Collection of provenance records attached to one support run."""

    bundle_id: str = Field(default_factory=lambda: str(uuid4()))
    ticket_id: str | None = None
    records: list[EvidenceRecord] = Field(default_factory=list)
