import unittest

from supportmaster.control_gates import (
    evaluate_action_policy,
    evaluate_implementation_authorization_gate,
    evaluate_publish_authorization_gate,
)
from supportmaster.models.control import (
    AuthorizationGrant,
    ExternalOperationReceipt,
    PolicyDecision,
)
from supportmaster.workflow_state import (
    GateDecision,
    SupportMasterState,
    append_gate_history,
    issue_authorization,
)


class ControlContractTests(unittest.TestCase):
    def test_state_has_traceability_and_lifecycle_defaults(self) -> None:
        state = SupportMasterState()

        self.assertEqual(state.policy_version, "v1")
        self.assertEqual(state.gate_history, [])
        self.assertEqual(state.authorizations, [])
        self.assertEqual(state.operation_receipts, [])
        self.assertIsNone(state.terminal_outcome)

    def test_gate_history_is_appended_with_a_decision_id(self) -> None:
        state: dict[str, object] = {}
        decision = GateDecision(
            gate="REVIEW",
            route="SAFETY_STOP",
            reason="Review was not approved.",
            blocking_reasons=["REVIEW_STATUS:REJECTED"],
        )

        record = append_gate_history(state, decision)

        self.assertTrue(record.decision_id)
        self.assertEqual(len(state["gate_history"]), 1)
        self.assertEqual(state["gate_history"][0]["gate"], "REVIEW")

    def test_duplicate_uncertainty_cannot_authorize_mutation(self) -> None:
        state = {
            "duplicate_work_analysis": {
                "duplicate_status": "INSUFFICIENT_EVIDENCE"
            }
        }

        implementation = evaluate_action_policy(state, "IMPLEMENTATION")
        publishing = evaluate_action_policy(state, "PUBLISH")

        self.assertEqual(implementation.disposition, "REQUEST_INFORMATION")
        self.assertEqual(publishing.disposition, "REQUEST_INFORMATION")
        self.assertIn("NO_VERIFIED_DUPLICATE_CHECK", implementation.blocking_reasons)

    def test_approved_review_and_clean_duplicate_allow_implementation(self) -> None:
        state = {
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
        }

        decision = evaluate_action_policy(state, "IMPLEMENTATION")

        self.assertEqual(decision.disposition, "ALLOW")
        self.assertEqual(decision.policy_version, "v1")

    def test_production_action_always_pauses_for_human_authorization(self) -> None:
        decision = evaluate_action_policy({}, "PRODUCTION")

        self.assertEqual(decision.disposition, "PAUSE")
        self.assertIn(
            "PRODUCTION_ACTION_REQUIRES_HUMAN_APPROVAL",
            decision.blocking_reasons,
        )

    def test_implementation_authorization_gate_fails_closed_on_uncertainty(self) -> None:
        policy, gate = evaluate_implementation_authorization_gate(
            {
                "duplicate_work_analysis": {
                    "duplicate_status": "INSUFFICIENT_EVIDENCE"
                }
            }
        )

        self.assertEqual(policy.disposition, "REQUEST_INFORMATION")
        self.assertEqual(gate.route, "SAFETY_STOP")
        self.assertEqual(gate.gate, "IMPLEMENTATION_AUTHORIZATION")

    def test_publish_authorization_requires_a_publish_plan(self) -> None:
        state = {
            "duplicate_work_analysis": {
                "duplicate_status": "NO_DUPLICATE_FOUND"
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
            "publish_plan": {"publication_allowed": False},
        }

        policy, gate = evaluate_publish_authorization_gate(state)

        self.assertEqual(policy.disposition, "DENY")
        self.assertEqual(gate.route, "SAFETY_STOP")
        self.assertIn("PUBLISH_PLAN_NOT_AUTHORIZED", gate.blocking_reasons)

    def test_control_artifacts_round_trip(self) -> None:
        grant = AuthorizationGrant(scope="IMPLEMENTATION", run_id="run-1")
        receipt = ExternalOperationReceipt(
            operation_type="TEST",
            requested_action="pytest",
            status="SUCCEEDED",
        )
        decision = PolicyDecision(
            action="IMPLEMENTATION",
            disposition="ALLOW",
            reason="Approved",
        )

        self.assertEqual(
            AuthorizationGrant.model_validate(grant.model_dump()).grant_id,
            grant.grant_id,
        )
        self.assertEqual(
            ExternalOperationReceipt.model_validate(receipt.model_dump()).status,
            "SUCCEEDED",
        )
        self.assertEqual(
            PolicyDecision.model_validate(decision.model_dump()).action,
            "IMPLEMENTATION",
        )

    def test_denied_policy_cannot_issue_authorization(self) -> None:
        state: dict[str, object] = {"run_id": "run-1"}
        decision = PolicyDecision(
            action="PUBLISH",
            disposition="DENY",
            reason="Tests have not passed.",
        )

        with self.assertRaises(ValueError):
            issue_authorization(
                state,
                scope="PUBLISH",
                decision=decision,
            )
        self.assertEqual(state.get("authorizations", []), [])


if __name__ == "__main__":
    unittest.main()
