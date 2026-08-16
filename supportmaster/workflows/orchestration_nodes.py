"""Shared deterministic nodes used to join read-only investigation forks."""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.workflow import node

from ..orchestration.contracts import BranchResult, ForkJoinResult
from ..workflow_state import GateDecision, append_gate_history


@node(name="investigation_evidence_fan_in")
def investigation_evidence_fan_in(ctx: Context, node_input: dict) -> dict:
    """Join independent evidence/repository branches before root-cause work."""
    state = ctx.state.to_dict()
    required = ("evidence_analysis", "repository_analysis")
    missing = [key for key in required if state.get(key) is None]
    branch_names = ("evidence_agent", "repository_agent")
    branch_results = [
        BranchResult(
            task_name=name,
            status="SUCCEEDED" if state.get(key) is not None else "FAILED",
            output={"state_key": key},
            error=(f"{key} was not produced." if state.get(key) is None else None),
        )
        for name, key in zip(branch_names, required)
    ]
    status = "BLOCKED" if missing else "COMPLETED"
    result = ForkJoinResult(
        group_name="read_only_investigation",
        status=status,
        branches=branch_results,
        missing_required=missing,
        warnings=(
            ["Required read-only investigation output is missing."]
            if missing
            else []
        ),
    )
    results = state.get("fork_join_results") or []
    results.append(result.model_dump())
    ctx.state["fork_join_results"] = results

    decision = GateDecision(
        gate="ORCHESTRATION",
        route="SAFETY_STOP" if missing else "CONTINUE",
        reason=(
            "Read-only investigation branches completed and produced the required outputs."
            if not missing
            else "Read-only investigation join is incomplete; root-cause analysis cannot proceed."
        ),
        blocking_reasons=[f"Missing required branch output: {key}." for key in missing],
        required_actions=(
            ["Retry or inspect the incomplete read-only investigation branch."]
            if missing
            else []
        ),
        evidence_keys=list(required),
    )
    ctx.state["last_gate_decision"] = decision.model_dump()
    append_gate_history(ctx.state, decision)
    ctx.route = decision.route
    return {
        "join": result.model_dump(),
        "gate": decision.model_dump(),
        "branches": list(branch_names),
    }
