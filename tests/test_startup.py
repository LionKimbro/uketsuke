import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from uketsuke import paths, startup
from uketsuke_dev_harness import make_configuration


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.configuration = make_configuration(
            self.root / "inbox",
            self.root / "work-space",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_startup_creates_the_directory_tree_and_configures_paths(self):
        startup.initialize_program_at_startup_time_once(self.configuration)

        expected_paths = {
            "inbox": self.root / "inbox",
            "work-space": self.root / "work-space",
            "working": self.root / "work-space" / "working",
            "done": self.root / "work-space" / "done",
            "dead-letter": self.root / "work-space" / "dead-letter",
            "job": self.root / "work-space" / "working" / "job.json",
            "job-nextstate": self.root / "work-space" / "working" / "job-nextstate.json",
        }

        for name, expected_path in expected_paths.items():
            self.assertEqual(paths.path(name), expected_path)

        for name in ["inbox", "work-space", "working", "done", "dead-letter"]:
            self.assertTrue(paths.path(name).is_dir())

    def test_startup_replaces_the_job_with_a_valid_staged_replacement(self):
        startup.initialize_program_at_startup_time_once(self.configuration)

        staged_job = {"status": "claimed", "request-id": "request-1"}
        paths.path("job-nextstate").write_text(json.dumps(staged_job), encoding="utf-8")

        startup.initialize_program_at_startup_time_once(self.configuration)

        self.assertEqual(
            paths.path("job").read_text(encoding="utf-8"),
            json.dumps(staged_job),
        )
        self.assertFalse(paths.path("job-nextstate").exists())

    def test_startup_discards_a_malformed_staged_replacement(self):
        startup.initialize_program_at_startup_time_once(self.configuration)

        paths.path("job-nextstate").write_bytes(b"{")

        startup.initialize_program_at_startup_time_once(self.configuration)

        self.assertFalse(paths.path("job-nextstate").exists())

    def test_startup_resets_an_interrupted_execution_for_reexecution(self):
        interrupted_job = {
            "status": "execution-attempted",
            "request-id": "request-1",
            "error": None,
            "history": [],
        }
        startup.initialize_program_at_startup_time_once(self.configuration)
        paths.path("job").write_text(json.dumps(interrupted_job), encoding="utf-8")

        startup.initialize_program_at_startup_time_once(self.configuration)

        repaired_job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        self.assertEqual(repaired_job["status"], "claimed")
        self.assertEqual(
            repaired_job["history"][-1]["operation"],
            "startup-repaired-interrupted-execution",
        )


if __name__ == "__main__":
    unittest.main()
