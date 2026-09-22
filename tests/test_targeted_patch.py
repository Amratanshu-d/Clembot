import shutil
import tempfile
import unittest
from pathlib import Path

from app.editor.code_patch_engine import CodePatchEngine, TargetedPatch


class TestTargetedPatchEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="clembot_test_patch_"))
        self.engine = CodePatchEngine()

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_read_and_write_file_preserving_eol(self):
        # Test CRLF
        crlf_file = self.temp_dir / "crlf.py"
        crlf_bytes = b"def foo():\r\n    return 42\r\n"
        crlf_file.write_bytes(crlf_bytes)

        text, eol = self.engine.read_file_with_eol(crlf_file)
        self.assertEqual(eol, "\r\n")
        self.assertIn("def foo()", text)

        updated_text = "def foo():\n    return 100\n"
        self.engine.write_file_preserving_eol(crlf_file, updated_text, eol)
        written_bytes = crlf_file.read_bytes()
        self.assertIn(b"\r\n", written_bytes)
        self.assertNotIn(b"[^\r]\n", written_bytes)

    def test_locate_target_block_exact(self):
        source = "def one():\n    pass\n\ndef two():\n    return True\n"
        target = "def two():\n    return True"
        start, end = self.engine.locate_target_block(source, target)
        self.assertNotEqual(start, -1)
        self.assertEqual(source[start:end], target)

    def test_locate_target_block_whitespace_tolerance(self):
        source = "def add(a, b):\n    return a + b\n"
        # Target with different indentation spacing
        target = "def add(a, b):\n  return a + b"
        start, end = self.engine.locate_target_block(source, target)
        self.assertNotEqual(start, -1)

    def test_locate_target_block_line_hint(self):
        source = (
            "# duplicate blocks\n"
            "x = 1\n"
            "print(x)\n\n"
            "# second instance\n"
            "x = 1\n"
            "print(x)\n"
        )
        target = "x = 1\nprint(x)"
        # Line hint near line 6 should pick second instance
        start, end = self.engine.locate_target_block(source, target, line_hint=6)
        self.assertNotEqual(start, -1)
        self.assertGreater(start, 25)

    def test_validate_syntax_python_valid_and_invalid(self):
        valid_py = "def hello():\n    print('hi')\n"
        ok, err = self.engine.validate_syntax(valid_py, "hello.py")
        self.assertTrue(ok)
        self.assertIsNone(err)

        invalid_py = "def broken(:\n    print('error')\n"
        ok, err = self.engine.validate_syntax(invalid_py, "broken.py")
        self.assertFalse(ok)
        self.assertIsNotNone(err)

    def test_validate_syntax_brackets(self):
        valid_js = "function test() { if (true) { return [1, 2]; } }"
        ok, err = self.engine.validate_syntax(valid_js, "app.js")
        self.assertTrue(ok)

        invalid_js = "function test() { if (true) { return [1, 2; }"
        ok, err = self.engine.validate_syntax(invalid_js, "app.js")
        self.assertFalse(ok)

    def test_apply_patch_replace_success(self):
        test_file = self.temp_dir / "math_ops.py"
        test_file.write_text("def multiply(a, b):\n    return a * b\n", encoding="utf-8")

        patch = TargetedPatch(
            file_path=test_file,
            target_code="return a * b",
            replacement_code="return float(a * b)",
            explanation="Cast multiplication result to float",
            patch_action="replace"
        )

        success, msg, diff = self.engine.apply_patch(patch)
        self.assertTrue(success)
        self.assertIn("+    return float(a * b)", diff)
        self.assertIn("-    return a * b", diff)

        content = test_file.read_text(encoding="utf-8")
        self.assertIn("float(a * b)", content)
        self.assertTrue(test_file.with_suffix(".py.bak").is_file())

    def test_apply_patch_insert_before(self):
        test_file = self.temp_dir / "service.py"
        test_file.write_text("def run():\n    execute()\n", encoding="utf-8")

        patch = TargetedPatch(
            file_path=test_file,
            target_code="def run():",
            replacement_code="import logging\n\n",
            explanation="Add logging import",
            patch_action="insert_before"
        )

        success, msg, diff = self.engine.apply_patch(patch)
        self.assertTrue(success)
        content = test_file.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("import logging\n\ndef run():"))

    def test_apply_patch_insert_after(self):
        test_file = self.temp_dir / "views.py"
        test_file.write_text("def view():\n    return 'ok'\n", encoding="utf-8")

        patch = TargetedPatch(
            file_path=test_file,
            target_code="def view():\n    return 'ok'",
            replacement_code="\n\ndef health():\n    return 'healthy'",
            explanation="Add health check endpoint",
            patch_action="insert_after"
        )

        success, msg, diff = self.engine.apply_patch(patch)
        self.assertTrue(success)
        content = test_file.read_text(encoding="utf-8")
        self.assertIn("def health():", content)

    def test_apply_patch_delete(self):
        test_file = self.temp_dir / "clean.py"
        test_file.write_text("import pdb\n\ndef work():\n    pass\n", encoding="utf-8")

        patch = TargetedPatch(
            file_path=test_file,
            target_code="import pdb\n",
            replacement_code="",
            explanation="Remove pdb import",
            patch_action="delete"
        )

        success, msg, diff = self.engine.apply_patch(patch)
        self.assertTrue(success)
        content = test_file.read_text(encoding="utf-8")
        self.assertNotIn("import pdb", content)

    def test_apply_patch_syntax_error_rollback(self):
        test_file = self.temp_dir / "safety.py"
        initial_content = "def calculate(x):\n    return x * 2\n"
        test_file.write_text(initial_content, encoding="utf-8")

        # Introduce broken syntax
        patch = TargetedPatch(
            file_path=test_file,
            target_code="return x * 2",
            replacement_code="return x * (",
            explanation="Intentional broken syntax",
            patch_action="replace"
        )

        success, msg, diff = self.engine.apply_patch(patch)
        self.assertFalse(success)
        self.assertIn("syntax error", msg.lower())
        # Verify file rolled back to untouched original
        content = test_file.read_text(encoding="utf-8")
        self.assertEqual(content, initial_content)

    def test_undo_last_patch(self):
        test_file = self.temp_dir / "undo_test.py"
        orig = "val = 10\n"
        test_file.write_text(orig, encoding="utf-8")

        patch = TargetedPatch(
            file_path=test_file,
            target_code="val = 10",
            replacement_code="val = 20",
            explanation="Change value to 20",
        )

        success, _, _ = self.engine.apply_patch(patch)
        self.assertTrue(success)
        self.assertIn("val = 20", test_file.read_text(encoding="utf-8"))

        undo_ok, undo_msg = self.engine.undo_last_patch(test_file)
        self.assertTrue(undo_ok)
        self.assertEqual(test_file.read_text(encoding="utf-8"), orig)


if __name__ == "__main__":
    unittest.main()
