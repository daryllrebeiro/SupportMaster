# SupportMaster state contract

Every structured agent result is written through its `output_key` and consumed
from the matching field in `SupportMasterState`.

| Agent | `output_key` | State field |
| --- | --- | --- |
| Ticket | `ticket_analysis` | `ticket_analysis` |
| Investigation | `investigation_plan` | `investigation_plan` |
| Duplicate work | `duplicate_work_analysis` | `duplicate_work_analysis` |
| Evidence | `evidence_analysis` | `evidence_analysis` |
| Repository | `repository_analysis` | `repository_analysis` |
| Root cause | `root_cause_analysis` | `root_cause_analysis` |
| Remediation | `remediation_plan` | `remediation_plan` |
| Review | `review_analysis` | `review_analysis` |
| Code change | `code_change_result` | `code_change_result` |
| Implementation | `implementation_result` | `implementation_result` |
| Validation | `validation_analysis` | `validation_analysis` |
| Test result | `test_result` | `test_result` |
| Publish | `publish_plan` | `publish_plan` |
| GitHub publish | `github_publish_result` | `github_publish_result` |
| Resolution | `resolution_analysis` | `resolution_analysis` |
| Customer response | `customer_response` | `customer_response` |
| Audit | `workflow_audit` | `workflow_audit` |
| Escalation | `escalation_analysis` | `escalation_analysis` |
| Workflow summary | `workflow_summary` | `workflow_summary` |
| Workflow control | `workflow_control` | `workflow_control` |
| Autonomous safety stop | `autonomous_stop` | `autonomous_stop` |

Gate-only fields are `last_gate_decision` and `terminal_status`; they are not
agent output keys. A blocked autonomous run records `terminal_status=SAFETY_STOP`
and the deterministic `autonomous_stop` payload instead of waiting for a human.

The control-plane foundation also includes lifecycle and traceability fields:

- `run_id`, `ticket_id`, `current_stage`, and `policy_version`
- `evidence_bundle` and `evidence_records` for sanitized, hash-addressed source artifacts
- `terminal_outcome` for completed, blocked, paused, safety-stop, and execution-failure outcomes
- `gate_history` for append-only deterministic gate records
- `policy_decisions` for action-level ALLOW/DENY/PAUSE/REQUEST_INFORMATION results
- `authorizations` for scoped implementation, publish, or human-approved grants
- `operation_receipts` for evidence returned by future Git/GitHub/CI executors
- `pending_human_review` and `human_review_history` for durable, scoped pause/resume
- `fork_join_results` for bounded read-only branch outcomes, conflicts, and missing outputs

Durable execution metadata is stored alongside the run snapshot: queued tasks
have unique idempotency keys, attempt counts, leases, retry state, and result
receipts; task checkpoints are append-only; and run controls represent
`RUNNABLE`, `RUNNING`, `PAUSED`, `CANCEL_REQUESTED`, `CANCELLED`, `COMPLETED`,
or `FAILED`. Replay plans are explicitly dry-run and can never authorize a
mutation.

Integration reads and writes use `IntegrationGateway` policy checks. Every
adapter returns an `ExternalOperationReceipt`; structured results can be stored
under `integration_results` with `record_integration_result()`. A `DRY_RUN`
policy blocks mutations and records what would have happened. `LIVE` mode still
requires an explicit permission (`WRITE_ISSUES`, `WRITE_REPOSITORY`,
`TRIGGER_CI`, or `SEND_NOTIFICATIONS`) and an optional target allow-list.

Observability is persisted separately from the state snapshot in the
`telemetry_events` table. `TelemetryEvent` carries `run_id`, a stable
`correlation_id`, task/operation/gate identifiers, redacted attributes, and a
severity level. `DurableTaskWorker` and `IntegrationGateway` emit lifecycle
events and metrics without allowing telemetry failures to change task control
outcomes. `AuditExporter` merges run events, telemetry, receipts, and gate
history into a redacted, hash-chained `AuditTimeline` that operators can export
to JSON and verify offline.

Operational limits are kept outside the workflow state and validated at
startup. Admission leases bound concurrent model runs, issue payload limits
bound memory and request size, and circuit breakers provide fail-closed
dependency protection. These controls do not grant workflow authorization and
cannot bypass deterministic safety gates.

Security context is part of the durable run contract: `tenant_id` identifies
the owning tenant and `initiated_by` identifies the authenticated operator (or
the explicit local anonymous principal). These values are supplied by the
operator boundary rather than the model and are carried into ADK session state,
run snapshots, and `SECURITY_RUN_AUTHORIZED` telemetry. API keys are hashed at
configuration load; plaintext secrets are never stored in state or telemetry.

Functional case intake is represented by `SupportCase` and persisted in the
`support_cases` table. A case includes source-neutral customer impact,
reproduction, environment, product/service, attachment, and metadata fields.
`CaseIntakeService` normalizes common aliases from manual forms, webhooks, and
ticket systems; repeated `(tenant_id, source_system, external_id)` submissions
return the original case instead of creating duplicate work.

Organization configuration is represented by `OrganizationProfile` and
`WorkflowPolicy` in the `organizations` table. The profile is linked to each
run through `organization_id` and `organization_profile`. Organization policy
can require evidence sources, duplicate checks, implementation/publication or
production approval, and define allowed external actions; these values guide
functional routing but never weaken deterministic safety gates.

Investigation artifacts are represented by `InvestigationSummary` and stored
in `investigation_summaries`. The summary links ingested evidence records,
related-case matches, incident correlations, repository signals, and explicit
evidence gaps. `READY`, `PARTIAL`, and `BLOCKED` statuses describe evidence
readiness only; they do not authorize implementation or publication.

`PlanningAssessment` persists the deterministic root-cause and remediation
pair for a case. Root-cause evidence references and verification gaps remain
visible in the plan. A remediation may be `READY` as an engineering proposal,
but `implementation_allowed` remains false until the existing authorization
and implementation gates independently grant scope.

`ResolutionBundle` persists `ResolutionAnalysis`, `CustomerResponse`, and
`EscalationAnalysis` together for a case. Resolution status cannot become
`RESOLVED` without verified implementation and validation, required
publication/deployment evidence, and any configured customer confirmation.
Customer communication remains `safe_to_send=false` when blocking evidence is
missing, and escalation records the required human actions.

`CaseWorkspaceSnapshot` is the operator read model combining the canonical
case, organization profile, investigation summary, planning assessment,
resolution bundle, and linked durable runs. Workspace reads and status updates
are tenant-scoped; a case from another tenant is rejected rather than exposed.

`EngineeringExecutionResult` is the durable execution contract for approved
implementation work. It records preflight, change, validation, and optional
rollback receipts, changed paths, validation status, and errors. The executor
requires an active `IMPLEMENTATION` grant at every mutating boundary and
rejects absolute or parent-directory paths before invoking an adapter.

An `INSUFFICIENT_EVIDENCE` duplicate result can remain on the read-only
investigation path, but it cannot authorize implementation or publication.

Verified execution adapters write `ExternalOperationReceipt` records for Git
preflight, commit, push, pull-request creation, pull-request verification, and
test execution. A publication executor rejects missing, expired, mismatched,
or inactive `PUBLISH` grants before invoking an adapter and re-checks the grant
before each mutating operation.

Evidence ingestion hashes the original bytes but stores only redacted content.
Each record retains its source URI, capture time, classification, confidence,
size, and redaction flags. `EvidenceIngestor.attach_to_state()` writes the
bundle, records, and generated `EvidenceAnalysis` as plain dictionaries so the
same provenance contract works in ADK state and durable run snapshots.
