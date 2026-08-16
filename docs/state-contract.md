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
