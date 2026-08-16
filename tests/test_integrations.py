import unittest

from supportmaster.models.control import ExternalOperationReceipt
from supportmaster.integrations import (
    CIStatus,
    IncidentRecord,
    IntegrationGateway,
    IntegrationPolicy,
    InMemoryCIAdapter,
    InMemoryIssueTrackerAdapter,
    InMemoryMonitoringAdapter,
    InMemoryNotificationAdapter,
    IssueRecord,
    HttpCIAdapter,
    HttpIssueTrackerAdapter,
    HttpMonitoringAdapter,
    HttpNotificationAdapter,
    MetricSample,
    PolicyGuardedGitHubAdapter,
)
from supportmaster.operations import CircuitBreaker
from supportmaster.execution import InMemoryGitHubAdapter
from supportmaster.integrations.policy import record_integration_receipt, record_integration_result


class IntegrationAdapterTests(unittest.TestCase):
    def test_gateway_respects_dependency_circuit_breaker(self) -> None:
        breaker = CircuitBreaker(failure_threshold=1, recovery_seconds=60)
        gateway = IntegrationGateway(
            IntegrationPolicy(mode="LIVE", allowed_permissions=["READ_ISSUES"]),
            circuit_breaker=breaker,
        )
        first = gateway.execute(
            permission="READ_ISSUES",
            target="jira",
            operation_type="issue.read",
            requested_action="read issue",
            operation=lambda: (_ for _ in ()).throw(RuntimeError("jira unavailable")),
        )
        self.assertEqual(first.status, "FAILED")
        second = gateway.execute(
            permission="READ_ISSUES",
            target="jira",
            operation_type="issue.read",
            requested_action="read issue",
            operation=lambda: ExternalOperationReceipt(operation_type="x", requested_action="x", status="SUCCEEDED"),
        )
        self.assertEqual(second.status, "BLOCKED")

    def test_default_policy_allows_reads_and_blocks_mutations(self) -> None:
        issues = InMemoryIssueTrackerAdapter(
            [IssueRecord(key="SUP-4821", title="API gateway timeout")]
        )
        matches, search_receipt = issues.search("gateway")
        self.assertEqual([issue.key for issue in matches], ["SUP-4821"])
        self.assertEqual(search_receipt.status, "SUCCEEDED")

        comment_receipt = issues.add_comment("SUP-4821", "investigating")
        self.assertEqual(comment_receipt.status, "BLOCKED")
        self.assertEqual(issues.comments, [])

    def test_live_policy_is_least_privilege_and_target_scoped(self) -> None:
        policy = IntegrationPolicy(
            mode="LIVE",
            allowed_permissions=["WRITE_ISSUES", "TRIGGER_CI", "SEND_NOTIFICATIONS"],
            allowed_targets=["SUP-4821", "build-main", "#supportmaster"],
        )
        issue = InMemoryIssueTrackerAdapter(
            [IssueRecord(key="SUP-4821", title="API gateway timeout")],
            gateway=IntegrationGateway(policy),
        )
        receipt = issue.add_comment("SUP-4821", "approved update")
        self.assertEqual(receipt.status, "SUCCEEDED")
        self.assertEqual(len(issue.comments), 1)

        blocked = issue.add_comment("OTHER-1", "must not escape target scope")
        self.assertEqual(blocked.status, "BLOCKED")

    def test_ci_trigger_and_status_are_receipt_backed(self) -> None:
        ci = InMemoryCIAdapter(
            gateway=IntegrationGateway(
                IntegrationPolicy(mode="LIVE", allowed_permissions=["TRIGGER_CI", "READ_CI"])
            )
        )
        trigger = ci.trigger("build-main", commit_sha="abc123")
        self.assertEqual(trigger.status, "SUCCEEDED")
        status, read_receipt = ci.status(trigger.external_id or "")
        self.assertIsInstance(status, CIStatus)
        self.assertEqual(read_receipt.status, "SUCCEEDED")

    def test_monitoring_reads_and_notifications_respect_policy(self) -> None:
        monitoring = InMemoryMonitoringAdapter(
            incidents=[IncidentRecord(incident_id="inc-1", service="api", severity="P1")],
            metrics=[MetricSample(metric="http.5xx", value=12, dimensions={"service": "api"})],
        )
        incidents, incident_receipt = monitoring.incidents("api")
        metrics, metric_receipt = monitoring.metric("http.5xx", service="api")
        self.assertEqual(len(incidents), 1)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(incident_receipt.status, "SUCCEEDED")
        self.assertEqual(metric_receipt.status, "SUCCEEDED")

        notifications = InMemoryNotificationAdapter()
        receipt = notifications.send("#supportmaster", "run complete")
        self.assertEqual(receipt.status, "BLOCKED")
        self.assertEqual(notifications.messages, [])

    def test_payload_limit_fails_closed_and_receipt_can_enter_state(self) -> None:
        gateway = IntegrationGateway(
            IntegrationPolicy(max_payload_bytes=8, allowed_permissions=["SEND_NOTIFICATIONS"])
        )
        notifications = InMemoryNotificationAdapter(gateway=gateway)
        receipt = notifications.send("#ops", "this is too large")
        self.assertEqual(receipt.status, "BLOCKED")

        state = {}
        record_integration_receipt(state, receipt)
        self.assertEqual(state["operation_receipts"][0]["operation_type"], "NOTIFICATION_SEND")
        record_integration_result(state, "notification_attempt", {"channel": "#ops"}, receipt)
        self.assertEqual(state["integration_results"]["notification_attempt"]["channel"], "#ops")

    def test_http_adapters_use_injected_transport_and_policy(self) -> None:
        class FakeTransport:
            def __init__(self):
                self.calls = []

            def request(self, method, path, payload=None):
                self.calls.append((method, path, payload))
                if path == "/issues/search":
                    return 200, {"items": [{"key": "SUP-4821", "title": "Gateway timeout"}]}
                if path == "/pipelines/build-main/runs":
                    return 201, {"run_id": "ci-1"}
                if path == "/runs/ci-1":
                    return 200, {"status": "PASSED", "commit_sha": "abc"}
                if path == "/incidents":
                    return 200, {"items": [{"incident_id": "inc-1", "service": "api"}]}
                if path == "/metrics":
                    return 200, {"items": [{"metric": "http.5xx", "value": 4}]}
                if path == "/messages":
                    return 202, {"message_id": "msg-1"}
                return 404, {"error": "not found"}

        transport = FakeTransport()
        live = IntegrationGateway(
            IntegrationPolicy(
                mode="LIVE",
                allowed_permissions=[
                    "READ_ISSUES",
                    "TRIGGER_CI",
                    "READ_CI",
                    "READ_MONITORING",
                    "SEND_NOTIFICATIONS",
                ],
            )
        )
        issues, issue_receipt = HttpIssueTrackerAdapter(transport, gateway=live).search("gateway")
        trigger = HttpCIAdapter(transport, gateway=live).trigger("build-main", commit_sha="abc")
        status, status_receipt = HttpCIAdapter(transport, gateway=live).status("ci-1")
        incidents, incident_receipt = HttpMonitoringAdapter(transport, gateway=live).incidents("api")
        metrics, metric_receipt = HttpMonitoringAdapter(transport, gateway=live).metric("http.5xx", service="api")
        notification = HttpNotificationAdapter(transport, gateway=live).send("ops", "done")

        self.assertEqual(issues[0].key, "SUP-4821")
        self.assertEqual(issue_receipt.status, "SUCCEEDED")
        self.assertEqual(trigger.external_id, "ci-1")
        self.assertEqual(status.status, "PASSED")
        self.assertEqual(status_receipt.status, "SUCCEEDED")
        self.assertEqual(len(incidents), 1)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(incident_receipt.status, "SUCCEEDED")
        self.assertEqual(metric_receipt.status, "SUCCEEDED")
        self.assertEqual(notification.status, "SUCCEEDED")
        self.assertEqual(len(transport.calls), 6)

    def test_github_mutation_requires_integration_write_scope(self) -> None:
        dry_run = PolicyGuardedGitHubAdapter(InMemoryGitHubAdapter())
        blocked = dry_run.create_pull_request(
            repository="org/repo",
            title="fix",
            body="details",
            base_branch="main",
            head_branch="support/fix",
        )
        self.assertEqual(blocked.status, "BLOCKED")

        live = PolicyGuardedGitHubAdapter(
            InMemoryGitHubAdapter(),
            gateway=IntegrationGateway(
                IntegrationPolicy(
                    mode="LIVE",
                    allowed_permissions=["WRITE_REPOSITORY", "READ_REPOSITORY"],
                    allowed_targets=["org/repo"],
                )
            ),
        )
        created = live.create_pull_request(
            repository="org/repo",
            title="fix",
            body="details",
            base_branch="main",
            head_branch="support/fix",
        )
        self.assertEqual(created.status, "SUCCEEDED")


if __name__ == "__main__":
    unittest.main()
