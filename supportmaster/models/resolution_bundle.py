"""Persisted resolution, communication, and escalation bundle."""

from pydantic import BaseModel

from .customer_response import CustomerResponse
from .escalation import EscalationAnalysis
from .resolution import ResolutionAnalysis


class ResolutionBundle(BaseModel):
    case_id: str
    tenant_id: str
    resolution: ResolutionAnalysis
    customer_response: CustomerResponse
    escalation: EscalationAnalysis
