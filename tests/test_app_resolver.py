import json
import unittest
from unittest.mock import MagicMock, patch
from app.windows.apps import WindowsAppCatalog


class TestAppResolver(unittest.TestCase):
    def setUp(self):
        self.catalog = WindowsAppCatalog()

    def test_builtin_apps_resolved(self):
        # VS Code
        res = self.catalog.find_executable("vscode")
        self.assertIsNotNone(res)
        target, app_type = res
        self.assertIn(app_type, ["exe", "system"])

        # Notepad
        res = self.catalog.find_executable("notepad")
        self.assertIsNotNone(res)

        # Calculator
        res = self.catalog.find_executable("calculator")
        self.assertIsNotNone(res)

    def test_homophone_and_fuzzy_resolution(self):
        # User says "post grey sql" -> mapped to postgresql
        res = self.catalog.find_executable("post grey sql")
        self.assertIsNotNone(res)

        # User says "vs code"
        res = self.catalog.find_executable("vs code")
        self.assertIsNotNone(res)

        # User says "brave browser"
        res = self.catalog.find_executable("brave browser")
        self.assertIsNotNone(res)

    def test_disk_cache_io(self):
        cache_path = self.catalog._cache_file
        self.assertTrue(cache_path.parent.exists())

        # Test injecting into catalog and saving/loading
        with self.catalog._lock:
            self.catalog._catalog["testapp"] = {
                "name": "TestApp",
                "type": "exe",
                "target": "C:\\test\\testapp.exe",
                "aliases": ["testapp", "test app"]
            }
        self.catalog._save_cache()
        self.assertTrue(cache_path.exists())

        # Re-read cache
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        self.assertIn("testapp", raw)
        self.assertEqual(raw["testapp"]["name"], "TestApp")

        # Lookup testapp
        res = self.catalog.find_executable("test app")
        self.assertIsNotNone(res)
        target, app_type = res
        self.assertEqual(target, "C:\\test\\testapp.exe")

    def test_open_or_activate_mocked(self):
        with patch.object(self.catalog, "find_executable", return_value=("notepad.exe", "system")):
            with patch("subprocess.Popen") as mock_popen:
                msg = self.catalog.open_or_activate("notepad")
                self.assertIn("Opening notepad", msg)
                mock_popen.assert_called_once()

    def test_close_app_mocked(self):
        # Calling close on non-running app
        msg = self.catalog.close_app("non_existent_fake_app_xyz")
        self.assertIn("No open windows found", msg)


if __name__ == "__main__":
    unittest.main()
