"""Authorization-enforcing publication executor."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models.control import AuthorizationGrant, ExternalOperationReceipt
from ..models.github_publish import (
    GitCommitResult,
    GitHubPublishResult,
    GitPushResult,
    PullRequestResult,
)
from ..models.publish import PublishPlan
from .adapters import GitHubAdapter, GitRepositoryAdapter
from .contracts import PublicationExecutionResult


def _value(state: Mapping[str, Any], key: str, field: str) -> Any:
    value = state.get(key)
    if isinstance(value, Mapping):
        return value.get(field)
    return getattr(value, field, None)


class PublicationExecutor:
    """Execute commit/push/PR operations only with a valid PUBLISH grant."""

    def __init__(self, git: GitRepositoryAdapter, github: GitHubAdapter) -> None:
        self.git = git
        self.github = github

    def _grant(self, state: Mapping[str, Any]) -> AuthorizationGrant | None:
        run_id = state.get("run_id")
        grants = state.get("authorizations") or []
        now = datetime.now(timezone.utc)
        for raw in grants:
            grant = raw if isinstance(raw, AuthorizationGrant) else AuthorizationGrant.model_validate(raw)
            if grant.scope != "PUBLISH" or not grant.active:
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

    def _require_grant(self, state: Mapping[str, Any]) -> ExternalOperationReceipt | None:
        if self._grant(state) is not None:
            return None
        return ExternalOperationReceipt(
            operation_type="PUBLICATION_AUTHORIZATION",
            requested_action="verify_publish_grant",
            status="BLOCKED",
            error="No active PUBLISH authorization grant exists for this run.",
        )

    def execute(
        self,
        state: Mapping[str, Any],
        *,
        repository_path: str | Path,
        plan: PublishPlan | Mapping[str, Any],
    ) -> PublicationExecutionResult:
        """Run the publication sequence and return only verified receipts."""
        repository = Path(repository_path)
        publish_plan = plan if isinstance(plan, PublishPlan) else PublishPlan.model_validate(plan)
        approved_paths = [item.file_path for item in publish_plan.commit.files]
        receipts: list[ExternalOperationReceipt] = []

        blocked = self._require_grant(state)
        if blocked:
            return PublicationExecutionResult(status="BLOCKED", receipts=[blocked], errors=[blocked.error or "Authorization blocked."])

        if publish_plan.status != "READY_TO_PUBLISH" or not publish_plan.publication_allowed:
            blocked = ExternalOperationReceipt(
                operation_type="PUBLICATION_PLAN",
                requested_action="verify_publish_plan",
                status="BLOCKED",
                error="Publish plan is not explicitly authorized.",
            )
            return PublicationExecutionResult(status="BLOCKED", receipts=[blocked], errors=[blocked.error or "Publish plan blocked."])
        if not approved_paths or not publish_plan.commit.scope_verified:
            blocked = ExternalOperationReceipt(
                operation_type="PUBLICATION_SCOPE",
                requested_action="verify_approved_files",
                status="BLOCKED",
                error="Publication requires a verified non-empty file scope.",
            )
            return PublicationExecutionResult(status="BLOCKED", receipts=[blocked], errors=[blocked.error or "Publication scope blocked."])

        preflight = self.git.preflight(repository, approved_paths)
        receipts.append(preflight)
        if preflight.status != "SUCCEEDED":
            return PublicationExecutionResult(status="BLOCKED", receipts=receipts, errors=[preflight.error or "Git preflight failed."])

        blocked = self._require_grant(state)
        if blocked:
            receipts.append(blocked)
            return PublicationExecutionResult(status="BLOCKED", receipts=receipts, errors=[blocked.error or "Authorization expired."])
        commit = self.git.commit(repository, publish_plan.commit.message, approved_paths)
        receipts.append(commit)
        if commit.status != "SUCCEEDED":
            return PublicationExecutionResult(status="FAILED", receipts=receipts, errors=[commit.error or "Git commit failed."])

        blocked = self._require_grant(state)
        if blocked:
            receipts.append(blocked)
            return PublicationExecutionResult(status="PARTIALLY_PUBLISHED", receipts=receipts, commit_sha=commit.external_id, errors=[blocked.error or "Authorization expired before push."])
        push = self.git.push(repository, publish_plan.pull_request.head_branch)
        receipts.append(push)
        if push.status != "SUCCEEDED":
            return PublicationExecutionResult(status="PARTIALLY_PUBLISHED", receipts=receipts, commit_sha=commit.external_id, errors=[push.error or "Git push failed."])

        blocked = self._require_grant(state)
        if blocked:
            receipts.append(blocked)
            return PublicationExecutionResult(status="PARTIALLY_PUBLISHED", receipts=receipts, commit_sha=commit.external_id, errors=[blocked.error or "Authorization expired before PR creation."])
        pr = self.github.create_pull_request(
            repository=publish_plan.repository,
            title=publish_plan.pull_request.title,
            body=publish_plan.pull_request.body,
            base_branch=publish_plan.pull_request.base_branch,
            head_branch=publish_plan.pull_request.head_branch,
        )
        receipts.append(pr)
        if pr.status != "SUCCEEDED" or not pr.external_id:
            return PublicationExecutionResult(status="PARTIALLY_PUBLISHED", receipts=receipts, commit_sha=commit.external_id, errors=[pr.error or "Pull request creation failed."])

        blocked = self._require_grant(state)
        if blocked:
            receipts.append(blocked)
            return PublicationExecutionResult(status="PARTIALLY_PUBLISHED", receipts=receipts, commit_sha=commit.external_id, errors=[blocked.error or "Authorization expired before PR verification."])
        verification = self.github.verify_pull_request(
            repository=publish_plan.repository,
            pull_request_id=pr.external_id,
            expected_head=publish_plan.pull_request.head_branch,
            expected_base=publish_plan.pull_request.base_branch,
        )
        receipts.append(verification)
        if verification.status != "SUCCEEDED":
            return PublicationExecutionResult(status="PARTIALLY_PUBLISHED", receipts=receipts, commit_sha=commit.external_id, errors=[verification.error or "Pull request verification failed."])

        return PublicationExecutionResult(
            status="PUBLISHED",
            receipts=receipts,
            commit_sha=commit.external_id,
            pull_request_url=pr.details.get("url"),
            pull_request_number=int(pr.external_id),
        )


def persist_publication_receipts(
    state: dict[str, Any],
    result: PublicationExecutionResult,
) -> None:
    """Copy verified executor receipts into a mutable workflow state."""
    receipts = state.get("operation_receipts") or []
    receipts.extend(receipt.model_dump() for receipt in result.receipts)
    state["operation_receipts"] = receipts


def build_github_publish_result(
    plan: PublishPlan | Mapping[str, Any],
    result: PublicationExecutionResult,
    state: Mapping[str, Any],
) -> GitHubPublishResult:
    """Translate verified receipts into the existing publication contract."""
    publish_plan = plan if isinstance(plan, PublishPlan) else PublishPlan.model_validate(plan)
    by_type = {receipt.operation_type: receipt for receipt in result.receipts}
    commit = by_type.get("GIT_COMMIT")
    push = by_type.get("GIT_PUSH")
    pr = by_type.get("GITHUB_PULL_REQUEST")
    commit_ok = commit is not None and commit.status == "SUCCEEDED"
    push_ok = push is not None and push.status == "SUCCEEDED"
    pr_ok = pr is not None and pr.status == "SUCCEEDED"
    status = result.status
    next_action = "REVIEW_PULL_REQUEST" if status == "PUBLISHED" else "STOP"
    if status in {"FAILED", "PARTIALLY_PUBLISHED"}:
        next_action = "RETRY_PUBLICATION"

    return GitHubPublishResult(
        status=status,
        repository=publish_plan.repository,
        commit=GitCommitResult(
            status="COMPLETED" if commit_ok else ("FAILED" if commit else "NOT_STARTED"),
            branch=publish_plan.branch,
            commit_hash=result.commit_sha,
            commit_message=publish_plan.commit.message,
        ),
        push=GitPushResult(
            status="COMPLETED" if push_ok else ("FAILED" if push else "NOT_STARTED"),
            branch=publish_plan.pull_request.head_branch,
            remote="origin",
            remote_branch=publish_plan.pull_request.head_branch,
        ),
        pull_request=PullRequestResult(
            status="CREATED" if pr_ok else ("FAILED" if pr else "NOT_CREATED"),
            url=result.pull_request_url,
            number=result.pull_request_number,
            title=publish_plan.pull_request.title,
            base_branch=publish_plan.pull_request.base_branch,
            head_branch=publish_plan.pull_request.head_branch,
        ),
        files_published=[item.file_path for item in publish_plan.commit.files] if commit_ok else [],
        validation_confirmed=_value(state, "validation_analysis", "overall_status") == "PASSED",
        duplicate_check_confirmed=_value(state, "duplicate_work_analysis", "duplicate_status") == "NO_DUPLICATE_FOUND",
        publication_plan_confirmed=publish_plan.publication_allowed,
        pre_publish_checks=["PUBLISH_AUTHORIZATION", "GIT_PREFLIGHT"],
        errors=result.errors,
        warnings=result.warnings,
        rollback_required=False,
        rollback_notes=[],
        summary=(
            "Publication completed and all returned receipts were verified."
            if status == "PUBLISHED"
            else "Publication did not complete fully; see operation receipts."
        ),
        next_action=next_action,
    )
