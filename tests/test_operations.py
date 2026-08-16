import tempfile
import time
import unittest
from pathlib import Path

from supportmaster.operations import (
    CircuitBreaker,
    CircuitState,
    HealthReporter,
    RunAdmissionController,
    load_operation_settings,
)


class OperationsTests(unittest.TestCase):
    def test_admission_is_bounded_idempotent_and_released(self) -> None:
        controller = RunAdmissionController(max_active_runs=1)
        self.assertEqual(controller.admit("run-1").status, "ACCEPTED")
        self.assertEqual(controller.admit("run-1").status, "ACCEPTED")
        rejected = controller.admit("run-2")
        self.assertEqual(rejected.status, "REJECTED")
        self.assertTrue(controller.release("run-1"))
        self.assertEqual(controller.admit("run-2").status, "ACCEPTED")

    def test_circuit_breaker_opens_and_recovers(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=0.01)
        self.assertTrue(breaker.allow_request())
        breaker.record_failure()
        breaker.record_failure()
        self.assertEqual(breaker.state, CircuitState.OPEN)
        self.assertFalse(breaker.allow_request())
        time.sleep(0.02)
        self.assertEqual(breaker.state, CircuitState.HALF_OPEN)
        self.assertTrue(breaker.allow_request())
        breaker.record_success()
        self.assertEqual(breaker.state, CircuitState.CLOSED)

    def test_settings_are_validated_from_environment(self) -> None:
        settings = load_operation_settings({"SUPPORTMASTER_MAX_ACTIVE_RUNS": "7", "SUPPORTMASTER_CIRCUIT_RECOVERY_SECONDS": "2.5"})
        self.assertEqual(settings.max_active_runs, 7)
        self.assertEqual(settings.circuit_recovery_seconds, 2.5)
        with self.assertRaises(ValueError):
            load_operation_settings({"SUPPORTMASTER_MAX_ACTIVE_RUNS": "nope"})

    def test_health_report_checks_sqlite_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_db = Path(directory) / "run.db"
            session_db = Path(directory) / "session.db"
            reporter = HealthReporter(run_db=run_db, session_db=session_db)
            self.assertEqual(reporter.liveness().status, "LIVE")
            self.assertEqual(reporter.readiness().status, "READY")
            self.assertEqual(reporter.readiness().checks["run_store"], "ok")


if __name__ == "__main__":
    unittest.main()
