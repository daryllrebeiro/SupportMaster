"""SupportMaster's application entrypoint and runtime workflow factory."""

from __future__ import annotations

from google.adk.workflow import Workflow

from .config import select_model
from .workflows.publishing_gate_workflow import create_publishing_gate_workflow


def create_root_agent(model_name: str | None = None) -> Workflow:
    """Create an isolated, conditionally gated workflow for one run."""
    return create_publishing_gate_workflow(select_model(model_name))


# ADK's default application entrypoint. Runtime callers should use
# create_root_agent() so every run gets an isolated workflow/model selection.
root_agent = create_root_agent()
