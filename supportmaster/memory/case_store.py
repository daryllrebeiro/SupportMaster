"""Agent memory: SQLite FTS5 case similarity index for cross-run learning."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SimilarCase:
    case_id: str
    title: str
    root_cause: str
    resolution_summary: str
    similarity_rank: float

    def to_context_block(self) -> str:
        return (
            f"[Similar past case: {self.case_id}]\n"
            f"  Title: {self.title}\n"
            f"  Root cause: {self.root_cause}\n"
            f"  How it was resolved: {self.resolution_summary}\n"
        )


class CaseMemoryStore:
    """
    SQLite-backed FTS5 similarity index that persists resolved case
    knowledge across runs for a given tenant.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        path = db_path or os.getenv("SUPPORTMASTER_MEMORY_DB", ".supportmaster/memory.db")
        self._db_path = str(path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript("""
                CREATE VIRTUAL TABLE IF NOT EXISTS case_memory USING fts5(
                    case_id UNINDEXED,
                    tenant_id UNINDEXED,
                    title,
                    description,
                    root_cause,
                    resolution_summary,
                    tags
                );
            """)
        finally:
            conn.close()

    def record(
        self,
        *,
        case_id: str,
        tenant_id: str,
        title: str,
        description: str,
        root_cause: str,
        resolution_summary: str,
        tags: list[str] | None = None,
    ) -> None:
        """Persist a resolved case into the memory index."""
        tag_str = " ".join(tags or [])
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    "DELETE FROM case_memory WHERE case_id = ? AND tenant_id = ?",
                    (case_id, tenant_id),
                )
                conn.execute(
                    "INSERT INTO case_memory(case_id, tenant_id, title, description, root_cause, resolution_summary, tags) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (case_id, tenant_id, title, description, root_cause, resolution_summary, tag_str),
                )
        finally:
            conn.close()

    def retrieve_similar(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 3,
    ) -> list[SimilarCase]:
        """Return the top-k most similar past cases for the given query text."""
        if not query.strip():
            return []
        sanitized = " ".join(
            word for word in query.split() if word.isalnum() or len(word) > 2
        )
        if not sanitized:
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT case_id, title, root_cause, resolution_summary,
                       rank AS similarity_rank
                FROM case_memory
                WHERE case_memory MATCH ? AND tenant_id = ?
                ORDER BY rank
                LIMIT ?
                """,
                (sanitized, tenant_id, top_k),
            ).fetchall()
            return [
                SimilarCase(
                    case_id=row["case_id"],
                    title=row["title"],
                    root_cause=row["root_cause"],
                    resolution_summary=row["resolution_summary"],
                    similarity_rank=float(row["similarity_rank"] or 0.0),
                )
                for row in rows
            ]
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()
