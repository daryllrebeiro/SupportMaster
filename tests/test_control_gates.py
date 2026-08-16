import unittest

from supportmaster.control_gates import (
    evaluate_audit_gate,
    evaluate_duplicate_gate,
    evaluate_review_gate,
    evaluate_validation_gate,
)


class ControlGateTests(unittest.TestCase):
    def test_duplicate_gate_requires_verified_clean_result(self) -> None:
        self.assertEqual(
            evaluate_duplicate_gate(
                {"duplicate_work_analysis": {"duplicate_status": "NO_DUPLICATE_FOUND"}}
            ).route,
            "CONTINUE",
        )
        for status in ("DUPLICATE_FOUND", "RELATED_WORK_FOUND", "INSUFFICIENT_EVIDENCE", "UNKNOWN", None):
            with self.subTest(status=status):
                decision = evaluate_duplicate_gate(
                    {"duplicate_work_analysis": {"duplicate_status": status}}
                )
                self.assertEqual(decision.route, "HUMAN_REVIEW_REQUIRED")

    def test_review_gate_requires_all_safety_checks(self) -> None:
        approved = {
            "review_status": "APPROVED",
            "root_cause_sufficiently_established": True,
            "remediation_alignment": True,
            "implementation_scope_acceptable": True,
            "duplicate_work_safety_passed": True,
            "regression_risk_acceptable": True,
            "implementation_reviewable": True,
        }
        self.assertEqual(
            evaluate_review_gate({"review_analysis": approved}).route,
            "READY_FOR_IMPLEMENTATION",
        )
        approved["implementation_scope_acceptable"] = False
        self.assertEqual(
            evaluate_review_gate({"review_analysis": approved}).route,
            "HUMAN_REVIEW_REQUIRED",
        )

    def test_validation_gate_requires_both_validation_and_tests(self) -> None:
        self.assertEqual(
            evaluate_validation_gate(
                {
                    "validation_analysis": {"overall_status": "PASSED"},
                    "test_result": {"overall_status": "PASSED"},
                }
            ).route,
            "READY_FOR_PUBLISH",
        )
        self.assertEqual(
            evaluate_validation_gate(
                {
                    "validation_analysis": {"overall_status": "PASSED"},
                    "test_result": {"overall_status": "NOT_RUN"},
                }
            ).route,
            "HUMAN_REVIEW_REQUIRED",
        )

    def test_audit_gate_blocks_everything_except_approved(self) -> None:
        self.assertEqual(
            evaluate_audit_gate({"workflow_audit": {"audit_status": "APPROVED"}}).route,
            "COMPLETED",
        )
        self.assertEqual(
            evaluate_audit_gate({"workflow_audit": {"audit_status": "BLOCKED"}}).route,
            "HUMAN_REVIEW_REQUIRED",
        )


if __name__ == "__main__":
    unittest.main()
