from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from supportmaster.execution import ControlledEngineeringExecutor
from supportmaster.models.control import AuthorizationGrant, ExternalOperationReceipt
from supportmaster.models.remediation import RemediationPlan


class FakeGit:
    def preflight(self, repository, approved_paths):
        return ExternalOperationReceipt(operation_type="GIT_PREFLIGHT", requested_action="verify_scope", status="SUCCEEDED")


class FakeChange:
    def __init__(self, status="SUCCEEDED"):
        self.status = status
        self.applied = 0
        self.rolled_back = 0

    def apply(self, repository, plan, approved_paths):
        self.applied += 1
        return ExternalOperationReceipt(operation_type="CODE_CHANGE", requested_action="apply", status=self.status)

    def rollback(self, repository, approved_paths):
        self.rolled_back += 1
        return ExternalOperationReceipt(operation_type="CODE_ROLLBACK", requested_action="rollback", status="SUCCEEDED")


class FakeTests:
    def __init__(self, status="SUCCEEDED"):
        self.status = status

    def run(self, repository, command):
        return ExternalOperationReceipt(operation_type="TEST_EXECUTION", requested_action=" ".join(command), status=self.status, error=None if self.status == "SUCCEEDED" else "tests failed")


def ready_plan() -> RemediationPlan:
    return RemediationPlan(remediation_status="READY", objective="Fix issue", root_cause="Verified cause", proposed_approach="Small change", implementation_allowed=True, next_action="IMPLEMENT_FIX")


class EngineeringExecutionTests(unittest.TestCase):
    def state(self, *, expires_at=None):
        return {"run_id": "run-1", "authorizations": [AuthorizationGrant(run_id="run-1", scope="IMPLEMENTATION", expires_at=expires_at)]}

    def test_missing_authorization_blocks_before_adapter_calls(self):
        change = FakeChange()
        executor = ControlledEngineeringExecutor(FakeGit(), change, FakeTests())
        with tempfile.TemporaryDirectory() as directory:
            result = executor.execute({"run_id": "run-1", "authorizations": []}, repository_path=directory, plan=ready_plan(), approved_paths=["src/app.py"], test_command=["python", "-m", "unittest"])
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(change.applied, 0)

    def test_authorized_change_is_validated(self):
        executor = ControlledEngineeringExecutor(FakeGit(), FakeChange(), FakeTests())
        with tempfile.TemporaryDirectory() as directory:
            result = executor.execute(self.state(), repository_path=directory, plan=ready_plan(), approved_paths=["src/app.py"], test_command=["python", "-m", "unittest"])
        self.assertEqual(result.status, "VALIDATED")
        self.assertTrue(result.validation_passed)
        self.assertEqual(result.changed_files, ["src/app.py"])

    def test_failed_validation_attempts_rollback(self):
        change = FakeChange()
        executor = ControlledEngineeringExecutor(FakeGit(), change, FakeTests("FAILED"))
        with tempfile.TemporaryDirectory() as directory:
            result = executor.execute(self.state(), repository_path=directory, plan=ready_plan(), approved_paths=["src/app.py"], test_command=["python", "-m", "unittest"])
        self.assertEqual(result.status, "FAILED")
        self.assertTrue(result.rollback_attempted)
        self.assertEqual(change.rolled_back, 1)

    def test_expired_grant_and_unsafe_scope_fail_closed(self):
        executor = ControlledEngineeringExecutor(FakeGit(), FakeChange(), FakeTests())
        with tempfile.TemporaryDirectory() as directory:
            expired = executor.execute(self.state(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)), repository_path=directory, plan=ready_plan(), approved_paths=["src/app.py"], test_command=["true"])
            unsafe = executor.execute(self.state(), repository_path=directory, plan=ready_plan(), approved_paths=["../secrets.txt"], test_command=["true"])
        self.assertEqual(expired.status, "BLOCKED")
        self.assertEqual(unsafe.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
