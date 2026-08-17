# SupportMaster demo runbook

## Prepare

Create `.venv`, install `requirements.txt`, and copy `.env.example` to `.env`.
The deterministic demo does not need `GOOGLE_API_KEY`.

## Preflight

Run `.\scripts\demo.ps1 check`. This executes the offline quality pack and
local release checks. It exits non-zero if a safety or regression check fails.

## Golden path

Run `.\scripts\demo.ps1 run`. Explain the output in this order:

1. The vendor-neutral case is normalized.
2. Investigation preserves tenant context and identifies evidence gaps.
3. The resolution gate refuses to claim an unverified fix.
4. Every stage is represented by an auditable check.

## Workspace

Run `.\scripts\demo.ps1 serve` and open
http://127.0.0.1:8001/workspace. The workspace shows the case timeline, gate
statuses, and next action.

## Container path

Run `docker compose up --build` and open the same workspace URL. The container
uses optional authentication for local demonstration; production deployments
should provide required API-key authentication.

## Close

End with the safety message: SupportMaster can investigate and prepare work
autonomously, but implementation, publication, deployment, and closure remain
evidence- and authorization-gated.
