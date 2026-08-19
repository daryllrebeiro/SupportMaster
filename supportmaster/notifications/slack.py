"""Autonomous Slack webhook notifications for key workflow lifecycle events."""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Literal

NotificationLevel = Literal["info", "warning", "success", "critical"]

_LEVEL_EMOJIS: dict[NotificationLevel, str] = {
    "info": "ℹ️",
    "warning": "⚠️",
    "success": "✅",
    "critical": "🚨",
}
_LEVEL_COLORS: dict[NotificationLevel, str] = {
    "info": "#3b82f6",
    "warning": "#f59e0b",
    "success": "#10b981",
    "critical": "#ef4444",
}


def notify(
    title: str,
    message: str,
    level: NotificationLevel = "info",
    fields: dict[str, str] | None = None,
) -> bool:
    """
    Send a structured Slack notification.

    Uses the SUPPORTMASTER_SLACK_WEBHOOK environment variable.
    If dry-run mode (SUPPORTMASTER_NOTIFICATIONS_DRY_RUN=true), only logs.
    Returns True on success, False on failure or dry-run.
    """
    webhook_url = os.getenv("SUPPORTMASTER_SLACK_WEBHOOK")
    dry_run = os.getenv("SUPPORTMASTER_NOTIFICATIONS_DRY_RUN", "true").lower() == "true"

    emoji = _LEVEL_EMOJIS.get(level, "ℹ️")
    color = _LEVEL_COLORS.get(level, "#3b82f6")

    attachment = {
        "color": color,
        "fallback": f"{emoji} {title}: {message}",
        "title": f"{emoji} {title}",
        "text": message,
        "fields": [
            {"title": k, "value": v, "short": True}
            for k, v in (fields or {}).items()
        ],
        "footer": "SupportMaster Autonomous Notifier",
    }
    payload = {"attachments": [attachment]}

    if dry_run or not webhook_url:
        import logging
        logging.getLogger("supportmaster.notifications.slack").info(
            "[DRY-RUN] Slack notification: %s — %s", title, message
        )
        return False

    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


def notify_case_ingested(case_id: str, title: str, tenant_id: str) -> bool:
    return notify(
        title="New Case Ingested",
        message=f"A new support case has been received and queued for autonomous investigation.",
        level="info",
        fields={"Case ID": case_id, "Title": title[:80], "Tenant": tenant_id},
    )


def notify_workflow_blocked(case_id: str, gate_name: str, reason: str) -> bool:
    return notify(
        title="Workflow Blocked at Safety Gate",
        message=reason,
        level="warning",
        fields={"Case ID": case_id, "Gate": gate_name},
    )


def notify_case_resolved(case_id: str, title: str, tenant_id: str) -> bool:
    return notify(
        title="Case Autonomously Resolved",
        message=f"SupportMaster has completed the resolution pipeline for this case.",
        level="success",
        fields={"Case ID": case_id, "Title": title[:80], "Tenant": tenant_id},
    )


def notify_critical_escalation(case_id: str, reason: str) -> bool:
    return notify(
        title="🚨 Critical Escalation Required",
        message=reason,
        level="critical",
        fields={"Case ID": case_id},
    )
