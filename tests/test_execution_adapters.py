import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from supportmaster.execution import (
    InMemoryGitHubAdapter,
    PublicationExecutor,
    build_github_publish_result,
)
from supportmaster.models.control import AuthorizationGrant, ExternalOperationReceipt
from supportmaster.models.publish import (
    CommitPlan,
    PlannedFileChange,
    PullRequestPlan,
    PublishPlan,
)


class FakeGit:
    def __init__(self, *, push_status: str = "SUCCEEDED") -> None:
        self.push_status = push_status
        self.calls: list[str] = []

    def preflight(self, repository: Path, approved_paths: list[str]) -> ExternalOperationReceipt:
        self.calls.append("preflight")
        return ExternalOperationReceipt(
            operation_type="GIT_PREFLIGHT",
            requested_action="verify_scope",
            status="SUCCEEDED",
        )

    def commit(self, repository: Path, message: str, approved_paths: list[str]) -> ExternalOperationReceipt:
        self.calls.append("commit")
        return ExternalOperationReceipt(
            operation_type="GIT_COMMIT",
            requested_action="stage_and_commit",
            status="SUCCEEDED",
            external_id="abc123",
        )

    def push(self, repository: Path, branch: str) -> ExternalOperationReceipt:
        self.calls.append("push")
        return ExternalOperationReceipt(
            operation_type="GIT_PUSH",
            requested_action="push",
            status=self.push_status,
            error=None if self.push_status == "SUCCEEDED" else "push failed",
        )


def publication_plan() -> PublishPlan:
    return PublishPlan(
        status="READY_TO_PUBLISH",
        repository="example/supportmaster",
        branch="fix/support-1",
        implementation_summary="Implemented the approved fix.",
        root_cause_summary="Verified resource leak.",
        validation_summary="Required tests passed.",
        review_summary="Review approved.",
        commit=CommitPlan(
            message="Fix resource leak",
            summary="Close the resource on cancellation.",
            files=[
                PlannedFileChange(
                    file_path="src/fix.py",
                    change_type="MODIFY",
                    summary="Close the resource.",
                    reason="Approved remediation.",
                )
            ],
            scope_verified=True,
        ),
        pull_request=PullRequestPlan(
            title="Fix resource leak",
            body="Validation-backed fix.",
            base_branch="main",
            head_branch="fix/support-1",
            testing_summary="Tests passed.",
            risk_summary="Low risk.",
            validation_status="PASSED",
        ),
        validation_passed=True,
        review_passed=True,
        publication_allowed=True,
        uncommitted_changes_present=True,
        unexpected_changes_present=False,
        recommended_action="CREATE_PULL_REQUEST",
        recommendation="Publish the approved change.",
    )


class PublicationExecutorTests(unittest.TestCase):
    def test_missing_grant_blocks_before_adapter_calls(self) -> None:
        git = FakeGit()
        executor = PublicationExecutor(git, InMemoryGitHubAdapter())

        result = executor.execute(
            {"run_id": "run-1"},
            repository_path=".",
            plan=publication_plan(),
        )

        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(git.calls, [])
        self.assertEqual(result.receipts[0].status, "BLOCKED")

    def test_valid_grant_requires_and_records_every_publication_step(self) -> None:
        git = FakeGit()
        executor = PublicationExecutor(git, InMemoryGitHubAdapter())
        state = {
            "run_id": "run-1",
            "authorizations": [
                AuthorizationGrant(scope="PUBLISH", run_id="run-1").model_dump()
            ],
        }

        result = executor.execute(
            state,
            repository_path=".",
            plan=publication_plan(),
        )

        self.assertEqual(result.status, "PUBLISHED")
        self.assertEqual(git.calls, ["preflight", "commit", "push"])
        self.assertEqual(
            [receipt.status for receipt in result.receipts],
            ["SUCCEEDED", "SUCCEEDED", "SUCCEEDED", "SUCCEEDED", "SUCCEEDED"],
        )
        self.assertEqual(result.commit_sha, "abc123")
        self.assertEqual(result.pull_request_number, 1)
        github_result = build_github_publish_result(
            publication_plan(),
            result,
            {
                "validation_analysis": {"overall_status": "PASSED"},
                "duplicate_work_analysis": {"duplicate_status": "NO_DUPLICATE_FOUND"},
            },
        )
        self.assertEqual(github_result.status, "PUBLISHED")
        self.assertEqual(github_result.commit.commit_hash, "abc123")
        self.assertEqual(github_result.pull_request.status, "CREATED")

    def test_push_failure_is_reported_as_partial_publication(self) -> None:
        executor = PublicationExecutor(
            FakeGit(push_status="FAILED"),
            InMemoryGitHubAdapter(),
        )
        state = {
            "run_id": "run-1",
            "authorizations": [
                AuthorizationGrant(scope="PUBLISH", run_id="run-1").model_dump()
            ],
        }

        result = executor.execute(state, repository_path=".", plan=publication_plan())

        self.assertEqual(result.status, "PARTIALLY_PUBLISHED")
        self.assertEqual(result.commit_sha, "abc123")
        self.assertIn("push failed", result.errors)

    def test_expired_grant_is_not_accepted(self) -> None:
        executor = PublicationExecutor(FakeGit(), InMemoryGitHubAdapter())
        expired = AuthorizationGrant(
            scope="PUBLISH",
            run_id="run-1",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )

        result = executor.execute(
            {"run_id": "run-1", "authorizations": [expired.model_dump()]},
            repository_path=".",
            plan=publication_plan(),
        )

        self.assertEqual(result.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
