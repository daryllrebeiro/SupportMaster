"""Deterministic safety-gate contracts for the SupportMaster graph.

These functions do not call an LLM and do not perform external actions. They
will be used by ADK Workflow route nodes in a later phase. For now they make
the non-negotiable routing policy executable and unit-testable in isolation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models.root_cause import RootCauseAnalysis
from .workflow_state import GateDecision


def _value(state: Mapping[str, Any], key: str, field: str) -> Any:
    value = state.get(key)
    if isinstance(value, Mapping):
        return value.get(field)
    return getattr(value, field, None)


def evaluate_duplicate_gate(state: Mapping[str, Any]) -> GateDecision:
    """Allow autonomous continuation only after a verified clean check."""
    status = _value(state, "duplicate_work_analysis", "duplicate_status")
    if status == "NO_DUPLICATE_FOUND":
        return GateDecision(
            gate="DUPLICATE_WORK",
            route="CONTINUE",
            reason="Duplicate-work analysis explicitly found no duplicate.",
            evidence_keys=["duplicate_work_analysis"],
        )

    if status == "DUPLICATE_FOUND":
        reason = "Existing duplicate work was found."
    elif status == "RELATED_WORK_FOUND":
        reason = "Related engineering work requires review before continuation."
    elif status == "INSUFFICIENT_EVIDENCE":
        return GateDecision(
            gate="DUPLICATE_WORK",
            route="CONTINUE",
            reason=(
                "Duplicate-work verification is incomplete; continuing in "
                "autonomous best-effort mode while preserving the uncertainty."
            ),
            required_actions=[
                "Record duplicate-work uncertainty and verify related work when search access is available."
            ],
            evidence_keys=["duplicate_work_analysis"],
            warnings=["DUPLICATE_CHECK_INCOMPLETE"],
        )
    else:
        reason = "Duplicate-work status is missing or unknown."

    return GateDecision(
        gate="DUPLICATE_WORK",
        route="SAFETY_STOP",
        reason=reason,
        blocking_reasons=["NO_VERIFIED_DUPLICATE_CHECK"],
        required_actions=["Verify duplicate and related engineering work."],
        evidence_keys=["duplicate_work_analysis"],
    )


def evaluate_review_gate(state: Mapping[str, Any]) -> GateDecision:
    """Authorize implementation only after a complete safe review."""
    status = _value(state, "review_analysis", "review_status")
    best_effort_duplicate = (
        state.get("autonomous_best_effort") is True
        and _value(state, "duplicate_work_analysis", "duplicate_status")
        == "INSUFFICIENT_EVIDENCE"
    )
    required_checks = (
        "root_cause_sufficiently_established",
        "remediation_alignment",
        "implementation_scope_acceptable",
        "duplicate_work_safety_passed",
        "regression_risk_acceptable",
        "implementation_reviewable",
    )
    failed_checks = [
        check
        for check in required_checks
        if _value(state, "review_analysis", check) is not True
        and not (check == "duplicate_work_safety_passed" and best_effort_duplicate)
    ]
    actionable_high_findings = []
    findings = state.get("review_analysis")
    findings = _value(state, "review_analysis", "findings") or []
    for finding in findings:
        severity = finding.get("severity") if isinstance(finding, Mapping) else getattr(finding, "severity", None)
        requires_action = finding.get("requires_action") if isinstance(finding, Mapping) else getattr(finding, "requires_action", False)
        if requires_action and severity in {"HIGH", "CRITICAL"}:
            actionable_high_findings.append(f"{severity}_ACTION_REQUIRED")

    if status == "APPROVED" and not failed_checks and not actionable_high_findings:
        return GateDecision(
            gate="REVIEW",
            route="READY_FOR_IMPLEMENTATION",
            reason="Review approved the change and all implementation safety checks passed.",
            evidence_keys=["review_analysis"],
            warnings=(
                ["DUPLICATE_CHECK_INCOMPLETE"]
                if best_effort_duplicate
                else []
            ),
        )

    return GateDecision(
        gate="REVIEW",
        route="SAFETY_STOP",
        reason="Review did not provide sufficient approval for implementation.",
        blocking_reasons=[
            f"REVIEW_STATUS:{status or 'UNKNOWN'}",
            *[f"REVIEW_CHECK_FAILED:{check}" for check in failed_checks],
            *[f"REVIEW_FINDING:{finding}" for finding in actionable_high_findings],
        ],
        required_actions=["Resolve review blockers and obtain explicit approval."],
        evidence_keys=["review_analysis"],
    )


def evaluate_validation_gate(state: Mapping[str, Any]) -> GateDecision:
    """Authorize publishing only after validation and testing both pass."""
    validation_status = _value(state, "validation_analysis", "overall_status")
    test_status = _value(state, "test_result", "overall_status")
    validation_ready = _value(
        state, "validation_analysis", "implementation_ready_for_review"
    ) is True
    tests_executed = _value(state, "test_result", "tests_executed") is True
    testing_complete = _value(
        state, "test_result", "required_testing_completed"
    ) is True
    if (
        validation_status == "PASSED"
        and test_status == "PASSED"
        and validation_ready
        and tests_executed
        and testing_complete
    ):
        return GateDecision(
            gate="VALIDATION",
            route="READY_FOR_PUBLISH",
            reason="Validation and testing both passed.",
            evidence_keys=["validation_analysis", "test_result"],
        )

    blockers = []
    if validation_status != "PASSED":
        blockers.append(f"VALIDATION_STATUS:{validation_status or 'UNKNOWN'}")
    if test_status != "PASSED":
        blockers.append(f"TEST_STATUS:{test_status or 'UNKNOWN'}")
    if not validation_ready:
        blockers.append("VALIDATION_NOT_READY_FOR_REVIEW")
    if not tests_executed:
        blockers.append("TESTS_NOT_EXECUTED")
    if not testing_complete:
        blockers.append("REQUIRED_TESTING_INCOMPLETE")
    return GateDecision(
        gate="VALIDATION",
        route="SAFETY_STOP",
        reason="Publishing is blocked until validation and tests both pass.",
        blocking_reasons=blockers,
        required_actions=["Complete and pass required validation and testing."],
        evidence_keys=["validation_analysis", "test_result"],
    )


def evaluate_audit_gate(state: Mapping[str, Any]) -> GateDecision:
    """Permit completion only after an approved final audit."""
    audit_status = _value(state, "workflow_audit", "audit_status")
    if audit_status == "APPROVED":
        return GateDecision(
            gate="AUDIT",
            route="COMPLETED",
            reason="Final audit approved the workflow result.",
            evidence_keys=["workflow_audit"],
        )

    return GateDecision(
        gate="AUDIT",
        route="SAFETY_STOP",
        reason="Final audit did not approve completion.",
        blocking_reasons=[f"AUDIT_STATUS:{audit_status or 'UNKNOWN'}"],
        required_actions=["Resolve audit findings before declaring completion."],
        evidence_keys=["workflow_audit"],
    )


def harden_root_cause_analysis(
    analysis: RootCauseAnalysis | Mapping[str, Any],
    *,
    repository_available: bool = False,
) -> RootCauseAnalysis:
    """Prevent unsupported HIGH-confidence RCA claims.

    Root-cause analysis runs before implementation and validation, so a HIGH
    confidence claim requires a confirmed classification, direct facts, no
    unresolved questions, and an identified repository. Otherwise confidence
    is conservatively reduced and the classification remains unconfirmed.
    """
    normalized = (
        analysis
        if isinstance(analysis, RootCauseAnalysis)
        else RootCauseAnalysis.model_validate(analysis)
    )
    if normalized.confidence != "HIGH":
        return normalized

    high_confidence_supported = (
        normalized.root_cause_determined
        and normalized.classification == "CONFIRMED"
        and bool(normalized.confirmed_facts)
        and not normalized.remaining_unknowns
        and repository_available
    )
    if high_confidence_supported:
        return normalized

    downgraded_confidence = (
        "MEDIUM"
        if normalized.classification == "STRONGLY_SUPPORTED"
        and normalized.confirmed_facts
        else "LOW"
    )
    updates: dict[str, Any] = {
        "confidence": downgraded_confidence,
        "classification": (
            normalized.classification
            if normalized.classification in {"POSSIBLE", "UNKNOWN", "REJECTED"}
            else "POSSIBLE"
        ),
    }
    if not repository_available:
        updates["remaining_unknowns"] = [
            *normalized.remaining_unknowns,
            "Repository/code evidence was not available for confirmation.",
        ]
    return normalized.model_copy(update=updates)
