import tempfile
import unittest
from pathlib import Path

from supportmaster.integrations import IntegrationGateway, IntegrationPolicy
from supportmaster.models.control import ExternalOperationReceipt
from supportmaster.persistence import SQLiteRunStore
from supportmaster.telemetry import (
    AuditExporter,
    InMemoryTelemetrySink,
    MetricsRegistry,
    Redactor,
    SQLiteTelemetrySink,
    TelemetryRecorder,
    verify_audit_chain,
)
from supportmaster.workflow_state import SupportMasterState


class TelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SQLiteRunStore(Path(self.temp_dir.name) / "runs.db")
        self.store.create_run(SupportMasterState(run_id="run-telemetry"))
        self.sink = InMemoryTelemetrySink()
        self.metrics = MetricsRegistry()
        self.recorder = TelemetryRecorder(
            [self.sink, SQLiteTelemetrySink(self.store)],
            metrics=self.metrics,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_redactor_handles_secret_fields_and_inline_tokens(self) -> None:
        redactor = Redactor()
        value = redactor.value({"api_key": "super-secret", "message": "Bearer abc123"})
        self.assertEqual(value["api_key"], "[REDACTED]")
        self.assertIn("[REDACTED]", value["message"])

    def test_recorder_persists_correlation_and_metrics(self) -> None:
        event = self.recorder.emit(
            "INVESTIGATION_STARTED",
            run_id="run-telemetry",
            attributes={"ticket": "SUP-4821", "token": "hidden"},
        )
        self.assertEqual(event.correlation_id, "run-telemetry")
        self.assertEqual(self.store.list_telemetry("run-telemetry")[0].attributes["token"], "[REDACTED]")
        self.assertEqual(len(self.sink.events), 1)
        self.assertEqual(self.metrics.snapshot()[0].name, "supportmaster.telemetry.events")

    def test_span_records_success_and_error(self) -> None:
        with self.recorder.span("adapter.read", run_id="run-telemetry") as span:
            self.assertEqual(span.status, "OK")
        self.assertEqual(span.status, "OK")
        with self.assertRaises(RuntimeError):
            with self.recorder.span("adapter.write", run_id="run-telemetry"):
                raise RuntimeError("connector secret=bad")
        self.assertTrue(any(event.event_name == "SPAN_FINISHED" and event.level == "ERROR" for event in self.sink.events))

    def test_integration_gateway_emits_blocked_and_success_events(self) -> None:
        gateway = IntegrationGateway(
            IntegrationPolicy(mode="LIVE", allowed_permissions=["READ_ISSUES"]),
            telemetry=self.recorder,
            run_id="run-telemetry",
        )
        blocked = gateway.execute(
            permission="WRITE_ISSUES",
            target="jira",
            operation_type="issue.update",
            requested_action="update issue",
            operation=lambda: ExternalOperationReceipt(operation_type="x", requested_action="x", status="SUCCEEDED"),
        )
        self.assertEqual(blocked.status, "BLOCKED")
        allowed = gateway.execute(
            permission="READ_ISSUES",
            target="jira",
            operation_type="issue.read",
            requested_action="read issue",
            operation=lambda: ExternalOperationReceipt(operation_type="x", requested_action="x", status="SUCCEEDED"),
        )
        self.assertEqual(allowed.status, "SUCCEEDED")
        self.assertTrue(any(event.event_name == "INTEGRATION_BLOCKED" for event in self.sink.events))

    def test_audit_export_is_redacted_and_chain_verifiable(self) -> None:
        self.store.append_event("run-telemetry", "SECRET_EVENT", {"password": "do-not-export"})
        self.recorder.emit("RUN_NOTE", run_id="run-telemetry", attributes={"api_key": "do-not-export"})
        timeline = AuditExporter(self.store).build("run-telemetry")
        self.assertTrue(verify_audit_chain(timeline))
        serialized = timeline.model_dump_json()
        self.assertNotIn("do-not-export", serialized)
        self.assertIn("[REDACTED]", serialized)
        timeline.entries[0]["event_name"] = "TAMPERED"
        self.assertFalse(verify_audit_chain(timeline))


if __name__ == "__main__":
    unittest.main()
