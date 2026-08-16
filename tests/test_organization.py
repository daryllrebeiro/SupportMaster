import tempfile
import unittest
from pathlib import Path

from supportmaster.models.organization import OrganizationProfile, WorkflowPolicy
from supportmaster.organization import OrganizationContextService
from supportmaster.persistence import SQLiteRunStore


class OrganizationContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SQLiteRunStore(Path(self.temp_dir.name) / "runs.db")
        self.service = OrganizationContextService(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_ensure_creates_neutral_default_context(self) -> None:
        profile = self.service.ensure("org-a", display_name="Acme Support")
        self.assertEqual(profile.organization_id, "org-a")
        self.assertEqual(profile.display_name, "Acme Support")
        self.assertTrue(profile.workflow_policy.require_duplicate_check)

    def test_update_changes_config_without_changing_identity(self) -> None:
        self.service.ensure("org-a")
        updated = self.service.update(
            "org-a",
            {
                "products": ["Payments"],
                "terminology": {"incident": "service event"},
                "workflow_policy": WorkflowPolicy(allow_autonomous_code_change=True).model_dump(),
            },
        )
        self.assertEqual(updated.organization_id, "org-a")
        self.assertEqual(updated.products, ["Payments"])
        self.assertTrue(updated.workflow_policy.allow_autonomous_code_change)

    def test_suspended_context_round_trips(self) -> None:
        profile = OrganizationProfile(organization_id="org-b", display_name="Beta", status="SUSPENDED")
        self.service.save(profile)
        self.assertEqual(self.service.get("org-b").status, "SUSPENDED")
        self.assertEqual(len(self.store.list_organizations(status="SUSPENDED")), 1)


if __name__ == "__main__":
    unittest.main()
