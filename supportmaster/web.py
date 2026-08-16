"""Small local UI for choosing the model for a SupportMaster workflow run."""

from __future__ import annotations

import argparse
import asyncio
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai import types

from .agent import create_root_agent
from .config import DEFAULT_MODEL, supported_models
from .persistence import SQLiteRunStore
from .runtime import DurableTaskWorker
from .telemetry import MetricsRegistry, SQLiteTelemetrySink, TelemetryRecorder
from .operations import HealthReporter, RunAdmissionController, load_operation_settings
from .security import Authenticator, Principal, load_security_settings
from .intake import normalize_case
from .organization import OrganizationContextService
from .models.organization import OrganizationProfile
from .investigation import InvestigationService
from .planning import PlanningService
from .models.planning import PlanningAssessment
from .workflow_state import SupportMasterState
from .workspace import CaseWorkspaceService


MOCK_JIRA_ISSUE = """Jira key: FIN-1847
Summary: CSV invoice export fails with OutOfMemoryError for enterprise tenants

Customer: Northstar Retail Group (Enterprise)
Reporter: Priya Shah, Finance Operations Lead
Priority: P1 — Finance teams cannot complete month-end reconciliation
Environment: Production, EU region, application version 4.18.2
First observed: 2026-08-14 09:17 UTC

Customer impact:
- 38 finance users are blocked from downloading invoice exports.
- The month-end close is due on 2026-08-18.
- Smaller exports below approximately 50,000 invoices complete successfully.

Expected behavior:
An authorized user can export the requested invoice range as a CSV file. Large
exports should either complete within the documented asynchronous export flow
or fail gracefully with a clear, recoverable message.

Actual behavior:
Exports covering approximately 1.2–1.5 million invoices remain on “Preparing
export” for 6–9 minutes, then the user sees “Export failed. Please try again.”
No file is delivered.

Customer-provided reproduction steps:
1. Sign in as a Finance Administrator.
2. Open Billing > Invoices > Export CSV.
3. Select date range 2025-01-01 through 2025-12-31; leave all regions selected.
4. Click Export.
5. Observe the failure after several minutes.

Customer-provided technical evidence (not independently verified):
2026-08-14T09:25:41Z ERROR export-worker java.lang.OutOfMemoryError: Java heap space
  at com.northstar.billing.export.InvoiceCsvSerializer.writeRows(InvoiceCsvSerializer.java:184)
  at com.northstar.billing.export.InvoiceExportJob.run(InvoiceExportJob.java:92)
Job ID: exp_7f31a2; tenant ID: tenant_redacted; request ID: req_94a7c1

Recent changes reported by the customer:
- Their invoice volume increased after an acquisition on 2026-08-01.
- No application upgrade, permission change, or browser change was made by the customer.

Attachments referenced but not supplied to SupportMaster:
- Full export-worker logs for job exp_7f31a2
- Screenshot of the customer-facing failure message
- Heap metrics dashboard for the export worker

Requested outcome:
Identify whether this is a known issue or existing work, determine the safest
next action, and provide a customer-safe status update. Do not claim a fix,
deployment, validation, GitHub publication, or customer confirmation without
direct evidence."""


OPERATION_SETTINGS = load_operation_settings()
RUN_ADMISSION = RunAdmissionController(OPERATION_SETTINGS.max_active_runs)
SECURITY_SETTINGS = load_security_settings()
AUTHENTICATOR = Authenticator(SECURITY_SETTINGS)


def _configured_health_reporter() -> HealthReporter:
    return HealthReporter(
        run_db=os.getenv("SUPPORTMASTER_RUN_DB", ".supportmaster/runs.db"),
        session_db=os.getenv("SUPPORTMASTER_SESSION_DB", ".supportmaster/adk_sessions.db"),
    )


def _model_label(model_name: str) -> str:
    return model_name.replace("gemini-", "Gemini ").replace("-", " ").title()


def render_page(
    selected_model: str,
    issue: str = MOCK_JIRA_ISSUE,
    status: str | None = None,
    result: str | None = None,
) -> str:
    """Render the model picker without placing secrets in the browser."""
    options = "\n".join(
        (
            f'<option value="{escape(model)}"'
            f'{" selected" if model == selected_model else ""}>'
            f"{escape(_model_label(model))}"
            "</option>"
        )
        for model in supported_models()
    )
    status_html = (
        f'<p class="status" role="status">{escape(status)}</p>' if status else ""
    )
    result_html = (
        f'<section class="results"><h2>Workflow events</h2><pre>{escape(result)}</pre></section>'
        if result
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SupportMaster</title>
    <style>
      :root {{ color-scheme: dark; font-family: Inter, system-ui, sans-serif; }}
      body {{ margin: 0; min-height: 100vh; display: grid; place-items: center;
        background: radial-gradient(circle at top left, #1e3a5f, #0a1020 55%); color: #edf3ff; }}
      main {{ width: min(540px, calc(100% - 40px)); padding: 38px; border: 1px solid #31476a;
        border-radius: 22px; background: rgba(13, 24, 45, .92); box-shadow: 0 24px 64px #020714aa; }}
      h1 {{ margin: 0; font-size: 2rem; }}
      .eyebrow {{ color: #8fc5ff; font-size: .8rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }}
      .intro {{ color: #b9c9e2; line-height: 1.55; }}
      label {{ display: block; margin: 28px 0 8px; font-weight: 650; }}
      select, button {{ width: 100%; box-sizing: border-box; border-radius: 10px; font: inherit; }}
      select {{ padding: 13px; background: #111f38; border: 1px solid #46638d; color: inherit; }}
      textarea {{ width: 100%; min-height: 360px; box-sizing: border-box; resize: vertical; padding: 13px;
        border-radius: 10px; background: #111f38; border: 1px solid #46638d; color: inherit; font: .85rem/1.45 ui-monospace, monospace; }}
      button {{ margin-top: 22px; padding: 13px; border: 0; background: #48a5ff; color: #071426; font-weight: 750; cursor: pointer; }}
      button:hover {{ background: #79beff; }}
      .status {{ margin: 22px 0 0; padding: 13px; border-radius: 10px; background: #153d36; color: #b7f5db; }}
      .results {{ margin-top: 26px; }}
      h2 {{ font-size: 1.1rem; }}
      pre {{ max-height: 680px; overflow: auto; white-space: pre-wrap; padding: 15px; border-radius: 10px; background: #071120; border: 1px solid #2b4265; color: #d5e5fb; }}
      .note {{ color: #91a6c4; font-size: .86rem; line-height: 1.45; }}
    </style>
  </head>
  <body>
    <main>
      <p class="eyebrow">Controlled autonomous support engineering</p>
      <h1>SupportMaster</h1>
      <p class="intro">Choose the Gemini model for this workflow execution.</p>
      <form action="/" method="post">
        <label for="model">Gemini model</label>
        <select id="model" name="model">{options}</select>
        <label for="issue">Support issue</label>
        <textarea id="issue" name="issue" required>{escape(issue)}</textarea>
        <button type="submit">Run SupportMaster</button>
      </form>
      {status_html}
      {result_html}
      <p class="note">The workflow uses the selected model for this run. SupportMaster must still distinguish plans, hypotheses, and evidence from verified engineering actions.</p>
    </main>
  </body>
</html>"""


def render_workspace() -> str:
    """Render a small operator workspace backed by the case APIs."""
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SupportMaster Case Workspace</title><style>body{font-family:system-ui;background:#0a1020;color:#edf3ff;margin:0;padding:32px}main{max-width:1000px;margin:auto}a{color:#8fc5ff}.case{border:1px solid #31476a;border-radius:12px;padding:16px;margin:12px 0;background:#0d182d}.muted{color:#a9bad5}</style></head><body><main><h1>SupportMaster Case Workspace</h1><p class="muted">Tenant-scoped cases, evidence, planning, resolution, and escalation.</p><div id="cases">Loading cases…</div><script>fetch('/api/cases').then(r=>r.json()).then(data=>{const root=document.getElementById('cases'); if(!data.cases.length){root.textContent='No cases yet.';return;} root.innerHTML=data.cases.map(c=>`<article class="case"><a href="/api/cases/${encodeURIComponent(c.case_id)}"><strong>${c.title}</strong></a><div class="muted">${c.status} · ${c.source_system} · ${c.case_id}</div><p>${c.description.slice(0,240)}</p></article>`).join('');}).catch(e=>document.getElementById('cases').textContent='Unable to load cases: '+e);</script></main></body></html>"""


class SupportMasterHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/workspace":
            auth = AUTHENTICATOR.authenticate(self.headers)
            if self._authorized(auth, "AUDIT_READ"):
                self._send_page(render_workspace())
            return
        if path == "/api/cases" or (path.startswith("/api/cases/") and path.count("/") == 3):
            auth = AUTHENTICATOR.authenticate(self.headers)
            if not self._authorized(auth, "AUDIT_READ"):
                return
            try:
                assert auth.principal is not None
                store = SQLiteRunStore(os.getenv("SUPPORTMASTER_RUN_DB", ".supportmaster/runs.db"))
                workspace = CaseWorkspaceService(store)
                if path == "/api/cases":
                    self._send_json({"cases": [item.model_dump(mode="json") for item in workspace.list(auth.principal.tenant_id)]}, status=200)
                else:
                    case_id = path.rsplit("/", 1)[-1]
                    self._send_json(workspace.snapshot(case_id, auth.principal.tenant_id).model_dump(mode="json"), status=200)
            except KeyError as error:
                self._send_json({"error": str(error)}, status=404)
            return
        if path in {"/health/live", "/health/ready"}:
            auth = AUTHENTICATOR.authenticate(self.headers)
            if path.endswith("/ready") and not self._authorized(auth, "HEALTH_READ"):
                return
            reporter = _configured_health_reporter()
            report = reporter.liveness() if path.endswith("/live") else reporter.readiness()
            self._send_json(
                report.model_dump(mode="json"),
                status=200 if report.status in {"LIVE", "READY"} else 503,
            )
            return
        query = parse_qs(urlparse(self.path).query)
        selected_model = query.get("model", [DEFAULT_MODEL])[0]
        page = render_page(selected_model)
        self._send_page(page)

    def do_POST(self) -> None:  # noqa: N802
        auth = AUTHENTICATOR.authenticate(self.headers)
        path = urlparse(self.path).path
        if not self._authorized(auth, "ORG_ADMIN" if path == "/api/organizations" else "RUN_EXECUTE"):
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length > OPERATION_SETTINGS.max_issue_bytes * 2:
            self._send_json({"error": "Request body exceeds the configured limit."}, status=413)
            return

        if path == "/api/organizations":
            try:
                assert auth.principal is not None
                payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("Organization payload must be a JSON object.")
                payload["organization_id"] = auth.principal.tenant_id
                profile = OrganizationProfile.model_validate(payload)
                store = SQLiteRunStore(os.getenv("SUPPORTMASTER_RUN_DB", ".supportmaster/runs.db"))
                saved = OrganizationContextService(store).save(profile)
                self._send_json(saved.model_dump(mode="json"), status=200)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._send_json({"error": str(error)}, status=400)
            return
        if path == "/api/cases":
            try:
                assert auth.principal is not None
                payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("Case intake payload must be a JSON object.")
                source_system = str(
                    self.headers.get("X-SupportMaster-Source")
                    or payload.pop("source_system", None)
                    or "API"
                )
                store = SQLiteRunStore(os.getenv("SUPPORTMASTER_RUN_DB", ".supportmaster/runs.db"))
                from .intake import CaseIntakeService

                result = CaseIntakeService(store).ingest(
                    payload,
                    source_system=source_system,
                    tenant_id=auth.principal.tenant_id,
                )
                self._send_json(result.model_dump(mode="json"), status=201 if result.status == "CREATED" else 200)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self._send_json({"error": str(error)}, status=400)
            return
        if path.startswith("/api/cases/") and path.endswith("/status"):
            try:
                assert auth.principal is not None
                payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                if not isinstance(payload, dict) or not payload.get("status"):
                    raise ValueError("A case status is required.")
                case_id = path.split("/")[3]
                store = SQLiteRunStore(os.getenv("SUPPORTMASTER_RUN_DB", ".supportmaster/runs.db"))
                case = CaseWorkspaceService(store).update_status(case_id, auth.principal.tenant_id, str(payload["status"]))
                self._send_json(case.model_dump(mode="json"), status=200)
            except (ValueError, TypeError, json.JSONDecodeError, KeyError) as error:
                self._send_json({"error": str(error)}, status=400)
            return
        form = parse_qs(self.rfile.read(content_length).decode("utf-8"))
        selected_model = form.get("model", [DEFAULT_MODEL])[0]
        issue = form.get("issue", [MOCK_JIRA_ISSUE])[0].strip()

        try:
            assert auth.principal is not None
            result = asyncio.run(
                run_workflow(
                    issue,
                    selected_model,
                    tenant_id=auth.principal.tenant_id,
                    initiated_by=auth.principal.subject,
                )
            )
            status = f"Completed SupportMaster workflow with {_model_label(selected_model)}."
        except Exception as error:
            result = None
            status = f"Workflow did not run ({type(error).__name__}): {error}"

        page = render_page(selected_model, issue, status, result)
        self._send_page(page)

    def _send_page(self, page: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def _send_json(self, payload: dict[str, object], *, status: int) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self, auth, scope: str) -> bool:
        if auth.status == "REJECTED" or auth.principal is None or not auth.principal.allows(scope):
            self._send_json({"error": auth.reason or f"Missing required scope: {scope}."}, status=401 if auth.status == "REJECTED" else 403)
            return False
        return True

    def log_message(self, format: str, *args: object) -> None:
        return


async def run_workflow(
    issue: str,
    model_name: str,
    *,
    tenant_id: str = "default",
    initiated_by: str = "anonymous",
) -> str:
    """Admit one bounded run and release its lease on every exit path."""
    admission_id = str(uuid4())
    with RUN_ADMISSION.lease(admission_id):
        return await _run_workflow(issue, model_name, run_id=admission_id, tenant_id=tenant_id, initiated_by=initiated_by)


async def _run_workflow(
    issue: str,
    model_name: str,
    *,
    run_id: str | None = None,
    tenant_id: str = "default",
    initiated_by: str = "anonymous",
) -> str:
    """Run one isolated, durable workflow and return generated agent messages."""
    if not issue:
        raise ValueError("A support issue is required.")
    if len(issue.encode("utf-8")) > OPERATION_SETTINGS.max_issue_bytes:
        raise ValueError("The support issue exceeds the configured size limit.")

    app_name = "supportmaster-local"
    user_id = f"tenant:{tenant_id}"
    session_db = Path(
        os.getenv("SUPPORTMASTER_SESSION_DB", ".supportmaster/adk_sessions.db")
    )
    run_db = Path(os.getenv("SUPPORTMASTER_RUN_DB", ".supportmaster/runs.db"))
    session_db.parent.mkdir(parents=True, exist_ok=True)
    session_service = SqliteSessionService(str(session_db))
    run_store = SQLiteRunStore(run_db)
    if run_store.active_queue_depth() >= OPERATION_SETTINGS.max_queue_depth:
        raise RuntimeError("SupportMaster task queue is at its configured capacity.")
    organization = OrganizationContextService(run_store).ensure(tenant_id)
    if organization.status != "ACTIVE":
        raise RuntimeError(f"Organization {tenant_id} is not active.")
    case = normalize_case(
        {"title": issue.splitlines()[0][:2_000] or "Support case", "description": issue},
        source_system="MANUAL",
        tenant_id=tenant_id,
    )
    run_store.save_case(case)
    investigation_summary = InvestigationService(run_store).summarize(case)
    run_store.save_investigation_summary(investigation_summary)
    root_cause, remediation = PlanningService().build(case, investigation_summary)
    planning_assessment = PlanningAssessment(
        case_id=case.case_id,
        tenant_id=tenant_id,
        root_cause=root_cause,
        remediation=remediation,
    )
    run_store.save_planning_assessment(planning_assessment)
    organization_context = (
        f"Organization: {organization.display_name}\n"
        f"Products: {', '.join(organization.products) or 'Not configured'}\n"
        f"Services: {', '.join(organization.services) or 'Not configured'}\n"
        f"Response style: {organization.response_style}\n"
        f"Terminology: {organization.terminology or 'Use the case source terminology.'}"
    )
    missing_context = "\n".join(
        f"- {item.evidence_type}: {item.reason}" for item in investigation_summary.missing_evidence
    ) or "- No deterministic evidence gaps detected yet."
    workflow_issue = organization_context + "\n\nInvestigation evidence gaps:\n" + missing_context + "\n\n" + case.workflow_text()
    workflow_issue += "\n\nPreliminary planning status: " + remediation.remediation_status
    run_id = run_id or str(uuid4())
    metrics = MetricsRegistry()
    telemetry = TelemetryRecorder(
        [SQLiteTelemetrySink(run_store)],
        metrics=metrics,
    )
    telemetry.emit(
        "SECURITY_RUN_AUTHORIZED",
        run_id=run_id,
        attributes={"tenant_id": tenant_id, "initiated_by": initiated_by, "case_id": case.case_id},
    )
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        state={
            "run_id": run_id,
            "case_id": case.case_id,
            "tenant_id": tenant_id,
            "organization_id": organization.organization_id,
            "organization_profile": organization.model_dump(mode="json"),
            "investigation_summary": investigation_summary.model_dump(mode="json"),
            "planning_assessment": planning_assessment.model_dump(mode="json"),
            "initiated_by": initiated_by,
        },
        session_id=run_id,
    )
    run_store.create_run(
        SupportMasterState(
            run_id=session.id,
            case_id=case.case_id,
            support_case=case,
            tenant_id=tenant_id,
            initiated_by=initiated_by,
            organization_id=organization.organization_id,
            organization_profile=organization,
            investigation_summary=investigation_summary,
            planning_assessment=planning_assessment,
        )
    )
    run_store.enqueue_task(
        session.id,
        task_name="adk_workflow",
        idempotency_key=f"{session.id}:adk_workflow",
        payload={"issue": workflow_issue, "case_id": case.case_id, "model_name": model_name, "session_id": session.id},
        max_attempts=3,
    )
    worker = DurableTaskWorker(
        run_store,
        worker_id=f"web-{session.id[:12]}",
        lease_seconds=60,
        telemetry=telemetry,
        metrics=metrics,
    )

    async def execute_task(task, cancellation):
        runner = Runner(
            app_name=app_name,
            agent=create_root_agent(model_name),
            session_service=session_service,
        )
        events: list[str] = []
        message = types.Content(role="user", parts=[types.Part(text=workflow_issue)])
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=message,
        ):
            if cancellation.is_set():
                break
            if not event.content or not event.content.parts:
                continue
            text = "\n".join(part.text for part in event.content.parts if part.text)
            if text:
                events.append(f"[{event.author}]\n{text}")
                run_store.append_event(
                    session.id,
                    "ADK_EVENT",
                    {"author": event.author, "text": text},
                )
                telemetry.emit(
                    "ADK_EVENT",
                    run_id=session.id,
                    task_id=task.task_id,
                    attributes={"author": event.author, "text": text},
                )
                worker.checkpoint(
                    task,
                    {"event_index": len(events), "author": event.author},
                )

        try:
            persisted_session = await session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session.id,
            )
            state = SupportMasterState.model_validate(persisted_session.state)
            run_store.save_state(state, event_type="ADK_RUN_SNAPSHOT")
        except Exception as error:
            run_store.append_event(
                session.id,
                "ADK_RUN_SNAPSHOT_FAILED",
                {"error": f"{type(error).__name__}: {error}"},
            )
            raise

        return {"text": "\n\n".join(events) or "The workflow returned no text events."}

    worker_result = await worker.run_once_async(execute_task)
    if worker_result is None:
        raise RuntimeError("The durable workflow task could not be claimed.")
    if worker_result.outcome != "SUCCEEDED":
        raise RuntimeError(
            f"Durable workflow task ended with {worker_result.outcome}: "
            f"{worker_result.error or 'no additional error details'}"
        )
    run_store.mark_run_completed(session.id)
    return worker_result.result.get("text", "The workflow returned no text events.")


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), SupportMasterHandler)
    print(f"SupportMaster model picker running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SupportMaster model-picker UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    run_server(args.host, args.port)
