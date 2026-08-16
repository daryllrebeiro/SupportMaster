# SupportMaster workflow routing

The active application entrypoint is the graph created by
`create_publishing_gate_workflow`. `SequentialAgent` is not used by the
runner. A real publication run must inject a `PublicationExecutor` into
`create_root_agent`; the default local UI intentionally has no mutating
adapter and therefore stops at the verified executor.

```text
ticket → investigation → duplicate check → duplicate gate
                                             ├─ CONTINUE (verified) → evidence → repository
                                             │              → root cause → RCA check
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

Human-required work is persisted as a review task with an expiring hashed
resume token. Approval scopes are explicit (`IMPLEMENTATION`, `PUBLISH`,
`PRODUCTION`, or `CLOSE_TICKET`); resuming a run never grants broader scope
than the task allowed.
