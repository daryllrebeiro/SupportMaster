import hashlib
import unittest

from supportmaster.evidence import EvidenceIngestor, ingest_sup_4821


class EvidenceIngestionTests(unittest.TestCase):
    def test_sup_4821_ingests_all_expected_artifacts_with_hashes(self) -> None:
        bundle, analysis = ingest_sup_4821()

        self.assertEqual(bundle.ticket_id, "SUP-4821")
        self.assertEqual(len(bundle.records), 8)
        self.assertTrue(all(len(record.content_hash) == 64 for record in bundle.records))
        self.assertTrue(analysis.evidence_collection_performed)
        self.assertEqual(len(analysis.evidence_items), 8)
        self.assertEqual(analysis.root_cause_readiness, "READY_FOR_ROOT_CAUSE_ANALYSIS")

    def test_ingestion_redacts_secrets_but_hashes_original_content(self) -> None:
        content = "Authorization: Bearer secret-token\napi_key=abc123"
        ingestor = EvidenceIngestor()
        record = ingestor.ingest_text(
            content,
            source_uri="ticket://SUP-4821/comment/1",
            source_type="TICKET_COMMENT",
        )

        self.assertTrue(record.sensitive_data_detected)
        self.assertNotIn("secret-token", record.content)
        self.assertNotIn("abc123", record.content)
        self.assertEqual(record.content_hash, hashlib.sha256(content.encode()).hexdigest())

    def test_size_limit_is_fail_closed(self) -> None:
        ingestor = EvidenceIngestor(max_bytes=4)
        with self.assertRaises(ValueError):
            ingestor.ingest_text(
                "12345",
                source_uri="ticket://SUP-4821/oversized",
                source_type="ATTACHMENT",
            )

    def test_attach_to_state_preserves_bundle_and_analysis_provenance(self) -> None:
        ingestor = EvidenceIngestor()
        ingestor.bundle.ticket_id = "SUP-4821"
        ingestor.ingest_text(
            "gateway=api status=502",
            source_uri="ticket://SUP-4821/logs/1",
            source_type="TICKET_ATTACHMENT",
        )

        state = {}
        analysis = ingestor.attach_to_state(state)

        self.assertEqual(state["ticket_id"], "SUP-4821")
        self.assertEqual(len(state["evidence_records"]), 1)
        self.assertEqual(state["evidence_bundle"]["ticket_id"], "SUP-4821")
        self.assertEqual(state["evidence_analysis"]["evidence_items"][0]["name"], "1")
        self.assertEqual(analysis.root_cause_readiness, "READY_FOR_ROOT_CAUSE_ANALYSIS")


if __name__ == "__main__":
    unittest.main()
