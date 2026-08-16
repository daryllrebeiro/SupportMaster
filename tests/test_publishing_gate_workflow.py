import unittest

from supportmaster.workflows.publishing_gate_workflow import (
    create_publishing_gate_workflow,
)


class PublishingGateWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = create_publishing_gate_workflow("gemini-3.6-flash")
        self.graph = self.workflow.graph
        assert self.graph is not None

    def test_validation_must_pass_before_publishing(self) -> None:
        self.assertEqual(
            self.graph.get_next_pending_nodes(
                "validation_testing_gate", "READY_FOR_PUBLISH"
            ),
            ["publish_agent"],
        )
        self.assertEqual(
            self.graph.get_next_pending_nodes(
                "validation_testing_gate", "SAFETY_STOP"
            ),
            ["autonomous_safety_stop"],
        )

    def test_audit_must_approve_before_completion(self) -> None:
        self.assertEqual(
            self.graph.get_next_pending_nodes("final_audit_gate", "COMPLETED"),
            ["workflow_summary_agent"],
        )
        self.assertEqual(
            self.graph.get_next_pending_nodes(
                "final_audit_gate", "SAFETY_STOP"
            ),
            ["autonomous_safety_stop"],
        )

    def test_validation_and_audit_nodes_are_in_the_graph(self) -> None:
        node_names = {node.name for node in self.graph.nodes}
        self.assertIn("validation_agent", node_names)
        self.assertIn("test_result_agent", node_names)
        self.assertIn("github_publish_agent", node_names)
        self.assertIn("audit_agent", node_names)
        self.assertIn("workflow_control_agent", node_names)


if __name__ == "__main__":
    unittest.main()
