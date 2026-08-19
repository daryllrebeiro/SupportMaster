import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

# Import export script module by modifying path
from supportmaster.persistence import SQLiteRunStore
from supportmaster.workflow_state import SupportMasterState

# We can import it dynamically
sys.path.append(str(Path(__file__).parent.parent / ".agents" / "skills" / "audit-exporter" / "scripts"))
import export


class AuditExporterTests(unittest.TestCase):
    def test_exporter_redacts_secrets_and_filters_by_tenant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "runs.db"
            store = SQLiteRunStore(db_path)

            # Create demo runs for two different tenants
            state_a = SupportMasterState(run_id="run-a", tenant_id="tenant-a")
            state_b = SupportMasterState(run_id="run-b", tenant_id="tenant-b")
            store.create_run(state_a)
            store.create_run(state_b)

            # Record some events, including secrets
            store.append_event("run-a", "TEST_EVENT", {"info": "clear", "api_key": "secret|operator|tenant-a"})
            store.append_event("run-b", "TEST_EVENT", {"info": "tenant-b-clear"})

            output_path = Path(directory) / "audit.json"

            # Execute main with mock args
            with patch("sys.argv", ["export.py", "--db", str(db_path), "--tenant", "tenant-a", "--output", str(output_path)]):
                export.main()

            # Verify file contents
            self.assertTrue(output_path.exists())
            with open(output_path, "r", encoding="utf-8") as f:
                logs = json.load(f)

            # Assert only tenant-a events exist
            self.assertEqual(len(logs), 2)  # run creation event + test event
            self.assertEqual(logs[0]["run_id"], "run-a")

            # Assert secret is redacted
            test_event_payload = logs[1]["payload"]
            self.assertEqual(test_event_payload["api_key"], "[REDACTED_SECRET]")
            self.assertEqual(test_event_payload["info"], "clear")


if __name__ == "__main__":
    unittest.main()
