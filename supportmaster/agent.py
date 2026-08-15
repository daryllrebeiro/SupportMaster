from google.adk.agents import SequentialAgent

from .agents.ticket_agent import ticket_analysis_agent
from .agents.investigation_agent import investigation_agent
from .agents.duplicate_work_agent import duplicate_work_agent
from .agents.evidence_agent import evidence_agent
from .agents.repository_agent import repository_agent
from .agents.root_cause_agent import root_cause_agent
from .agents.remediation_agent import remediation_agent
from .agents.review_agent import review_agent
from .agents.code_change_agent import code_change_agent
from .agents.implementation_agent import implementation_agent
from .agents.validation_agent import validation_agent
from .agents.test_result_agent import test_result_agent
from .agents.publish_agent import publish_agent
from .agents.github_publish_agent import github_publish_agent
from .agents.resolution_agent import resolution_agent
from .agents.customer_response_agent import customer_response_agent
from .agents.audit_agent import audit_agent
from .agents.escalation_agent import escalation_agent
from .agents.workflow_summary_agent import workflow_summary_agent
from .agents.workflow_control_agent import workflow_control_agent


root_agent = SequentialAgent(
    name="supportmaster",
    description=(
        "SupportMaster is an autonomous customer-support engineering "
        "workflow that analyzes customer issues, investigates evidence, "
        "detects duplicate engineering work, identifies root causes, "
        "plans and implements remediation, validates and tests changes, "
        "publishes approved changes through GitHub, determines resolution "
        "status, communicates with the customer, and performs final "
        "safety, escalation, audit, and workflow-control checks."
    ),
    sub_agents=[
        # ==========================================================
        # PHASE 1 — UNDERSTAND THE CUSTOMER ISSUE
        # ==========================================================

        # Analyze the original support ticket and establish:
        # - customer goal
        # - expected behavior
        # - actual behavior
        # - customer impact
        ticket_analysis_agent,

        # Determine what technical investigation is required.
        investigation_agent,

        # ==========================================================
        # PHASE 2 — SAFETY / EVIDENCE
        # ==========================================================

        # Check for existing fixes, duplicate implementations,
        # related PRs, branches, or other engineering work.
        #
        # This is intentionally performed BEFORE code modification.
        duplicate_work_agent,

        # Consolidate and assess the technical evidence gathered
        # from the investigation.
        evidence_agent,

        # ==========================================================
        # PHASE 3 — REPOSITORY / ROOT CAUSE
        # ==========================================================

        # Identify the relevant repository, modules, files,
        # classes, methods, and source-code behavior.
        repository_agent,

        # Determine the most strongly supported root cause.
        # Hypotheses must remain hypotheses unless evidence supports them.
        root_cause_agent,

        # ==========================================================
        # PHASE 4 — REMEDIATION DESIGN
        # ==========================================================

        # Determine the appropriate technical remediation without
        # immediately modifying source code.
        remediation_agent,

        # Review the proposed remediation for correctness, safety,
        # scope, architecture, and consistency with the evidence.
        review_agent,

        # ==========================================================
        # PHASE 5 — CODE CHANGE
        # ==========================================================

        # Produce the concrete source-code change based on the
        # reviewed remediation.
        code_change_agent,

        # Apply/implement the approved code change.
        implementation_agent,

        # ==========================================================
        # PHASE 6 — VALIDATION / TESTING
        # ==========================================================

        # Validate that the implementation is technically consistent
        # with the identified problem and remediation.
        validation_agent,

        # Execute/evaluate the applicable tests and record their
        # actual results.
        test_result_agent,

        # ==========================================================
        # PHASE 7 — PUBLISHING
        # ==========================================================

        # Prepare the implementation for publication.
        #
        # This stage should NOT itself imply that GitHub publication
        # or PR creation has happened.
        publish_agent,

        # Publish the approved changes through GitHub.
        #
        # This replaces the old PR agent. Any branch / commit / PR
        # creation performed through GitHub belongs to this stage.
        github_publish_agent,

        # ==========================================================
        # PHASE 8 — DETERMINE ACTUAL RESOLUTION
        # ==========================================================

        # Determine whether the original customer issue is actually
        # resolved based on implementation + validation + test evidence.
        #
        # IMPORTANT:
        # A code change or GitHub PR alone must never imply RESOLVED.
        resolution_agent,

        # ==========================================================
        # PHASE 9 — CUSTOMER COMMUNICATION
        # ==========================================================

        # Generate the evidence-based customer-facing response.
        customer_response_agent,

        # ==========================================================
        # PHASE 10 — FINAL SAFETY / AUDIT
        # ==========================================================

        # Perform the final consistency and safety audit across the
        # complete workflow.
        audit_agent,

        # Determine whether human intervention is required.
        #
        # This happens after the audit so escalation can consider the
        # complete workflow state.
        escalation_agent,

        # ==========================================================
        # PHASE 11 — FINAL SYNTHESIS
        # ==========================================================

        # Produce the final structured workflow summary.
        workflow_summary_agent,

        # ==========================================================
        # PHASE 12 — FINAL CONTROL PLANE
        # ==========================================================

        # Produce the final orchestration/control decision describing
        # whether the workflow completed, is blocked, requires review,
        # or requires additional information.
        workflow_control_agent,
    ],
)