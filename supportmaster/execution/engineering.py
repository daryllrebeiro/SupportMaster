"""Authorization-aware implementation and validation execution."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from ..models.control import AuthorizationGrant, ExternalOperationReceipt
from ..models.remediation import RemediationPlan
from .adapters import GitRepositoryAdapter, TestRunnerAdapter
from .contracts import EngineeringExecutionResult


class CodeChangeAdapter(Protocol):
    def apply(self, repository: Path, plan: RemediationPlan, approved_paths: Sequence[str]) -> ExternalOperationReceipt: ...

    def rollback(self, repository: Path, approved_paths: Sequence[str]) -> ExternalOperationReceipt: ...


def _grant(state: Mapping[str, Any], scope: str) -> AuthorizationGrant | None:
    now = datetime.now(timezone.utc)
    run_id = state.get("run_id")
    for raw in state.get("authorizations") or []:
        grant = raw if isinstance(raw, AuthorizationGrant) else AuthorizationGrant.model_validate(raw)
        if grant.scope != scope or not grant.active:
            continue
        if grant.run_id and run_id and grant.run_id != run_id:
            continue
        expires_at = grant.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and expires_at <= now:
            continue
        return grant
    return None


class ControlledEngineeringExecutor:
    """Execute only a ready plan with an active implementation grant."""

    def __init__(self, git: GitRepositoryAdapter, code_change: CodeChangeAdapter, tests: TestRunnerAdapter) -> None:
        self.git = git
        self.code_change = code_change
        self.tests = tests

    def execute(
        self,
        state: Mapping[str, Any],
        *,
        repository_path: str | Path,
        plan: RemediationPlan | Mapping[str, Any],
        approved_paths: Sequence[str],
        test_command: Sequence[str],
        rollback_on_failure: bool = True,
    ) -> EngineeringExecutionResult:
        remediation = plan if isinstance(plan, RemediationPlan) else RemediationPlan.model_validate(plan)
        receipts: list[ExternalOperationReceipt] = []
        repository = Path(repository_path)
        paths = list(approved_paths)
        invalid = [path for path in paths if Path(path).is_absolute() or ".." in Path(path).parts]
        if _grant(state, "IMPLEMENTATION") is None:
            return self._blocked("IMPLEMENTATION_AUTHORIZATION", "No active IMPLEMENTATION authorization grant exists.")
        if remediation.remediation_status != "READY" or not remediation.implementation_allowed:
            return self._blocked("IMPLEMENTATION_PLAN", "Remediation plan is not explicitly ready for implementation.")
        if not paths or invalid:
            return self._blocked("IMPLEMENTATION_SCOPE", "Implementation requires a non-empty repository-relative approved path scope.")
        preflight = self.git.preflight(repository, paths)
        receipts.append(preflight)
        if preflight.status != "SUCCEEDED":
            return EngineeringExecutionResult(status="BLOCKED", receipts=receipts, errors=[preflight.error or "Git preflight failed."])
        if _grant(state, "IMPLEMENTATION") is None:
            receipts.append(self._authorization_receipt())
            return EngineeringExecutionResult(status="BLOCKED", receipts=receipts, errors=["Implementation authorization expired before change execution."])
        change = self.code_change.apply(repository, remediation, paths)
        receipts.append(change)
        if change.status != "SUCCEEDED":
            return EngineeringExecutionResult(status="FAILED", receipts=receipts, errors=[change.error or "Code change adapter failed."])
        if _grant(state, "IMPLEMENTATION") is None:
            receipts.append(self._authorization_receipt())
            return EngineeringExecutionResult(status="PARTIAL", receipts=receipts, changed_files=paths, errors=["Implementation authorization expired before validation."])
        validation = self.tests.run(repository, test_command)
        receipts.append(validation)
        if validation.status == "SUCCEEDED":
            return EngineeringExecutionResult(status="VALIDATED", receipts=receipts, changed_files=paths, validation_passed=True)
        if rollback_on_failure:
            rollback = self.code_change.rollback(repository, paths)
            receipts.append(rollback)
            return EngineeringExecutionResult(status="FAILED", receipts=receipts, changed_files=paths, rollback_attempted=True, errors=[validation.error or "Validation failed; rollback attempted."])
        return EngineeringExecutionResult(status="PARTIAL", receipts=receipts, changed_files=paths, errors=[validation.error or "Validation failed."])

    @staticmethod
    def _authorization_receipt() -> ExternalOperationReceipt:
        return ExternalOperationReceipt(operation_type="IMPLEMENTATION_AUTHORIZATION", requested_action="verify_implementation_grant", status="BLOCKED", error="Implementation authorization is missing or expired.")

    def _blocked(self, operation_type: str, error: str) -> EngineeringExecutionResult:
        receipt = ExternalOperationReceipt(operation_type=operation_type, requested_action="verify_implementation_request", status="BLOCKED", error=error)
        return EngineeringExecutionResult(status="BLOCKED", receipts=[receipt], errors=[error])


def persist_engineering_receipts(state: dict[str, Any], result: EngineeringExecutionResult) -> None:
    receipts = state.get("operation_receipts") or []
    receipts.extend(receipt.model_dump() for receipt in result.receipts)
    state["operation_receipts"] = receipts
