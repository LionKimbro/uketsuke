import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from uketsuke import paths, runtime, startup
from uketsuke_dev_harness import make_configuration


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        configuration = make_configuration(
            self.root / "inbox",
            self.root / "work-space",
        )
        startup.initialize_program_at_startup_time_once(configuration)
        runtime.g["operation"] = None
        runtime.g["quit"] = False
        runtime.panel.update(
            {
                "turn-count": 0,
                "last-operation": None,
                "last-result": None,
                "last-error": None,
                "quit": False,
            }
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_tick_claims_the_most_recent_valid_inbox_request(self):
        older_request = paths.path("inbox") / "older.json"
        older_request.write_text('{"request-id": "older"}', encoding="utf-8")
        os.utime(older_request, (1, 1))
        request = paths.path("inbox") / "request.json"
        request.write_text(
            '{"request-id": "request-1", "reply-to": "reply.json"}',
            encoding="utf-8",
        )

        self.assertTrue(runtime.do_tick())

        job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "claimed")
        self.assertEqual(job["request-id"], "request-1")
        self.assertEqual(job["request-original-filename"], "request.json")
        self.assertEqual(job["reply-to"], "reply.json")
        self.assertFalse(request.exists())
        self.assertTrue(older_request.exists())
        self.assertTrue(paths.path("opaque-request-file").exists())
        self.assertEqual(runtime.panel["last-operation"], "claim-inbox-request")

    def test_tick_reports_idle_when_there_is_no_work(self):
        self.assertTrue(runtime.do_tick())

        self.assertEqual(runtime.g["operation"], "idle")
        self.assertEqual(runtime.panel["last-operation"], "idle")

    def test_ticks_move_an_unrecognizable_request_to_dead_letter(self):
        request = paths.path("inbox") / "broken.json"
        request.write_bytes(b"not json")

        self.assertTrue(runtime.do_tick())
        self.assertEqual(runtime.panel["last-operation"], "claim-inbox-request")
        self.assertFalse(request.exists())

        self.assertTrue(runtime.do_tick())

        self.assertFalse(paths.path("job").exists())
        self.assertFalse(paths.path("opaque-request-file").exists())
        dead_letter_jobs = list(paths.path("dead-letter").glob("job-*.json"))
        dead_letter_requests = list(
            paths.path("dead-letter").glob("job-*-original-request")
        )
        self.assertEqual(len(dead_letter_jobs), 1)
        self.assertEqual(len(dead_letter_requests), 1)
        dead_letter_job = json.loads(dead_letter_jobs[0].read_text(encoding="utf-8"))
        self.assertEqual(
            dead_letter_job["status"], "transferred-to-dead-letter-directory"
        )
        self.assertEqual(dead_letter_job["request-id"], None)
        self.assertEqual(runtime.panel["last-operation"], "complete-dead-letter-transition")


if __name__ == "__main__":
    unittest.main()
