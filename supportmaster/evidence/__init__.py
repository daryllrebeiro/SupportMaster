"""Deterministic evidence ingestion and fixture loading."""

from .ingestion import EvidenceIngestor
from .fixtures import ingest_sup_4821, sup_4821_directory

__all__ = ["EvidenceIngestor", "ingest_sup_4821", "sup_4821_directory"]
