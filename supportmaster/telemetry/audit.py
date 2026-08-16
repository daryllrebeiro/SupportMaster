"""Operator-friendly run timelines with a tamper-evident hash chain."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .redaction import Redactor


class AuditTimeline(BaseModel):
    run_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entries: list[dict[str, Any]] = Field(default_factory=list)
    chain_head: str = ""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _chain(entries: list[dict[str, Any]]) -> str:
    previous = "0" * 64
    for entry in entries:
        entry["previous_hash"] = previous
        previous = hashlib.sha256(_canonical(entry).encode("utf-8")).hexdigest()
        entry["hash"] = previous
    return previous


def verify_audit_chain(timeline: AuditTimeline) -> bool:
    previous = "0" * 64
    for original in timeline.entries:
        entry = dict(original)
        recorded_hash = entry.pop("hash", None)
        recorded_previous = entry.pop("previous_hash", None)
        if recorded_previous != previous:
            return False
        entry["previous_hash"] = previous
        expected = hashlib.sha256(_canonical(entry).encode("utf-8")).hexdigest()
        if recorded_hash != expected:
            return False
        previous = expected
    return previous == timeline.chain_head


class AuditExporter:
    """Combine durable events, telemetry, receipts, and gate history into one timeline."""

    def __init__(self, store: Any, *, redactor: Redactor | None = None) -> None:
        self.store = store
        self.redactor = redactor or Redactor()

    def build(self, run_id: str) -> AuditTimeline:
        snapshot = self.store.load_snapshot(run_id)
        entries: list[dict[str, Any]] = []
        for event in self.store.list_events(run_id):
            entries.append({
                "timestamp": event.recorded_at.isoformat(),
                "source": "run_event",
                "event_name": event.event_type,
                "sequence": event.sequence,
                "run_id": run_id,
                "attributes": self.redactor.value(event.payload),
            })
        for event in self.store.list_telemetry(run_id):
            entries.append({
                "timestamp": event.timestamp.isoformat(),
                "source": "telemetry",
                "event_name": event.event_name,
                "event_id": event.event_id,
                "run_id": run_id,
                "correlation_id": event.correlation_id,
                "task_id": event.task_id,
                "operation_id": event.operation_id,
                "gate_id": event.gate_id,
                "level": event.level,
                "message": event.message,
                "attributes": self.redactor.value(event.attributes),
            })
        state = snapshot.state
        for index, receipt in enumerate(state.get("operation_receipts") or []):
            entries.append({
                "timestamp": snapshot.updated_at.isoformat(),
                "source": "operation_receipt",
                "event_name": "INTEGRATION_RECEIPT",
                "sequence": index,
                "run_id": run_id,
                "attributes": self.redactor.value(receipt),
            })
        for index, decision in enumerate(state.get("gate_history") or []):
            entries.append({
                "timestamp": snapshot.updated_at.isoformat(),
                "source": "gate_history",
                "event_name": "GATE_DECISION",
                "sequence": index,
                "run_id": run_id,
                "attributes": self.redactor.value(decision),
            })
        entries.sort(key=lambda item: (str(item.get("timestamp", "")), str(item.get("source", "")), int(item.get("sequence", 0))))
        head = _chain(entries)
        return AuditTimeline(run_id=run_id, entries=entries, chain_head=head)

    def export_json(self, run_id: str, *, indent: int = 2) -> str:
        return self.build(run_id).model_dump_json(indent=indent)

    def export_file(self, run_id: str, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.export_json(run_id), encoding="utf-8")
        return destination
