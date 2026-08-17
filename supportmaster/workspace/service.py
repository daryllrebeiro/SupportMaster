"""Tenant-scoped workspace projections over durable case artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models.workspace import CaseActivityEvent, CaseWorkspaceSnapshot, WorkspaceRun, WorkspaceTimelineEvent


class CaseWorkspaceService:
    def __init__(self, store: Any) -> None:
        self.store = store

    def list(self, tenant_id: str, *, status: str | None = None):
        return self.store.list_cases(tenant_id, status=status)

    def snapshot(self, case_id: str, tenant_id: str) -> CaseWorkspaceSnapshot:
        case = self.store.get_case(case_id, tenant_id=tenant_id)
        organization = self._optional(lambda: self.store.get_organization(tenant_id))
        investigation = self._optional(lambda: self.store.get_investigation_summary(case_id, tenant_id=tenant_id))
        planning = self._optional(lambda: self.store.get_planning_assessment(case_id, tenant_id=tenant_id))
        resolution = self._optional(lambda: self.store.get_resolution_bundle(case_id, tenant_id=tenant_id))
        runs = [WorkspaceRun.model_validate(item) for item in self.store.list_runs_for_case(case_id, tenant_id=tenant_id)]
        timeline = [WorkspaceTimelineEvent(stage="INTAKE", status="COMPLETE", detail="Support case was accepted and normalized.")]
        gates: dict[str, str] = {}
        if investigation is None:
            timeline.append(WorkspaceTimelineEvent(stage="INVESTIGATION", status="NOT_STARTED", detail="No investigation summary has been recorded."))
            next_action = "Start investigation and collect the missing evidence."
            workflow_stage = "INVESTIGATION"
        else:
            investigation_status = investigation.investigation_status
            timeline.append(WorkspaceTimelineEvent(stage="INVESTIGATION", status=investigation_status, detail=investigation.readiness_reason))
            gates["investigation"] = investigation_status
            if investigation_status != "READY":
                next_action = "Collect the missing evidence before creating a remediation plan."
                workflow_stage = "INVESTIGATION"
            elif planning is None:
                next_action = "Review investigation gaps and create a remediation plan."
                workflow_stage = "PLANNING"
            else:
                plan_status = planning.remediation.remediation_status
                timeline.append(WorkspaceTimelineEvent(stage="PLANNING", status=plan_status, detail="Root-cause and remediation assessment is available."))
                gates["planning"] = plan_status
                if resolution is None:
                    next_action = "Review the remediation plan and execute only with the required authorization."
                    workflow_stage = "EXECUTION"
                else:
                    resolution_status = resolution.resolution.resolution_status
                    timeline.append(WorkspaceTimelineEvent(stage="RESOLUTION", status=resolution_status, detail=resolution.resolution.summary))
                    gates.update({"implementation": resolution.resolution.implementation_gate.status, "validation": resolution.resolution.validation_gate.status, "publication": resolution.resolution.publication_gate.status})
                    next_action = resolution.resolution.recommended_action
                    workflow_stage = "COMPLETED" if resolution.resolution.ticket_closure_allowed else "REVIEW"
        return CaseWorkspaceSnapshot(case=case, organization=organization, investigation=investigation, planning=planning, resolution=resolution, runs=runs, workflow_stage=workflow_stage, next_action=next_action, gate_statuses=gates, timeline=timeline)

    def update_status(self, case_id: str, tenant_id: str, status: str):
        case = self.store.get_case(case_id, tenant_id=tenant_id)
        case.status = status  # type: ignore[assignment]
        case.updated_at = datetime.now(timezone.utc)
        return self.store.save_case(case)

    def activity(self, case_id: str, tenant_id: str) -> list[CaseActivityEvent]:
        self.store.get_case(case_id, tenant_id=tenant_id)
        events: list[CaseActivityEvent] = []
        for run in self.store.list_runs_for_case(case_id, tenant_id=tenant_id):
            for event in self.store.list_events(run["run_id"]):
                events.append(CaseActivityEvent(sequence=event.sequence, run_id=event.run_id, event_type=event.event_type, recorded_at=event.recorded_at))
        return sorted(events, key=lambda event: (event.recorded_at, event.sequence))

    @staticmethod
    def _optional(loader):
        try:
            return loader()
        except KeyError:
            return None
