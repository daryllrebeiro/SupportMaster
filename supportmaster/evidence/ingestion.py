"""Safe, provenance-preserving evidence ingestion."""

from __future__ import annotations

from pathlib import Path
import hashlib
import re
from typing import Any, Iterable

from ..models.evidence import EvidenceAnalysis, EvidenceItem, EvidenceSource
from ..models.evidence_record import EvidenceBundle, EvidenceRecord


_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,]+"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,]+"),
    re.compile(r"(?i)(password\s*[=:]\s*)[^\s,]+"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)


class EvidenceIngestor:
    """Ingest text/files, hash raw content, and redact common secrets."""

    def __init__(self, *, max_bytes: int = 5_000_000) -> None:
        self.max_bytes = max_bytes
        self.bundle = EvidenceBundle()

    def ingest_text(
        self,
        content: str,
        *,
        source_uri: str,
        source_type: str,
        name: str | None = None,
        classification: str = "CONFIRMED",
        confidence: str = "HIGH",
        metadata: dict[str, str] | None = None,
    ) -> EvidenceRecord:
        raw = content.encode("utf-8")
        if len(raw) > self.max_bytes:
            raise ValueError(f"Evidence exceeds the {self.max_bytes}-byte limit.")
        digest = hashlib.sha256(raw).hexdigest()
        sanitized, sensitive = self._redact(content)
        record = EvidenceRecord(
            source_uri=source_uri,
            source_type=source_type,
            name=name or Path(source_uri).name or source_uri,
            content=sanitized,
            content_hash=digest,
            size_bytes=len(raw),
            classification=classification,  # type: ignore[arg-type]
            confidence=confidence,  # type: ignore[arg-type]
            sensitive_data_detected=sensitive,
            redactions_performed=sensitive,
            metadata=metadata or {},
        )
        self.bundle.records.append(record)
        return record

    def ingest_file(
        self,
        path: str | Path,
        *,
        source_type: str = "ATTACHMENT",
        classification: str = "CONFIRMED",
        confidence: str = "HIGH",
    ) -> EvidenceRecord:
        file_path = Path(path)
        raw = file_path.read_bytes()
        if len(raw) > self.max_bytes:
            raise ValueError(f"Evidence exceeds the {self.max_bytes}-byte limit.")
        content = raw.decode("utf-8", errors="replace")
        return self.ingest_text(
            content,
            source_uri=str(file_path),
            source_type=source_type,
            name=file_path.name,
            classification=classification,
            confidence=confidence,
            metadata={"encoding": "utf-8-replace"},
        )

    def ingest_files(self, paths: Iterable[str | Path], *, source_type: str = "ATTACHMENT") -> EvidenceBundle:
        for path in paths:
            self.ingest_file(path, source_type=source_type)
        return self.bundle

    def to_analysis(self) -> EvidenceAnalysis:
        records = self.bundle.records
        items = [
            EvidenceItem(
                category=record.source_type,
                name=record.name,
                value=record.content,
                source=record.source_uri,
                classification=record.classification,
                confidence=record.confidence,
                relevance="Ingested source artifact retained with a SHA-256 provenance hash.",
            )
            for record in records
        ]
        sources = [
            EvidenceSource(
                source_type=record.source_type,
                source_name=record.name,
                available=True,
                inspected=True,
                notes=f"sha256={record.content_hash}; bytes={record.size_bytes}",
            )
            for record in records
        ]
        return EvidenceAnalysis(
            evidence_available=bool(records),
            evidence_collection_performed=bool(records),
            evidence_sources=sources,
            evidence_items=items,
            findings=[],
            evidence_gaps=[],
            strongest_evidence=[record.name for record in records[:5]],
            root_cause_readiness=(
                "READY_FOR_ROOT_CAUSE_ANALYSIS" if records else "INSUFFICIENT_EVIDENCE"
            ),
            sensitive_data_detected=any(record.sensitive_data_detected for record in records),
            redactions_performed=any(record.redactions_performed for record in records),
            confidence_summary="Deterministically ingested evidence with source hashes.",
            recommendation="Proceed to model-assisted evidence correlation with provenance preserved.",
        )

    def attach_to_state(
        self,
        state: dict[str, Any],
        *,
        analysis: EvidenceAnalysis | None = None,
    ) -> EvidenceAnalysis:
        """Attach the bundle, records, and analysis to an ADK-compatible state.

        The state receives plain dictionaries so the helper works with both an
        ADK ``CallbackContext.state`` mapping and serialized run snapshots.
        The returned analysis is also useful to callers that need to pass the
        structured value directly to an agent.
        """
        resolved_analysis = analysis or self.to_analysis()
        state["evidence_bundle"] = self.bundle.model_dump()
        state["evidence_records"] = [record.model_dump() for record in self.bundle.records]
        state["evidence_analysis"] = resolved_analysis.model_dump()
        if self.bundle.ticket_id and not state.get("ticket_id"):
            state["ticket_id"] = self.bundle.ticket_id
        return resolved_analysis

    @staticmethod
    def _redact(content: str) -> tuple[str, bool]:
        sanitized = content
        detected = False
        for pattern in _SECRET_PATTERNS:
            sanitized, count = pattern.subn(
                lambda match: f"{match.group(1)}[REDACTED]" if match.lastindex else "[REDACTED]",
                sanitized,
            )
            detected = detected or count > 0
        return sanitized, detected
