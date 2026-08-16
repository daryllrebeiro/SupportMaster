"""Deterministic terminal nodes for autonomous workflow outcomes."""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.workflow import node

from ..workflow_state import AutonomousStop


@node(name="autonomous_safety_stop")
def autonomous_safety_stop(ctx: Context) -> dict:
    """Record a fail-closed stop without asking a human to resume the run."""
    decision = ctx.state.get("last_gate_decision") or {}
    stop = AutonomousStop(
        gate=decision.get("gate", "DUPLICATE_WORK"),
        reason=decision.get(
            "reason", "A mandatory safety gate did not pass."
        ),
        blocking_reasons=decision.get("blocking_reasons", []),
        required_actions=decision.get("required_actions", []),
        evidence_keys=decision.get("evidence_keys", []),
    )
    ctx.state["autonomous_stop"] = stop.model_dump()
    ctx.state["terminal_status"] = "SAFETY_STOP"
    ctx.route = "SAFETY_STOP"
    return stop.model_dump()
