import unittest

from supportmaster.agents.audit_agent import audit_agent
from supportmaster.agents.code_change_agent import code_change_agent
from supportmaster.agents.customer_response_agent import customer_response_agent
from supportmaster.agents.duplicate_work_agent import duplicate_work_agent
from supportmaster.agents.escalation_agent import escalation_agent
from supportmaster.agents.evidence_agent import evidence_agent
from supportmaster.agents.github_publish_agent import github_publish_agent
from supportmaster.agents.implementation_agent import implementation_agent
from supportmaster.agents.investigation_agent import investigation_agent
from supportmaster.agents.publish_agent import publish_agent
from supportmaster.agents.remediation_agent import remediation_agent
from supportmaster.agents.repository_agent import repository_agent
from supportmaster.agents.resolution_agent import resolution_agent
from supportmaster.agents.review_agent import review_agent
from supportmaster.agents.root_cause_agent import root_cause_agent
from supportmaster.agents.test_result_agent import test_result_agent
from supportmaster.agents.ticket_agent import ticket_analysis_agent
from supportmaster.agents.validation_agent import validation_agent
from supportmaster.agents.workflow_control_agent import workflow_control_agent
from supportmaster.agents.workflow_summary_agent import workflow_summary_agent
from supportmaster.workflow_state import OUTPUT_KEY_TO_STATE_FIELD, SupportMasterState


class StateContractTests(unittest.TestCase):
    def test_every_structured_agent_output_key_is_declared(self) -> None:
        agents = (
            ticket_analysis_agent,
            investigation_agent,
            duplicate_work_agent,
            evidence_agent,
            repository_agent,
            root_cause_agent,
            remediation_agent,
            review_agent,
            code_change_agent,
            implementation_agent,
            validation_agent,
            test_result_agent,
            publish_agent,
            github_publish_agent,
            resolution_agent,
            customer_response_agent,
            audit_agent,
            escalation_agent,
            workflow_summary_agent,
            workflow_control_agent,
        )
        state_fields = set(SupportMasterState.model_fields)
        for agent in agents:
            with self.subTest(agent=agent.name):
                self.assertIsNotNone(agent.output_key)
                self.assertIn(agent.output_key, OUTPUT_KEY_TO_STATE_FIELD)
                self.assertIn(OUTPUT_KEY_TO_STATE_FIELD[agent.output_key], state_fields)
                self.assertIsNotNone(agent.output_schema)


if __name__ == "__main__":
    unittest.main()
