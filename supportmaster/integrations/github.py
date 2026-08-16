"""Policy wrapper for GitHub adapters used by the publication executor."""

from __future__ import annotations

from ..execution.adapters import GitHubAdapter
from ..models.control import ExternalOperationReceipt
from .policy import IntegrationGateway


class PolicyGuardedGitHubAdapter(GitHubAdapter):
    """Require integration scope in addition to the workflow PUBLISH grant."""

    def __init__(self, adapter: GitHubAdapter, *, gateway: IntegrationGateway | None = None) -> None:
        self.adapter = adapter
        self.gateway = gateway or IntegrationGateway()

    def create_pull_request(
        self,
        *,
        repository: str,
        title: str,
        body: str,
        base_branch: str,
        head_branch: str,
    ) -> ExternalOperationReceipt:
        return self.gateway.execute(
            permission="WRITE_REPOSITORY",
            target=repository,
            operation_type="GITHUB_PULL_REQUEST",
            requested_action="create_pull_request",
            operation=lambda: self.adapter.create_pull_request(
                repository=repository,
                title=title,
                body=body,
                base_branch=base_branch,
                head_branch=head_branch,
            ),
            payload={"repository": repository, "title": title, "base": base_branch, "head": head_branch},
        )

    def verify_pull_request(
        self,
        *,
        repository: str,
        pull_request_id: str,
        expected_head: str,
        expected_base: str,
    ) -> ExternalOperationReceipt:
        return self.gateway.execute(
            permission="READ_REPOSITORY",
            target=repository,
            operation_type="GITHUB_PULL_REQUEST_VERIFY",
            requested_action="verify_pull_request",
            operation=lambda: self.adapter.verify_pull_request(
                repository=repository,
                pull_request_id=pull_request_id,
                expected_head=expected_head,
                expected_base=expected_base,
            ),
            payload={"repository": repository, "pull_request_id": pull_request_id},
        )
