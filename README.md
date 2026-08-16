# SupportMaster

SupportMaster is an autonomous customer-support bug investigation and resolution agent.

It takes a support bug, gathers evidence, searches historical issues and code repositories, determines the likely root cause, proposes or implements a fix, runs tests, generates an RCA, and publishes only when the deterministic safety gates permit it. Explicit duplicates and malformed or unknown gate data stop the run. An incomplete duplicate search may continue read-only investigation, but it cannot authorize autonomous implementation or publication.

## Hackathon Track

Taskmaster

## Status

Early development.

## Model selection

SupportMaster uses `SUPPORTMASTER_MODEL` as its default Gemini model. The
runtime model picker should use `supportmaster.config.supported_models()` and
create each execution through `supportmaster.agent.create_root_agent(model)`.
That factory creates an isolated agent tree, so a selected model affects only
the workflow run that chose it.

Copy `.env.example` to `.env`, add `GOOGLE_API_KEY`, and optionally tailor the
picker allow-list with `SUPPORTMASTER_MODELS`.

Local runs persist ADK sessions and control-plane snapshots under
`.supportmaster/` by default. Override them with `SUPPORTMASTER_SESSION_DB`
and `SUPPORTMASTER_RUN_DB` when using a shared or managed SQLite location.

To open the local model picker:

```powershell
.\.venv\Scripts\python.exe -m supportmaster.web --port 8001
```

Then browse to `http://127.0.0.1:8001`. The official ADK developer UI remains
available at `http://127.0.0.1:8000`.

The application entrypoint now uses the conditionally routed ADK `Workflow`.
Duplicate work, review, validation/testing, and final audit decisions are
enforced by graph gates. The state contract also records policy version, gate
history, scoped authorization grants, and external-operation receipts. Git/GitHub
publication now goes through an injected verified executor; if adapters are not
configured, the run stops safely instead of allowing an LLM to claim publication.
Evidence ingestion now preserves sanitized source artifacts with SHA-256 hashes,
redaction metadata, and deterministic provenance. The reproducible `SUP-4821`
fixture set under `fixtures/sup-4821/` exercises the evidence-to-gate and
publication safety paths without network access.
Successful runs can reach completion autonomously;
blocked runs terminate through `autonomous_safety_stop` with no human-review
pause. The legacy always-on sequential workflow is no longer used by the
runner or local UI.

## Verification

Run the deterministic unit and routing tests with:

```powershell
python -m unittest discover -s tests -v
```

These tests do not call Gemini or require network access. Live ADK execution
still requires a valid API key and an account-enabled model.
