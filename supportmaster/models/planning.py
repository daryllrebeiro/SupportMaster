"""Persisted deterministic planning assessment."""

from pydantic import BaseModel

from .remediation import RemediationPlan
from .root_cause import RootCauseAnalysis


class PlanningAssessment(BaseModel):
    case_id: str
    tenant_id: str
    root_cause: RootCauseAnalysis
    remediation: RemediationPlan
