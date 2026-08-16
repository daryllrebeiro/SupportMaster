import tempfile
import unittest
from pathlib import Path

from supportmaster.intake import CaseIntakeService
from supportmaster.models.control import ExternalOperationReceipt
from supportmaster.models.planning import PlanningAssessment
from supportmaster.persistence import SQLiteRunStore, TenantAccessError
from supportmaster.resolution import ResolutionService


class ResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SQLiteRunStore(Path(self.temp_dir.name) / "runs.db")
        self.case = CaseIntakeService(self.store).ingest(
            {"id": "CASE-9", "title": "Checkout failure", "description": "Checkout fails", "service": "checkout"},
            source_system="portal",
            tenant_id="tenant-a",
        ).case
        self.service = ResolutionService()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_unverified_state_cannot_claim_resolution(self) -> None:
        bundle = self.service.build(self.case, {})
        self.assertNotEqual(bundle.resolution.resolution_status, "RESOLVED")
        self.assertFalse(bundle.customer_response.safe_to_send)
        self.assertEqual(bundle.escalation.escalation_status, "WORKFLOW_BLOCKED")

    def test_verified_validation_and_deployment_can_resolve(self) -> None:
        state = {
            "engineering_execution": {"status": "VALIDATED", "validation_passed": True},
            "implementation_result": {"implementation_status": "IMPLEMENTED", "implementation_summary": "Fixed checkout handling."},
            "validation_analysis": {"overall_status": "PASSED"},
            "github_publish_result": {"status": "PUBLISHED"},
        }
        bundle = self.service.build(self.case, state, deployment_confirmed=True, publication_required=True)
        self.assertEqual(bundle.resolution.resolution_status, "RESOLVED")
        self.assertTrue(bundle.resolution.ticket_closure_allowed)
        self.assertTrue(bundle.customer_response.safe_to_send)
        self.assertEqual(bundle.escalation.escalation_status, "NO_ESCALATION_REQUIRED")

    def test_customer_confirmation_remains_explicit(self) -> None:
        state = {"engineering_execution": {"status": "VALIDATED", "validation_passed": True}, "validation_analysis": {"overall_status": "PASSED"}}
        bundle = self.service.build(self.case, state, deployment_confirmed=True, customer_confirmation_required=True)
        self.assertEqual(bundle.customer_response.customer_confirmation_status, "PENDING")
        self.assertTrue(bundle.customer_response.customer_action_required)
        self.assertFalse(bundle.resolution.ticket_closure_allowed)

    def test_resolution_bundle_is_tenant_guarded(self) -> None:
        bundle = self.service.build(self.case, {})
        self.store.save_resolution_bundle(bundle)
        self.assertEqual(self.store.get_resolution_bundle(self.case.case_id, tenant_id="tenant-a").case_id, self.case.case_id)
        with self.assertRaises(TenantAccessError):
            self.store.get_resolution_bundle(self.case.case_id, tenant_id="tenant-b")


if __name__ == "__main__":
    unittest.main()
