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

    def test_publish_authorization_must_pass_before_github_mutation(self) -> None:
        self.assertEqual(
            self.graph.get_next_pending_nodes("publish_agent", None),
            ["publish_authorization_gate"],
        )
        self.assertEqual(
            self.graph.get_next_pending_nodes(
                "publish_authorization_gate", "READY_FOR_PUBLISH"
            ),
            ["verified_publication_executor"],
        )
        self.assertEqual(
            self.graph.get_next_pending_nodes(
                "publish_authorization_gate", "SAFETY_STOP"
            ),
            ["autonomous_safety_stop"],
        )

    def test_unconfigured_executor_cannot_claim_publication(self) -> None:
        self.assertEqual(
            self.graph.get_next_pending_nodes(
                "verified_publication_executor", "SAFETY_STOP"
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
        self.assertIn("verified_publication_executor", node_names)
        self.assertIn("implementation_authorization_gate", node_names)
        self.assertIn("publish_authorization_gate", node_names)
        self.assertIn("audit_agent", node_names)
        self.assertIn("workflow_control_agent", node_names)

    def test_read_only_investigation_fans_out_and_joins_before_root_cause(self) -> None:
        self.assertEqual(
            self.graph.get_next_pending_nodes("duplicate_work_gate", "CONTINUE"),
            ["evidence_agent", "repository_agent"],
        )
        self.assertEqual(
            self.graph.get_next_pending_nodes("evidence_agent", None),
            ["investigation_evidence_join"],
        )
        self.assertEqual(
            self.graph.get_next_pending_nodes("repository_agent", None),
            ["investigation_evidence_join"],
        )
        self.assertEqual(
            self.graph.get_next_pending_nodes("investigation_evidence_fan_in", "CONTINUE"),
            ["root_cause_agent"],
        )

    def test_workflow_bounds_concurrency_for_read_only_fan_out(self) -> None:
        self.assertEqual(self.workflow.max_concurrency, 2)


if __name__ == "__main__":
    unittest.main()
