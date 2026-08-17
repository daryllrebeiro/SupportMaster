import tempfile
import unittest
from pathlib import Path

from supportmaster.evaluation import load_scenarios
from supportmaster.evaluation.quality import run_quality_pack
from supportmaster.persistence import SQLiteRunStore


class QualityPackTests(unittest.TestCase):
    def test_quality_pack_combines_functional_and_e2e_suites(self) -> None:
        scenarios = load_scenarios(Path(__file__).parents[1] / "fixtures" / "cases")
        with tempfile.TemporaryDirectory() as directory:
            result = run_quality_pack(SQLiteRunStore(Path(directory) / "quality.db"), scenarios)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.functional.status, "PASS")
        self.assertEqual(result.end_to_end.status, "PASS")
        self.assertGreater(result.check_counts["canonical_case"], 0)
        self.assertGreater(result.check_counts["e2e:unsafe_resolution_blocked"], 0)
        self.assertEqual(result.failures, [])

    def test_quality_pack_reports_failed_expectation(self) -> None:
        scenarios = load_scenarios(Path(__file__).parents[1] / "fixtures" / "cases")
        scenarios[0].expectations = {"canonical_case": "FAIL"}
        with tempfile.TemporaryDirectory() as directory:
            result = run_quality_pack(SQLiteRunStore(Path(directory) / "quality.db"), scenarios[:1])
        self.assertEqual(result.status, "FAIL")
        self.assertIn(f"{scenarios[0].scenario_id}:expectation:canonical_case", result.failures)


if __name__ == "__main__":
    unittest.main()
