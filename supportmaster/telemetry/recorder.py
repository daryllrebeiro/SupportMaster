"""Structured event recorder with correlation and span helpers."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Any, Iterator, Protocol
from uuid import uuid4

from .contracts import SpanRecord, TelemetryEvent
from .metrics import MetricsRegistry
from .redaction import Redactor


class TelemetrySink(Protocol):
    def emit(self, event: TelemetryEvent) -> None: ...


class InMemoryTelemetrySink:
    def __init__(self) -> None:
        self.events: list[TelemetryEvent] = []
        self._lock = Lock()

    def emit(self, event: TelemetryEvent) -> None:
        with self._lock:
            self.events.append(event)


class JsonLineTelemetrySink:
    """Append-only JSONL sink for local operators; every value is redacted first."""

    def __init__(self, path: str | Path, *, redactor: Redactor | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.redactor = redactor or Redactor()
        self._lock = Lock()

    def emit(self, event: TelemetryEvent) -> None:
        payload = self.redactor.value(event.model_dump(mode="json"))
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")


class TelemetryRecorder:
    def __init__(
        self,
        sinks: list[TelemetrySink] | None = None,
        *,
        redactor: Redactor | None = None,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self.sinks = sinks or []
        self.redactor = redactor or Redactor()
        self.metrics = metrics or MetricsRegistry()

    def emit(
        self,
        event_name: str,
        *,
        run_id: str | None = None,
        correlation_id: str | None = None,
        task_id: str | None = None,
        operation_id: str | None = None,
        gate_id: str | None = None,
        level: str = "INFO",
        message: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TelemetryEvent:
        event = TelemetryEvent(
            event_name=event_name,
            level=level,
            run_id=run_id,
            correlation_id=correlation_id or run_id,
            task_id=task_id,
            operation_id=operation_id,
            gate_id=gate_id,
            message=self.redactor.text(message) if message else None,
            attributes=self.redactor.mapping(attributes or {}),
        )
        for sink in self.sinks:
            sink.emit(event)
        self.metrics.increment("supportmaster.telemetry.events", labels={"event": event_name})
        return event

    @contextmanager
    def span(
        self,
        name: str,
        *,
        run_id: str | None = None,
        correlation_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[SpanRecord]:
        started = datetime.now(timezone.utc)
        span = SpanRecord(
            trace_id=correlation_id or run_id or str(uuid4()),
            span_id=str(uuid4()),
            parent_span_id=parent_span_id,
            name=name,
            start_time=started,
            end_time=started,
            run_id=run_id,
            attributes=self.redactor.mapping(attributes or {}),
        )
        self.emit("SPAN_STARTED", run_id=run_id, correlation_id=span.trace_id, attributes={"span_id": span.span_id, "name": name})
        try:
            yield span
        except Exception as error:
            span.status = "ERROR"
            span.end_time = datetime.now(timezone.utc)
            self.emit("SPAN_FINISHED", level="ERROR", run_id=run_id, correlation_id=span.trace_id, attributes={"span_id": span.span_id, "name": name, "status": "ERROR", "error": f"{type(error).__name__}: {error}"})
            raise
        else:
            span.end_time = datetime.now(timezone.utc)
            self.emit("SPAN_FINISHED", run_id=run_id, correlation_id=span.trace_id, attributes={"span_id": span.span_id, "name": name, "status": "OK"})
