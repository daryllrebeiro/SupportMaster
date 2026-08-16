"""Case workspace read model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .customer_response import CustomerResponse
from .investigation_artifacts import InvestigationSummary
from .organization import OrganizationProfile
from .planning import PlanningAssessment
from .resolution_bundle import ResolutionBundle
from .support_case import SupportCase


class WorkspaceRun(BaseModel):
    run_id: str
    status: str | None = None
    updated_at: Any = None


class CaseWorkspaceSnapshot(BaseModel):
    case: SupportCase
    organization: OrganizationProfile | None = None
    investigation: InvestigationSummary | None = None
    planning: PlanningAssessment | None = None
    resolution: ResolutionBundle | None = None
    runs: list[WorkspaceRun] = Field(default_factory=list)
