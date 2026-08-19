import tempfile
import unittest
from pathlib import Path
from supportmaster.memory import CaseMemoryStore, CaseContextRetriever


class AgentMemoryTests(unittest.TestCase):
    def test_case_memory_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_memory.db"
            store = CaseMemoryStore(db_path=db_path)

            # Record some past resolved cases
            store.record(
                case_id="AUTH-001",
                tenant_id="tenant-a",
                title="SSO authentication callback error",
                description="SAML redirection failed with 400 Bad Request.",
                root_cause="SSO callback handler signature mismatch.",
                resolution_summary="Updated signing certificate settings.",
                tags=["sso", "auth", "saml"]
            )
            store.record(
                case_id="PERF-002",
                tenant_id="tenant-a",
                title="Database CPU utilization spike",
                description="DB CPU utilization hit 100% during bulk exports.",
                root_cause="Missing database table indexes.",
                resolution_summary="Added missing indexes on user_id.",
                tags=["db", "performance"]
            )
            store.record(
                case_id="AUTH-003",
                tenant_id="tenant-b",  # Cross-tenant case
                title="SSO login redirects forever",
                description="Users loop indefinitely on SSO.",
                root_cause="Session cookie invalidation.",
                resolution_summary="Fixed SameSite session cookies.",
                tags=["sso", "auth"]
            )

            # 1. Retrieve matches for SSO error (tenant-a)
            # 1. Retrieve matches for SSO (tenant-a)
            matches_sso = store.retrieve_similar("SSO", tenant_id="tenant-a")
            self.assertEqual(len(matches_sso), 1)
            self.assertEqual(matches_sso[0].case_id, "AUTH-001")
            self.assertEqual(matches_sso[0].title, "SSO authentication callback error")

            # 2. Assert tenant boundary (tenant-a queries shouldn't retrieve tenant-b's SSO case)
            matches_sso_b = store.retrieve_similar("SSO", tenant_id="tenant-b")
            self.assertEqual(len(matches_sso_b), 1)
            self.assertEqual(matches_sso_b[0].case_id, "AUTH-003")

            # 3. Context retriever formats correctly
            retriever = CaseContextRetriever(store)
            context = retriever.get_context("SSO", tenant_id="tenant-a")
            self.assertIn("## Relevant Past Cases (Retrieved from Memory)", context)
            self.assertIn("AUTH-001", context)
            self.assertIn("Updated signing certificate settings.", context)

            # 4. Context retriever returns empty string if no matches found
            no_match_context = retriever.get_context("unrelated search query", tenant_id="tenant-a")
            self.assertEqual(no_match_context, "")


if __name__ == "__main__":
    unittest.main()
