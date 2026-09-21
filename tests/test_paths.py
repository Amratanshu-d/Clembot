import unittest
from pathlib import Path
from app.filesystem.paths import WindowsPathResolver


class TestWindowsPathResolver(unittest.TestCase):
    def test_standard_folders_resolved(self):
        folders = WindowsPathResolver.get_standard_folders()
        self.assertIn("Desktop", folders)
        self.assertIn("Downloads", folders)
        self.assertIn("Documents", folders)
        self.assertTrue(folders["Desktop"].is_absolute())

    def test_resolve_standard_aliases(self):
        p_downloads = WindowsPathResolver.resolve_path("Downloads")
        self.assertTrue(str(p_downloads).lower().endswith("downloads"))

        p_desktop = WindowsPathResolver.resolve_path("Desktop")
        self.assertTrue(str(p_desktop).lower().endswith("desktop"))

    def test_resolve_subpath_in_folder(self):
        p = WindowsPathResolver.resolve_path("Projects on Desktop")
        self.assertTrue(str(p).lower().endswith("desktop\\projects") or str(p).lower().endswith("desktop/projects"))

    def test_available_drives(self):
        drives = WindowsPathResolver.get_available_drives()
        self.assertTrue(len(drives) > 0)
        self.assertIn("C:\\", [d.upper() for d in drives])


if __name__ == "__main__":
    unittest.main()
