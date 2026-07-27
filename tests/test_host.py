from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from uketsuke import host, state
from uketsuke_dev_harness import make_configuration


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        configuration = make_configuration(root / "inbox", root / "work-space")
        self.summary_calls = []
        self.dispatch_calls = []
        self.reply_calls = []

        def summarize_request(request_file_path):
            self.summary_calls.append(request_file_path)
            return "request-1"

        def dispatch_job(job):
            self.dispatch_calls.append(job)
            return {"result": "ok"}

        def send_reply(job):
            self.reply_calls.append(job)

        configuration["host-functions"] = {
            "summarize-request": summarize_request,
            "dispatch-job": dispatch_job,
            "send-reply": send_reply,
        }
        state.initialize_configuration_when_the_program_starts_up(configuration)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_host_delegates_to_the_configured_functions(self):
        request_path = Path("request.json")
        job = {"request-id": "request-1"}

        self.assertEqual(host.summarize_request(request_path), "request-1")
        self.assertEqual(host.dispatch_job(job), {"result": "ok"})
        self.assertIsNone(host.send_reply(job))
        self.assertEqual(self.summary_calls, [request_path])
        self.assertEqual(self.dispatch_calls, [job])
        self.assertEqual(self.reply_calls, [job])
