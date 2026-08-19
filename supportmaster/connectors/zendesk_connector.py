"""Plug-and-play connector for Zendesk Webhooks."""

from __future__ import annotations

import hmac
import hashlib
from collections.abc import Mapping
from typing import Any


class ZendeskConnector:
    @staticmethod
    def verify_signature(body: bytes, secret: str, signature: str) -> bool:
        """Verify Zendesk webhook signature using standard HMAC validation."""
        if not secret or not signature:
            return False
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def map_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
        """Convert a Zendesk ticket payload into standard SupportCase format."""
        ticket = payload.get("ticket", {})
        
        ticket_id = str(ticket.get("id", ""))
        subject = ticket.get("subject", "")
        description = ticket.get("description", "")
        
        return {
            "external_id": ticket_id,
            "title": f"Zendesk ticket #{ticket_id} | {subject}" if ticket_id else subject,
            "description": description or subject or "No description provided.",
            "priority": ticket.get("priority"),
            "reporter": ticket.get("requester", {}).get("email"),
            "metadata": {
                "zendesk_status": ticket.get("status"),
                "zendesk_tags": ticket.get("tags", [])
            }
        }
