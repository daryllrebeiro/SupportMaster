"""HTTP-backed adapters using the same policy and receipt contracts as fakes."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import quote
from uuid import uuid4

from ..models.control import ExternalOperationReceipt
from .adapters import (
    CIAdapter,
    IssueTrackerAdapter,
    MonitoringAdapter,
    NotificationAdapter,
)
from .contracts import CIStatus, IncidentRecord, IssueRecord, MetricSample
from .http import JsonHttpTransport
from .policy import IntegrationGateway


def _success(code: int) -> bool:
    return 200 <= code < 300


class HttpIssueTrackerAdapter(IssueTrackerAdapter):
    def __init__(self, transport: JsonHttpTransport, *, gateway: IntegrationGateway | None = None) -> None:
        self.transport = transport
        self.gateway = gateway or IntegrationGateway()

    def search(self, query: str) -> tuple[list[IssueRecord], ExternalOperationReceipt]:
        items: list[IssueRecord] = []

        def operation() -> ExternalOperationReceipt:
            code, payload = self.transport.request("GET", "/issues/search", {"q": query})
            if not _success(code):
                return ExternalOperationReceipt(
                    operation_type="ISSUE_SEARCH",
                    requested_action="search_issues",
                    status="FAILED",
                    details={"http_status": str(code)},
                    error=str(payload.get("error", "Issue search failed.")),
                )
            raw_items = payload.get("items", [])
            items.extend(IssueRecord.model_validate(item) for item in raw_items)
            return ExternalOperationReceipt(
                operation_type="ISSUE_SEARCH",
                requested_action="search_issues",
                status="SUCCEEDED",
                external_id=str(len(items)),
                details={"http_status": str(code)},
            )

        receipt = self.gateway.execute(
            permission="READ_ISSUES",
            target="issue_tracker",
            operation_type="ISSUE_SEARCH",
            requested_action="search_issues",
            operation=operation,
            payload={"query": query},
        )
        return items if receipt.status == "SUCCEEDED" else [], receipt

    def add_comment(self, issue_key: str, body: str) -> ExternalOperationReceipt:
        def operation() -> ExternalOperationReceipt:
            code, payload = self.transport.request(
                "POST",
                f"/issues/{quote(issue_key, safe='')}/comments",
                {"body": body},
            )
            return ExternalOperationReceipt(
                operation_type="ISSUE_COMMENT",
                requested_action="add_comment",
                status="SUCCEEDED" if _success(code) else "FAILED",
                external_id=str(payload.get("id", issue_key)),
                details={"http_status": str(code)},
                error=None if _success(code) else str(payload.get("error", "Issue comment failed.")),
            )

        return self.gateway.execute(
            permission="WRITE_ISSUES",
            target=issue_key,
            operation_type="ISSUE_COMMENT",
            requested_action="add_comment",
            operation=operation,
            payload={"issue_key": issue_key, "body": body},
        )


class HttpCIAdapter(CIAdapter):
    def __init__(self, transport: JsonHttpTransport, *, gateway: IntegrationGateway | None = None) -> None:
        self.transport = transport
        self.gateway = gateway or IntegrationGateway()

    def trigger(
        self,
        pipeline: str,
        *,
        commit_sha: str,
        parameters: Mapping[str, str] | None = None,
    ) -> ExternalOperationReceipt:
        def operation() -> ExternalOperationReceipt:
            code, payload = self.transport.request(
                "POST",
                f"/pipelines/{quote(pipeline, safe='')}/runs",
                {"commit_sha": commit_sha, "parameters": dict(parameters or {})},
            )
            return ExternalOperationReceipt(
                operation_type="CI_TRIGGER",
                requested_action="trigger_pipeline",
                status="SUCCEEDED" if _success(code) else "FAILED",
                external_id=str(payload.get("run_id", uuid4())),
                details={"http_status": str(code), "pipeline": pipeline},
                error=None if _success(code) else str(payload.get("error", "CI trigger failed.")),
            )

        return self.gateway.execute(
            permission="TRIGGER_CI",
            target=pipeline,
            operation_type="CI_TRIGGER",
            requested_action="trigger_pipeline",
            operation=operation,
            payload={"pipeline": pipeline, "commit_sha": commit_sha, "parameters": dict(parameters or {})},
        )

    def status(self, run_id: str) -> tuple[CIStatus, ExternalOperationReceipt]:
        status = CIStatus(run_id=run_id, status="UNKNOWN")

        def operation() -> ExternalOperationReceipt:
            nonlocal status
            code, payload = self.transport.request("GET", f"/runs/{quote(run_id, safe='')}")
            if _success(code):
                status = CIStatus.model_validate({"run_id": run_id, **payload})
            return ExternalOperationReceipt(
                operation_type="CI_STATUS",
                requested_action="read_pipeline_status",
                status="SUCCEEDED" if _success(code) else "FAILED",
                external_id=run_id,
                details={"http_status": str(code)},
                error=None if _success(code) else str(payload.get("error", "CI status failed.")),
            )

        receipt = self.gateway.execute(
            permission="READ_CI",
            target=run_id,
            operation_type="CI_STATUS",
            requested_action="read_pipeline_status",
            operation=operation,
        )
        return status, receipt


class HttpMonitoringAdapter(MonitoringAdapter):
    def __init__(self, transport: JsonHttpTransport, *, gateway: IntegrationGateway | None = None) -> None:
        self.transport = transport
        self.gateway = gateway or IntegrationGateway()

    def incidents(self, service: str) -> tuple[list[IncidentRecord], ExternalOperationReceipt]:
        items: list[IncidentRecord] = []

        def operation() -> ExternalOperationReceipt:
            code, payload = self.transport.request("GET", "/incidents", {"service": service})
            if _success(code):
                items.extend(IncidentRecord.model_validate(item) for item in payload.get("items", []))
            return ExternalOperationReceipt(
                operation_type="MONITORING_INCIDENTS",
                requested_action="read_incidents",
                status="SUCCEEDED" if _success(code) else "FAILED",
                external_id=str(len(items)),
                details={"http_status": str(code), "service": service},
                error=None if _success(code) else str(payload.get("error", "Incident query failed.")),
            )

        receipt = self.gateway.execute(
            permission="READ_MONITORING",
            target=service,
            operation_type="MONITORING_INCIDENTS",
            requested_action="read_incidents",
            operation=operation,
            payload={"service": service},
        )
        return items if receipt.status == "SUCCEEDED" else [], receipt

    def metric(self, name: str, *, service: str) -> tuple[list[MetricSample], ExternalOperationReceipt]:
        items: list[MetricSample] = []

        def operation() -> ExternalOperationReceipt:
            code, payload = self.transport.request("GET", "/metrics", {"metric": name, "service": service})
            if _success(code):
                items.extend(MetricSample.model_validate(item) for item in payload.get("items", []))
            return ExternalOperationReceipt(
                operation_type="MONITORING_METRIC",
                requested_action="read_metric",
                status="SUCCEEDED" if _success(code) else "FAILED",
                external_id=str(len(items)),
                details={"http_status": str(code), "metric": name, "service": service},
                error=None if _success(code) else str(payload.get("error", "Metric query failed.")),
            )

        receipt = self.gateway.execute(
            permission="READ_MONITORING",
            target=service,
            operation_type="MONITORING_METRIC",
            requested_action="read_metric",
            operation=operation,
            payload={"metric": name, "service": service},
        )
        return items if receipt.status == "SUCCEEDED" else [], receipt


class HttpNotificationAdapter(NotificationAdapter):
    def __init__(self, transport: JsonHttpTransport, *, gateway: IntegrationGateway | None = None) -> None:
        self.transport = transport
        self.gateway = gateway or IntegrationGateway()

    def send(self, channel: str, message: str) -> ExternalOperationReceipt:
        def operation() -> ExternalOperationReceipt:
            code, payload = self.transport.request(
                "POST",
                "/messages",
                {"channel": channel, "message": message},
            )
            return ExternalOperationReceipt(
                operation_type="NOTIFICATION_SEND",
                requested_action="send_notification",
                status="SUCCEEDED" if _success(code) else "FAILED",
                external_id=str(payload.get("message_id", channel)),
                details={"http_status": str(code), "channel": channel},
                error=None if _success(code) else str(payload.get("error", "Notification failed.")),
            )

        return self.gateway.execute(
            permission="SEND_NOTIFICATIONS",
            target=channel,
            operation_type="NOTIFICATION_SEND",
            requested_action="send_notification",
            operation=operation,
            payload={"channel": channel, "message": message},
        )
