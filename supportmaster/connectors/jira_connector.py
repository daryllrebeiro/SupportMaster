"""Plug-and-play connector for Jira Webhooks."""

from __future__ import annotations

import hmac
import hashlib
from collections.abc import Mapping
from typing import Any


class JiraConnector:
    @staticmethod
    def verify_signature(body: bytes, secret: str, signature: str) -> bool:
        """Verify HMAC-SHA256 webhook signature from Jira."""
        if not secret or not signature:
            return False
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def map_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
        """Convert a Jira webhook issue payload into standard SupportCase format."""
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        
        key = issue.get("key", "")
        summary = fields.get("summary", "")
        description = fields.get("description", "")
        
        return {
            "external_id": key,
            "title": f"Jira key: {key} | {summary}" if key else summary,
            "description": description or summary or "No description provided.",
            "priority": fields.get("priority", {}).get("name"),
            "reporter": fields.get("reporter", {}).get("emailAddress"),
            "metadata": {
                "jira_project": fields.get("project", {}).get("key"),
                "jira_status": fields.get("status", {}).get("name")
            }
        }
