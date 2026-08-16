"""Deterministic final-status and communication decisions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..models.customer_response import CustomerResponse
from ..models.escalation import EscalationAction, EscalationAnalysis
from ..models.resolution import ResolutionAnalysis, ResolutionEvidence, ResolutionGate, VerificationCheck
from ..models.resolution_bundle import ResolutionBundle
from ..models.support_case import SupportCase


def _value(value: Any, field: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(field, default)
    return getattr(value, field, default)


class ResolutionService:
    """Assess outcomes without conflating implementation, deployment, or closure."""

    def build(
        self,
        case: SupportCase,
        state: Mapping[str, Any],
        *,
        deployment_confirmed: bool = False,
        customer_confirmed: bool = False,
        customer_confirmation_required: bool = False,
        publication_required: bool = False,
    ) -> ResolutionBundle:
        execution = state.get("engineering_execution")
        implementation = state.get("implementation_result")
        validation = state.get("validation_analysis")
        published = state.get("github_publish_result") or state.get("publish_result")
        implementation_done = _value(execution, "status") in {"IMPLEMENTED", "VALIDATED"} or _value(implementation, "implementation_status") == "IMPLEMENTED"
        validation_passed = bool(_value(execution, "validation_passed")) or _value(validation, "overall_status") == "PASSED"
        publication_done = _value(published, "status") == "PUBLISHED"
        blocking: list[str] = []
        if not implementation_done:
            blocking.append("Implementation is not verified as completed.")
        if not validation_passed:
            blocking.append("Validation evidence is not confirmed as passed.")
        if publication_required and not publication_done:
            blocking.append("Required publication is not verified.")
        if not deployment_confirmed:
            blocking.append("Deployment has not been independently confirmed.")
        if customer_confirmation_required and not customer_confirmed:
            blocking.append("Customer confirmation is pending.")

        all_complete = not blocking
        status = "RESOLVED" if all_complete else ("PARTIALLY_RESOLVED" if implementation_done and validation_passed else "VERIFICATION_REQUIRED")
        confidence = "HIGH" if all_complete else ("MEDIUM" if implementation_done and validation_passed else "LOW")
        implementation_gate = ResolutionGate(name="IMPLEMENTATION", status="PASSED" if implementation_done else "FAILED", evidence=["engineering_execution", "implementation_result"] if implementation_done else [], blocking=True)
        validation_gate = ResolutionGate(name="VALIDATION", status="PASSED" if validation_passed else "UNKNOWN", evidence=["engineering_execution", "validation_analysis"] if validation_passed else [], blocking=True)
        publication_gate = ResolutionGate(name="PUBLICATION", status="PASSED" if publication_done else ("NOT_APPLICABLE" if not publication_required else "UNKNOWN"), evidence=["github_publish_result"] if publication_done else [], blocking=publication_required)
        regression_gate = ResolutionGate(name="REGRESSION", status="PASSED" if validation_passed else "UNKNOWN", evidence=["validation_analysis"] if validation_passed else [], blocking=True)
        customer_gate = ResolutionGate(name="CUSTOMER_IMPACT", status="PASSED" if deployment_confirmed else "UNKNOWN", evidence=["deployment_confirmation"] if deployment_confirmed else [], blocking=customer_confirmation_required)
        checks = [
            VerificationCheck(name="Implementation", objective="Approved change was executed", result="PASSED" if implementation_done else "NOT_RUN", expected_result="Approved implementation completed", actual_result="Completed" if implementation_done else "Not verified", evidence=["engineering_execution"], confidence=confidence, blocking=True),
            VerificationCheck(name="Validation", objective="Change passes relevant validation", result="PASSED" if validation_passed else "NOT_RUN", expected_result="Validation passes", actual_result="Passed" if validation_passed else "Not verified", evidence=["validation_analysis"], confidence=confidence, blocking=True),
        ]
        evidence = [ResolutionEvidence(source="workflow_state", evidence=item, classification="CONFIRMED" if item not in blocking else "UNKNOWN", relevant_to="resolution status") for item in ["Implementation status recorded.", "Validation status recorded."]]
        resolution = ResolutionAnalysis(
            ticket_id=case.external_id,
            resolution_status=status,
            summary="The case is resolved only when implementation, validation, required publication, deployment, and customer confirmation gates are satisfied.",
            original_problem=case.title,
            root_cause=_value(state.get("root_cause_analysis"), "primary_root_cause", "Not confirmed"),
            implemented_change=_value(implementation, "implementation_summary", "No verified implementation recorded."),
            expected_resolution=case.expected_behavior or "The reported failure no longer occurs.",
            observed_behavior="Deployment and customer behavior are confirmed." if deployment_confirmed else "Not verified.",
            implementation_gate=implementation_gate,
            validation_gate=validation_gate,
            publication_gate=publication_gate,
            regression_gate=regression_gate,
            customer_impact_gate=customer_gate,
            verification_checks=checks,
            resolution_evidence=evidence,
            blocking_issues=blocking,
            remaining_risks=[] if all_complete else ["Production/customer outcome remains unconfirmed."],
            remaining_work=[] if all_complete else blocking,
            regression_concerns=[] if validation_passed else ["Relevant validation has not passed."],
            customer_impact_after_change="Customer impact is confirmed resolved." if all_complete else "Customer impact remains unverified.",
            customer_confirmation_required=customer_confirmation_required,
            confidence=confidence,
            recommended_action="CLOSE_TICKET" if all_complete else ("REQUEST_CUSTOMER_CONFIRMATION" if deployment_confirmed and customer_confirmation_required else "RUN_ADDITIONAL_VALIDATION"),
            ticket_closure_allowed=all_complete,
        )
        response = self._response(case, resolution, customer_confirmed, customer_confirmation_required)
        escalation = self._escalation(case, resolution)
        return ResolutionBundle(case_id=case.case_id, tenant_id=case.tenant_id, resolution=resolution, customer_response=response, escalation=escalation)

    def _response(self, case: SupportCase, resolution: ResolutionAnalysis, customer_confirmed: bool, confirmation_required: bool) -> CustomerResponse:
        safe = resolution.resolution_status == "RESOLVED"
        communication = "RESOLUTION" if safe else ("VERIFICATION_REQUEST" if resolution.resolution_status == "VERIFICATION_REQUIRED" else "PROGRESS_UPDATE")
        summary = "We have completed the verified resolution workflow." if safe else "We are continuing to investigate the reported issue."
        remaining = list(resolution.remaining_work)
        if confirmation_required and not customer_confirmed:
            remaining.append("Confirm the behavior in your environment.")
        full = summary + (" Please confirm the behavior in your environment." if confirmation_required and not customer_confirmed else "")
        return CustomerResponse(
            ticket_id=case.external_id or "Not provided",
            response_status=resolution.resolution_status,
            communication_type=communication,
            subject=f"Update on: {case.title}",
            summary=summary,
            resolution="The issue is resolved based on the recorded evidence." if safe else "No confirmed resolution is being claimed yet.",
            verification="Validation and required outcome checks passed." if safe else "Validation or outcome confirmation is still pending.",
            customer_impact=resolution.customer_impact_after_change,
            resolution_confidence=resolution.confidence,
            evidence_strength="STRONG" if safe else ("MODERATE" if resolution.confidence == "MEDIUM" else "LIMITED"),
            evidence_basis=[item.evidence for item in resolution.resolution_evidence],
            customer_confirmation_status="CONFIRMED" if customer_confirmed else ("PENDING" if confirmation_required else "NOT_REQUIRED"),
            customer_confirmation_required=confirmation_required,
            customer_action_required=confirmation_required and not customer_confirmed,
            customer_action="Please confirm whether the expected behavior is restored." if confirmation_required and not customer_confirmed else "No customer action required.",
            remaining_work=remaining,
            limitations=resolution.blocking_issues,
            next_steps=remaining or ["No further action is required."],
            tone="PROFESSIONAL",
            safe_to_send=not resolution.blocking_issues,
            requires_human_review=not safe,
            internal_notes=resolution.blocking_issues,
            unsupported_claims=["Deployment or production resolution without direct evidence."],
            full_response=full,
        )

    def _escalation(self, case: SupportCase, resolution: ResolutionAnalysis) -> EscalationAnalysis:
        if resolution.resolution_status == "RESOLVED":
            return EscalationAnalysis(ticket_id=case.external_id or "Not provided", escalation_status="NO_ESCALATION_REQUIRED", reason="NONE", priority="LOW", summary="No escalation is required.", safety_gate_passed=True, autonomous_continuation_allowed=True, confidence="HIGH", recommended_next_stage="AUDIT", resume_condition="None required", final_recommendation="Continue to final audit and closure.")
        reason = "VALIDATION_INCOMPLETE" if "Validation evidence is not confirmed as passed." in resolution.blocking_issues else "DEPLOYMENT_REQUIRED"
        return EscalationAnalysis(ticket_id=case.external_id or "Not provided", escalation_status="WORKFLOW_BLOCKED", reason=reason, priority="HIGH", summary="Human or additional engineering action is required before closure.", safety_gate_passed=False, autonomous_continuation_allowed=False, blocking_factors=resolution.blocking_issues, required_human_actions=[EscalationAction(action="Review the blocking resolution conditions.", reason="The case cannot be represented as resolved without the missing evidence.", priority="HIGH")], unresolved_questions=resolution.remaining_work, affected_workflow_stages=["RESOLUTION", "CUSTOMER_RESPONSE"], evidence=["resolution_analysis"], confidence="HIGH", recommended_next_stage="RESOLUTION", resume_condition="Resolve the listed blocking conditions.", final_recommendation="Do not close the case or claim production resolution.")
