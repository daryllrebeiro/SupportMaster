"""Bounded fork/join execution for independent, read-only investigation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from copy import deepcopy
from datetime import datetime, timezone
import json
from threading import Event
from time import monotonic
from types import MappingProxyType
from typing import Any, TypeAlias, TYPE_CHECKING

from .contracts import BranchResult, ForkGroupSpec, ForkJoinResult, TaskSpec

if TYPE_CHECKING:
    from ..workflow_state import SupportMasterState


BranchHandler: TypeAlias = Callable[[Mapping[str, Any], Event], Mapping[str, Any]]


class ForkJoinExecutor:
    """Run read-only branches with bounded concurrency and fail-closed joins.

    Handlers receive an immutable-by-convention snapshot and a cancellation
    event. They must return a mapping and must not mutate shared workflow state.
    Mutating operations are rejected at the task-contract boundary.
    """

    def __init__(self, *, max_concurrency: int = 4) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least one.")
        self.max_concurrency = max_concurrency

    def run(
        self,
        group: ForkGroupSpec,
        state: Mapping[str, Any] | "SupportMasterState",
        handlers: Mapping[str, BranchHandler],
        *,
        cancel_event: Event | None = None,
    ) -> ForkJoinResult:
        started_at = datetime.now(timezone.utc)
        cancellation = cancel_event or Event()
        task_map = self._validate_group(group, handlers)
        state_snapshot = self._snapshot_state(state)
        results: dict[str, BranchResult] = {}
        pending = set(task_map)
        deadline = monotonic() + group.timeout_seconds

        while pending:
            if cancellation.is_set():
                for task_name in sorted(pending):
                    results[task_name] = self._simple_result(
                        task_name, "CANCELLED", "Fork group cancellation requested."
                    )
                break

            ready = sorted(
                task_name
                for task_name in pending
                if all(
                    dependency in results
                    and results[dependency].status == "SUCCEEDED"
                    for dependency in task_map[task_name].dependencies
                )
            )
            blocked = sorted(
                task_name
                for task_name in pending
                if any(
                    dependency in results
                    and results[dependency].status != "SUCCEEDED"
                    for dependency in task_map[task_name].dependencies
                )
            )
            for task_name in blocked:
                results[task_name] = self._simple_result(
                    task_name,
                    "SKIPPED",
                    "A required dependency did not complete successfully.",
                )
                pending.remove(task_name)

            if not ready:
                if pending:
                    for task_name in sorted(pending):
                        results[task_name] = self._simple_result(
                            task_name,
                            "SKIPPED",
                            "No runnable task remained; dependency graph is incomplete.",
                        )
                        pending.remove(task_name)
                break

            wave = ready[: min(group.max_concurrency, self.max_concurrency)]
            for task_name in wave:
                pending.remove(task_name)
            wave_results = self._run_wave(
                wave,
                task_map,
                handlers,
                state_snapshot,
                cancellation,
                max(0.0, deadline - monotonic()),
            )
            results.update(wave_results)

        return self._join(
            group,
            [results[name] for name in sorted(results)],
            started_at=started_at,
        )

    @staticmethod
    def _validate_group(
        group: ForkGroupSpec,
        handlers: Mapping[str, BranchHandler],
    ) -> dict[str, TaskSpec]:
        task_map = {task.name: task for task in group.tasks}
        if len(task_map) != len(group.tasks):
            raise ValueError("Fork task names must be unique.")
        for task in group.tasks:
            if not task.read_only:
                raise ValueError(
                    f"Fork task {task.name!r} is mutating; mutations must remain serialized."
                )
            if task.name not in handlers:
                raise ValueError(f"No handler was provided for fork task {task.name!r}.")
            unknown = set(task.dependencies) - set(task_map)
            if unknown:
                raise ValueError(
                    f"Fork task {task.name!r} has unknown dependencies: {sorted(unknown)}."
                )
        ForkJoinExecutor._assert_acyclic(task_map)
        return task_map

    @staticmethod
    def _assert_acyclic(task_map: Mapping[str, TaskSpec]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise ValueError("Fork task dependencies must form an acyclic graph.")
            if name in visited:
                return
            visiting.add(name)
            for dependency in task_map[name].dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)

        for task_name in task_map:
            visit(task_name)

    @staticmethod
    def _snapshot_state(state: Mapping[str, Any] | "SupportMasterState") -> Mapping[str, Any]:
        if hasattr(state, "model_dump"):
            raw = state.model_dump(mode="json")
        elif hasattr(state, "to_dict"):
            raw = state.to_dict()  # type: ignore[union-attr]
        else:
            raw = dict(state)
        return MappingProxyType(deepcopy(raw))

    def _run_wave(
        self,
        task_names: list[str],
        task_map: Mapping[str, TaskSpec],
        handlers: Mapping[str, BranchHandler],
        state_snapshot: Mapping[str, Any],
        cancellation: Event,
        remaining_seconds: float,
    ) -> dict[str, BranchResult]:
        if remaining_seconds <= 0:
            return {
                name: self._simple_result(name, "TIMED_OUT", "Fork group deadline expired.")
                for name in task_names
            }
        executor = ThreadPoolExecutor(
            max_workers=min(self.max_concurrency, len(task_names)),
            thread_name_prefix="supportmaster-fork",
        )
        futures: dict[str, Future[Mapping[str, Any]]] = {}
        started: dict[str, tuple[datetime, float]] = {}
        try:
            for task_name in task_names:
                task = task_map[task_name]
                started[task_name] = (datetime.now(timezone.utc), monotonic())
                futures[task_name] = executor.submit(
                    handlers[task_name], state_snapshot, cancellation
                )
            pending_futures = set(futures.values())
            done_set: set[Future[Mapping[str, Any]]] = set()
            timed_out: set[str] = set()
            group_deadline = monotonic() + remaining_seconds
            while pending_futures:
                now = monotonic()
                if now >= group_deadline:
                    timed_out.update(
                        task_name
                        for task_name, future in futures.items()
                        if future in pending_futures
                    )
                    break
                expiring = [
                    max(0.0, task_map[task_name].timeout_seconds - (now - started[task_name][1]))
                    for task_name, future in futures.items()
                    if future in pending_futures
                ]
                wait_seconds = min(group_deadline - now, min(expiring, default=0.0))
                done, pending_futures = wait(
                    pending_futures,
                    timeout=wait_seconds,
                    return_when=FIRST_COMPLETED,
                )
                if done:
                    done_set.update(done)
                    continue
                timed_out.update(
                    task_name
                    for task_name, future in futures.items()
                    if future in pending_futures
                    and monotonic() - started[task_name][1]
                    >= task_map[task_name].timeout_seconds
                )
                if not timed_out and not pending_futures:
                    break
            results: dict[str, BranchResult] = {}
            for task_name in task_names:
                future = futures[task_name]
                started_at, started_mono = started[task_name]
                duration_ms = max(0, int((monotonic() - started_mono) * 1000))
                if task_name in timed_out:
                    future.cancel()
                    results[task_name] = BranchResult(
                        task_name=task_name,
                        status="TIMED_OUT",
                        error=f"Task exceeded {task_map[task_name].timeout_seconds:g}s or fork deadline.",
                        started_at=started_at,
                        finished_at=datetime.now(timezone.utc),
                        duration_ms=duration_ms,
                    )
                    continue
                if future not in done_set:
                    results[task_name] = self._simple_result(
                        task_name, "CANCELLED", "Task was cancelled before execution."
                    )
                    continue
                try:
                    output = future.result()
                    if not isinstance(output, Mapping):
                        raise TypeError("Fork handlers must return a mapping.")
                    results[task_name] = BranchResult(
                        task_name=task_name,
                        status="SUCCEEDED",
                        output=dict(output),
                        started_at=started_at,
                        finished_at=datetime.now(timezone.utc),
                        duration_ms=duration_ms,
                    )
                except Exception as exc:  # branch failures are represented, not hidden
                    results[task_name] = BranchResult(
                        task_name=task_name,
                        status="FAILED",
                        error=f"{type(exc).__name__}: {exc}",
                        started_at=started_at,
                        finished_at=datetime.now(timezone.utc),
                        duration_ms=duration_ms,
                    )
            return results
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _simple_result(task_name: str, status: Any, error: str) -> BranchResult:
        now = datetime.now(timezone.utc)
        return BranchResult(
            task_name=task_name,
            status=status,
            error=error,
            started_at=now,
            finished_at=now,
            duration_ms=0,
        )

    @staticmethod
    def _join(
        group: ForkGroupSpec,
        branches: list[BranchResult],
        *,
        started_at: datetime,
    ) -> ForkJoinResult:
        task_map = {task.name: task for task in group.tasks}
        by_name = {branch.task_name: branch for branch in branches}
        missing_required = [
            task.name
            for task in group.tasks
            if task.required and by_name[task.name].status != "SUCCEEDED"
        ]
        conflicts: list[str] = []
        merged: dict[str, Any] = {}
        for branch in branches:
            if branch.status != "SUCCEEDED":
                continue
            for key, value in sorted(branch.output.items()):
                if key in conflicts:
                    continue
                if key in merged and not ForkJoinExecutor._same_value(merged[key], value):
                    conflicts.append(key)
                    merged.pop(key, None)
                    continue
                merged[key] = value
        conflicts = sorted(set(conflicts))
        if conflicts or missing_required:
            status = "BLOCKED"
        elif any(branch.status != "SUCCEEDED" for branch in branches):
            status = "PARTIAL"
        else:
            status = "COMPLETED"
        warnings = []
        if any(branch.status == "TIMED_OUT" for branch in branches):
            warnings.append("One or more read-only branches timed out.")
        if conflicts:
            warnings.append("Conflicting branch outputs were withheld from the merged result.")
        return ForkJoinResult(
            group_name=group.name,
            status=status,
            branches=branches,
            merged_output=merged,
            conflicts=conflicts,
            missing_required=missing_required,
            warnings=warnings,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _same_value(left: Any, right: Any) -> bool:
        try:
            return json.dumps(left, sort_keys=True, default=str) == json.dumps(
                right, sort_keys=True, default=str
            )
        except (TypeError, ValueError):
            return left == right


def record_fork_join_result(
    state: dict[str, Any],
    result: ForkJoinResult,
) -> None:
    """Append a fork/join result without exposing branch mutation to callers."""
    history = state.get("fork_join_results") or []
    history.append(result.model_dump())
    state["fork_join_results"] = history
