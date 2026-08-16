"""ADK Workflow branch that gates implementation on engineering review."""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.agents.context import Context
from google.adk.workflow import START, Workflow, node

from ..agents.code_change_agent import code_change_agent
from ..agents.duplicate_work_agent import duplicate_work_agent
from ..agents.evidence_agent import evidence_agent
from ..agents.implementation_agent import implementation_agent
from ..agents.investigation_agent import investigation_agent
from ..agents.remediation_agent import remediation_agent
from ..agents.repository_agent import repository_agent
from ..agents.review_agent import review_agent
from ..agents.root_cause_agent import root_cause_agent
from ..agents.ticket_agent import ticket_analysis_agent
from ..config import select_model
from ..control_gates import evaluate_duplicate_gate, evaluate_review_gate
from .terminal_nodes import autonomous_safety_stop


def _clone_agent(agent: Agent, model_name: str) -> Agent:
    cloned = agent.clone(update={"model": model_name})
    cloned.parent_agent = None
    return cloned


@node(name="duplicate_work_gate")
def duplicate_work_gate(ctx: Context) -> dict:
    decision = evaluate_duplicate_gate(ctx.state.to_dict())
    ctx.state["last_gate_decision"] = decision.model_dump()
    if "DUPLICATE_CHECK_INCOMPLETE" in decision.warnings:
        ctx.state["autonomous_best_effort"] = True
        ctx.state["uncertainty_flags"] = ["DUPLICATE_CHECK_INCOMPLETE"]
    ctx.route = decision.route
    return decision.model_dump()


@node(name="implementation_review_gate")
def implementation_review_gate(ctx: Context) -> dict:
    decision = evaluate_review_gate(ctx.state.to_dict())
    ctx.state["last_gate_decision"] = decision.model_dump()
    ctx.route = decision.route
    return decision.model_dump()


def create_implementation_gate_workflow(
    model_name: str | None = None,
) -> Workflow:
    """Create the investigation-to-implementation gated workflow branch."""
    selected_model = select_model(model_name)
    ticket = _clone_agent(ticket_analysis_agent, selected_model)
    investigation = _clone_agent(investigation_agent, selected_model)
    duplicate = _clone_agent(duplicate_work_agent, selected_model)
    evidence = _clone_agent(evidence_agent, selected_model)
    repository = _clone_agent(repository_agent, selected_model)
    root_cause = _clone_agent(root_cause_agent, selected_model)
    remediation = _clone_agent(remediation_agent, selected_model)
    review = _clone_agent(review_agent, selected_model)
    code_change = _clone_agent(code_change_agent, selected_model)
    implementation = _clone_agent(implementation_agent, selected_model)

    return Workflow(
        name="supportmaster_implementation_gate",
        description=(
            "SupportMaster investigation and remediation workflow with duplicate "
            "and implementation safety gates."
        ),
        edges=[
            (
                START,
                ticket,
                investigation,
                duplicate,
                duplicate_work_gate,
                {
                    "CONTINUE": evidence,
                    "SAFETY_STOP": autonomous_safety_stop,
                },
            ),
            (
                evidence,
                repository,
                root_cause,
                remediation,
                review,
                implementation_review_gate,
                {
                    "READY_FOR_IMPLEMENTATION": code_change,
                    "SAFETY_STOP": autonomous_safety_stop,
                },
            ),
            (code_change, implementation),
        ],
    )
