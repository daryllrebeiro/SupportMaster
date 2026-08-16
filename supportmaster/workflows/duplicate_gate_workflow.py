"""First conditional ADK Workflow branch for duplicate-work safety."""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.agents.context import Context
from google.adk.workflow import START, Workflow, node

from ..agents.duplicate_work_agent import duplicate_work_agent
from ..agents.escalation_agent import escalation_agent
from ..agents.evidence_agent import evidence_agent
from ..agents.investigation_agent import investigation_agent
from ..agents.ticket_agent import ticket_analysis_agent
from ..config import select_model
from ..control_gates import evaluate_duplicate_gate


def _clone_agent(agent: Agent, model_name: str) -> Agent:
    """Clone an existing agent without sharing its old workflow parent."""
    cloned = agent.clone(update={"model": model_name})
    cloned.parent_agent = None
    return cloned


@node(name="duplicate_work_gate")
def duplicate_work_gate(ctx: Context) -> dict:
    """Route only a verified clean duplicate check to evidence analysis."""
    decision = evaluate_duplicate_gate(ctx.state.to_dict())
    ctx.state["last_gate_decision"] = decision.model_dump()
    ctx.route = decision.route
    return decision.model_dump()


def create_duplicate_gate_workflow(
    model_name: str | None = None,
) -> Workflow:
    """Create an isolated ticket → duplicate-check → safety-gate graph.

    The continue branch ends at evidence analysis for this phase. The blocked
    branch ends at escalation. Later phases will extend these terminal nodes.
    """
    selected_model = select_model(model_name)
    ticket = _clone_agent(ticket_analysis_agent, selected_model)
    investigation = _clone_agent(investigation_agent, selected_model)
    duplicate = _clone_agent(duplicate_work_agent, selected_model)
    evidence = _clone_agent(evidence_agent, selected_model)
    escalation = _clone_agent(escalation_agent, selected_model)

    return Workflow(
        name="supportmaster_duplicate_gate",
        description=(
            "SupportMaster's first conditional safety branch: verify duplicate "
            "work before allowing evidence analysis to continue."
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
                    "HUMAN_REVIEW_REQUIRED": escalation,
                },
            ),
        ],
    )
