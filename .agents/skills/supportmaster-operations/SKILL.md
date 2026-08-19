---
name: supportmaster-operations
description: >-
  Use this skill to configure, start, and monitor the local SupportMaster HTTP server.
  This includes setting up mock environment variables, scoped credentials, liveness/readiness, and the auto-approve mode.
---

# SupportMaster Operations Skill

This skill provides the runbook and executable scripts to launch and manage the SupportMaster local development HTTP server.

## Configurable Options
Before starting the server, you can set the following environment variables:
* `SUPPORTMASTER_AUTH_MODE`: Set to `REQUIRED` or `OPTIONAL` to enforce scoped token checks.
* `SUPPORTMASTER_API_KEYS`: A semicolon-separated list of credentials in the format `secret|subject|tenant_id|scopes`.
* `SUPPORTMASTER_AUTO_APPROVE`: Set to `true` to enable fully autonomous execution without human-in-the-loop pauses.

---

## Server Startup Procedures

1. **Launch Server**:
   Execute the automated launcher script to spin up the local server with default credentials:
   [serve.ps1](./scripts/serve.ps1)

   Or run manually from the terminal:
   ```powershell
   $env:SUPPORTMASTER_AUTH_MODE="REQUIRED"
   $env:SUPPORTMASTER_API_KEYS="secret|operator|demo-acme|RUN_EXECUTE,AUDIT_READ;secret-bad|operator|demo-bad|RUN_EXECUTE"
   $env:SUPPORTMASTER_AUTO_APPROVE="false"
   .venv/Scripts/python.exe -m supportmaster.web --port 8001
   ```

2. **Verify Interfaces**:
   * Picker Frontend: Navigate to http://localhost:8001
   * Operator Workspace: Navigate to http://localhost:8001/workspace
   * Liveness Probe: http://localhost:8001/health/live
