"""Stable, JSON-serializable observability contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


TelemetryLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class TelemetryEvent(BaseModel):
    """A structured event with explicit run and correlation identity."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_name: str
    level: TelemetryLevel = "INFO"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str | None = None
    correlation_id: str | None = None
    task_id: str | None = None
    operation_id: str | None = None
    gate_id: str | None = None
    message: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class MetricPoint(BaseModel):
    """A metric observation suitable for a local exporter or adapter."""

    name: str
    value: float
    metric_type: Literal["counter", "gauge", "histogram"] = "gauge"
    labels: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str | None = None


class SpanRecord(BaseModel):
    """A completed trace span; timestamps remain portable ISO values."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    name: str
    start_time: datetime
    end_time: datetime
    status: Literal["OK", "ERROR"] = "OK"
    run_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
