"""Small read-only integration bundle for the operator/demo workflow."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..models.control import ExternalOperationReceipt
from ..models.support_case import SupportCase
from .adapters import CIAdapter, IssueTrackerAdapter, MonitoringAdapter
from .contracts import CIStatus, IncidentRecord, IssueRecord


class IntegrationEvidenceBundle(BaseModel):
    """Collected external evidence, always paired with operation receipts."""

    issues: list[IssueRecord] = Field(default_factory=list)
    incidents: list[IncidentRecord] = Field(default_factory=list)
    ci_status: CIStatus | None = None
    receipts: list[ExternalOperationReceipt] = Field(default_factory=list)
    status: str = "COMPLETE"


class ReadOnlyIntegrationBundle:
    """Coordinate issue, monitoring, and CI reads without performing mutations."""

    def __init__(
        self,
        *,
        issue_tracker: IssueTrackerAdapter | None = None,
        monitoring: MonitoringAdapter | None = None,
        ci: CIAdapter | None = None,
    ) -> None:
        self.issue_tracker = issue_tracker
        self.monitoring = monitoring
        self.ci = ci

    def collect(self, case: SupportCase, *, ci_run_id: str | None = None) -> IntegrationEvidenceBundle:
        bundle = IntegrationEvidenceBundle()
        attempted = 0
        failed = 0
        query = " ".join(item for item in (case.external_id, case.title) if item)
        if self.issue_tracker is not None and query:
            attempted += 1
            issues, receipt = self.issue_tracker.search(query)
            bundle.issues = issues
            bundle.receipts.append(receipt)
            failed += receipt.status != "SUCCEEDED"
        if self.monitoring is not None and case.service:
            attempted += 1
            incidents, receipt = self.monitoring.incidents(case.service)
            bundle.incidents = incidents
            bundle.receipts.append(receipt)
            failed += receipt.status != "SUCCEEDED"
        if self.ci is not None and ci_run_id:
            attempted += 1
            status, receipt = self.ci.status(ci_run_id)
            bundle.ci_status = status
            bundle.receipts.append(receipt)
            failed += receipt.status != "SUCCEEDED"
        bundle.status = "FAILED" if failed else ("COMPLETE" if attempted else "NO_SOURCES")
        return bundle
