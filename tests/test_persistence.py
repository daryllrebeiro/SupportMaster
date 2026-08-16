import tempfile
import unittest
from pathlib import Path

from supportmaster.models.human_review import HumanReviewTask
from supportmaster.persistence import ConcurrentUpdateError, SQLiteRunStore
from supportmaster.workflow_state import SupportMasterState


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SQLiteRunStore(Path(self.temp_dir.name) / "runs.db")
        self.state = SupportMasterState(run_id="run-1")
        self.store.create_run(self.state)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_snapshot_round_trip_and_optimistic_versioning(self) -> None:
        snapshot = self.store.load_snapshot("run-1")
        self.assertEqual(snapshot.version, 0)

        self.state.current_stage = "INVESTIGATION"
        saved = self.store.save_state(self.state, expected_version=0)
        self.assertEqual(saved.version, 1)
        self.assertEqual(self.store.load_state("run-1").current_stage, "INVESTIGATION")

        with self.assertRaises(ConcurrentUpdateError):
            self.store.save_state(self.state, expected_version=0)

    def test_events_are_append_only_and_ordered(self) -> None:
        self.store.append_event("run-1", "TEST_EVENT", {"value": "one"})
        self.store.append_event("run-1", "TEST_EVENT", {"value": "two"})

        events = self.store.list_events("run-1")
        self.assertEqual([event.event_type for event in events], ["RUN_CREATED", "TEST_EVENT", "TEST_EVENT"])
        self.assertEqual(events[-1].payload["value"], "two")

    def test_review_task_requires_token_and_scoped_approval_to_resume(self) -> None:
        task, token = self.store.create_review_task(
            "run-1",
            reason="Publish requires human approval.",
            blocking_reasons=["PRODUCTION_ACTION_REQUIRES_HUMAN_APPROVAL"],
            required_actions=["Approve publication."],
            evidence_keys=["publish_plan"],
            allowed_scopes=["PUBLISH"],
            resume_condition="A reviewer approves publication.",
        )
        self.assertEqual(self.store.load_state("run-1").terminal_outcome, "PAUSED_FOR_HUMAN_REVIEW")

        with self.assertRaises(ValueError):
            self.store.decide_review_task(
                task.task_id,
                reviewer="alice",
                decision="APPROVE",
                resume_token="wrong-token",
                approved_scopes=["PUBLISH"],
            )

        approved = self.store.decide_review_task(
            task.task_id,
            reviewer="alice",
            decision="APPROVE",
            resume_token=token,
            approved_scopes=["PUBLISH"],
            comment="Reviewed the publication scope.",
        )
        self.assertEqual(approved.status, "APPROVED")

        resumed = self.store.resume_run("run-1", task.task_id, token)
        self.assertIsNone(resumed.pending_human_review)
        self.assertIsNone(resumed.terminal_outcome)
        self.assertEqual(len(resumed.human_review_history), 1)
        self.assertEqual(resumed.authorizations[0].scope, "PUBLISH")
        self.assertEqual(resumed.authorizations[0].human_approval_id, approved.decision.decision_id)
        self.assertEqual(self.store.get_review_task(task.task_id).status, "RESUMED")

    def test_approval_cannot_escalate_beyond_task_scope(self) -> None:
        task, token = self.store.create_review_task(
            "run-1",
            reason="Implementation review.",
            allowed_scopes=["IMPLEMENTATION"],
            resume_condition="Implementation approved.",
        )

        with self.assertRaises(ValueError):
            self.store.decide_review_task(
                task.task_id,
                reviewer="alice",
                decision="APPROVE",
                resume_token=token,
                approved_scopes=["PUBLISH"],
            )


if __name__ == "__main__":
    unittest.main()
