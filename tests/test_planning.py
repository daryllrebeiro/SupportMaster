import tempfile
import unittest
from pathlib import Path

from supportmaster.investigation import InvestigationService
from supportmaster.intake import CaseIntakeService
from supportmaster.models.investigation_artifacts import EvidenceLink, InvestigationSummary, RepositorySignal
from supportmaster.models.planning import PlanningAssessment
from supportmaster.persistence import SQLiteRunStore, TenantAccessError
from supportmaster.planning import PlanningService


class PlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SQLiteRunStore(Path(self.temp_dir.name) / "runs.db")
        self.case = CaseIntakeService(self.store).ingest(
            {"title": "Payment timeout", "description": "Payment service times out", "service": "payments", "environment": "production", "steps": ["Submit payment"]},
            source_system="manual",
            tenant_id="tenant-a",
        ).case
        self.service = PlanningService()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_blocked_investigation_never_produces_authorized_fix(self) -> None:
        summary = InvestigationSummary(case_id=self.case.case_id, tenant_id="tenant-a", investigation_status="BLOCKED", missing_evidence=[])
        root, remediation = self.service.build(self.case, summary)
        self.assertEqual(root.classification, "UNKNOWN")
        self.assertEqual(remediation.remediation_status, "NEEDS_MORE_EVIDENCE")
        self.assertFalse(remediation.implementation_allowed)

    def test_evidence_linked_signals_produce_conservative_plan(self) -> None:
        summary = InvestigationSummary(
            case_id=self.case.case_id,
            tenant_id="tenant-a",
            evidence_links=[EvidenceLink(record_id="e-1", relevance="Timeout log")],
            repository_signals=[RepositorySignal(repository="payments", path="worker.py", summary="timeout handling", commit_sha="abc")],
            investigation_status="READY",
        )
        root, remediation = self.service.build(self.case, summary)
        self.assertEqual(root.classification, "STRONGLY_SUPPORTED")
        self.assertEqual(remediation.remediation_status, "READY")
        self.assertFalse(remediation.implementation_allowed)
        self.assertEqual(remediation.remediation_steps[0].change_type, "CODE")

    def test_planning_assessment_round_trips_with_tenant_guard(self) -> None:
        summary = InvestigationSummary(case_id=self.case.case_id, tenant_id="tenant-a", investigation_status="BLOCKED")
        root, remediation = self.service.build(self.case, summary)
        assessment = PlanningAssessment(case_id=self.case.case_id, tenant_id="tenant-a", root_cause=root, remediation=remediation)
        self.store.save_planning_assessment(assessment)
        self.assertEqual(self.store.get_planning_assessment(self.case.case_id, tenant_id="tenant-a").case_id, self.case.case_id)
        with self.assertRaises(TenantAccessError):
            self.store.get_planning_assessment(self.case.case_id, tenant_id="tenant-b")


if __name__ == "__main__":
    unittest.main()
