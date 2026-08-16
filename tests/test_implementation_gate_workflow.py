import unittest

from supportmaster.workflows.implementation_gate_workflow import (
    create_implementation_gate_workflow,
)


class ImplementationGateWorkflowTests(unittest.TestCase):
    def test_review_routes_only_approval_to_implementation(self) -> None:
        workflow = create_implementation_gate_workflow("gemini-3.6-flash")

        self.assertIsNotNone(workflow.graph)
        graph = workflow.graph
        assert graph is not None
        next_on_approval = graph.get_next_pending_nodes(
            "implementation_review_gate", "READY_FOR_IMPLEMENTATION"
        )
        next_on_block = graph.get_next_pending_nodes(
            "implementation_review_gate", "SAFETY_STOP"
        )

        self.assertEqual(next_on_approval, ["implementation_authorization_gate"])
        self.assertEqual(next_on_block, ["autonomous_safety_stop"])

    def test_implementation_authorization_must_pass_before_code_change(self) -> None:
        workflow = create_implementation_gate_workflow("gemini-3.6-flash")

        graph = workflow.graph
        assert graph is not None
        self.assertEqual(
            graph.get_next_pending_nodes(
                "implementation_authorization_gate", "READY_FOR_IMPLEMENTATION"
            ),
            ["code_change_agent"],
        )
        self.assertEqual(
            graph.get_next_pending_nodes(
                "implementation_authorization_gate", "SAFETY_STOP"
            ),
            ["autonomous_safety_stop"],
        )

    def test_workflow_contains_implementation_after_code_change_plan(self) -> None:
        workflow = create_implementation_gate_workflow()

        self.assertIsNotNone(workflow.graph)
        graph = workflow.graph
        assert graph is not None
        next_after_plan = graph.get_next_pending_nodes(
            "code_change_agent", None
        )
        self.assertEqual(next_after_plan, ["implementation_agent"])

    def test_read_only_investigation_fans_out_before_root_cause(self) -> None:
        workflow = create_implementation_gate_workflow()
        graph = workflow.graph
        assert graph is not None
        self.assertEqual(
            graph.get_next_pending_nodes("duplicate_work_gate", "CONTINUE"),
            ["evidence_agent", "repository_agent"],
        )
        self.assertEqual(
            graph.get_next_pending_nodes("investigation_evidence_fan_in", "CONTINUE"),
            ["root_cause_agent"],
        )
        self.assertEqual(workflow.max_concurrency, 2)


if __name__ == "__main__":
    unittest.main()
