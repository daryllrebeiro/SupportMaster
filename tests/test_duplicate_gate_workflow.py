import unittest

from supportmaster.config import DEFAULT_MODEL
from supportmaster.workflows.duplicate_gate_workflow import (
    create_duplicate_gate_workflow,
)


class DuplicateGateWorkflowTests(unittest.TestCase):
    def test_graph_contains_conditional_duplicate_routes(self) -> None:
        workflow = create_duplicate_gate_workflow(DEFAULT_MODEL)

        self.assertIsNotNone(workflow.graph)
        graph = workflow.graph
        assert graph is not None
        next_on_continue = graph.get_next_pending_nodes(
            "duplicate_work_gate", "CONTINUE"
        )
        next_on_stop = graph.get_next_pending_nodes(
            "duplicate_work_gate", "SAFETY_STOP"
        )

        self.assertEqual(next_on_continue, ["evidence_agent"])
        self.assertEqual(next_on_stop, ["autonomous_safety_stop"])

    def test_selected_model_is_applied_to_branch_agents(self) -> None:
        workflow = create_duplicate_gate_workflow("gemini-3.6-flash")

        modelled_agents = [
            node for node in workflow.graph.nodes
            if hasattr(node, "model")
        ]
        self.assertTrue(modelled_agents)
        self.assertTrue(
            all(agent.model == "gemini-3.6-flash" for agent in modelled_agents)
        )


if __name__ == "__main__":
    unittest.main()
