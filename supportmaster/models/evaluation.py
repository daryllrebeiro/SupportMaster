"""Machine-readable functional evaluation contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class EvaluationScenario(BaseModel):
    scenario_id: str
    domain: str
    source_system: str
    tenant_id: str
    payload: dict
    tags: list[str] = Field(default_factory=list)
    expectations: dict[str, Literal["PASS", "FAIL"]] = Field(default_factory=dict)


class EvaluationCheck(BaseModel):
    name: str
    status: Literal["PASS", "FAIL"]
    detail: str


class EvaluationResult(BaseModel):
    scenario_id: str
    status: Literal["PASS", "FAIL"]
    checks: list[EvaluationCheck] = Field(default_factory=list)
    duration_ms: float = 0.0
    error: str | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationSuiteResult(BaseModel):
    suite_name: str
    status: Literal["PASS", "FAIL"]
    scenarios: list[EvaluationResult] = Field(default_factory=list)
    passed: int = 0
    failed: int = 0
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OrganizationAcceptanceResult(BaseModel):
    """Machine-readable onboarding acceptance for one tenant."""

    organization_id: str
    status: Literal["PASS", "FAIL"]
    checks: list[EvaluationCheck] = Field(default_factory=list)
    suite: EvaluationSuiteResult | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowSimulationStep(BaseModel):
    """One deterministic stage observed during an end-to-end simulation."""

    name: str
    status: Literal["PASS", "FAIL", "SKIPPED"]
    detail: str


class WorkflowSimulationResult(BaseModel):
    """Machine-readable trace for a fixture through the local workflow services."""

    scenario_id: str
    tenant_id: str
    status: Literal["PASS", "FAIL"]
    steps: list[WorkflowSimulationStep] = Field(default_factory=list)
    case_id: str | None = None
    resolution_status: str | None = None
    error: str | None = None
    duration_ms: float = 0.0


class WorkflowSimulationSuiteResult(BaseModel):
    """Aggregate result for end-to-end simulations."""

    suite_name: str
    status: Literal["PASS", "FAIL"]
    simulations: list[WorkflowSimulationResult] = Field(default_factory=list)
    passed: int = 0
    failed: int = 0
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QualityPackResult(BaseModel):
    """Pre-demo quality summary across functional and end-to-end checks."""

    status: Literal["PASS", "FAIL"]
    functional: EvaluationSuiteResult
    end_to_end: WorkflowSimulationSuiteResult
    category_counts: dict[str, int] = Field(default_factory=dict)
    check_counts: dict[str, int] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReleaseCheck(BaseModel):
    name: str
    status: Literal["PASS", "FAIL"]
    detail: str


class ReleaseReadinessResult(BaseModel):
    """Deployment-readiness report with explicit checks and no hidden state."""

    status: Literal["PASS", "FAIL"]
    checks: list[ReleaseCheck] = Field(default_factory=list)
    quality: QualityPackResult | None = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
