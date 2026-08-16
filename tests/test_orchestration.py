import threading
import time
import unittest

from supportmaster.orchestration import ForkGroupSpec, ForkJoinExecutor, TaskSpec


class ForkJoinExecutorTests(unittest.TestCase):
    def test_independent_branches_are_bounded_and_joined(self) -> None:
        lock = threading.Lock()
        active = 0
        peak = 0

        def handler(state, cancel):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.03)
            with lock:
                active -= 1
            return {"completed": state["ticket_id"]}

        group = ForkGroupSpec(
            name="investigation",
            max_concurrency=2,
            tasks=[TaskSpec(name=f"branch_{index}") for index in range(4)],
        )
        result = ForkJoinExecutor(max_concurrency=2).run(
            group,
            {"ticket_id": "SUP-4821"},
            {task.name: handler for task in group.tasks},
        )

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(peak, 2)
        self.assertEqual(len(result.branches), 4)
        self.assertEqual(result.merged_output["completed"], "SUP-4821")

    def test_required_failure_blocks_join_and_optional_failure_is_partial(self) -> None:
        group = ForkGroupSpec(
            name="failure-policy",
            tasks=[
                TaskSpec(name="required"),
                TaskSpec(name="optional", required=False),
            ],
        )

        def fail(state, cancel):
            raise RuntimeError("connector unavailable")

        result = ForkJoinExecutor().run(
            group,
            {},
            {"required": fail, "optional": lambda state, cancel: {"ok": True}},
        )
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.missing_required, ["required"])

        optional_group = ForkGroupSpec(
            name="optional-only",
            tasks=[TaskSpec(name="optional", required=False)],
        )
        partial = ForkJoinExecutor().run(
            optional_group,
            {},
            {"optional": fail},
        )
        self.assertEqual(partial.status, "PARTIAL")

    def test_conflicting_outputs_are_withheld(self) -> None:
        group = ForkGroupSpec(
            name="conflict",
            tasks=[TaskSpec(name="a"), TaskSpec(name="b")],
        )
        result = ForkJoinExecutor().run(
            group,
            {},
            {"a": lambda state, cancel: {"answer": "one"}, "b": lambda state, cancel: {"answer": "two"}},
        )
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.conflicts, ["answer"])
        self.assertNotIn("answer", result.merged_output)

    def test_timeout_is_recorded_and_dependency_is_skipped(self) -> None:
        group = ForkGroupSpec(
            name="timeout",
            timeout_seconds=0.2,
            tasks=[
                TaskSpec(name="slow", timeout_seconds=0.02),
                TaskSpec(name="dependent", dependencies=["slow"]),
            ],
        )
        result = ForkJoinExecutor().run(
            group,
            {},
            {
                "slow": lambda state, cancel: (time.sleep(0.1), {"done": True})[1],
                "dependent": lambda state, cancel: {"should_not": "run"},
            },
        )
        statuses = {branch.task_name: branch.status for branch in result.branches}
        self.assertEqual(statuses["slow"], "TIMED_OUT")
        self.assertEqual(statuses["dependent"], "SKIPPED")
        self.assertEqual(result.status, "BLOCKED")

    def test_mutating_tasks_are_rejected(self) -> None:
        group = ForkGroupSpec(name="unsafe", tasks=[TaskSpec(name="write", read_only=False)])
        with self.assertRaises(ValueError):
            ForkJoinExecutor().run(group, {}, {"write": lambda state, cancel: {}})


if __name__ == "__main__":
    unittest.main()
