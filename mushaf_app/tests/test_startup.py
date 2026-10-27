import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import runtime as app_runtime  # noqa: E402


class StartupStreamTests(unittest.TestCase):
    def test_desktop_launch_without_console_gets_log_streams(self):
        original_stdout, original_stderr = sys.stdout, sys.stderr
        with tempfile.TemporaryDirectory() as temp:
            created_stream = None
            try:
                state_dir = Path(temp) / "state" / "siraj"
                log_path = state_dir / "logs" / app_runtime.STARTUP_LOG_NAME
                sys.stdout = None
                sys.stderr = None
                with mock.patch.object(app_runtime, "runtime_state_dir", return_value=state_dir):
                    created_stream = app_runtime.configure_runtime_streams()
                self.assertIs(sys.stdout, created_stream)
                self.assertIs(sys.stderr, created_stream)
                created_stream.write("AppImage desktop startup diagnostic\n")
                created_stream.flush()
                self.assertIn("AppImage desktop startup diagnostic", log_path.read_text(encoding="utf-8"))
            finally:
                if created_stream is not None:
                    created_stream.close()
                sys.stdout, sys.stderr = original_stdout, original_stderr


if __name__ == "__main__":
    unittest.main()
