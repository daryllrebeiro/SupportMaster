"""Small local UI for choosing the model for a SupportMaster workflow run."""

from __future__ import annotations

import asyncio
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agent import create_root_agent
from .config import DEFAULT_MODEL, supported_models


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


class SupportMasterHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        query = parse_qs(urlparse(self.path).query)
        selected_model = query.get("model", [DEFAULT_MODEL])[0]
        page = render_page(selected_model)
        self._send_page(page)

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(content_length).decode("utf-8"))
        selected_model = form.get("model", [DEFAULT_MODEL])[0]
        issue = form.get("issue", [MOCK_JIRA_ISSUE])[0].strip()

        try:
            result = asyncio.run(run_workflow(issue, selected_model))
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

    def log_message(self, format: str, *args: object) -> None:
        return


async def run_workflow(issue: str, model_name: str) -> str:
    """Run one isolated workflow and return only the generated agent messages."""
    if not issue:
        raise ValueError("A support issue is required.")

    app_name = "supportmaster-local"
    user_id = "local-demo-user"
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=str(uuid4()),
    )
    runner = Runner(
        app_name=app_name,
        agent=create_root_agent(model_name),
        session_service=session_service,
    )
    events: list[str] = []
    message = types.Content(role="user", parts=[types.Part(text=issue)])

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=message,
    ):
        if not event.content or not event.content.parts:
            continue
        text = "\n".join(part.text for part in event.content.parts if part.text)
        if text:
            events.append(f"[{event.author}]\n{text}")

    return "\n\n".join(events) or "The workflow returned no text events."


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), SupportMasterHandler)
    print(f"SupportMaster model picker running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
