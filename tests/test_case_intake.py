import tempfile
import unittest
from pathlib import Path

from supportmaster.intake import CaseIntakeService, normalize_case
from supportmaster.persistence import SQLiteRunStore, TenantAccessError
from supportmaster.models.support_case import SupportCase


class CaseIntakeTests(unittest.TestCase):
    def test_normalizer_maps_common_vendor_aliases(self) -> None:
        case = normalize_case(
            {
                "key": "CASE-17",
                "summary": "Login fails for enterprise users",
                "body": "Users receive a 502 after SSO callback.",
                "reporter": "Ari",
                "steps": "Open login\nComplete SSO\nObserve 502",
                "impact": "Enterprise users are blocked",
                "unknown_vendor_field": "preserved",
            },
            source_system="ticketing.example",
            tenant_id="tenant-a",
        )
        self.assertEqual(case.external_id, "CASE-17")
        self.assertEqual(case.title, "Login fails for enterprise users")
        self.assertEqual(len(case.reproduction_steps), 3)
        self.assertEqual(case.metadata["unknown_vendor_field"], "preserved")
        self.assertIn("Customer impact", case.workflow_text())

    def test_missing_description_fails_validation(self) -> None:
        with self.assertRaises(ValueError):
            normalize_case({"title": "No details"}, source_system="manual")

    def test_intake_is_idempotent_per_tenant_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteRunStore(Path(directory) / "runs.db")
            intake = CaseIntakeService(store)
            payload = {"id": "INC-9", "title": "Cache errors", "description": "Requests fail intermittently."}
            first = intake.ingest(payload, source_system="zendesk", tenant_id="tenant-a")
            replay = intake.ingest(payload, source_system="zendesk", tenant_id="tenant-a")
            other_tenant = intake.ingest(payload, source_system="zendesk", tenant_id="tenant-b")
            self.assertEqual(first.status, "CREATED")
            self.assertEqual(replay.status, "REPLAYED")
            self.assertEqual(first.case.case_id, replay.case.case_id)
            self.assertEqual(other_tenant.status, "CREATED")
            self.assertEqual(len(store.list_cases("tenant-a")), 1)
            with self.assertRaises(TenantAccessError):
                store.get_case(first.case.case_id, tenant_id="tenant-b")

    def test_support_case_round_trip(self) -> None:
        case = SupportCase(title="API failure", description="Requests fail", tenant_id="tenant-a")
        self.assertEqual(SupportCase.model_validate(case.model_dump()).case_id, case.case_id)


if __name__ == "__main__":
    unittest.main()
