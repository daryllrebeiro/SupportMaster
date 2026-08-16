import unittest

from supportmaster.control_gates import evaluate_action_policy
from supportmaster.evidence import ingest_sup_4821
from supportmaster.execution import InMemoryGitHubAdapter, PublicationExecutor
from supportmaster.models.control import AuthorizationGrant

from tests.test_execution_adapters import FakeGit, publication_plan


class Sup4821ScenarioTests(unittest.TestCase):
    def test_incomplete_duplicate_search_stops_before_implementation(self) -> None:
        bundle, analysis = ingest_sup_4821()
        state = {
            "evidence_bundle": bundle.model_dump(),
            "evidence_analysis": analysis.model_dump(),
            "duplicate_work_analysis": {
                "duplicate_status": "INSUFFICIENT_EVIDENCE"
            },
        }

        decision = evaluate_action_policy(state, "IMPLEMENTATION")

        self.assertEqual(len(bundle.records), 8)
        self.assertEqual(decision.disposition, "REQUEST_INFORMATION")
        self.assertIn("NO_VERIFIED_DUPLICATE_CHECK", decision.blocking_reasons)

    def test_verified_sup4821_path_can_publish_with_receipts(self) -> None:
        bundle, analysis = ingest_sup_4821()
        state = {
            "run_id": "sup-4821-run",
            "evidence_bundle": bundle.model_dump(),
            "evidence_analysis": analysis.model_dump(),
            "duplicate_work_analysis": {
                "duplicate_status": "NO_DUPLICATE_FOUND"
            },
            "authorizations": [
                AuthorizationGrant(
                    scope="PUBLISH",
                    run_id="sup-4821-run",
                ).model_dump()
            ],
        }
        result = PublicationExecutor(
            FakeGit(),
            InMemoryGitHubAdapter(),
        ).execute(state, repository_path=".", plan=publication_plan())

        self.assertEqual(result.status, "PUBLISHED")
        self.assertEqual(len(result.receipts), 5)

    def test_github_failure_is_not_reported_as_fully_published(self) -> None:
        bundle, _ = ingest_sup_4821()
        state = {
            "run_id": "sup-4821-run",
            "evidence_bundle": bundle.model_dump(),
            "duplicate_work_analysis": {
                "duplicate_status": "NO_DUPLICATE_FOUND"
            },
            "authorizations": [
                AuthorizationGrant(
                    scope="PUBLISH",
                    run_id="sup-4821-run",
                ).model_dump()
            ],
        }
        result = PublicationExecutor(
            FakeGit(),
            InMemoryGitHubAdapter(create_success=False),
        ).execute(state, repository_path=".", plan=publication_plan())

        self.assertEqual(result.status, "PARTIALLY_PUBLISHED")
        self.assertNotEqual(result.status, "PUBLISHED")


if __name__ == "__main__":
    unittest.main()
