---
name: supportmaster-testing
description: >-
  Use this skill when you need to run, configure, or debug tests in SupportMaster.
  This includes setting up database mocks, unit testing, and integration verification.
---

# SupportMaster Testing Skill

This skill provides step-by-step instructions on running and debugging SupportMaster test suites.

## Prerequisites
* Active Python Virtual Environment (`.venv`)
* Installed developer dependencies (`pip install -r requirements.txt`)

---

## Test Execution Runbook

1. **Run Integration Tests**:
   Run the automated test runner script to verify HTTP controllers, tenant security checks, and gate resumption logic:
   [test.ps1](./scripts/test.ps1)

   Or run manually from the workspace root:
   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```

2. **Diagnose Failures**:
   If specific tests fail (e.g. `test_web_reviews.py` fails due to locked files):
   * Verify that no stray python worker threads are running.
   * Clear the `.supportmaster/` runtime directory to reset databases.
