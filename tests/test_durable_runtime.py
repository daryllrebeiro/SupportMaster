import tempfile
import time
import unittest
from pathlib import Path

from supportmaster.models.durable_task import DurableTask
from supportmaster.persistence import SQLiteRunStore
from supportmaster.runtime import DurableTaskWorker
from supportmaster.workflow_state import SupportMasterState


class DurableRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SQLiteRunStore(Path(self.temp_dir.name) / "runs.db")
        self.store.create_run(SupportMasterState(run_id="run-1"))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_enqueue_is_idempotent_and_checkpoint_is_durable(self) -> None:
        first = self.store.enqueue_task(
            "run-1",
            task_name="investigation",
            idempotency_key="run-1:investigation",
            payload={"ticket": "SUP-4821"},
        )
        duplicate = self.store.enqueue_task(
            "run-1",
            task_name="investigation",
            idempotency_key="run-1:investigation",
            payload={"ticket": "changed-but-not-replaced"},
        )
        self.assertEqual(first.task_id, duplicate.task_id)

        claimed = self.store.claim_next_task("worker-a", lease_seconds=3)
        assert claimed is not None
        checkpoint = self.store.checkpoint_task(
            claimed.task_id,
            "worker-a",
            {"stage": "evidence", "cursor": 2},
        )
        self.assertEqual(checkpoint.sequence, 1)
        self.assertTrue(self.store.heartbeat_task(claimed.task_id, "worker-a", lease_seconds=3))
        self.store.complete_task(claimed.task_id, "worker-a", {"status": "done"})

        self.assertEqual(self.store.get_task(claimed.task_id).status, "SUCCEEDED")
        self.assertEqual(self.store.list_task_checkpoints(claimed.task_id)[0].payload["cursor"], 2)

    def test_worker_retries_then_completes_with_idempotent_task(self) -> None:
        task = self.store.enqueue_task(
            "run-1",
            task_name="retryable",
            idempotency_key="run-1:retryable",
            max_attempts=2,
        )
        worker = DurableTaskWorker(
            self.store,
            worker_id="worker-a",
            lease_seconds=3,
            heartbeat_interval_seconds=1,
            max_backoff_seconds=0,
        )
        calls = 0

        def handler(current: DurableTask, cancel):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("temporary connector failure")
            return {"attempt": current.attempt_count}

        first = worker.run_once(handler)
        assert first is not None
        self.assertEqual(first.outcome, "RETRY_WAIT")
        second = worker.run_once(handler)
        assert second is not None
        self.assertEqual(second.outcome, "SUCCEEDED")
        self.assertEqual(self.store.get_task(task.task_id).attempt_count, 2)

    def test_pause_resume_and_cancel_are_cooperative(self) -> None:
        pause_task = self.store.enqueue_task(
            "run-1",
            task_name="pausable",
            idempotency_key="run-1:pausable",
            max_attempts=1,
        )
        worker = DurableTaskWorker(self.store, worker_id="worker-p", lease_seconds=3, heartbeat_interval_seconds=1)

        def pause_handler(task: DurableTask, cancel):
            self.store.pause_run("run-1", reason="operator review")
            return {"checkpoint": True}

        paused = worker.run_once(pause_handler)
        assert paused is not None
        self.assertEqual(paused.outcome, "PAUSED")
        self.assertEqual(self.store.get_task(pause_task.task_id).status, "RETRY_WAIT")

        self.store.resume_durable_run("run-1")
        resumed = worker.run_once(lambda task, cancel: {"resumed": True})
        assert resumed is not None
        self.assertEqual(resumed.outcome, "SUCCEEDED")

        cancel_task = self.store.enqueue_task(
            "run-1",
            task_name="cancelled",
            idempotency_key="run-1:cancelled",
            max_attempts=1,
        )

        def cancel_handler(task: DurableTask, cancel):
            self.store.request_cancel("run-1", reason="operator stop")
            return {"should_not_publish": True}

        cancelled = worker.run_once(cancel_handler)
        assert cancelled is not None
        self.assertEqual(cancelled.outcome, "CANCELLED")
        self.assertEqual(self.store.get_task(cancel_task.task_id).status, "CANCELLED")

    def test_replay_plan_is_read_only(self) -> None:
        self.store.append_event("run-1", "ADK_EVENT", {"author": "ticket_agent"})
        plan = self.store.replay_run("run-1")
        self.assertTrue(plan.dry_run)
        self.assertFalse(plan.mutating_replay_allowed)
        self.assertGreaterEqual(len(plan.event_sequences), 2)
        self.assertEqual(self.store.get_run_control("run-1").status, "RUNNABLE")

    def test_expired_lease_is_reclaimed_by_another_worker(self) -> None:
        task = self.store.enqueue_task(
            "run-1",
            task_name="recoverable",
            idempotency_key="run-1:recoverable",
            max_attempts=2,
        )
        first = self.store.claim_next_task("worker-a", lease_seconds=1)
        assert first is not None
        time.sleep(1.05)
        second = self.store.claim_next_task("worker-b", lease_seconds=1)
        assert second is not None
        self.assertEqual(second.task_id, task.task_id)
        self.assertEqual(second.attempt_count, 2)


if __name__ == "__main__":
    unittest.main()
