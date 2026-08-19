"""Notifications package: Slack and email autonomous outreach."""

from .slack import (
    notify,
    notify_case_ingested,
    notify_workflow_blocked,
    notify_case_resolved,
    notify_critical_escalation,
)
from .email import send_resolution_email, send_escalation_email

__all__ = [
    "notify",
    "notify_case_ingested",
    "notify_workflow_blocked",
    "notify_case_resolved",
    "notify_critical_escalation",
    "send_resolution_email",
    "send_escalation_email",
]
