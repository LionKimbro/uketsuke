import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from uketsuke import jobs, paths, startup
from uketsuke_dev_harness import make_configuration


class JobsTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        configuration = make_configuration(root / "inbox", root / "work-space")
        startup.initialize_program_at_startup_time_once(configuration)

        self.job = {
            "request-file-path": str(paths.path("working") / "opaque-request-file"),
            "status": "claimed",
            "completion-status": None,
            "request-id": "request-1",
            "error": None,
            "history": [],
        }
        paths.path("job").write_text(json.dumps(self.job), encoding="utf-8")
        jobs.read_the_current_active_job_if_there_is_one()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_append_result_records_a_durable_history_entry(self):
        jobs.append_result("claimed", "ok", [])

        saved_job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        history_entry = saved_job["history"][-1]
        self.assertEqual(history_entry["operation"], "claimed")
        self.assertEqual(history_entry["result"], "ok")
        self.assertIsNone(history_entry["error"])
        self.assertEqual(saved_job["error"], None)
        self.assertFalse(paths.path("job-nextstate").exists())

    def test_append_result_captures_the_active_exception_trace(self):
        try:
            raise ValueError("broken request")
        except ValueError:
            jobs.append_result("dispatch", "failed", ["error"])

        saved_job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        history_entry = saved_job["history"][-1]
        self.assertIn("ValueError: broken request", history_entry["error"])
        self.assertEqual(saved_job["error"], history_entry["error"])

    def test_read_the_current_active_job_sets_none_when_the_job_is_absent(self):
        paths.path("job").unlink()

        jobs.read_the_current_active_job_if_there_is_one()

        self.assertIsNone(jobs.g["job"])


if __name__ == "__main__":
    unittest.main()
