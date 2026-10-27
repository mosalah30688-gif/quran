import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import main as app_main  # noqa: E402


class StartupStreamTests(unittest.TestCase):
    def test_windowed_executable_without_console_gets_log_streams(self):
        original_stdout, original_stderr = sys.stdout, sys.stderr
        created_stream = None
        try:
            with tempfile.TemporaryDirectory() as temp:
                log_dir = Path(temp) / "UserData" / "logs"
                log_path = log_dir / "siraj-startup.log"
                sys.stdout = None
                sys.stderr = None
                with mock.patch.object(app_main, "cache_dir", return_value=log_dir) as cache:
                    created_stream = app_main.configure_runtime_streams()
                cache.assert_called_once_with("logs")
                self.assertIs(sys.stdout, created_stream)
                self.assertIs(sys.stderr, created_stream)
                created_stream.write("double-click startup diagnostic\n")
                created_stream.flush()
                self.assertIn("double-click startup diagnostic", log_path.read_text(encoding="utf-8"))
        finally:
            if created_stream is not None:
                created_stream.close()
            sys.stdout, sys.stderr = original_stdout, original_stderr


if __name__ == "__main__":
    unittest.main()
