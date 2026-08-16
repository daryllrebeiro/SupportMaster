import unittest

from supportmaster.control_gates import (
    evaluate_audit_gate,
    evaluate_duplicate_gate,
    evaluate_review_gate,
    evaluate_validation_gate,
)
from supportmaster.workflows.publishing_gate_workflow import (
    create_publishing_gate_workflow,
)


class EndToEndSafetyScenarioTests(unittest.TestCase):
    def test_duplicate_found_stops_before_downstream_work(self) -> None:
        decision = evaluate_duplicate_gate(
            {"duplicate_work_analysis": {"duplicate_status": "DUPLICATE_FOUND"}}
        )

        self.assertEqual(decision.route, "HUMAN_REVIEW_REQUIRED")
        self.assertIn("NO_VERIFIED_DUPLICATE_CHECK", decision.blocking_reasons)

    def test_duplicate_verification_incomplete_is_not_clean(self) -> None:
        decision = evaluate_duplicate_gate(
            {
                "duplicate_work_analysis": {
                    "duplicate_status": "INSUFFICIENT_EVIDENCE"
                }
            }
        )

        self.assertNotEqual(decision.route, "CONTINUE")

    def test_rejected_review_cannot_reach_implementation(self) -> None:
        decision = evaluate_review_gate(
            {
                "review_analysis": {
                    "review_status": "REJECTED",
                    "root_cause_sufficiently_established": False,
                }
            }
        )

        self.assertEqual(decision.route, "HUMAN_REVIEW_REQUIRED")

    def test_failed_validation_cannot_reach_publish(self) -> None:
        decision = evaluate_validation_gate(
            {
                "validation_analysis": {"overall_status": "FAILED"},
                "test_result": {"overall_status": "PASSED"},
            }
        )

        self.assertEqual(decision.route, "HUMAN_REVIEW_REQUIRED")
        self.assertNotEqual(decision.route, "READY_FOR_PUBLISH")

    def test_tests_not_run_cannot_reach_publish(self) -> None:
        decision = evaluate_validation_gate(
            {
                "validation_analysis": {"overall_status": "PASSED"},
                "test_result": {"overall_status": "NOT_RUN"},
            }
        )

        self.assertEqual(decision.route, "HUMAN_REVIEW_REQUIRED")

    def test_blocked_audit_cannot_reach_completed(self) -> None:
        decision = evaluate_audit_gate(
            {"workflow_audit": {"audit_status": "BLOCKED"}}
        )

        self.assertEqual(decision.route, "HUMAN_REVIEW_REQUIRED")
        self.assertNotEqual(decision.route, "COMPLETED")

    def test_full_workflow_exposes_all_enforcement_gates(self) -> None:
        workflow = create_publishing_gate_workflow("gemini-3.6-flash")
        self.assertIsNotNone(workflow.graph)
        graph = workflow.graph
        assert graph is not None
        node_names = {node.name for node in graph.nodes}

        self.assertIn("duplicate_work_gate", node_names)
        self.assertIn("implementation_review_gate", node_names)
        self.assertIn("validation_testing_gate", node_names)
        self.assertIn("final_audit_gate", node_names)


if __name__ == "__main__":
    unittest.main()
