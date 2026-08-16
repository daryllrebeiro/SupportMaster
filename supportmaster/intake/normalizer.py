"""Normalize manual, webhook, and issue-tracker payloads to ``SupportCase``."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel

from ..models.support_case import SupportCase


class IntakeResult(BaseModel):
    status: Literal["CREATED", "REPLAYED"]
    case: SupportCase
    duplicate_case_id: str | None = None


def _first(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None and value != "":
            return value
    return None


def _steps(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [line.strip(" -\t") for line in value.splitlines() if line.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]


def normalize_case(
    payload: Mapping[str, Any],
    *,
    source_system: str,
    tenant_id: str = "default",
) -> SupportCase:
    """Map common aliases without imposing a vendor-specific schema."""
    title = str(_first(payload, "title", "summary", "subject", "name") or "Untitled support case").strip()
    description = str(_first(payload, "description", "body", "details", "problem", "text") or "").strip()
    if not description:
        raise ValueError("A support case description is required.")
    known = {
        "title", "summary", "subject", "name", "description", "body", "details", "problem", "text",
        "id", "case_id", "ticket_id", "key", "external_id", "requester", "reporter", "customer", "customer_account",
        "priority", "severity", "product", "service", "environment", "application_version", "version",
        "reproduction_steps", "reproduction", "steps", "expected_behavior", "expected", "actual_behavior", "actual",
        "customer_impact", "impact", "attachments", "metadata",
    }
    metadata = dict(payload.get("metadata") or {}) if isinstance(payload.get("metadata"), Mapping) else {}
    metadata.update({str(key): value for key, value in payload.items() if key not in known})
    return SupportCase(
        tenant_id=tenant_id,
        source_system=source_system,
        external_id=str(_first(payload, "external_id", "ticket_id", "case_id", "key", "id") or "") or None,
        title=title,
        description=description,
        requester=_first(payload, "requester", "reporter"),
        customer_account=_first(payload, "customer_account", "customer"),
        priority=_first(payload, "priority"),
        severity=_first(payload, "severity"),
        product=_first(payload, "product"),
        service=_first(payload, "service"),
        environment=_first(payload, "environment"),
        application_version=_first(payload, "application_version", "version"),
        reproduction_steps=_steps(_first(payload, "reproduction_steps", "reproduction", "steps")),
        expected_behavior=_first(payload, "expected_behavior", "expected"),
        actual_behavior=_first(payload, "actual_behavior", "actual"),
        customer_impact=_first(payload, "customer_impact", "impact"),
        attachments=payload.get("attachments") or [],
        metadata=metadata,
        status="NORMALIZED",
    )


class CaseIntakeService:
    """Normalize and persist cases with tenant-scoped external-id idempotency."""

    def __init__(self, store: Any) -> None:
        self.store = store

    def ingest(
        self,
        payload: Mapping[str, Any],
        *,
        source_system: str,
        tenant_id: str = "default",
    ) -> IntakeResult:
        case = normalize_case(payload, source_system=source_system, tenant_id=tenant_id)
        if case.external_id:
            existing = self.store.find_case_by_external_id(tenant_id, source_system, case.external_id)
            if existing is not None:
                return IntakeResult(status="REPLAYED", case=existing, duplicate_case_id=existing.case_id)
        self.store.save_case(case)
        return IntakeResult(status="CREATED", case=case)
