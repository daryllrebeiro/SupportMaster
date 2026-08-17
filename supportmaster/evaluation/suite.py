"""Deterministic fixture suite for functional safety and portability checks."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

from ..intake import CaseIntakeService, normalize_case
from ..investigation import InvestigationService
from ..models.evaluation import (
    EvaluationCheck, EvaluationResult, EvaluationScenario, EvaluationSuiteResult,
    OrganizationAcceptanceResult, WorkflowSimulationResult, WorkflowSimulationStep,
    WorkflowSimulationSuiteResult,
)
from ..models.organization import OrganizationProfile
from ..organization import OrganizationContextService
from ..persistence import SQLiteRunStore
from ..resolution import ResolutionService


def load_scenarios(directory: str | Path) -> list[EvaluationScenario]:
    path = Path(directory)
    scenarios: list[EvaluationScenario] = []
    for fixture in sorted(path.glob("*.json")):
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        evaluation = payload.pop("evaluation", {}) if isinstance(payload.get("evaluation"), dict) else {}
        scenarios.append(EvaluationScenario(scenario_id=fixture.stem, domain=fixture.stem.split("_")[0], source_system="fixture", tenant_id=f"tenant-{fixture.stem}", payload=payload, tags=["domain-neutral", "intake"], expectations=evaluation.get("expectations", {})))
    return scenarios


class FunctionalEvaluationSuite:
    """Run reusable functional checks without Gemini or external services."""

    def __init__(self, store: SQLiteRunStore, *, suite_name: str = "organization-neutral-functional") -> None:
        self.store = store
        self.suite_name = suite_name

    def run(self, scenarios: list[EvaluationScenario]) -> EvaluationSuiteResult:
        results = [self._evaluate(scenario) for scenario in scenarios]
        failed = sum(result.status == "FAIL" for result in results)
        return EvaluationSuiteResult(suite_name=self.suite_name, status="FAIL" if failed else "PASS", scenarios=results, passed=len(results) - failed, failed=failed)

    def _evaluate(self, scenario: EvaluationScenario) -> EvaluationResult:
        started = perf_counter()
        checks: list[EvaluationCheck] = []
        try:
            case = normalize_case(scenario.payload, source_system=scenario.source_system, tenant_id=scenario.tenant_id)
            checks.append(EvaluationCheck(name="canonical_case", status="PASS", detail="Payload normalized to SupportCase."))
            checks.append(EvaluationCheck(name="source_neutral_prompt", status="PASS" if case.workflow_text() else "FAIL", detail="Workflow text is available without vendor-specific fields."))
            CaseIntakeService(self.store).ingest(scenario.payload, source_system=scenario.source_system, tenant_id=scenario.tenant_id)
            summary = InvestigationService(self.store).summarize(case)
            checks.append(EvaluationCheck(name="tenant_scoped_investigation", status="PASS" if summary.tenant_id == scenario.tenant_id else "FAIL", detail="Investigation summary retains tenant context."))
            checks.append(EvaluationCheck(name="evidence_gaps_explicit", status="PASS" if isinstance(summary.missing_evidence, list) else "FAIL", detail="Missing evidence is represented explicitly."))
            resolution = ResolutionService().build(case, {})
            checks.append(EvaluationCheck(name="unsafe_resolution_blocked", status="PASS" if not resolution.customer_response.safe_to_send and resolution.escalation.escalation_status != "NO_ESCALATION_REQUIRED" else "FAIL", detail="Unverified cases cannot produce a send-ready resolution."))
            for name, expected in scenario.expectations.items():
                actual = next((check.status for check in checks if check.name == name), None)
                checks.append(EvaluationCheck(name=f"expectation:{name}", status="PASS" if actual == expected else "FAIL", detail=f"Expected {name}={expected}; observed {actual or 'MISSING'}."))
            status = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
            return EvaluationResult(scenario_id=scenario.scenario_id, status=status, checks=checks, duration_ms=round((perf_counter() - started) * 1000, 3))
        except Exception as error:
            return EvaluationResult(scenario_id=scenario.scenario_id, status="FAIL", checks=checks, duration_ms=round((perf_counter() - started) * 1000, 3), error=f"{type(error).__name__}: {error}")


class OrganizationAcceptanceSuite:
    """Validate onboarding defaults and run fixtures in a tenant context."""

    def __init__(self, store: SQLiteRunStore) -> None:
        self.store = store

    def run(self, profile: OrganizationProfile, scenarios: list[EvaluationScenario]) -> OrganizationAcceptanceResult:
        checks: list[EvaluationCheck] = []
        try:
            saved = OrganizationContextService(self.store).save(profile)
            checks.append(EvaluationCheck(name="organization_active", status="PASS" if saved.status == "ACTIVE" else "FAIL", detail="Organization must be active for onboarding."))
            policy = saved.workflow_policy
            checks.append(EvaluationCheck(name="safe_default_policy", status="PASS" if policy.require_duplicate_check and policy.require_implementation_approval and policy.require_publication_approval and policy.require_production_approval and not policy.allow_autonomous_code_change else "FAIL", detail="Safety-sensitive workflow defaults remain enabled."))
            tenant_scenarios = [scenario.model_copy(update={"tenant_id": saved.organization_id}) for scenario in scenarios]
            # A suspended tenant must never execute onboarding fixtures, even in a
            # deterministic local harness.  Return an explicit skipped suite.
            if saved.status != "ACTIVE":
                suite = EvaluationSuiteResult(
                    suite_name=f"onboarding:{saved.organization_id}", status="PASS",
                    scenarios=[], passed=0, failed=0,
                )
            else:
                suite = FunctionalEvaluationSuite(self.store, suite_name=f"onboarding:{saved.organization_id}").run(tenant_scenarios)
            checks.append(EvaluationCheck(name="functional_fixtures", status=suite.status, detail=f"{suite.passed} passed, {suite.failed} failed."))
            status = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
            return OrganizationAcceptanceResult(organization_id=saved.organization_id, status=status, checks=checks, suite=suite)
        except Exception as error:
            checks.append(EvaluationCheck(name="acceptance_execution", status="FAIL", detail=f"{type(error).__name__}: {error}"))
            return OrganizationAcceptanceResult(organization_id=profile.organization_id, status="FAIL", checks=checks)


class EndToEndWorkflowSimulator:
    """Exercise the local workflow boundary without invoking an LLM or connectors."""

    def __init__(self, store: SQLiteRunStore) -> None:
        self.store = store

    def run(self, scenario: EvaluationScenario, *, tenant_id: str | None = None) -> WorkflowSimulationResult:
        started = perf_counter()
        tenant = tenant_id or scenario.tenant_id
        steps: list[WorkflowSimulationStep] = []
        try:
            intake = CaseIntakeService(self.store).ingest(scenario.payload, source_system=scenario.source_system, tenant_id=tenant)
            steps.append(WorkflowSimulationStep(name="intake", status="PASS", detail=f"Case {intake.case.case_id} was {intake.status.lower()}."))
            case = intake.case
            steps.append(WorkflowSimulationStep(name="canonical_case", status="PASS", detail="Payload normalized to SupportCase."))
            summary = InvestigationService(self.store).summarize(case)
            steps.append(WorkflowSimulationStep(name="investigation", status="PASS", detail=f"Investigation status: {summary.investigation_status}."))
            tenant_ok = summary.tenant_id == tenant
            steps.append(WorkflowSimulationStep(name="tenant_boundary", status="PASS" if tenant_ok else "FAIL", detail=f"Expected tenant {tenant}; observed {summary.tenant_id}."))
            steps.append(WorkflowSimulationStep(name="tenant_scoped_investigation", status="PASS" if tenant_ok else "FAIL", detail="Investigation summary retains the simulation tenant."))
            resolution = ResolutionService().build(case, {})
            fail_closed = not resolution.customer_response.safe_to_send and not resolution.resolution.ticket_closure_allowed
            steps.append(WorkflowSimulationStep(name="resolution_gate", status="PASS" if fail_closed else "FAIL", detail="Unverified resolution remains blocked from customer send and closure."))
            steps.append(WorkflowSimulationStep(name="unsafe_resolution_blocked", status="PASS" if fail_closed else "FAIL", detail="Unverified resolution cannot be sent or closed."))
            for name, expected in scenario.expectations.items():
                observed = next((step.status for step in steps if step.name == name), None)
                steps.append(WorkflowSimulationStep(name=f"expectation:{name}", status="PASS" if observed == expected else "FAIL", detail=f"Expected {expected}; observed {observed or 'MISSING'}."))
            status = "PASS" if all(step.status in {"PASS", "SKIPPED"} for step in steps) else "FAIL"
            return WorkflowSimulationResult(scenario_id=scenario.scenario_id, tenant_id=tenant, status=status, steps=steps, case_id=case.case_id, resolution_status=resolution.resolution.resolution_status, duration_ms=round((perf_counter() - started) * 1000, 3))
        except Exception as error:
            return WorkflowSimulationResult(scenario_id=scenario.scenario_id, tenant_id=tenant, status="FAIL", steps=steps, error=f"{type(error).__name__}: {error}", duration_ms=round((perf_counter() - started) * 1000, 3))


class EndToEndWorkflowSuite:
    """Run complete deterministic simulations for fixtures or onboarding."""

    def __init__(self, store: SQLiteRunStore, *, suite_name: str = "end-to-end-workflow") -> None:
        self.store = store
        self.suite_name = suite_name

    def run(self, scenarios: list[EvaluationScenario], *, tenant_id: str | None = None) -> WorkflowSimulationSuiteResult:
        simulations = [EndToEndWorkflowSimulator(self.store).run(scenario, tenant_id=tenant_id) for scenario in scenarios]
        failed = sum(item.status == "FAIL" for item in simulations)
        return WorkflowSimulationSuiteResult(suite_name=self.suite_name, status="FAIL" if failed else "PASS", simulations=simulations, passed=len(simulations) - failed, failed=failed)


def simulate_workflow(store: SQLiteRunStore, scenario: EvaluationScenario, *, tenant_id: str | None = None) -> WorkflowSimulationResult:
    """Convenience API for one fixture simulation."""
    return EndToEndWorkflowSimulator(store).run(scenario, tenant_id=tenant_id)
