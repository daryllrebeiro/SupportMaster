"""Serializable results for verified external operations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..models.control import ExternalOperationReceipt


class PublicationExecutionResult(BaseModel):
    """Actual publication outcome assembled from adapter receipts."""

    status: Literal["PUBLISHED", "PARTIALLY_PUBLISHED", "BLOCKED", "FAILED"]
    receipts: list[ExternalOperationReceipt] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    commit_sha: str | None = None
    pull_request_url: str | None = None
    pull_request_number: int | None = None


class EngineeringExecutionResult(BaseModel):
    """Implementation outcome assembled only from adapter receipts."""

    status: Literal["IMPLEMENTED", "VALIDATED", "BLOCKED", "FAILED", "PARTIAL"]
    receipts: list[ExternalOperationReceipt] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    validation_passed: bool = False
    rollback_attempted: bool = False
