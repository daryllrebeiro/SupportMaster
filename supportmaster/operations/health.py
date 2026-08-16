"""Dependency-light liveness and readiness reporting."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthReport(BaseModel):
    status: Literal["LIVE", "READY", "NOT_READY"]
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checks: dict[str, str] = Field(default_factory=dict)


class HealthReporter:
    def __init__(self, *, run_db: str | Path, session_db: str | Path | None = None) -> None:
        self.run_db = Path(run_db)
        self.session_db = Path(session_db) if session_db else None

    def liveness(self) -> HealthReport:
        return HealthReport(status="LIVE", checks={"process": "ok"})

    def readiness(self) -> HealthReport:
        checks: dict[str, str] = {}
        for name, path in (("run_store", self.run_db), ("session_store", self.session_db)):
            if path is None:
                continue
            try:
                connection = sqlite3.connect(str(path), timeout=1.0)
                try:
                    connection.execute("SELECT 1").fetchone()
                finally:
                    connection.close()
                checks[name] = "ok"
            except Exception as error:
                checks[name] = f"error:{type(error).__name__}"
        status: Literal["READY", "NOT_READY"] = "READY" if all(value == "ok" for value in checks.values()) else "NOT_READY"
        return HealthReport(status=status, checks=checks)
