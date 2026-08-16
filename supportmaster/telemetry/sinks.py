"""Persistence-backed telemetry sinks."""

from __future__ import annotations

from typing import Any

from .contracts import TelemetryEvent


class SQLiteTelemetrySink:
    """Persist structured events using the existing run store connection boundary."""

    def __init__(self, store: Any) -> None:
        self.store = store

    def emit(self, event: TelemetryEvent) -> None:
        if event.run_id:
            self.store.append_telemetry_event(event)
