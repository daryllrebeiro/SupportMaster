"""Least-privilege and dry-run controls for integration adapters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..models.control import ExternalOperationReceipt
from ..telemetry.metrics import MetricsRegistry
from ..telemetry.recorder import TelemetryRecorder
from ..operations.circuit_breaker import CircuitBreaker
from .contracts import IntegrationPermission


class IntegrationPolicy(BaseModel):
    """Allow-list for one run's external integration capabilities."""

    mode: Literal["LIVE", "DRY_RUN"] = "DRY_RUN"
    allowed_permissions: list[IntegrationPermission] = Field(
        default_factory=lambda: [
            "READ_ISSUES",
            "READ_REPOSITORY",
            "READ_CI",
            "READ_MONITORING",
        ]
    )
    allowed_targets: list[str] = Field(default_factory=list)
    max_payload_bytes: int = Field(default=100_000, ge=1)

    def allows(self, permission: IntegrationPermission, target: str) -> bool:
        return permission in self.allowed_permissions and (
            not self.allowed_targets or target in self.allowed_targets
        )


class IntegrationGateway:
    """Guard an adapter operation and return receipts for every decision."""

    def __init__(
        self,
        policy: IntegrationPolicy | None = None,
        *,
        telemetry: TelemetryRecorder | None = None,
        metrics: MetricsRegistry | None = None,
        run_id: str | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.policy = policy or IntegrationPolicy()
        self.telemetry = telemetry
        self.metrics = metrics or (telemetry.metrics if telemetry else MetricsRegistry())
        self.run_id = run_id
        self.circuit_breaker = circuit_breaker

    def execute(
        self,
        *,
        permission: IntegrationPermission,
        target: str,
        operation_type: str,
        requested_action: str,
        operation: Callable[[], ExternalOperationReceipt],
        payload: Mapping[str, Any] | None = None,
    ) -> ExternalOperationReceipt:
        payload_size = len(str(dict(payload or {})).encode("utf-8"))
        common = {
            "permission": permission,
            "target": target,
            "operation_type": operation_type,
            "requested_action": requested_action,
            "payload_bytes": payload_size,
        }
        if self.circuit_breaker and not self.circuit_breaker.allow_request():
            receipt = ExternalOperationReceipt(
                operation_type=operation_type,
                requested_action=requested_action,
                status="BLOCKED",
                details={"target": target, "circuit": "OPEN"},
                error="Integration circuit breaker is open; retry later.",
            )
            return self._record(receipt, common)
        if payload_size > self.policy.max_payload_bytes:
            receipt = ExternalOperationReceipt(
                operation_type=operation_type,
                requested_action=requested_action,
                status="BLOCKED",
                details={"target": target, "payload_bytes": str(payload_size)},
                error="Integration payload exceeds the configured safety limit.",
            )
            return self._record(receipt, common)
        if not self.policy.allows(permission, target):
            receipt = ExternalOperationReceipt(
                operation_type=operation_type,
                requested_action=requested_action,
                status="BLOCKED",
                details={"target": target, "permission": permission},
                error="Integration permission or target is not allow-listed.",
            )
            return self._record(receipt, common)
        if self.policy.mode == "DRY_RUN" and permission not in {
            "READ_ISSUES",
            "READ_REPOSITORY",
            "READ_CI",
            "READ_MONITORING",
        }:
            receipt = ExternalOperationReceipt(
                operation_type=operation_type,
                requested_action=requested_action,
                status="BLOCKED",
                details={"target": target, "mode": "DRY_RUN", "would_execute": "true"},
                error="Dry-run mode prevents integration mutations.",
            )
            return self._record(receipt, common)
        try:
            receipt = operation()
        except Exception as error:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            receipt = ExternalOperationReceipt(
                operation_type=operation_type,
                requested_action=requested_action,
                status="FAILED",
                details={"target": target},
                error=f"{type(error).__name__}: {error}",
            )
            return self._record(receipt, common)
        if self.circuit_breaker:
            self.circuit_breaker.record_success()
        receipt.operation_type = operation_type
        receipt.requested_action = requested_action
        receipt.details.setdefault("target", target)
        receipt.details.setdefault("mode", self.policy.mode)
        return self._record(receipt, common)

    def _record(self, receipt: ExternalOperationReceipt, attributes: dict[str, Any]) -> ExternalOperationReceipt:
        event_name = "INTEGRATION_COMPLETED" if receipt.status in {"SUCCEEDED", "PARTIAL"} else "INTEGRATION_" + receipt.status
        self.metrics.increment("supportmaster.integrations.operations", labels={"status": receipt.status, "operation": receipt.operation_type})
        if self.telemetry:
            self.telemetry.emit(
                event_name,
                run_id=self.run_id,
                operation_id=receipt.operation_id,
                level="ERROR" if receipt.status == "FAILED" else ("WARNING" if receipt.status == "BLOCKED" else "INFO"),
                attributes={**attributes, "status": receipt.status, "error": receipt.error},
            )
        return receipt


def record_integration_receipt(
    state: dict[str, Any],
    receipt: ExternalOperationReceipt,
) -> None:
    """Append an integration receipt to the same evidence stream as Git/CI."""
    receipts = state.get("operation_receipts") or []
    receipts.append(receipt.model_dump())
    state["operation_receipts"] = receipts


def record_integration_result(
    state: dict[str, Any],
    key: str,
    result: Any,
    receipt: ExternalOperationReceipt,
) -> None:
    """Persist structured integration data and its receipt together."""
    results = state.get("integration_results") or {}
    if hasattr(result, "model_dump"):
        results[key] = result.model_dump(mode="json")
    elif isinstance(result, list):
        results[key] = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in result
        ]
    elif isinstance(result, Mapping):
        results[key] = dict(result)
    else:
        results[key] = result
    state["integration_results"] = results
    record_integration_receipt(state, receipt)
