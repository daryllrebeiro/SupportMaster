import tempfile
import unittest
from pathlib import Path

from supportmaster.integrations.contracts import IncidentRecord
from supportmaster.investigation import InvestigationService, TokenRepositorySearch
from supportmaster.intake import CaseIntakeService
from supportmaster.persistence import SQLiteRunStore, TenantAccessError
from supportmaster.evidence.ingestion import EvidenceIngestor


class InvestigationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SQLiteRunStore(Path(self.temp_dir.name) / "runs.db")
        self.intake = CaseIntakeService(self.store)
        self.service = InvestigationService(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_related_case_and_duplicate_detection_are_tenant_scoped(self) -> None:
        first = self.intake.ingest({"id": "CASE-1", "title": "Checkout timeout", "description": "Checkout API times out for orders."}, source_system="portal", tenant_id="tenant-a").case
        second = self.intake.ingest({"id": "CASE-2", "title": "Checkout API timeout", "description": "Orders time out in checkout."}, source_system="portal", tenant_id="tenant-a").case
        self.intake.ingest({"id": "CASE-2", "title": "Checkout API timeout", "description": "Orders time out in checkout."}, source_system="portal", tenant_id="tenant-b")
        matches = self.service.related_cases(first)
        self.assertEqual(matches[0].case_id, second.case_id)
        self.assertEqual(matches[0].relation, "RELATED")

    def test_incident_correlation_and_repository_signals(self) -> None:
        case = self.intake.ingest({"title": "Payment worker failure", "description": "Payment worker returns timeout", "service": "payments", "environment": "production", "steps": ["Submit payment"]}, source_system="manual", tenant_id="tenant-a").case
        incidents = [IncidentRecord(incident_id="INC-1", service="payments", severity="high", summary="Payment worker timeout")]
        search = TokenRepositorySearch([{"repository": "payments", "path": "worker.py", "symbol": "process_payment", "summary": "payment timeout handling", "commit_sha": "abc123"}])
        summary = self.service.summarize(case, incidents=incidents, repository_search=search)
        self.assertEqual(summary.incident_correlations[0].incident_id, "INC-1")
        self.assertEqual(summary.repository_signals[0].path, "worker.py")

    def test_missing_evidence_is_explicit_and_persisted(self) -> None:
        case = self.intake.ingest({"title": "Unknown failure", "description": "Something failed"}, source_system="manual", tenant_id="tenant-a").case
        summary = self.service.summarize(case)
        self.assertEqual(summary.investigation_status, "BLOCKED")
        self.assertTrue(any(item.evidence_type == "AFFECTED_COMPONENT" for item in summary.missing_evidence))
        self.store.save_investigation_summary(summary)
        loaded = self.store.get_investigation_summary(case.case_id, tenant_id="tenant-a")
        self.assertEqual(loaded.case_id, case.case_id)
        with self.assertRaises(TenantAccessError):
            self.store.get_investigation_summary(case.case_id, tenant_id="tenant-b")

    def test_ingested_evidence_links_into_summary(self) -> None:
        case = self.intake.ingest({"title": "API error", "description": "API fails", "service": "gateway", "environment": "staging", "steps": ["Call endpoint"]}, source_system="manual", tenant_id="tenant-a").case
        ingestor = EvidenceIngestor()
        record = ingestor.ingest_text("ERROR gateway timeout", source_uri="log://1", source_type="LOG_FILE")
        summary = self.service.summarize(case, records=[record])
        self.assertEqual(summary.evidence_links[0].record_id, record.record_id)
        self.assertFalse(any(item.evidence_type == "APPLICATION_LOGS" for item in summary.missing_evidence))


if __name__ == "__main__":
    unittest.main()
