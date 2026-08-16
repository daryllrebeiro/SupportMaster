"""Reproducible evidence fixtures used by deterministic demos and tests."""

from __future__ import annotations

from pathlib import Path

from ..models.evidence_record import EvidenceBundle
from ..models.evidence import EvidenceAnalysis
from .ingestion import EvidenceIngestor


def sup_4821_directory() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "sup-4821"


def ingest_sup_4821() -> tuple[EvidenceBundle, EvidenceAnalysis]:
    """Ingest all eight SUP-4821 artifacts and return bundle plus analysis."""
    directory = sup_4821_directory()
    paths = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.name != "README.md"
    )
    ingestor = EvidenceIngestor()
    ingestor.bundle.ticket_id = "SUP-4821"
    bundle = ingestor.ingest_files(paths, source_type="TICKET_ATTACHMENT")
    return bundle, ingestor.to_analysis()
