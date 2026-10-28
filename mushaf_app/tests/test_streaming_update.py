import ast
import sys
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))


class StreamingUpdateSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (APP / "main.py").read_text(encoding="utf-8")
        tree = ast.parse(cls.source)
        window = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Main")
        cls.methods = {
            node.name: node
            for node in window.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def calls(self, method, attribute):
        return [
            node
            for node in ast.walk(self.methods[method])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == attribute
        ]

    def test_payload_is_opened_as_part_file_and_bounded_buffer_is_used(self):
        self.assertIn("download_update", self.methods)
        self.assertTrue(self.calls("download_update", "open"))
        self.assertTrue(self.calls("download_update", "setReadBufferSize"))
        self.assertIn("readyRead.connect", ast.unparse(self.methods["download_update"]))

    def test_ready_read_writes_and_hashes_incremental_chunks(self):
        method = self.methods["_update_ready_read"]
        text = ast.unparse(method)
        self.assertIn("reply.readAll()", text)
        self.assertIn("state['file'].write(chunk)", text)
        self.assertIn("state['hasher'].update(chunk)", text)
        self.assertIn("state['size'] += len(chunk)", text)

    def test_finished_handler_does_not_materialize_payload(self):
        method = self.methods["_update_downloaded"]
        # readAll is allowed only in the bounded readyRead handler, never in the
        # completion handler where it previously materialized the whole AppImage.
        self.assertFalse(self.calls("_update_downloaded", "readAll"))
        text = ast.unparse(method)
        self.assertIn("os.fsync", text)
        self.assertIn("state['hasher'].hexdigest()", text)
        self.assertIn("state['temp'].unlink", text)

    def test_window_close_aborts_and_removes_partial_file(self):
        text = ast.unparse(self.methods["closeEvent"])
        self.assertIn("abort()", text)
        self.assertIn("unlink(missing_ok=True)", text)


if __name__ == "__main__":
    unittest.main()
