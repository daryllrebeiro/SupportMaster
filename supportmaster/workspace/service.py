"""Tenant-scoped workspace projections over durable case artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models.workspace import CaseWorkspaceSnapshot, WorkspaceRun


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
        return CaseWorkspaceSnapshot(case=case, organization=organization, investigation=investigation, planning=planning, resolution=resolution, runs=runs)

    def update_status(self, case_id: str, tenant_id: str, status: str):
        case = self.store.get_case(case_id, tenant_id=tenant_id)
        case.status = status  # type: ignore[assignment]
        case.updated_at = datetime.now(timezone.utc)
        return self.store.save_case(case)

    @staticmethod
    def _optional(loader):
        try:
            return loader()
        except KeyError:
            return None
