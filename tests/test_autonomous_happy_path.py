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


class AutonomousHappyPathTests(unittest.TestCase):
    """Exercise the complete deterministic control path without an LLM."""

    def test_all_gates_reach_completed_without_human_input(self) -> None:
        state: dict[str, object] = {
            "duplicate_work_analysis": {
                "duplicate_status": "NO_DUPLICATE_FOUND"
            },
            "review_analysis": {
                "review_status": "APPROVED",
                "root_cause_sufficiently_established": True,
                "remediation_alignment": True,
                "implementation_scope_acceptable": True,
                "duplicate_work_safety_passed": True,
                "regression_risk_acceptable": True,
                "implementation_reviewable": True,
                "findings": [],
            },
            "validation_analysis": {
                "overall_status": "PASSED",
                "implementation_ready_for_review": True,
            },
            "test_result": {
                "overall_status": "PASSED",
                "tests_executed": True,
                "required_testing_completed": True,
            },
            "workflow_audit": {"audit_status": "APPROVED"},
        }

        decisions = [
            evaluate_duplicate_gate(state),
            evaluate_review_gate(state),
            evaluate_validation_gate(state),
            evaluate_audit_gate(state),
        ]

        self.assertEqual(
            [decision.route for decision in decisions],
            [
                "CONTINUE",
                "READY_FOR_IMPLEMENTATION",
                "READY_FOR_PUBLISH",
                "COMPLETED",
            ],
        )
        self.assertTrue(all(decision.route != "HUMAN_REVIEW_REQUIRED" for decision in decisions))
        self.assertEqual(decisions[-1].route, "COMPLETED")

    def test_incomplete_duplicate_search_is_recoverable_uncertainty(self) -> None:
        decision = evaluate_duplicate_gate(
            {
                "duplicate_work_analysis": {
                    "duplicate_status": "INSUFFICIENT_EVIDENCE"
                }
            }
        )
        self.assertEqual(decision.route, "CONTINUE")
        self.assertIn("DUPLICATE_CHECK_INCOMPLETE", decision.warnings)

    def test_blocked_routes_are_terminal_safety_stops(self) -> None:
        graph = create_publishing_gate_workflow("gemini-3.6-flash").graph
        assert graph is not None
        self.assertEqual(
            graph.get_next_pending_nodes("duplicate_work_gate", "SAFETY_STOP"),
            ["autonomous_safety_stop"],
        )
        self.assertEqual(
            graph.get_next_pending_nodes("final_audit_gate", "SAFETY_STOP"),
            ["autonomous_safety_stop"],
        )


if __name__ == "__main__":
    unittest.main()
