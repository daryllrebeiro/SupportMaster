# SupportMaster

SupportMaster is an autonomous customer-support bug investigation and resolution agent.

It takes a support bug, gathers evidence, searches historical issues and code repositories, determines the likely root cause, proposes or implements a fix, runs tests, generates an RCA, and prepares the issue and pull request for human review.

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

To open the local model picker:

```powershell
.\.venv\Scripts\python.exe -m supportmaster.web
```

Then browse to `http://127.0.0.1:8000`.

The application entrypoint now uses the conditionally routed ADK `Workflow`.
Duplicate work, review, validation/testing, and final audit decisions are
enforced by graph gates; the legacy always-on sequential workflow is no longer
used by the runner or local UI.
