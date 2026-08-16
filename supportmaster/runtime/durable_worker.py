"""Lease-aware worker for durable, idempotent SupportMaster tasks."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from threading import Event, Thread
from time import monotonic
from typing import Any, TypeAlias
from uuid import uuid4

from ..models.durable_task import DurableTask, WorkerTaskResult
from ..persistence.run_store import ConcurrentUpdateError, SQLiteRunStore
from ..telemetry.metrics import MetricsRegistry
from ..telemetry.recorder import TelemetryRecorder


TaskHandler: TypeAlias = Callable[[DurableTask, Event], Mapping[str, Any]]
AsyncTaskHandler: TypeAlias = Callable[
    [DurableTask, Event], Awaitable[Mapping[str, Any]]
]


class _LeaseHeartbeat:
    def __init__(
        self,
        store: SQLiteRunStore,
        task: DurableTask,
        worker_id: str,
        cancel_event: Event,
        *,
        lease_seconds: int,
        interval_seconds: float,
    ) -> None:
        self.store = store
        self.task = task
        self.worker_id = worker_id
        self.cancel_event = cancel_event
        self.lease_seconds = lease_seconds
        self.interval_seconds = interval_seconds
        self.stop_event = Event()
        self.thread = Thread(target=self._run, name=f"supportmaster-lease-{task.task_id[:8]}", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=max(1.0, self.interval_seconds * 2))

    def _run(self) -> None:
        while not self.stop_event.wait(self.interval_seconds):
            try:
                lease_alive = self.store.heartbeat_task(
                    self.task.task_id,
                    self.worker_id,
                    lease_seconds=self.lease_seconds,
                )
                control = self.store.get_run_control(self.task.run_id)
            except Exception:
                self.cancel_event.set()
                return
            if not lease_alive:
                self.cancel_event.set()
                return
            if control.status in {"PAUSED", "CANCEL_REQUESTED", "CANCELLED"}:
                self.cancel_event.set()
                return


class DurableTaskWorker:
    """Claim, execute, checkpoint, retry, and release durable tasks."""

    def __init__(
        self,
        store: SQLiteRunStore,
        *,
        worker_id: str | None = None,
        lease_seconds: int = 60,
        heartbeat_interval_seconds: float | None = None,
        max_backoff_seconds: float = 300.0,
        telemetry: TelemetryRecorder | None = None,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        if lease_seconds < 3:
            raise ValueError("lease_seconds must be at least three seconds.")
        self.store = store
        self.worker_id = worker_id or f"worker-{uuid4()}"
        self.lease_seconds = lease_seconds
        self.heartbeat_interval_seconds = heartbeat_interval_seconds or max(
            1.0, lease_seconds / 3
        )
        self.max_backoff_seconds = max_backoff_seconds
        self.telemetry = telemetry
        self.metrics = metrics or (telemetry.metrics if telemetry else MetricsRegistry())

    def run_once(
        self,
        handler: TaskHandler,
        *,
        cancel_event: Event | None = None,
    ) -> WorkerTaskResult | None:
        task = self.store.claim_next_task(
            self.worker_id,
            lease_seconds=self.lease_seconds,
        )
        if task is None:
            return None
        started = monotonic()
        self._emit("TASK_CLAIMED", task, attributes={"attempt": task.attempt_count})
        self.metrics.increment("supportmaster.tasks.claimed", labels={"task": task.task_name})
        cancellation = cancel_event or Event()
        heartbeat = _LeaseHeartbeat(
            self.store,
            task,
            self.worker_id,
            cancellation,
            lease_seconds=self.lease_seconds,
            interval_seconds=self.heartbeat_interval_seconds,
        )
        heartbeat.start()
        try:
            output = handler(task, cancellation)
            if not isinstance(output, Mapping):
                raise TypeError("Durable task handlers must return a mapping.")
            result = self._finish(task, dict(output), cancellation)
            self.metrics.observe("supportmaster.tasks.duration_seconds", monotonic() - started, labels={"task": task.task_name, "outcome": result.outcome})
            return result
        except Exception as error:
            result = self._fail(task, error, cancellation)
            self.metrics.observe("supportmaster.tasks.duration_seconds", monotonic() - started, labels={"task": task.task_name, "outcome": result.outcome})
            return result
        finally:
            heartbeat.stop()

    async def run_once_async(
        self,
        handler: AsyncTaskHandler,
        *,
        cancel_event: Event | None = None,
    ) -> WorkerTaskResult | None:
        task = self.store.claim_next_task(
            self.worker_id,
            lease_seconds=self.lease_seconds,
        )
        if task is None:
            return None
        started = monotonic()
        self._emit("TASK_CLAIMED", task, attributes={"attempt": task.attempt_count})
        self.metrics.increment("supportmaster.tasks.claimed", labels={"task": task.task_name})
        cancellation = cancel_event or Event()
        heartbeat = _LeaseHeartbeat(
            self.store,
            task,
            self.worker_id,
            cancellation,
            lease_seconds=self.lease_seconds,
            interval_seconds=self.heartbeat_interval_seconds,
        )
        heartbeat.start()
        try:
            output = await handler(task, cancellation)
            if not isinstance(output, Mapping):
                raise TypeError("Durable task handlers must return a mapping.")
            result = self._finish(task, dict(output), cancellation)
            self.metrics.observe("supportmaster.tasks.duration_seconds", monotonic() - started, labels={"task": task.task_name, "outcome": result.outcome})
            return result
        except Exception as error:
            result = self._fail(task, error, cancellation)
            self.metrics.observe("supportmaster.tasks.duration_seconds", monotonic() - started, labels={"task": task.task_name, "outcome": result.outcome})
            return result
        finally:
            heartbeat.stop()

    def run_until_idle(
        self,
        handler: TaskHandler,
        *,
        max_tasks: int | None = None,
    ) -> list[WorkerTaskResult]:
        outcomes: list[WorkerTaskResult] = []
        while max_tasks is None or len(outcomes) < max_tasks:
            outcome = self.run_once(handler)
            if outcome is None:
                break
            outcomes.append(outcome)
        return outcomes

    def checkpoint(self, task: DurableTask, payload: dict[str, Any]) -> None:
        self.store.checkpoint_task(task.task_id, self.worker_id, payload)
        self._emit("TASK_CHECKPOINTED", task, attributes={"checkpoint_keys": sorted(payload)})

    def _finish(
        self,
        task: DurableTask,
        output: dict[str, Any],
        cancellation: Event,
    ) -> WorkerTaskResult:
        control = self.store.get_run_control(task.run_id)
        if control.status in {"CANCEL_REQUESTED", "CANCELLED"}:
            self.store.cancel_task(
                task.task_id,
                self.worker_id,
                reason=control.reason or "Run cancellation requested.",
            )
            self._emit("TASK_CANCELLED", task, level="WARNING", attributes={"reason": control.reason})
            self.metrics.increment("supportmaster.tasks.cancelled", labels={"task": task.task_name})
            return WorkerTaskResult(
                task_id=task.task_id,
                run_id=task.run_id,
                outcome="CANCELLED",
                attempt_count=task.attempt_count,
                result=output,
                error=control.reason,
            )
        if control.status == "PAUSED" or cancellation.is_set():
            try:
                self.store.defer_task(
                    task.task_id,
                    self.worker_id,
                    reason=control.reason or "Run paused; task checkpoint is resumable.",
                )
            except ConcurrentUpdateError:
                self._emit("TASK_LEASE_LOST", task, level="ERROR")
                return WorkerTaskResult(
                    task_id=task.task_id,
                    run_id=task.run_id,
                    outcome="FAILED",
                    attempt_count=task.attempt_count,
                    result=output,
                    error="Task lease was lost before the pause could be persisted.",
                )
            self._emit("TASK_PAUSED", task, level="WARNING", attributes={"reason": control.reason})
            self.metrics.increment("supportmaster.tasks.paused", labels={"task": task.task_name})
            return WorkerTaskResult(
                task_id=task.task_id,
                run_id=task.run_id,
                outcome="PAUSED",
                attempt_count=task.attempt_count,
                result=output,
            )
        self.store.complete_task(task.task_id, self.worker_id, output)
        self._emit("TASK_COMPLETED", task, attributes={"result_keys": sorted(output)})
        self.metrics.increment("supportmaster.tasks.succeeded", labels={"task": task.task_name})
        return WorkerTaskResult(
            task_id=task.task_id,
            run_id=task.run_id,
            outcome="SUCCEEDED",
            attempt_count=task.attempt_count,
            result=output,
        )

    def _fail(
        self,
        task: DurableTask,
        error: Exception,
        cancellation: Event,
    ) -> WorkerTaskResult:
        control = self.store.get_run_control(task.run_id)
        if control.status in {"CANCEL_REQUESTED", "CANCELLED"}:
            self.store.cancel_task(
                task.task_id,
                self.worker_id,
                reason=control.reason or "Run cancellation requested.",
            )
            self._emit("TASK_CANCELLED", task, level="WARNING", attributes={"reason": control.reason})
            self.metrics.increment("supportmaster.tasks.cancelled", labels={"task": task.task_name})
            return WorkerTaskResult(
                task_id=task.task_id,
                run_id=task.run_id,
                outcome="CANCELLED",
                attempt_count=task.attempt_count,
                error=str(error),
            )
        if control.status == "PAUSED" or cancellation.is_set():
            try:
                self.store.defer_task(
                    task.task_id,
                    self.worker_id,
                    reason=control.reason or "Run paused; task will resume later.",
                )
            except ConcurrentUpdateError:
                self._emit("TASK_LEASE_LOST", task, level="ERROR")
                return WorkerTaskResult(
                    task_id=task.task_id,
                    run_id=task.run_id,
                    outcome="FAILED",
                    attempt_count=task.attempt_count,
                    error="Task lease was lost before the pause could be persisted.",
                )
            self._emit("TASK_PAUSED", task, level="WARNING", attributes={"reason": control.reason})
            self.metrics.increment("supportmaster.tasks.paused", labels={"task": task.task_name})
            return WorkerTaskResult(
                task_id=task.task_id,
                run_id=task.run_id,
                outcome="PAUSED",
                attempt_count=task.attempt_count,
                error=str(error),
            )
        delay = min(
            self.max_backoff_seconds,
            2 ** max(0, task.attempt_count - 1),
        )
        updated = self.store.fail_task(
            task.task_id,
            self.worker_id,
            f"{type(error).__name__}: {error}",
            retryable=True,
            retry_delay_seconds=delay,
        )
        outcome = "RETRY_WAIT" if updated.status == "RETRY_WAIT" else "FAILED"
        self._emit("TASK_RETRY_SCHEDULED" if outcome == "RETRY_WAIT" else "TASK_FAILED", task, level="WARNING" if outcome == "RETRY_WAIT" else "ERROR", attributes={"error": f"{type(error).__name__}: {error}", "attempt": updated.attempt_count})
        self.metrics.increment("supportmaster.tasks.failed", labels={"task": task.task_name, "outcome": outcome})
        return WorkerTaskResult(
            task_id=task.task_id,
            run_id=task.run_id,
            outcome=outcome,
            attempt_count=updated.attempt_count,
            error=updated.last_error,
        )

    def _emit(
        self,
        event_name: str,
        task: DurableTask,
        *,
        level: str = "INFO",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        if not self.telemetry:
            return
        try:
            self.telemetry.emit(
                event_name,
                run_id=task.run_id,
                correlation_id=task.run_id,
                task_id=task.task_id,
                level=level,
                attributes={"worker_id": self.worker_id, **(attributes or {})},
            )
        except Exception:
            # Telemetry must never turn a successfully controlled task into a failure.
            return
