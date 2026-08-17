import tempfile
import unittest
from pathlib import Path

from supportmaster.persistence import SQLiteRunStore
from supportmaster.release import run_release_readiness


class ReleaseReadinessTests(unittest.TestCase):
    def test_production_posture_requires_authentication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_release_readiness(
                SQLiteRunStore(Path(directory) / "release.db"),
                Path(__file__).parents[1] / "fixtures" / "cases",
                environ={"SUPPORTMASTER_AUTH_MODE": "DISABLED"},
            )
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(next(check for check in result.checks if check.name == "authentication").status, "FAIL")

    def test_configured_release_posture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_release_readiness(
                SQLiteRunStore(Path(directory) / "release.db"),
                Path(__file__).parents[1] / "fixtures" / "cases",
                environ={"SUPPORTMASTER_AUTH_MODE": "REQUIRED", "SUPPORTMASTER_API_KEYS": "demo-secret|demo|tenant-a|RUN_EXECUTE,HEALTH_READ,AUDIT_READ"},
            )
        self.assertEqual(result.status, "PASS")
        self.assertTrue(all(check.status == "PASS" for check in result.checks))


if __name__ == "__main__":
    unittest.main()
