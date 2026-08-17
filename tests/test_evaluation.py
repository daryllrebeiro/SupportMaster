import tempfile
import unittest
from pathlib import Path

from supportmaster.evaluation import FunctionalEvaluationSuite, OrganizationAcceptanceSuite, load_scenarios
from supportmaster.models.organization import OrganizationProfile
from supportmaster.persistence import SQLiteRunStore


class EvaluationTests(unittest.TestCase):
    def test_generic_fixtures_pass_functional_suite(self) -> None:
        scenarios = load_scenarios(Path(__file__).parents[1] / "fixtures" / "cases")
        self.assertGreaterEqual(len(scenarios), 3)
        with tempfile.TemporaryDirectory() as directory:
            result = FunctionalEvaluationSuite(SQLiteRunStore(Path(directory) / "runs.db")).run(scenarios)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.passed, len(scenarios))

    def test_suite_reports_malformed_scenario_as_failure(self) -> None:
        scenarios = load_scenarios(Path(__file__).parents[1] / "fixtures" / "cases")
        scenarios[0].payload = {"title": "missing description"}
        with tempfile.TemporaryDirectory() as directory:
            result = FunctionalEvaluationSuite(SQLiteRunStore(Path(directory) / "runs.db")).run(scenarios)
        self.assertEqual(result.status, "FAIL")
        self.assertGreater(result.failed, 0)
        self.assertTrue(result.scenarios[0].error)

    def test_expectations_are_reported_as_machine_readable_checks(self) -> None:
        scenarios = load_scenarios(Path(__file__).parents[1] / "fixtures" / "cases")
        scenarios[0].expectations = {"canonical_case": "PASS", "unsafe_resolution_blocked": "PASS"}
        with tempfile.TemporaryDirectory() as directory:
            result = FunctionalEvaluationSuite(SQLiteRunStore(Path(directory) / "runs.db")).run(scenarios[:1])
        self.assertEqual(result.status, "PASS")
        self.assertTrue(any(check.name == "expectation:canonical_case" for check in result.scenarios[0].checks))

    def test_organization_acceptance_runs_fixtures_in_tenant_context(self) -> None:
        scenarios = load_scenarios(Path(__file__).parents[1] / "fixtures" / "cases")
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteRunStore(Path(directory) / "runs.db")
            result = OrganizationAcceptanceSuite(store).run(OrganizationProfile(organization_id="acme", display_name="Acme"), scenarios)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.suite.status, "PASS")

    def test_suspended_organization_fails_acceptance(self) -> None:
        scenarios = load_scenarios(Path(__file__).parents[1] / "fixtures" / "cases")
        with tempfile.TemporaryDirectory() as directory:
            result = OrganizationAcceptanceSuite(SQLiteRunStore(Path(directory) / "runs.db")).run(OrganizationProfile(organization_id="paused", display_name="Paused", status="SUSPENDED"), scenarios)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.suite.status, "PASS")


if __name__ == "__main__":
    unittest.main()
