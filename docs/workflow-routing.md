# SupportMaster workflow routing

The active application entrypoint is the graph created by
`create_publishing_gate_workflow`. `SequentialAgent` is not used by the
runner. A real publication run must inject a `PublicationExecutor` into
`create_root_agent`; the default local UI intentionally has no mutating
adapter and therefore stops at the verified executor.

```text
ticket → investigation → duplicate check → duplicate gate
                                             ├─ CONTINUE (verified) ─┬→ evidence ─────┐
                                             │                       └→ repository ───┤
                                             │                          deterministic join
                                             │                              → root cause → RCA check
                                             │              → remediation → review
                                             │              → review gate
                                             │                 ├─ READY_FOR_IMPLEMENTATION
                                             │                 │  → implementation authorization
                                             │                 │     ├─ READY_FOR_IMPLEMENTATION
                                             │                 │     │  → code change → implementation
                                             │                 │     └─ SAFETY_STOP → autonomous stop
                                             │                 │  → validation → tests
                                             │                 │  → validation gate
                                             │                 │     ├─ READY_FOR_PUBLISH
                                             │                 │     │  → publish → publish authorization
                                             │                 │     │     ├─ READY_FOR_PUBLISH → GitHub publish
                                             │                 │     │     └─ SAFETY_STOP → autonomous stop
                                             │                 │     │  → resolution → response → audit
                                             │                 │     │  → final audit gate
                                             │                 │     │     ├─ COMPLETED → summary → control
                                             │                 │     │     └─ SAFETY_STOP → autonomous stop
                                             │                 │     └─ SAFETY_STOP → autonomous stop
                                             │                 └─ SAFETY_STOP → autonomous stop
                                             └─ SAFETY_STOP → autonomous stop
```

Evidence entering the `evidence` stage is ingested through
`supportmaster.evidence.EvidenceIngestor`. Source bytes are hashed before
redaction, and the sanitized records plus `EvidenceAnalysis` are attached to
state. The checked-in `fixtures/sup-4821/` artifacts provide a reproducible
eight-source scenario for validating this boundary and its downstream gates.

Evidence and repository identification are the first true read-only fork. ADK
fans them out with a workflow concurrency limit of two, waits at
`investigation_evidence_join`, and routes through `investigation_evidence_fan_in`.
The fan-in records missing branch outputs as an `ORCHESTRATION` gate failure;
root-cause analysis never runs on a partial required join. The reusable
`supportmaster.orchestration.ForkJoinExecutor` applies the same contract to
non-ADK branch handlers, including dependency checks, timeouts, cancellation,
and conflicting-output detection.

Explicit duplicate matches, related work, missing status, and malformed or
unknown gate data remain fail-closed. A duplicate search that was attempted but
could not complete is different: `INSUFFICIENT_EVIDENCE` continues read-only
investigation and records `DUPLICATE_CHECK_INCOMPLETE` as an uncertainty, but
the implementation and publish authorization gates deny high-impact actions.

Blocked runs do not wait for a person or ask for an approval callback. They
terminate with a deterministic `autonomous_safety_stop` node that records the
gate, reason, blockers, required actions, and evidence keys in
`autonomous_stop`, with `terminal_status=SAFETY_STOP`. Implementation and
publication now also require scoped authorization grants issued by their
deterministic policy gates; LLM output alone cannot authorize either action.
The verified executor records Git/GitHub receipts and represents partial
publication explicitly.

The local runner claims an `adk_workflow` task through the durable worker.
Worker leases are renewed by heartbeats; event checkpoints are persisted as
they arrive; transient failures are retried with bounded backoff; and a lease
expiry makes the task reclaimable by another worker. Pause and cancellation
requests are cooperative and are checked before a task can be completed.

The same worker lifecycle is observable through structured, redacted telemetry
(`TASK_CLAIMED`, checkpoints, completion, retry, and failure) correlated to the
run and task IDs. Integration policy decisions emit matching success, blocked,
and failure events. Operators can build a complete run timeline from the
SQLite event store with `AuditExporter`; each entry is linked by a SHA-256
hash chain so exported evidence can be checked for tampering.

Production operation is bounded by `OperationSettings`, loaded from
`SUPPORTMASTER_MAX_ACTIVE_RUNS`, `SUPPORTMASTER_MAX_ISSUE_BYTES`,
`SUPPORTMASTER_MAX_QUEUE_DEPTH`, and circuit-breaker environment variables.
`RunAdmissionController` releases a lease on success or failure, so rejected
requests cannot consume capacity permanently. Integration gateways may use a
`CircuitBreaker` to stop hammering an unavailable dependency and automatically
probe recovery after a cooldown. The local server exposes `/health/live` for
process liveness and `/health/ready` for SQLite dependency readiness.

The operator surface supports `DISABLED`, `OPTIONAL`, and `REQUIRED`
authentication modes. In required mode, API keys use the format
`secret|subject|tenant|scope1,scope2` (separate multiple credentials with `;`)
in `SUPPORTMASTER_API_KEYS`; missing or
invalid credentials fail closed, and authenticated runs cannot change their
tenant or subject through ticket content. The model workflow receives only the
validated tenant context and never handles raw API keys.

Every run now has a canonical `SupportCase` boundary before agent execution.
The case is persisted, linked to `SupportMasterState.case_id`, and rendered
into a stable source-neutral workflow prompt. Domain-specific payload names are
handled by `supportmaster.intake.normalize_case`; the workflow itself consumes
the normalized contract.

Before a case run starts, `OrganizationContextService` resolves the tenant's
active profile. The workflow receives organization terminology and response
style alongside the case, while repository mappings, escalation rules, and
workflow policy remain available in durable state for later functional stages.
Suspended organizations fail closed before a model task is queued.

Investigation begins with a deterministic summary built by
`InvestigationService`. It performs tenant-scoped related-case matching,
incident/service correlation, injectable repository search, and missing-
evidence assessment. The summary is attached to `SupportMasterState` and its
evidence gaps are included in the model input, so the agent can investigate
without treating unavailable data as fact.

`PlanningService` converts the investigation summary into a conservative
`RootCauseAnalysis` and `RemediationPlan` before model-assisted stages run.
Critical evidence gaps route to `GATHER_MORE_EVIDENCE`; a proposed fix always
includes affected components, risks, validation, regression, and rollout
considerations. Planning is advisory and cannot bypass implementation,
publication, or production-approval gates.

Implementation execution is provided by `ControlledEngineeringExecutor`.
It consumes a ready remediation plan and an injected code-change adapter,
performs Git preflight, rechecks authorization, applies only repository-
relative approved paths, runs the supplied validation command, and attempts
rollback when validation fails. The result is advisory evidence for later
validation and publication gates, never proof of production resolution.

`ResolutionService` performs the final functional distinction between
implemented, validated, published, deployed, and customer-confirmed. It
generates a customer-safe response only when the corresponding evidence gates
pass; otherwise it requests verification or confirmation and emits an
escalation package. The service never closes or modifies an external ticket by
itself.

The functional workspace is available at `/workspace` and through the
tenant-scoped case APIs. It presents the same evidence, planning, resolution,
escalation, and run artifacts used by the workflow, while status changes remain
explicit operator actions and do not silently authorize implementation,
publication, or closure.

`FunctionalEvaluationSuite` runs the domain-neutral fixtures in
`fixtures/cases/` without Gemini or external connectors. Each scenario is
checked through intake, investigation, and resolution boundaries. A failed
scenario reports its individual checks and error, making new organization or
industry cases additive rather than tied to a single historical ticket.
Onboarding uses `OrganizationAcceptanceSuite` to persist an active profile,
verify that duplicate, approval, and production safeguards remain enabled, and
execute the generic fixtures with the organization ID as tenant context.

`EndToEndWorkflowSuite` runs each fixture through intake, investigation, and
resolution as one trace, recording each stage and asserting that an unverified
resolution cannot be sent or closed. This keeps onboarding and CI checks
deterministic while still covering the workflow boundary end to end.

The Phase 23 `ReadOnlyIntegrationBundle` composes issue, monitoring, and CI
adapters for evidence collection. It performs no writes and returns one
receipt for every attempted read, including blocked or failed operations.

External systems are never called directly by an LLM. Issue tracking, CI,
monitoring, notifications, and GitHub are reached through injected adapters
and `IntegrationGateway`. Reads and mutations are separately permissioned,
payloads are size-limited, HTTPS transport is enforced for production URLs,
and dry-run mode is the default.

Human-required work is persisted as a review task with an expiring hashed
resume token. Approval scopes are explicit (`IMPLEMENTATION`, `PUBLISH`,
`PRODUCTION`, or `CLOSE_TICKET`); resuming a run never grants broader scope
than the task allowed.
