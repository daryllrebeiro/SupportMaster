import unittest

from supportmaster.control_gates import (
    evaluate_review_gate,
    evaluate_validation_gate,
    harden_root_cause_analysis,
)
from supportmaster.models.review import ReviewAnalysis, ReviewFinding
from supportmaster.models.root_cause import RootCauseAnalysis
from supportmaster.models.test_result import TestResult
from supportmaster.models.validation import ValidationAnalysis
from supportmaster.workflow_state import (
    OUTPUT_KEY_TO_STATE_FIELD,
    SupportMasterState,
)


def approved_review_with_finding(finding: ReviewFinding) -> ReviewAnalysis:
    return ReviewAnalysis(
        review_status="APPROVED",
        decision="PROCEED_TO_HUMAN_REVIEW",
        review_confidence="HIGH",
        original_problem="Problem",
        root_cause_reviewed="Cause",
        root_cause_sufficiently_established=True,
        remediation_alignment=True,
        implementation_scope_acceptable=True,
        duplicate_work_safety_passed=True,
        validation_sufficient=True,
        original_problem_resolved=False,
        regression_risk_acceptable=True,
        implementation_reviewable=True,
        findings=[finding],
        review_summary="Reviewed",
        recommendation="Proceed",
    )


class HardeningTests(unittest.TestCase):
    def test_actionable_critical_review_finding_fails_closed(self) -> None:
        review = approved_review_with_finding(
            ReviewFinding(
                area="SECURITY",
                finding="Unresolved security risk",
                severity="CRITICAL",
                requires_action=True,
            )
        )
        decision = evaluate_review_gate({"review_analysis": review})
        self.assertEqual(decision.route, "SAFETY_STOP")

    def test_pass_status_without_executed_tests_fails_closed(self) -> None:
        validation = ValidationAnalysis(
            overall_status="PASSED",
            validation_confidence="HIGH",
            implementation_ready_for_review=True,
            original_problem="Problem",
            expected_behavior="Expected",
            root_cause_addressed=True,
            root_cause_validation_summary="Validated",
            regression_detected=False,
            recommendation="Proceed",
            next_action="APPROVE_FOR_REVIEW",
        )
        tests = TestResult(
            ticket_id="TEST-1",
            overall_status="PASSED",
            tests_executed=False,
            required_testing_completed=False,
            original_issue_reproduced=False,
            original_issue_resolved=False,
            regression_risk="UNKNOWN",
            resolution_verifiable=False,
        )
        decision = evaluate_validation_gate(
            {"validation_analysis": validation, "test_result": tests}
        )
        self.assertEqual(decision.route, "SAFETY_STOP")

    def test_a_publish_plan_alone_cannot_bypass_validation(self) -> None:
        decision = evaluate_validation_gate(
            {"publish_plan": {"publication_ready": True}}
        )
        self.assertEqual(decision.route, "SAFETY_STOP")

    def test_high_confidence_rca_is_downgraded_without_repository_evidence(self) -> None:
        analysis = RootCauseAnalysis(
            root_cause_determined=True,
            primary_root_cause="Serializer retains the full dataset",
            confidence="HIGH",
            classification="CONFIRMED",
            explanation="Plausible from the customer-provided error",
            confirmed_facts=["Customer reported an out-of-memory error"],
            recommended_next_agent="MORE_INFORMATION_REQUIRED",
        )
        normalized = harden_root_cause_analysis(
            analysis, repository_available=False
        )
        self.assertNotEqual(normalized.confidence, "HIGH")
        self.assertEqual(normalized.classification, "POSSIBLE")
        self.assertTrue(normalized.remaining_unknowns)

    def test_high_confidence_rca_requires_direct_repository_supported_evidence(self) -> None:
        analysis = RootCauseAnalysis(
            root_cause_determined=True,
            primary_root_cause="Serializer retains the full dataset",
            confidence="HIGH",
            classification="CONFIRMED",
            explanation="Source and runtime evidence align",
            confirmed_facts=["Source behavior", "Measured heap evidence"],
            recommended_next_agent="FIX_PLANNING_AGENT",
        )
        normalized = harden_root_cause_analysis(
            analysis, repository_available=True
        )
        self.assertEqual(normalized.confidence, "HIGH")

    def test_output_keys_map_to_declared_state_fields(self) -> None:
        state_fields = set(SupportMasterState.model_fields)
        self.assertEqual(
            set(OUTPUT_KEY_TO_STATE_FIELD),
            set(OUTPUT_KEY_TO_STATE_FIELD.values()),
        )
        self.assertTrue(set(OUTPUT_KEY_TO_STATE_FIELD).issubset(state_fields))


if __name__ == "__main__":
    unittest.main()
