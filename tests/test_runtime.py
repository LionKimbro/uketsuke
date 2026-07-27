import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from uketsuke import paths, runtime, startup, state
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
            '{"request-id": "request-1"}',
            encoding="utf-8",
        )

        self.assertTrue(runtime.do_tick())

        job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "claimed")
        self.assertEqual(job["request-id"], "request-1")
        self.assertEqual(job["request-original-filename"], "request.json")
        self.assertNotIn("reply-to", job)
        self.assertFalse(request.exists())
        self.assertTrue(older_request.exists())
        self.assertTrue(paths.path("opaque-request-file").exists())
        self.assertEqual(runtime.panel["last-operation"], "claim-inbox-request")

    def test_tick_reports_idle_when_there_is_no_work(self):
        self.assertTrue(runtime.do_tick())

        self.assertEqual(runtime.g["operation"], "idle")
        self.assertEqual(runtime.panel["last-operation"], "idle")

    def test_ticks_execute_report_then_retire_a_claimed_job(self):
        request = paths.path("inbox") / "request.json"
        request.write_text(
            '{"request-id": "request-1"}',
            encoding="utf-8",
        )
        runtime.do_tick()

        self.assertTrue(runtime.do_tick())

        job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "executed")
        self.assertEqual(job["completion-status"], "success")
        self.assertIn("response", job)
        self.assertEqual(
            [entry["operation"] for entry in job["history"][-2:]],
            ["prepare-dispatch", "dispatch-job"],
        )
        self.assertEqual(runtime.panel["last-result"], "dispatch-succeeded")

        self.assertTrue(runtime.do_tick())
        done_job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        self.assertEqual(done_job["status"], "done")
        self.assertEqual(done_job["history"][-1]["operation"], "send-job-reply")
        self.assertEqual(runtime.panel["last-result"], "reply-succeeded")

        self.assertTrue(runtime.do_tick())
        self.assertFalse(paths.path("job").exists())
        self.assertFalse(paths.path("opaque-request-file").exists())
        done_jobs = list(paths.path("done").glob("job-*.json"))
        done_requests = list(paths.path("done").glob("job-*-original-request"))
        self.assertEqual(len(done_jobs), 1)
        self.assertEqual(len(done_requests), 1)
        archived_job = json.loads(done_jobs[0].read_text(encoding="utf-8"))
        self.assertEqual(archived_job["status"], "done")
        self.assertEqual(archived_job["history"][-1]["operation"], "retire-done-job")
        self.assertEqual(done_requests[0].read_bytes(), b'{"request-id": "request-1"}')
        timestamp = done_jobs[0].stem.removeprefix("job-")
        self.assertEqual(done_requests[0].name, f"job-{timestamp}-original-request")
        self.assertEqual(runtime.panel["last-operation"], "retire-done-job")

    def test_tick_executes_every_claimed_job_to_executed(self):
        (paths.path("inbox") / "request.json").write_text(
            '{"request-id": "request-1"}', encoding="utf-8"
        )
        runtime.do_tick()

        self.assertTrue(runtime.do_tick())

        job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "executed")
        self.assertEqual(job["completion-status"], "success")

    def test_tick_records_a_dispatch_error_in_a_claimed_job(self):
        def dispatch_job(job):
            raise RuntimeError("dispatcher broke")

        state.configuration["host-functions"]["dispatch-job"] = dispatch_job
        (paths.path("inbox") / "request.json").write_text(
            '{"request-id": "request-1"}',
            encoding="utf-8",
        )
        runtime.do_tick()

        self.assertTrue(runtime.do_tick())

        job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "executed")
        self.assertEqual(job["completion-status"], "fail")
        self.assertNotIn("response", job)
        self.assertIn("RuntimeError: dispatcher broke", job["error"])
        self.assertEqual(job["history"][-1]["operation"], "dispatch-job")
        self.assertIn("RuntimeError: dispatcher broke", runtime.panel["last-error"])

    def test_tick_records_a_reply_error_and_leaves_the_job_executed(self):
        def send_reply(job):
            raise RuntimeError("reply sender broke")

        state.configuration["host-functions"]["send-reply"] = send_reply
        (paths.path("inbox") / "request.json").write_text(
            '{"request-id": "request-1"}', encoding="utf-8"
        )
        runtime.do_tick()
        runtime.do_tick()

        self.assertTrue(runtime.do_tick())

        job = json.loads(paths.path("job").read_text(encoding="utf-8"))
        self.assertEqual(job["status"], "executed")
        self.assertIn("RuntimeError: reply sender broke", job["error"])
        self.assertEqual(job["history"][-1]["operation"], "send-job-reply")
        self.assertIn("RuntimeError: reply sender broke", runtime.panel["last-error"])

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
        self.assertEqual(dead_letter_requests[0].read_bytes(), b"not json")
        timestamp = dead_letter_jobs[0].stem.removeprefix("job-")
        self.assertEqual(
            dead_letter_requests[0].name,
            f"job-{timestamp}-original-request",
        )
        self.assertEqual(runtime.panel["last-operation"], "complete-dead-letter-transition")

    def test_dead_letter_completion_tolerates_a_missing_working_request(self):
        (paths.path("inbox") / "broken.json").write_bytes(b"not json")
        runtime.do_tick()
        paths.path("opaque-request-file").unlink()

        self.assertTrue(runtime.do_tick())

        self.assertFalse(paths.path("job").exists())
        self.assertEqual(len(list(paths.path("dead-letter").glob("job-*.json"))), 1)

    def test_tick_returns_false_after_quit(self):
        runtime.transition_to_the_quit_state()

        self.assertFalse(runtime.do_tick())
        self.assertTrue(runtime.panel["quit"])


if __name__ == "__main__":
    unittest.main()
