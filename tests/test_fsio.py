from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from uketsuke import fsio, paths, startup
from uketsuke_dev_harness import make_configuration


class Fsiotests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        startup.initialize_program_at_startup_time_once(
            make_configuration(root / "inbox", root / "work-space")
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_list_files_returns_only_immediate_files(self):
        inbox = paths.path("inbox")
        (inbox / "b.json").write_text("b", encoding="utf-8")
        (inbox / "a.json").write_text("a", encoding="utf-8")
        (inbox / "nested").mkdir()
        (inbox / "nested" / "hidden.json").write_text("hidden", encoding="utf-8")

        files = fsio.list_files(inbox)

        self.assertEqual(files, [inbox / "a.json", inbox / "b.json"])


if __name__ == "__main__":
    unittest.main()
