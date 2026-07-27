from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from uketsuke import state
from uketsuke_dev_harness import make_configuration


class StateTests(unittest.TestCase):
    def test_configuration_rejects_a_missing_required_value(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            configuration = make_configuration(root / "inbox", root / "work-space")
            del configuration["host-functions"]["dispatch-job"]

            with self.assertRaisesRegex(ValueError, "host-functions.dispatch-job"):
                state.initialize_configuration_when_the_program_starts_up(
                    configuration
                )


if __name__ == "__main__":
    unittest.main()
