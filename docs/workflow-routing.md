# SupportMaster workflow routing

The active application entrypoint is the graph created by
`create_publishing_gate_workflow`. `SequentialAgent` is not used by the
runner.

```text
ticket → investigation → duplicate check → duplicate gate
                                             ├─ CONTINUE (verified) → evidence → repository
                                             │              → root cause → RCA check
                                             │              → remediation → review
                                             │              → review gate
                                             │                 ├─ READY_FOR_IMPLEMENTATION
                                             │                 │  → code change → implementation
                                             │                 │  → validation → tests
                                             │                 │  → validation gate
                                             │                 │     ├─ READY_FOR_PUBLISH
                                             │                 │     │  → publish → GitHub publish
                                             │                 │     │  → resolution → response → audit
                                             │                 │     │  → final audit gate
                                             │                 │     │     ├─ COMPLETED → summary → control
                                             │                 │     │     └─ SAFETY_STOP → autonomous stop
                                             │                 │     └─ SAFETY_STOP → autonomous stop
                                             │                 └─ SAFETY_STOP → autonomous stop
                                             └─ SAFETY_STOP → autonomous stop
```

Explicit duplicate matches, related work, missing status, and malformed or
unknown gate data remain fail-closed. A duplicate search that was attempted but
could not complete is different: `INSUFFICIENT_EVIDENCE` continues in
best-effort mode and records `DUPLICATE_CHECK_INCOMPLETE` as an uncertainty.

Blocked runs do not wait for a person or ask for an approval callback. They
terminate with a deterministic `autonomous_safety_stop` node that records the
gate, reason, blockers, required actions, and evidence keys in
`autonomous_stop`, with `terminal_status=SAFETY_STOP`.
