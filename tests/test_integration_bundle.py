import unittest

from supportmaster.integrations import (
    InMemoryCIAdapter,
    InMemoryIssueTrackerAdapter,
    InMemoryMonitoringAdapter,
    IntegrationPolicy,
    IntegrationGateway,
    IssueRecord,
    ReadOnlyIntegrationBundle,
    IncidentRecord,
)
from supportmaster.models.support_case import SupportCase


class IntegrationBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = SupportCase(
            tenant_id="tenant-a", source_system="fixture", external_id="SUP-1",
            title="Gateway timeout", description="Requests time out.", service="gateway",
        )

    def test_collects_read_only_evidence_and_receipts(self) -> None:
        gateway = IntegrationGateway(IntegrationPolicy(mode="LIVE", allowed_permissions=["READ_ISSUES", "READ_MONITORING", "READ_CI", "TRIGGER_CI"]))
        issues = InMemoryIssueTrackerAdapter([IssueRecord(key="SUP-1", title="Gateway timeout")], gateway=gateway)
        monitoring = InMemoryMonitoringAdapter([IncidentRecord(incident_id="INC-1", service="gateway")], gateway=gateway)
        ci = InMemoryCIAdapter(gateway=gateway)
        run = ci.trigger("build", commit_sha="abc")
        bundle = ReadOnlyIntegrationBundle(issue_tracker=issues, monitoring=monitoring, ci=ci).collect(self.case, ci_run_id=run.external_id)
        self.assertEqual(bundle.status, "COMPLETE")
        self.assertEqual(len(bundle.issues), 1)
        self.assertEqual(len(bundle.incidents), 1)
        self.assertEqual(bundle.ci_status.status, "QUEUED")
        self.assertEqual(len(bundle.receipts), 3)

    def test_default_policy_fails_closed_without_calling_sources(self) -> None:
        issues = InMemoryIssueTrackerAdapter([IssueRecord(key="SUP-1", title="Gateway timeout")])
        bundle = ReadOnlyIntegrationBundle(issue_tracker=issues).collect(self.case)
        self.assertEqual(bundle.status, "COMPLETE")
        self.assertEqual(len(bundle.issues), 1)
        self.assertEqual(bundle.receipts[0].status, "SUCCEEDED")


if __name__ == "__main__":
    unittest.main()
