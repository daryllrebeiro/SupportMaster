"""Autonomous email notifications for resolved cases and escalations."""

from __future__ import annotations

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("supportmaster.notifications.email")


def send_email(
    to: str,
    subject: str,
    body_html: str,
) -> bool:
    """
    Send an HTML email notification.

    Requires SUPPORTMASTER_SMTP_HOST, SUPPORTMASTER_SMTP_PORT,
    SUPPORTMASTER_SMTP_USER, SUPPORTMASTER_SMTP_PASSWORD, and
    SUPPORTMASTER_SMTP_FROM env vars. Falls back to dry-run logging.
    """
    dry_run = os.getenv("SUPPORTMASTER_NOTIFICATIONS_DRY_RUN", "true").lower() == "true"
    smtp_host = os.getenv("SUPPORTMASTER_SMTP_HOST")

    if dry_run or not smtp_host:
        logger.info("[DRY-RUN] Email to %s — Subject: %s", to, subject)
        return False

    try:
        from_addr = os.getenv("SUPPORTMASTER_SMTP_FROM", "noreply@supportmaster.ai")
        port = int(os.getenv("SUPPORTMASTER_SMTP_PORT", "587"))
        user = os.getenv("SUPPORTMASTER_SMTP_USER", "")
        password = os.getenv("SUPPORTMASTER_SMTP_PASSWORD", "")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(smtp_host, port, timeout=10) as server:
            server.starttls()
            if user:
                server.login(user, password)
            server.sendmail(from_addr, [to], msg.as_string())
        return True
    except Exception as e:
        logger.warning("Email delivery failed: %s", e)
        return False


def send_resolution_email(
    to: str,
    case_id: str,
    title: str,
    resolution_summary: str,
) -> bool:
    """Send a customer-facing resolution confirmation email."""
    subject = f"[SupportMaster] Your case has been resolved — {title}"
    body = f"""
    <html><body style="font-family:Inter,sans-serif;background:#030712;color:#f3f4f6;padding:32px;">
      <div style="max-width:600px;margin:0 auto;background:rgba(17,24,39,0.9);
                  border-radius:16px;padding:32px;border:1px solid rgba(55,65,81,0.5);">
        <h1 style="color:#3b82f6;font-family:Outfit,sans-serif;">✅ Case Resolved</h1>
        <p><strong>Case ID:</strong> {case_id}</p>
        <p><strong>Title:</strong> {title}</p>
        <hr style="border-color:rgba(55,65,81,0.5);">
        <h2 style="color:#9ca3af;font-size:1rem;">Resolution Summary</h2>
        <p style="line-height:1.6;">{resolution_summary}</p>
        <hr style="border-color:rgba(55,65,81,0.5);">
        <p style="color:#6b7280;font-size:0.8rem;">
          This message was sent autonomously by SupportMaster.
        </p>
      </div>
    </body></html>
    """
    return send_email(to, subject, body)


def send_escalation_email(
    to: str,
    case_id: str,
    reason: str,
) -> bool:
    """Send an escalation notification to the on-call operator."""
    subject = f"[SupportMaster] 🚨 Escalation Required — Case {case_id}"
    body = f"""
    <html><body style="font-family:Inter,sans-serif;background:#030712;color:#f3f4f6;padding:32px;">
      <div style="max-width:600px;margin:0 auto;background:rgba(17,24,39,0.9);
                  border-radius:16px;padding:32px;border:1px solid rgba(239,68,68,0.4);">
        <h1 style="color:#ef4444;font-family:Outfit,sans-serif;">🚨 Escalation Required</h1>
        <p><strong>Case ID:</strong> {case_id}</p>
        <p><strong>Reason:</strong> {reason}</p>
        <p style="color:#6b7280;font-size:0.8rem;">
          Please review this case immediately in the SupportMaster workspace.
        </p>
      </div>
    </body></html>
    """
    return send_email(to, subject, body)
