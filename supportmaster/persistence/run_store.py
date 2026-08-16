"""SQLite-backed run snapshots, events, review tasks, and resume tokens."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
from typing import Any, Literal

from ..models.control import AuthorizationScope
from ..models.human_review import HumanReviewDecision, HumanReviewTask
from ..models.run_event import RunEvent, RunSnapshot
from ..workflow_state import (
    SupportMasterState,
    issue_human_authorization,
)


class ConcurrentUpdateError(RuntimeError):
    """Raised when a stale state version attempts to overwrite a run."""


class _ClosingConnection(sqlite3.Connection):
    """Connection context manager that also closes on Windows."""

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        try:
            super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class SQLiteRunStore:
    """Small durable control-plane store using only Python's sqlite3 module."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, factory=_ClosingConnection)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS run_events_run_id_idx
                    ON run_events(run_id, sequence);
                CREATE TABLE IF NOT EXISTS review_tasks (
                    task_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    task_json TEXT NOT NULL,
                    resume_token_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS review_tasks_run_id_idx
                    ON review_tasks(run_id, status);
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_run(self, state: SupportMasterState) -> RunSnapshot:
        payload = state.model_dump(mode="json")
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runs(run_id, version, state_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (state.run_id, 0, json.dumps(payload), now, now),
            )
            self._append_event(connection, state.run_id, "RUN_CREATED", {"version": 0})
        return RunSnapshot(run_id=state.run_id, version=0, state=payload)

    def load_snapshot(self, run_id: str) -> RunSnapshot:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT run_id, version, state_json, updated_at FROM runs WHERE run_id=?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown SupportMaster run: {run_id}")
        return RunSnapshot(
            run_id=row["run_id"],
            version=row["version"],
            state=json.loads(row["state_json"]),
            updated_at=row["updated_at"],
        )

    def load_state(self, run_id: str) -> SupportMasterState:
        return SupportMasterState.model_validate(self.load_snapshot(run_id).state)

    def save_state(
        self,
        state: SupportMasterState,
        *,
        expected_version: int | None = None,
        event_type: str = "STATE_SAVED",
    ) -> RunSnapshot:
        payload = state.model_dump(mode="json")
        now = self._now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT version FROM runs WHERE run_id=?",
                (state.run_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown SupportMaster run: {state.run_id}")
            current_version = int(row["version"])
            if expected_version is not None and current_version != expected_version:
                raise ConcurrentUpdateError(
                    f"Run {state.run_id} is at version {current_version}, expected {expected_version}."
                )
            next_version = current_version + 1
            connection.execute(
                "UPDATE runs SET version=?, state_json=?, updated_at=? WHERE run_id=?",
                (next_version, json.dumps(payload), now, state.run_id),
            )
            self._append_event(
                connection,
                state.run_id,
                event_type,
                {"version": next_version, "terminal_outcome": state.terminal_outcome},
            )
        return RunSnapshot(
            run_id=state.run_id,
            version=next_version,
            state=payload,
            updated_at=now,
        )

    def append_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> RunEvent:
        with self._connect() as connection:
            event_id = self._append_event(connection, run_id, event_type, payload or {})
        return self._event(run_id, event_id)

    def list_events(self, run_id: str) -> list[RunEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT sequence, run_id, event_type, payload_json, recorded_at FROM run_events WHERE run_id=? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        return [
            RunEvent(
                sequence=row["sequence"],
                run_id=row["run_id"],
                event_type=row["event_type"],
                payload=json.loads(row["payload_json"]),
                recorded_at=row["recorded_at"],
            )
            for row in rows
        ]

    def create_review_task(
        self,
        run_id: str,
        *,
        reason: str,
        blocking_reasons: Iterable[str] = (),
        required_actions: Iterable[str] = (),
        evidence_keys: Iterable[str] = (),
        allowed_scopes: Iterable[AuthorizationScope] = (),
        resume_condition: str,
        ttl_seconds: int = 3600,
    ) -> tuple[HumanReviewTask, str]:
        token = secrets.token_urlsafe(32)
        task = HumanReviewTask(
            run_id=run_id,
            reason=reason,
            blocking_reasons=list(blocking_reasons),
            required_actions=list(required_actions),
            evidence_keys=list(evidence_keys),
            allowed_scopes=list(allowed_scopes),
            resume_condition=resume_condition,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        )
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO review_tasks(task_id, run_id, status, task_json, resume_token_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    task.task_id,
                    run_id,
                    task.status,
                    task.model_dump_json(),
                    self._hash_token(token),
                    now,
                    now,
                ),
            )
            self._append_event(connection, run_id, "HUMAN_REVIEW_OPENED", task.model_dump(mode="json"))
        state = self.load_state(run_id)
        state.pending_human_review = task
        state.terminal_status = "HUMAN_REVIEW_REQUIRED"
        state.terminal_outcome = "PAUSED_FOR_HUMAN_REVIEW"
        self.save_state(state, event_type="RUN_PAUSED_FOR_HUMAN_REVIEW")
        return task, token

    def get_review_task(self, task_id: str) -> HumanReviewTask:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT task_json FROM review_tasks WHERE task_id=?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown human-review task: {task_id}")
        task = HumanReviewTask.model_validate(json.loads(row["task_json"]))
        if task.expires_at and task.expires_at <= datetime.now(timezone.utc) and task.status == "OPEN":
            self._set_task_status(task, "EXPIRED")
        return task

    def decide_review_task(
        self,
        task_id: str,
        *,
        reviewer: str,
        decision: Literal["APPROVE", "REJECT"],
        resume_token: str,
        approved_scopes: Iterable[AuthorizationScope] = (),
        comment: str = "",
    ) -> HumanReviewTask:
        task = self.get_review_task(task_id)
        self._verify_token(task_id, resume_token)
        if task.status != "OPEN":
            raise ValueError(f"Review task is not open: {task.status}")
        scopes = list(approved_scopes)
        if not set(scopes).issubset(set(task.allowed_scopes)):
            raise ValueError("Approval scope exceeds the review task's allowed scopes.")
        if decision == "REJECT" and scopes:
            raise ValueError("Rejected review tasks cannot issue approval scopes.")
        if not reviewer.strip():
            raise ValueError("A reviewer identity is required.")
        task.decision = HumanReviewDecision(
            task_id=task.task_id,
            reviewer=reviewer,
            decision=decision,
            approved_scopes=scopes,
            comment=comment,
        )
        task.status = "APPROVED" if decision == "APPROVE" else "REJECTED"
        self._save_task(task)
        self.append_event(task.run_id, "HUMAN_REVIEW_DECIDED", task.model_dump(mode="json"))
        return task

    def resume_run(self, run_id: str, task_id: str, resume_token: str) -> SupportMasterState:
        task = self.get_review_task(task_id)
        self._verify_token(task_id, resume_token)
        if task.run_id != run_id:
            raise ValueError("Review task does not belong to this run.")
        if task.status != "APPROVED" or task.decision is None:
            raise ValueError("Only an approved review task can resume a run.")
        state = self.load_state(run_id)
        for scope in task.decision.approved_scopes:
            issue_human_authorization(
                state,
                scope=scope,
                approval_id=task.decision.decision_id,
                expires_at=task.expires_at,
            )
        state.human_review_history.append(task.decision)
        state.pending_human_review = None
        state.terminal_status = None
        state.terminal_outcome = None
        task.status = "RESUMED"
        self._save_task(task)
        self.save_state(state, event_type="RUN_RESUMED")
        self.append_event(run_id, "HUMAN_REVIEW_RESUMED", {"task_id": task_id})
        return state

    def _verify_token(self, task_id: str, token: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT resume_token_hash FROM review_tasks WHERE task_id=?",
                (task_id,),
            ).fetchone()
        if row is None or not secrets.compare_digest(row["resume_token_hash"], self._hash_token(token)):
            raise ValueError("Invalid resume token.")

    def _save_task(self, task: HumanReviewTask) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE review_tasks SET status=?, task_json=?, updated_at=? WHERE task_id=?",
                (task.status, task.model_dump_json(), self._now(), task.task_id),
            )

    def _set_task_status(self, task: HumanReviewTask, status: str) -> None:
        task.status = status  # type: ignore[assignment]
        self._save_task(task)

    def _append_event(
        self,
        connection: sqlite3.Connection,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        cursor = connection.execute(
            "INSERT INTO run_events(run_id, event_type, payload_json, recorded_at) VALUES (?, ?, ?, ?)",
            (run_id, event_type, json.dumps(payload), self._now()),
        )
        return int(cursor.lastrowid)

    def _event(self, run_id: str, sequence: int) -> RunEvent:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT sequence, run_id, event_type, payload_json, recorded_at FROM run_events WHERE sequence=? AND run_id=?",
                (sequence, run_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown run event: {sequence}")
        return RunEvent(
            sequence=row["sequence"],
            run_id=row["run_id"],
            event_type=row["event_type"],
            payload=json.loads(row["payload_json"]),
            recorded_at=row["recorded_at"],
        )
