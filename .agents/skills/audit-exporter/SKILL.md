---
name: audit-exporter
description: >-
  Use this skill to extract and redact tenant telemetry audit logs from the SQLite database.
---

# SupportMaster Audit Exporter Skill

This skill explains how to extract audit trial logs, redact sensitive information, and save them in standard JSON formats for external reporting.

## Procedures

1. **Run the Exporter**:
   Execute the automated script using the target database path:
   `python .agents/skills/audit-exporter/scripts/export.py --db .supportmaster/runs.db --tenant demo-acme --output audit_log.json`

2. **Verify Redaction**:
   * Inspect the output file to confirm that authorization keys and personal developer tokens are successfully redacted or hashed.
   * Verify that the database connection lock is released upon program exit.
