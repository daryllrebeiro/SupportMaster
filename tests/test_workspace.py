import tempfile
import unittest
from pathlib import Path

from supportmaster.intake import CaseIntakeService
from supportmaster.models.investigation_artifacts import InvestigationSummary
from supportmaster.persistence import SQLiteRunStore, TenantAccessError
from supportmaster.workspace import CaseWorkspaceService


class WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SQLiteRunStore(Path(self.temp_dir.name) / "runs.db")
        self.case = CaseIntakeService(self.store).ingest({"title": "API issue", "description": "Fails", "id": "CASE-1"}, source_system="portal", tenant_id="tenant-a").case
        self.workspace = CaseWorkspaceService(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_snapshot_combines_available_artifacts_and_runs(self) -> None:
        self.store.save_investigation_summary(InvestigationSummary(case_id=self.case.case_id, tenant_id="tenant-a", investigation_status="BLOCKED"))
        snapshot = self.workspace.snapshot(self.case.case_id, "tenant-a")
        self.assertEqual(snapshot.case.case_id, self.case.case_id)
        self.assertIsNotNone(snapshot.investigation)
        self.assertEqual(snapshot.runs, [])

    def test_status_update_is_tenant_scoped(self) -> None:
        updated = self.workspace.update_status(self.case.case_id, "tenant-a", "ESCALATED")
        self.assertEqual(updated.status, "ESCALATED")
        with self.assertRaises(TenantAccessError):
            self.workspace.update_status(self.case.case_id, "tenant-b", "CLOSED")

    def test_list_filters_by_tenant_and_status(self) -> None:
        self.assertEqual(len(self.workspace.list("tenant-a")), 1)
        self.assertEqual(len(self.workspace.list("tenant-a", status="CLOSED")), 0)
        self.assertEqual(len(self.workspace.list("tenant-b")), 0)


if __name__ == "__main__":
    unittest.main()
