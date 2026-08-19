import json
import unittest
from unittest.mock import MagicMock, patch
from google.adk.agents.context import Context
from supportmaster.workflows.publishing_gate_workflow import validation_testing_gate
from supportmaster.workflow_state import SupportMasterState
from supportmaster.web import SupportMasterHandler
from supportmaster.persistence import SQLiteRunStore
import io
import os
import tempfile
from pathlib import Path


class MockSupportMasterHandler(SupportMasterHandler):
    def __init__(self, path, method="GET", body=b"", headers=None):
        self.path = path
        self.command = method
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.headers = headers or {}
        self.response_code = None
        self.response_headers = {}

    def send_response(self, code, message=None):
        self.response_code = code

    def send_header(self, keyword, value):
        self.response_headers[keyword] = value

    def end_headers(self):
        pass

    def log_message(self, format, *args):
        pass


class MockState:
    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)


class RobustnessAndCopilotTests(unittest.TestCase):
    def test_self_healing_retry_routing(self) -> None:
        # Mock Context with initial state
        state_data = {
            "run_id": "run-1",
            "tenant_id": "tenant-a",
            "healing_attempts": 0,
            "validation_failures": []
        }
        ctx = MagicMock(spec=Context)
        ctx.state = MockState(state_data)

        # Mock evaluate_validation_gate returning failure
        mock_decision = MagicMock()
        mock_decision.route = "SAFETY_STOP"
        mock_decision.status = "FAILED"
        mock_decision.model_dump.return_value = {"status": "FAILED", "route": "SAFETY_STOP"}

        with patch("supportmaster.workflows.publishing_gate_workflow.evaluate_validation_gate", return_value=mock_decision), \
             patch("supportmaster.workflows.publishing_gate_workflow.append_gate_history"):
            
            # Execute validation_testing_gate
            # Execute validation_testing_gate underlying function
            result = validation_testing_gate._func(ctx)
            
            # Should set route to RETRY_IMPLEMENTATION and increment healing_attempts
            self.assertEqual(ctx.route, "RETRY_IMPLEMENTATION")
            self.assertEqual(ctx.state["healing_attempts"], 1)
            self.assertEqual(len(ctx.state["validation_failures"]), 1)
            self.assertEqual(result["status"], "HEALING_RETRY")

    def test_self_healing_rollback_triggers(self) -> None:
        # Mock Context with 3 attempts already exhausted
        state_data = {
            "run_id": "run-1",
            "tenant_id": "tenant-a",
            "healing_attempts": 3,
            "operation_receipts": []
        }
        ctx = MagicMock(spec=Context)
        ctx.state = MockState(state_data)

        # Mock evaluate_validation_gate returning failure
        mock_decision = MagicMock()
        mock_decision.route = "SAFETY_STOP"
        mock_decision.status = "FAILED"
        mock_decision.model_dump.return_value = {"status": "FAILED", "route": "SAFETY_STOP"}

        with patch("supportmaster.workflows.publishing_gate_workflow.evaluate_validation_gate", return_value=mock_decision), \
             patch("supportmaster.workflows.publishing_gate_workflow.append_gate_history"):
            
            # Execute validation_testing_gate underlying function
            result = validation_testing_gate._func(ctx)
            
            # Should not retry (route stays SAFETY_STOP) and should record REPOSITORY_ROLLBACK receipt
            self.assertEqual(ctx.route, "SAFETY_STOP")
            self.assertEqual(len(ctx.state["operation_receipts"]), 1)
            self.assertEqual(ctx.state["operation_receipts"][0]["operation_type"], "REPOSITORY_ROLLBACK")

    def test_copilot_chat_endpoint(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / "test_run.db"
        old_run_db = os.environ.get("SUPPORTMASTER_RUN_DB")
        os.environ["SUPPORTMASTER_RUN_DB"] = str(db_path)

        try:
            store = SQLiteRunStore(db_path)
            # Seed mock run state and review task
            run_id = "run-123"
            state = SupportMasterState(run_id=run_id, tenant_id="demo-acme")
            store.create_run(state)
            task_obj, token = store.create_review_task(
                run_id=run_id,
                reason="gate-block",
                allowed_scopes=["IMPLEMENTATION"],
                resume_condition="continue"
            )

            # Build request payload
            payload = {"message": "Why was this code change chosen?"}
            body = json.dumps(payload).encode("utf-8")
            headers = {
                "X-SupportMaster-API-Key": "secret",
                "Content-Length": str(len(body))
            }

            handler = MockSupportMasterHandler(
                f"/api/reviews/{task_obj.task_id}/chat",
                method="POST",
                body=body,
                headers=headers
            )

            # Authenticate principal mock
            from supportmaster.security.auth import AuthResult, Principal
            principal = Principal(subject="operator", tenant_id="demo-acme", scopes=["RUN_EXECUTE", "AUDIT_READ"])
            auth_res = AuthResult(status="AUTHENTICATED", principal=principal)

            with patch("supportmaster.web.AUTHENTICATOR.authenticate", return_value=auth_res):
                handler.do_POST()

            self.assertEqual(handler.response_code, 200)
            res = json.loads(handler.wfile.getvalue().decode("utf-8"))
            self.assertIn("response", res)
            self.assertIn("Mock Response", res["response"])

        finally:
            os.environ["SUPPORTMASTER_RUN_DB"] = old_run_db or ""
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
