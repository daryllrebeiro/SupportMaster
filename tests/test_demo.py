import tempfile
import unittest
from pathlib import Path

from supportmaster.demo import main, reset, run_demo, seed


class DemoTests(unittest.TestCase):
    def test_golden_path_is_repeatable_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "demo.db"
            first = run_demo(db)
            second = run_demo(db)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(second["status"], "PASS")
        names = {step["name"] for step in first["steps"]}
        self.assertTrue({"intake", "investigation", "resolution_gate"}.issubset(names))
        self.assertEqual(first["resolution_status"], "VERIFICATION_REQUIRED")

    def test_seed_and_reset_commands_are_scoped_to_demo_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "demo.db"
            self.assertEqual(main(["seed", "--db", str(db)]), 0)
            self.assertTrue(db.exists())
            self.assertEqual(main(["reset", "--db", str(db)]), 0)
            self.assertFalse(db.exists())


if __name__ == "__main__":
    unittest.main()
