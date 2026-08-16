"""Deterministic safety-gate contracts for the SupportMaster graph.

These functions do not call an LLM and do not perform external actions. They
will be used by ADK Workflow route nodes in a later phase. For now they make
the non-negotiable routing policy executable and unit-testable in isolation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
        reason = "Duplicate-work verification is incomplete."
    else:
        reason = "Duplicate-work status is missing or unknown."

    return GateDecision(
        gate="DUPLICATE_WORK",
        route="HUMAN_REVIEW_REQUIRED",
        reason=reason,
        blocking_reasons=["NO_VERIFIED_DUPLICATE_CHECK"],
        required_actions=["Verify duplicate and related engineering work."],
        evidence_keys=["duplicate_work_analysis"],
    )


def evaluate_review_gate(state: Mapping[str, Any]) -> GateDecision:
    """Authorize implementation only after a complete safe review."""
    status = _value(state, "review_analysis", "review_status")
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
    ]

    if status == "APPROVED" and not failed_checks:
        return GateDecision(
            gate="REVIEW",
            route="READY_FOR_IMPLEMENTATION",
            reason="Review approved the change and all implementation safety checks passed.",
            evidence_keys=["review_analysis"],
        )

    return GateDecision(
        gate="REVIEW",
        route="HUMAN_REVIEW_REQUIRED",
        reason="Review did not provide sufficient approval for implementation.",
        blocking_reasons=[
            f"REVIEW_STATUS:{status or 'UNKNOWN'}",
            *[f"REVIEW_CHECK_FAILED:{check}" for check in failed_checks],
        ],
        required_actions=["Resolve review blockers and obtain explicit approval."],
        evidence_keys=["review_analysis"],
    )


def evaluate_validation_gate(state: Mapping[str, Any]) -> GateDecision:
    """Authorize publishing only after validation and testing both pass."""
    validation_status = _value(state, "validation_analysis", "overall_status")
    test_status = _value(state, "test_result", "overall_status")
    if validation_status == "PASSED" and test_status == "PASSED":
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
    return GateDecision(
        gate="VALIDATION",
        route="HUMAN_REVIEW_REQUIRED",
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
        route="HUMAN_REVIEW_REQUIRED",
        reason="Final audit did not approve completion.",
        blocking_reasons=[f"AUDIT_STATUS:{audit_status or 'UNKNOWN'}"],
        required_actions=["Resolve audit findings before declaring completion."],
        evidence_keys=["workflow_audit"],
    )
