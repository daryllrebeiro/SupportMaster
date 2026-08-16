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
