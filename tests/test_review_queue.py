import tempfile
import unittest
from pathlib import Path

from supportmaster.persistence import SQLiteRunStore
from supportmaster.review_queue import ReviewQueueService
from supportmaster.workflow_state import SupportMasterState


class ReviewQueueTests(unittest.TestCase):
    def test_queue_is_tenant_scoped_and_counts_open_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteRunStore(Path(directory) / "runs.db")
            state = SupportMasterState(run_id="run-a", tenant_id="tenant-a")
            store.create_run(state)
            store.create_review_task(state.run_id, reason="Approval required", resume_condition="Approve", ttl_seconds=60)
            other = SupportMasterState(run_id="run-b", tenant_id="tenant-b")
            store.create_run(other)
            store.create_review_task(other.run_id, reason="Other approval", resume_condition="Approve", ttl_seconds=60)
            snapshot = ReviewQueueService(store).snapshot("tenant-a")
        self.assertEqual(snapshot.open_count, 1)
        self.assertEqual(len(snapshot.tasks), 1)
        self.assertEqual(snapshot.tasks[0].reason, "Approval required")

    def test_metrics_report_review_outcomes_without_cross_tenant_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteRunStore(Path(directory) / "runs.db")
            state = SupportMasterState(run_id="run-a", tenant_id="tenant-a")
            store.create_run(state)
            task, token = store.create_review_task(state.run_id, reason="Approval required", resume_condition="Approve", ttl_seconds=60)
            store.decide_review_task(task.task_id, reviewer="operator", decision="REJECT", resume_token=token)
            metrics = ReviewQueueService(store).metrics("tenant-a")
        self.assertEqual(metrics.total, 1)
        self.assertEqual(metrics.rejections, 1)
        self.assertEqual(metrics.approvals, 0)
        self.assertEqual(metrics.open_count, 0)


if __name__ == "__main__":
    unittest.main()
